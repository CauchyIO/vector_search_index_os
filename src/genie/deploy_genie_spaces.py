"""
Deploy Genie Spaces

This script deploys Genie Space definitions to a Databricks workspace.
Definitions are imported from genie_space_definitions.py.

Usage:
    # Deploy all spaces in GENIE_SPACES list
    python deploy_genie_spaces.py

    # Deploy specific space(s)
    python deploy_genie_spaces.py --spaces worldbank_table_finder

    # Deploy to specific workspace
    python deploy_genie_spaces.py --workspace https://dbc-xxx.cloud.databricks.com

    # Dry run (show what would be deployed)
    python deploy_genie_spaces.py --dry-run

    # Export to JSON instead of deploying
    python deploy_genie_spaces.py --export-json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from databricks.sdk import WorkspaceClient

from genie.genie_space_definitions import GENIE_SPACES, GENIE_SPACE_REGISTRY
from genie.models import GenieSpaceConfig


def get_workspace_client(host: Optional[str] = None, profile: Optional[str] = None) -> WorkspaceClient:
    """Initialize WorkspaceClient with optional host or profile override."""
    if profile:
        return WorkspaceClient(profile=profile)
    if host:
        return WorkspaceClient(host=host)
    return WorkspaceClient()


def get_default_warehouse_id(client: WorkspaceClient) -> str:
    """Get the first available SQL warehouse ID."""
    warehouses = list(client.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found in workspace")
    return warehouses[0].id


def deploy_space(
    client: WorkspaceClient,
    space: GenieSpaceConfig,
    warehouse_id: str,
    dry_run: bool = False,
) -> Optional[str]:
    """
    Deploy a single Genie Space.

    Returns:
        space_id if successful, None if dry run
    """
    space.warehouse_id = warehouse_id

    if dry_run:
        print(f"  [DRY RUN] Would deploy: {space.title}")
        print(f"    Tables: {len(space.serialized_space.data_sources.tables)}")
        print(f"    Functions: {len(space.serialized_space.instructions.sql_functions)}")
        print(f"    Instructions: {len(space.serialized_space.instructions.text_instructions)}")
        return None

    result = space.create_or_update(client)
    return result.space_id


def deploy_all(
    client: WorkspaceClient,
    spaces: List[GenieSpaceConfig],
    warehouse_id: str,
    dry_run: bool = False,
) -> dict:
    """
    Deploy multiple Genie Spaces.

    Returns:
        Dict mapping space titles to space_ids
    """
    results = {}

    for space in spaces:
        print(f"\nDeploying: {space.title}")
        try:
            space_id = deploy_space(client, space, warehouse_id, dry_run)
            results[space.title] = space_id
            if space_id:
                print(f"  Success: {space_id}")
        except Exception as e:
            import traceback
            print(f"  Error: {e}")
            traceback.print_exc()
            results[space.title] = f"ERROR: {e}"

    return results


def export_to_json(spaces: List[GenieSpaceConfig], output_dir: Path) -> None:
    """Export Genie Spaces to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for space in spaces:
        filename = space.title.lower().replace(" ", "_") + ".json"
        filepath = output_dir / filename
        space.to_json_file(str(filepath))
        print(f"Exported: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Genie Spaces to Databricks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--workspace",
        "-w",
        help="Databricks workspace URL (uses default auth if not specified)",
    )
    parser.add_argument(
        "--profile",
        "-p",
        help="Databricks CLI profile name from ~/.databrickscfg",
    )
    parser.add_argument(
        "--warehouse-id",
        help="SQL warehouse ID (uses first available if not specified)",
    )
    parser.add_argument(
        "--spaces",
        "-s",
        nargs="+",
        choices=list(GENIE_SPACE_REGISTRY.keys()),
        help="Specific spaces to deploy (deploys all in GENIE_SPACES if not specified)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be deployed without deploying",
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export spaces to JSON files instead of deploying",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("exported_genie_spaces"),
        help="Output directory for JSON export (default: exported_genie_spaces)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available Genie Space definitions",
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        print("Available Genie Spaces:")
        print()
        for name, space in GENIE_SPACE_REGISTRY.items():
            in_default = "(*)" if space in GENIE_SPACES else ""
            print(f"  {name} {in_default}")
            print(f"    Title: {space.title}")
            print(f"    Tables: {len(space.serialized_space.data_sources.tables)}")
            print()
        print("(*) = included in default GENIE_SPACES list")
        return

    # Determine which spaces to deploy
    if args.spaces:
        spaces = [GENIE_SPACE_REGISTRY[name] for name in args.spaces]
    else:
        spaces = GENIE_SPACES

    if not spaces:
        print("No spaces to deploy. Use --spaces or add to GENIE_SPACES list.")
        sys.exit(1)

    print(f"Genie Spaces to process: {len(spaces)}")
    for space in spaces:
        print(f"  - {space.title}")

    # Export mode
    if args.export_json:
        print(f"\nExporting to: {args.output_dir}")
        export_to_json(spaces, args.output_dir)
        return

    # Deploy mode
    print(f"\nConnecting to workspace...")
    client = get_workspace_client(host=args.workspace, profile=args.profile)

    warehouse_id = args.warehouse_id
    if not warehouse_id:
        warehouse_id = get_default_warehouse_id(client)
        print(f"Using warehouse: {warehouse_id}")

    print(f"\n{'=' * 50}")
    print("DEPLOYING GENIE SPACES")
    print(f"{'=' * 50}")

    results = deploy_all(client, spaces, warehouse_id, args.dry_run)

    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")
    for title, space_id in results.items():
        status = "OK" if space_id and not space_id.startswith("ERROR") else "FAILED"
        print(f"  [{status}] {title}: {space_id}")


if __name__ == "__main__":
    main()
