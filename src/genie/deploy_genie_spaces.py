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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

from genie.genie_space_definitions import GENIE_SPACES, GENIE_SPACE_REGISTRY
from genie.models import GenieSpaceConfig


# =============================================================================
# Service Principal for Genie Space Management Functions
# =============================================================================

@dataclass
class ServicePrincipal:
    """Service Principal that needs access to deployed Genie Spaces."""
    application_id: str
    name: str


# SPN used by the SQL UDFs to manage Genie Space tables at runtime
GENIE_MANAGEMENT_SPN = ServicePrincipal(
    application_id="caf7ea80-d784-4e6e-b079-db47a7533d18",
    name="genie_spn",
)


# =============================================================================
# Genie Space Permissions
# =============================================================================

class GenieSpacePermission:
    """Permission levels for Genie Spaces."""
    CAN_VIEW = "CAN_VIEW"
    CAN_EDIT = "CAN_EDIT"
    CAN_MANAGE = "CAN_MANAGE"


def grant_spn_access_to_space(
    client: WorkspaceClient,
    space_id: str,
    spn: ServicePrincipal,
    permission: str = GenieSpacePermission.CAN_EDIT,
) -> None:
    """
    Grant a Service Principal access to a Genie Space.

    Tries multiple permission APIs since Genie spaces may use different
    permission systems depending on the Databricks version.

    Args:
        client: Authenticated WorkspaceClient
        space_id: The Genie Space ID
        spn: ServicePrincipal to grant access to
        permission: Permission level (CAN_VIEW, CAN_EDIT, CAN_MANAGE)

    Raises:
        RuntimeError: If unable to grant permissions via any known method
    """
    acl = [
        AccessControlRequest(
            service_principal_name=spn.application_id,
            permission_level=PermissionLevel(permission),
        )
    ]

    # Try different object types - Genie spaces may be registered differently
    object_types_to_try = [
        "genie-spaces",
        "dashboards",
        "dbsql-dashboards",
    ]

    errors = []
    for obj_type in object_types_to_try:
        try:
            client.permissions.update(
                request_object_type=obj_type,
                request_object_id=space_id,
                access_control_list=acl,
            )
            print(f"    Granted {permission} via {obj_type}")
            return
        except Exception as e:
            errors.append(f"{obj_type}: {e}")

    # All attempts failed - raise with details
    error_details = "\n      ".join(errors)
    raise RuntimeError(
        f"Could not grant {spn.name} access to space {space_id}. "
        f"Tried:\n      {error_details}\n\n"
        f"Please grant access manually via the Genie Space UI: "
        f"Share -> Add '{spn.name}' with CAN_EDIT permission."
    )


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
    debug: bool = False,
) -> Optional[str]:
    """
    Deploy a single Genie Space.

    Args:
        client: Authenticated WorkspaceClient
        space: GenieSpaceConfig to deploy
        warehouse_id: SQL warehouse ID to use
        dry_run: If True, show what would be deployed without deploying
        debug: If True, print the serialized JSON

    Returns:
        space_id if successful, None if dry run
    """
    space.warehouse_id = warehouse_id

    if dry_run or debug:
        print(f"  [{'DRY RUN' if dry_run else 'DEBUG'}] Would deploy: {space.title}")
        print(f"    Tables: {len(space.serialized_space.data_sources.tables)}")
        print(f"    Functions: {len(space.serialized_space.instructions.sql_functions)}")
        print(f"    Instructions: {len(space.serialized_space.instructions.text_instructions)}")
        if debug:
            print(f"\n  Serialized space JSON:")
            print(space.get_serialized_space_json())
            print()
        if dry_run:
            return None

    result = space.create_or_update(client)
    space_id = result.space_id

    # TODO: Grant SPN access so SQL UDFs can manage the space
    # The Genie Space permissions API is not yet available via the SDK.
    # For now, grant access manually via UI: Share -> Add 'genie_spn' with CAN_EDIT.
    # if grant_spn_access and space_id:
    #     print(f"  Granting {GENIE_MANAGEMENT_SPN.name} access...")
    #     grant_spn_access_to_space(client, space_id, GENIE_MANAGEMENT_SPN)

    return space_id


def deploy_all(
    client: WorkspaceClient,
    spaces: List[GenieSpaceConfig],
    warehouse_id: str,
    dry_run: bool = False,
    debug: bool = False,
) -> dict:
    """
    Deploy multiple Genie Spaces.

    Args:
        client: Authenticated WorkspaceClient
        spaces: List of GenieSpaceConfig to deploy
        warehouse_id: SQL warehouse ID to use
        dry_run: If True, show what would be deployed without deploying
        debug: If True, print the serialized JSON

    Returns:
        Dict mapping space titles to space_ids
    """
    results = {}

    for space in spaces:
        print(f"\nDeploying: {space.title}")
        try:
            space_id = deploy_space(client, space, warehouse_id, dry_run, debug)
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
        "--debug",
        "-d",
        action="store_true",
        help="Print the serialized JSON before deploying",
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

    results = deploy_all(
        client, spaces, warehouse_id, args.dry_run, args.debug
    )

    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")
    for title, space_id in results.items():
        status = "OK" if space_id and not space_id.startswith("ERROR") else "FAILED"
        print(f"  [{status}] {title}: {space_id}")

    # Reminder about SPN access
    successful = [sid for sid in results.values() if sid and not str(sid).startswith("ERROR")]
    if successful:
        print(f"\n{'=' * 50}")
        print("IMPORTANT: Grant SPN access manually")
        print(f"{'=' * 50}")
        print(f"The Genie Space permissions API is not yet available.")
        print(f"For each space, grant access via UI:")
        print(f"  1. Open the Genie Space")
        print(f"  2. Click 'Share'")
        print(f"  3. Add '{GENIE_MANAGEMENT_SPN.name}' with CAN_EDIT permission")


if __name__ == "__main__":
    main()
