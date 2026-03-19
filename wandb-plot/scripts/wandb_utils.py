"""Utility functions for W&B API interactions.

This module provides authentication, run retrieval, and directory management
utilities for interacting with Weights & Biases.
"""

import logging
import os
import json
from pathlib import Path
from typing import Tuple, Optional, Iterable, TypeVar, Any, Dict
import wandb
from wandb.apis.public import Run

T = TypeVar("T")


class WandBAuthError(Exception):
    """Raised when W&B authentication fails."""

    def __init__(self):
        super().__init__(
            "W&B authentication required.\n"
            "Please run one of the following:\n"
            "  1. wandb login\n"
            "  2. export WANDB_API_KEY=<your-key>\n"
            "  3. Add key to ~/.netrc"
        )


def setup_logging():
    """Configure default logging for CLI usage."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = os.getenv("WANDB_PLOT_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def get_api() -> wandb.Api:
    """Initialize W&B API with proper authentication.

    Returns:
        wandb.Api: Authenticated W&B API instance

    Raises:
        WandBAuthError: If authentication fails

    Example:
        >>> api = get_api()
        >>> runs = api.runs("entity/project")
    """
    logger = logging.getLogger(__name__)
    try:
        # Try to initialize API - will use WANDB_API_KEY env var or ~/.netrc
        api = wandb.Api()
        # Test the connection by attempting to access viewer info
        viewer = api.viewer
        if isinstance(viewer, dict):
            username = viewer.get("username")
        else:
            username = getattr(viewer, "username", None)
        logger.debug("W&B API initialized for user: %s", username)
        return api
    except wandb.errors.UsageError as e:
        if "Could not find" in str(e) or "login" in str(e).lower():
            logger.error("W&B authentication failed")
            raise WandBAuthError()
        raise
    except Exception as e:
        # Catch other authentication-related errors
        if "auth" in str(e).lower() or "login" in str(e).lower():
            logger.error("W&B authentication failed")
            raise WandBAuthError()
        raise


def parse_entity_project(
    entity_project: str,
    api: Optional[wandb.Api] = None,
) -> Tuple[str, str]:
    """Parse entity/project string into tuple.

    Handles both "entity/project" and "project" formats.
    If only project is provided, uses the current user's entity.

    Args:
        entity_project: String in format "entity/project" or "project"

    Returns:
        Tuple of (entity, project)

    Raises:
        ValueError: If entity_project is empty or invalid

    Example:
        >>> entity, project = parse_entity_project("my-org/my-project")
        >>> print(entity, project)
        my-org my-project

        >>> entity, project = parse_entity_project("my-project")
        >>> print(entity, project)
        <current-user> my-project
    """
    if not entity_project or not entity_project.strip():
        raise ValueError("entity_project cannot be empty")

    entity_project = entity_project.strip()

    if "/" in entity_project:
        parts = entity_project.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid format '{entity_project}'. "
                "Expected 'entity/project' or 'project'"
            )
        entity, project = parts
        if not entity or not project:
            raise ValueError(
                f"Invalid format '{entity_project}'. "
                "Entity and project cannot be empty"
            )
        return entity.strip(), project.strip()
    else:
        # Only project provided, use current user's entity
        api = api or get_api()
        viewer = api.viewer
        if isinstance(viewer, dict):
            entity = viewer.get("entity") or viewer.get("username")
        else:
            entity = getattr(viewer, "entity", None) or getattr(viewer, "username", None)
        return entity, entity_project


def get_run(entity_project: str, run_id: str) -> Run:
    """Get a W&B run object by ID or name.

    Args:
        entity_project: Project in format "entity/project" or "project"
        run_id: Run ID or run name

    Returns:
        Run object from W&B API

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If run not found or invalid parameters

    Example:
        >>> run = get_run("my-org/my-project", "abc123")
        >>> print(run.name, run.state)
        experiment-1 finished
    """
    if not run_id or not run_id.strip():
        raise ValueError("run_id cannot be empty")

    api = get_api()
    entity, project = parse_entity_project(entity_project, api=api)
    logger = logging.getLogger(__name__)

    run_path = f"{entity}/{project}/{run_id.strip()}"

    try:
        run = api.run(run_path)
        logger.debug("Retrieved run %s", run_path)
        return run
    except wandb.errors.CommError as e:
        # Run not found - provide helpful error message
        error_msg = (
            f"Run '{run_id}' not found in project '{entity}/{project}'.\n"
            f"Please check:\n"
            f"  1. The run ID or name is correct\n"
            f"  2. You have access to this project\n"
            f"  3. The project path is correct\n"
            f"\nOriginal error: {str(e)}"
        )
        raise ValueError(error_msg) from e
    except Exception as e:
        raise ValueError(f"Error retrieving run: {str(e)}") from e


def ensure_output_dir(
    entity_project: str,
    run_id: str,
    run_name: Optional[str] = None,
    base_dir: str = "wandb_plots"
) -> Path:
    """Create and return organized output directory for a run.

    Creates directory structure: {base_dir}/{entity}_{project}/{run_name}_{run_id}/

    Args:
        entity_project: Project in format "entity/project" or "project"
        run_id: Run ID
        run_name: Optional run name for directory naming
        base_dir: Base directory for all outputs (default: "wandb_plots")

    Returns:
        Path object for the created directory

    Raises:
        OSError: If directory creation fails

    Example:
        >>> path = ensure_output_dir("my-org/my-project", "abc123", "experiment-1")
        >>> print(path)
        wandb_plots/my-org_my-project/experiment-1_abc123
    """
    entity, project = parse_entity_project(entity_project)

    # Create project directory name
    project_dir = f"{entity}_{project}"

    # Create run directory name
    if run_name:
        run_dir = f"{run_name}_{run_id}"
    else:
        run_dir = run_id

    # Construct full path
    output_path = Path(base_dir) / project_dir / run_dir

    # Create directory
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    except OSError as e:
        raise OSError(
            f"Failed to create output directory '{output_path}': {str(e)}"
        ) from e


def ensure_output_dir_from_parts(
    entity: str,
    project: str,
    run_id: str,
    run_name: Optional[str] = None,
    base_dir: str = "wandb_plots",
) -> Path:
    """Create and return organized output directory for a run, without API calls."""
    if not entity or not project:
        raise ValueError("entity and project are required")

    project_dir = f"{entity}_{project}"
    run_dir = f"{run_name}_{run_id}" if run_name else run_id
    output_path = Path(base_dir) / project_dir / run_dir
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    except OSError as e:
        raise OSError(
            f"Failed to create output directory '{output_path}': {str(e)}"
        ) from e


def resolve_output_dir(
    entity_project: str,
    run: Run,
    output_dir: Optional[str] = None,
    base_dir: str = "wandb_plots",
) -> Path:
    """Resolve output directory for a run, honoring an explicit override."""
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    entity = getattr(run, "entity", None)
    project = getattr(run, "project", None)
    run_id = getattr(run, "id", None)
    run_name = getattr(run, "name", None)
    if entity and project and run_id:
        return ensure_output_dir_from_parts(
            entity=str(entity),
            project=str(project),
            run_id=str(run_id),
            run_name=str(run_name) if run_name else None,
            base_dir=base_dir,
        )

    if not run_id:
        raise ValueError("Run object is missing an id; cannot resolve output directory")
    return ensure_output_dir(entity_project, run_id=str(run_id), run_name=str(run_name) if run_name else None, base_dir=base_dir)


def progress_wrap(items: Iterable[T], desc: str) -> Iterable[T]:
    """Provide optional tqdm progress without a hard dependency."""
    try:
        from tqdm import tqdm  # type: ignore
    except Exception:
        return items
    return tqdm(items, desc=desc)


def safe_filename(name: str) -> str:
    """Convert a metric/file label into a filesystem-safe filename."""
    if not name:
        return "unnamed"
    return name.replace("/", "_").replace("\\", "_")


def write_metadata_json(
    output_path: Path,
    metadata: Dict[str, Any],
    filename: str = "metadata.json",
    merge: bool = True,
) -> None:
    """Write metadata JSON into the output directory, optionally merging with existing."""
    logger = logging.getLogger(__name__)
    metadata_path = output_path / filename

    if merge and metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                metadata = {**existing, **metadata}
        except Exception:
            pass

    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    except OSError as e:
        logger.warning("Failed to write metadata file %s: %s", metadata_path, e)


def format_entity_project(entity: str, project: str) -> str:
    """Format entity and project into standard string.

    Args:
        entity: Entity name
        project: Project name

    Returns:
        Formatted string "entity/project"

    Example:
        >>> format_entity_project("my-org", "my-project")
        'my-org/my-project'
    """
    return f"{entity}/{project}"
