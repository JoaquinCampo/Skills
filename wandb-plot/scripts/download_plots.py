#!/usr/bin/env python3
"""Download existing plot images from W&B run files.

This script downloads plot images that were logged to W&B during training,
which is faster than generating plots from raw data.
"""

import argparse
import logging
import sys
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from scripts.wandb_utils import (
    get_run,
    setup_logging,
    WandBAuthError,
    progress_wrap,
    resolve_output_dir,
    write_metadata_json,
)


def find_plot_files(run, patterns: Optional[List[str]] = None) -> List:
    """
    Find plot files in a run using multiple patterns.

    Args:
        run: W&B run object
        patterns: List of glob patterns to try (default: common image patterns)

    Returns:
        List of file objects matching the patterns
    """
    if patterns is None:
        # Try multiple common patterns
        patterns = [
            "media/images/*.png",
            "media/plots/*.png",
            "*.png",
            "media/images/*.jpg",
            "media/images/*.jpeg",
            "plots/*.png",
            "figures/*.png",
        ]

    all_files = []
    seen_names = set()

    for pattern in patterns:
        try:
            files = run.files(pattern=pattern)
            for file in files:
                # Avoid duplicates
                if file.name not in seen_names:
                    all_files.append(file)
                    seen_names.add(file.name)
        except Exception:
            # Pattern might not be supported or no files match
            continue

    return all_files


def download_plots(
    entity_project: str,
    run_id: str,
    pattern: Optional[str] = None,
    output_dir: Optional[str] = None,
    force: bool = False
) -> List[str]:
    """
    Download existing plot files from W&B run.

    Args:
        entity_project: Project in format "entity/project" or "project"
        run_id: Run ID or name
        pattern: Optional custom glob pattern (default: tries multiple patterns)
        output_dir: Optional custom output directory
        force: If True, re-download even if files exist

    Returns:
        List of downloaded file paths

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If run not found

    Example:
        >>> files = download_plots("my-org/my-project", "abc123")
        >>> print(f"Downloaded {len(files)} files")
    """
    logger = logging.getLogger(__name__)
    run = get_run(entity_project, run_id)

    # Find plot files
    if pattern:
        patterns = [pattern]
    else:
        patterns = None

    plot_files = find_plot_files(run, patterns)

    if not plot_files:
        return []

    # Determine output directory (only if there is work to do)
    output_path = resolve_output_dir(entity_project, run, output_dir=output_dir)

    # Download files
    downloaded_paths = []

    for file in progress_wrap(plot_files, "Downloading plots"):
        # Construct local path
        local_path = output_path / Path(file.name).name

        # Skip if exists and not forcing
        if local_path.exists() and not force:
            print(f"Skipping {file.name} (already exists)")
            logger.info("Skipping existing file %s", file.name)
            downloaded_paths.append(str(local_path))
            continue

        # Download file
        try:
            print(f"Downloading {file.name}...")
            logger.info("Downloading file %s", file.name)
            file.download(root=str(output_path), replace=force)

            # The file is downloaded to output_path/file.name structure
            # We need to handle the directory structure
            downloaded_file = output_path / file.name
            if downloaded_file.exists():
                final_path = output_path / Path(file.name).name
                if downloaded_file != final_path:
                    # Move file to flat structure
                    shutil.move(str(downloaded_file), str(final_path))
                    # Best-effort cleanup of now-empty parent dirs.
                    parent = downloaded_file.parent
                    while parent != output_path:
                        try:
                            parent.rmdir()
                        except OSError:
                            break
                        parent = parent.parent
                downloaded_paths.append(str(final_path))
            else:
                # File might be in current directory structure already
                final_path = output_path / Path(file.name).name
                if final_path.exists():
                    downloaded_paths.append(str(final_path))

        except Exception as e:
            logger.warning("Failed to download %s: %s", file.name, e)
            print(f"Warning: Failed to download {file.name}: {e}", file=sys.stderr)
            continue

    # Create metadata file
    if downloaded_paths:
        metadata = {
            "run_id": run.id,
            "run_name": run.name,
            "entity": getattr(run, "entity", None),
            "project": getattr(run, "project", None),
            "download_timestamp": datetime.now().isoformat(),
            "pattern_used": pattern if pattern else "auto",
            "files_downloaded": [str(Path(p).name) for p in downloaded_paths],
            "file_count": len(downloaded_paths)
        }

        write_metadata_json(output_path, metadata, merge=True)

    return downloaded_paths


def main():
    """Main entry point for the script."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Download plot images from W&B run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all PNG plots
  %(prog)s my-org/my-project abc123

  # Download with custom pattern
  %(prog)s my-org/my-project abc123 --pattern "figures/*.png"

  # Force re-download
  %(prog)s my-org/my-project abc123 --force

  # Custom output directory
  %(prog)s my-org/my-project abc123 --output ./my_plots
        """
    )

    parser.add_argument(
        "entity_project",
        help="W&B project in format 'entity/project' or 'project'"
    )
    parser.add_argument(
        "run_id",
        help="Run ID or name"
    )
    parser.add_argument(
        "--pattern",
        help="Glob pattern for files to download (default: tries multiple common patterns)"
    )
    parser.add_argument(
        "--output",
        help="Custom output directory (default: wandb_plots/<entity>_<project>/<run>/)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files already exist"
    )

    args = parser.parse_args()

    try:
        # Download plots
        downloaded = download_plots(
            args.entity_project,
            args.run_id,
            pattern=args.pattern,
            output_dir=args.output,
            force=args.force
        )

        if downloaded:
            print(f"\nSuccessfully downloaded {len(downloaded)} file(s):")
            for path in downloaded:
                print(f"  - {path}")
        else:
            print("\nNo plot files found in this run.")
            print("You can try:")
            print("  1. Using a custom pattern with --pattern")
            print("  2. Generating plots from metrics with generate_plots.py")

        return 0

    except WandBAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
