#!/usr/bin/env python3
"""Discover available metrics for a W&B run.

This script lists all metrics logged to a W&B run, with statistics
about each metric (min, max, count, data type).
"""

import argparse
import json
import logging
import sys
from typing import Dict, Any

import pandas as pd

from scripts.wandb_utils import get_run, setup_logging, WandBAuthError


def list_metrics(
    entity_project: str,
    run_id: str,
    include_system: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    List available metrics for a run with statistics.

    Args:
        entity_project: Project in format "entity/project" or "project"
        run_id: Run ID or name
        include_system: If True, include system columns (_step, _timestamp, etc.)

    Returns:
        Dict mapping metric names to statistics:
        {
            "metric_name": {
                "min": float,
                "max": float,
                "count": int,
                "non_null_count": int,
                "type": str
            }
        }

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If run not found

    Example:
        >>> metrics = list_metrics("my-org/my-project", "abc123")
        >>> for name, stats in metrics.items():
        ...     print(f"{name}: min={stats['min']}, max={stats['max']}")
    """
    logger = logging.getLogger(__name__)
    run = get_run(entity_project, run_id)

    try:
        # Get sampled history (typically ~500 points)
        history_df = run.history()
    except Exception as e:
        raise ValueError(f"Error fetching run history: {str(e)}") from e

    if history_df.empty:
        logger.info("Run %s has no history data", run_id)
        return {}

    # Filter columns
    columns = list(history_df.columns)

    if not include_system:
        # Filter out system columns
        system_prefixes = ('_', 'system/', 'gradients/')
        columns = [col for col in columns
                  if not any(col.startswith(prefix) for prefix in system_prefixes)]

    # Calculate statistics for each metric
    metrics_info = {}

    for col in columns:
        series = history_df[col]

        # Skip if all null
        if series.isna().all():
            continue

        # Determine data type
        dtype = str(series.dtype)
        if pd.api.types.is_numeric_dtype(series):
            data_type = "numeric"
        elif pd.api.types.is_string_dtype(series):
            data_type = "string"
        elif pd.api.types.is_bool_dtype(series):
            data_type = "boolean"
        else:
            data_type = dtype

        # Calculate statistics
        stats = {
            "type": data_type,
            "count": len(series),
            "non_null_count": series.notna().sum(),
        }

        # Add numeric statistics if applicable
        if pd.api.types.is_numeric_dtype(series):
            try:
                stats["min"] = float(series.min())
                stats["max"] = float(series.max())
                stats["mean"] = float(series.mean())
                stats["std"] = float(series.std())
            except (ValueError, TypeError):
                pass

        metrics_info[col] = stats

    logger.info("Found %d metric(s) in run %s", len(metrics_info), run_id)
    return metrics_info


def format_metrics_table(metrics: Dict[str, Dict[str, Any]]) -> str:
    """
    Format metrics as a human-readable table.

    Args:
        metrics: Dictionary of metric statistics

    Returns:
        Formatted table string
    """
    if not metrics:
        return "No metrics found."

    # Calculate column widths
    name_width = max(len(name) for name in metrics.keys()) + 2
    name_width = max(name_width, 25)

    # Create header
    header = f"{'Metric':<{name_width}} {'Type':<12} {'Count':<8} {'Min':<12} {'Max':<12} {'Mean':<12}"
    separator = "-" * (name_width + 12 + 8 + 12 + 12 + 12)

    lines = [header, separator]

    # Sort metrics by name for consistent output
    sorted_metrics = sorted(metrics.items())

    # Add rows
    for name, stats in sorted_metrics:
        data_type = stats.get("type", "unknown")
        count = stats.get("non_null_count", stats.get("count", 0))

        # Format numeric statistics
        if "min" in stats and "max" in stats:
            min_val = f"{stats['min']:.6g}"
            max_val = f"{stats['max']:.6g}"
            mean_val = f"{stats['mean']:.6g}" if "mean" in stats else "N/A"
        else:
            min_val = "N/A"
            max_val = "N/A"
            mean_val = "N/A"

        row = f"{name:<{name_width}} {data_type:<12} {count:<8} {min_val:<12} {max_val:<12} {mean_val:<12}"
        lines.append(row)

    # Add summary
    lines.append("")
    lines.append(f"Total metrics: {len(metrics)}")

    # Group by type
    type_counts = {}
    for stats in metrics.values():
        dtype = stats.get("type", "unknown")
        type_counts[dtype] = type_counts.get(dtype, 0) + 1

    if type_counts:
        type_summary = ", ".join(f"{dtype}: {count}" for dtype, count in sorted(type_counts.items()))
        lines.append(f"By type: {type_summary}")

    return "\n".join(lines)


def main():
    """Main entry point for the script."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="List available metrics for a W&B run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List metrics for a run
  %(prog)s my-org/my-project abc123

  # Include system metrics
  %(prog)s my-org/my-project abc123 --include-system

  # Get JSON output
  %(prog)s my-org/my-project abc123 --json
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
        "--include-system",
        action="store_true",
        help="Include system columns (_step, _timestamp, etc.)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    try:
        # Get metrics
        metrics = list_metrics(
            args.entity_project,
            args.run_id,
            include_system=args.include_system
        )

        # Output results
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print(format_metrics_table(metrics))

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
