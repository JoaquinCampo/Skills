#!/usr/bin/env python3
"""List runs in a W&B project with filtering and formatting options.

This script allows discovery of runs in a W&B project, with options to filter
by state and limit the number of results.
"""

import argparse
import json
import logging
import sys
from typing import List, Dict, Optional

from scripts.wandb_utils import (
    get_api,
    parse_entity_project,
    setup_logging,
    WandBAuthError,
)


def list_runs(
    entity_project: str,
    state: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    List runs in a W&B project.

    Args:
        entity_project: Project in format "entity/project" or "project"
        state: Optional state filter ("finished", "running", "crashed", "failed", etc.)
        limit: Maximum number of runs to return

    Returns:
        List of dicts with run info: id, name, state, created, metrics

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If invalid parameters or project not found

    Example:
        >>> runs = list_runs("my-org/my-project", state="finished", limit=10)
        >>> for run in runs:
        ...     print(f"{run['name']}: {run['state']}")
    """
    logger = logging.getLogger(__name__)
    api = get_api()
    entity, project = parse_entity_project(entity_project, api=api)

    # Get runs from API
    filters = {}
    if state:
        filters["state"] = state

    try:
        runs_iterator = api.runs(
            f"{entity}/{project}",
            filters=filters if filters else None
        )
    except Exception as e:
        raise ValueError(
            f"Error accessing project '{entity}/{project}': {str(e)}\n"
            f"Please check:\n"
            f"  1. The project exists\n"
            f"  2. You have access to it\n"
            f"  3. The entity/project path is correct"
        ) from e

    # Collect run info
    runs_list = []
    count = 0

    for run in runs_iterator:
        if count >= limit:
            break

        run_info = {
            "id": run.id,
            "name": run.name,
            "state": run.state,
            "created_at": (
                run.created_at.isoformat()
                if hasattr(run.created_at, "isoformat")
                else (str(run.created_at) if run.created_at is not None else None)
            ),
            "summary_metrics": to_json_friendly(run.summary) if run.summary else {},
            "tags": run.tags if hasattr(run, 'tags') else [],
        }

        runs_list.append(run_info)
        count += 1

    logger.info("Found %d run(s) in %s/%s", len(runs_list), entity, project)
    return runs_list


def to_json_friendly(value):
    """Convert W&B summary values into JSON-serializable types."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        items = value.items()
    except Exception:
        items = None
    if items is not None:
        return {str(k): to_json_friendly(v) for k, v in items}
    if isinstance(value, (list, tuple, set)):
        return [to_json_friendly(v) for v in value]
    try:
        isoformat = value.isoformat
    except Exception:
        isoformat = None
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass
    try:
        item = value.item
    except Exception:
        item = None
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    return str(value)


def format_run_table(runs: List[Dict]) -> str:
    """
    Format runs as a human-readable table.

    Args:
        runs: List of run dictionaries

    Returns:
        Formatted table string
    """
    if not runs:
        return "No runs found."

    # Calculate column widths
    id_width = max(len(run["id"]) for run in runs) + 2
    name_width = max(len(run["name"]) for run in runs) + 2
    state_width = max(len(run["state"]) for run in runs) + 2

    # Ensure minimum widths
    id_width = max(id_width, 12)
    name_width = max(name_width, 20)
    state_width = max(state_width, 12)

    # Create header
    header = f"{'ID':<{id_width}} {'Name':<{name_width}} {'State':<{state_width}} {'Created':<20} {'Summary Metrics'}"
    separator = "-" * (id_width + name_width + state_width + 20 + 40)

    lines = [header, separator]

    # Add rows
    for run in runs:
        # Format created date
        created_str = run["created_at"][:19] if run["created_at"] else "N/A"

        # Format summary metrics (show first 3)
        metrics = run.get("summary_metrics", {})
        if metrics:
            metric_strs = [f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                          for k, v in list(metrics.items())[:3]]
            metrics_str = ", ".join(metric_strs)
            if len(metrics) > 3:
                metrics_str += f" (+{len(metrics) - 3} more)"
        else:
            metrics_str = "None"

        row = f"{run['id']:<{id_width}} {run['name']:<{name_width}} {run['state']:<{state_width}} {created_str:<20} {metrics_str}"
        lines.append(row)

    # Add summary statistics
    state_counts = {}
    for run in runs:
        state = run["state"]
        state_counts[state] = state_counts.get(state, 0) + 1

    lines.append("")
    lines.append(f"Total: {len(runs)} runs")
    if state_counts:
        state_summary = ", ".join(f"{state}: {count}" for state, count in sorted(state_counts.items()))
        lines.append(f"By state: {state_summary}")

    return "\n".join(lines)


def main():
    """Main entry point for the script."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="List runs in a W&B project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all runs
  %(prog)s wandb/examples

  # List only finished runs
  %(prog)s my-org/my-project --state finished

  # List 5 most recent runs
  %(prog)s my-org/my-project --limit 5

  # Get JSON output
  %(prog)s my-org/my-project --json
        """
    )

    parser.add_argument(
        "entity_project",
        help="W&B project in format 'entity/project' or 'project'"
    )
    parser.add_argument(
        "--state",
        help="Filter by run state (finished, running, crashed, failed, etc.)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of runs to display (default: 100)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    try:
        # Get runs
        runs = list_runs(
            args.entity_project,
            state=args.state,
            limit=args.limit
        )

        # Output results
        if args.json:
            print(json.dumps(runs, indent=2))
        else:
            print(format_run_table(runs))

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
        return 1


if __name__ == "__main__":
    sys.exit(main())
