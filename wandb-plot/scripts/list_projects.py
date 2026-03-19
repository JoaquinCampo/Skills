#!/usr/bin/env python3
"""List W&B projects for an entity with optional formatting."""

import argparse
import json
import logging
import sys
from typing import List, Dict, Optional

from scripts.wandb_utils import (
    get_api,
    setup_logging,
    WandBAuthError,
)


def list_projects(
    entity: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    List projects for a W&B entity.

    Args:
        entity: W&B entity (user or org). If omitted, uses current viewer entity.
        limit: Maximum number of projects to return

    Returns:
        List of dicts with project info: name, entity, description, created_at, url

    Raises:
        WandBAuthError: If not authenticated
        ValueError: If entity is invalid or projects cannot be fetched
    """
    logger = logging.getLogger(__name__)
    api = get_api()

    if not entity:
        viewer = api.viewer
        if isinstance(viewer, dict):
            entity = viewer.get("entity") or viewer.get("username")
        else:
            entity = getattr(viewer, "entity", None) or getattr(viewer, "username", None)

    if not entity:
        raise ValueError("Could not determine default entity. Please pass --entity.")

    try:
        projects_iterator = api.projects(entity)
    except Exception as e:
        raise ValueError(
            f"Error accessing projects for entity '{entity}': {str(e)}\n"
            "Please check:\n"
            "  1. The entity exists\n"
            "  2. You have access to it\n"
            "  3. The entity name is correct"
        ) from e

    projects_list = []
    count = 0

    for project in projects_iterator:
        if count >= limit:
            break

        name = getattr(project, "name", None)
        description = getattr(project, "description", None)
        created_at = getattr(project, "created_at", None)
        created_at_str = (
            created_at.isoformat()
            if hasattr(created_at, "isoformat")
            else (str(created_at) if created_at is not None else None)
        )
        url = f"https://wandb.ai/{entity}/{name}" if name else None

        projects_list.append({
            "name": name,
            "entity": entity,
            "description": description,
            "created_at": created_at_str,
            "url": url,
        })
        count += 1

    logger.info("Found %d project(s) in %s", len(projects_list), entity)
    return projects_list


def format_project_table(projects: List[Dict]) -> str:
    """Format projects as a human-readable table."""
    if not projects:
        return "No projects found."

    name_width = max(len(p["name"] or "") for p in projects) + 2
    name_width = max(name_width, 24)

    header = f"{'Name':<{name_width}} {'Created':<20} {'Description'}"
    separator = "-" * (name_width + 20 + 40)
    lines = [header, separator]

    for project in projects:
        created_str = project["created_at"][:19] if project["created_at"] else "N/A"
        description = project.get("description") or ""
        if len(description) > 80:
            description = f"{description[:77]}..."
        lines.append(
            f"{project['name']:<{name_width}} {created_str:<20} {description}"
        )

    lines.append("")
    lines.append(f"Total: {len(projects)} projects")

    return "\n".join(lines)


def main() -> int:
    """Main entry point for the script."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="List projects for a W&B entity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List projects for your default entity
  %(prog)s

  # List projects for a specific entity
  %(prog)s --entity my-org

  # List 5 projects in JSON format
  %(prog)s --limit 5 --json
        """
    )

    parser.add_argument(
        "--entity",
        help="W&B entity (user or org). Defaults to current viewer entity."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of projects to display (default: 100)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    try:
        projects = list_projects(
            entity=args.entity,
            limit=args.limit
        )

        if args.json:
            print(json.dumps(projects, indent=2))
        else:
            print(format_project_table(projects))

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
