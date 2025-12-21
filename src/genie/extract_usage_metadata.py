"""
Extract metadata from system.billing.usage table for Genie Space descriptions.

This script analyzes the Usage table to generate insightful descriptions that help
users understand the data coverage, key values, and patterns.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
import json
from collections import defaultdict


def execute_query(client: WorkspaceClient, warehouse_id: str, query: str) -> list[dict]:
    """Execute a SQL query and return results as list of dicts."""
    response = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=query,
        wait_timeout="50s",
    )

    if response.status.state != StatementState.SUCCEEDED:
        raise Exception(f"Query failed: {response.status.error}")

    if not response.result or not response.result.data_array:
        return []

    columns = [col.name for col in response.manifest.schema.columns]
    return [dict(zip(columns, row)) for row in response.result.data_array]


def get_usage_metadata(client: WorkspaceClient, warehouse_id: str) -> dict:
    """Extract comprehensive metadata from system.billing.usage table."""

    metadata = {}

    # 1. Date range coverage
    print("Querying date range...")
    date_range = execute_query(client, warehouse_id, """
        SELECT
            MIN(usage_date) as min_date,
            MAX(usage_date) as max_date,
            COUNT(DISTINCT usage_date) as num_days,
            COUNT(*) as total_records
        FROM system.billing.usage
    """)
    metadata["date_range"] = date_range[0] if date_range else {}

    # 2. Record types distribution
    print("Querying record types...")
    record_types = execute_query(client, warehouse_id, """
        SELECT
            record_type,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM system.billing.usage
        GROUP BY record_type
        ORDER BY count DESC
    """)
    metadata["record_types"] = record_types

    # 3. Billing origin products
    print("Querying billing origin products...")
    products = execute_query(client, warehouse_id, """
        SELECT
            billing_origin_product,
            COUNT(*) as count,
            ROUND(SUM(usage_quantity), 2) as total_usage
        FROM system.billing.usage
        GROUP BY billing_origin_product
        ORDER BY count DESC
        LIMIT 20
    """)
    metadata["billing_origin_products"] = products

    # 4. SKU names (top 30 by usage)
    print("Querying SKU names...")
    skus = execute_query(client, warehouse_id, """
        SELECT
            sku_name,
            COUNT(*) as record_count,
            ROUND(SUM(usage_quantity), 2) as total_usage,
            usage_unit
        FROM system.billing.usage
        GROUP BY sku_name, usage_unit
        ORDER BY total_usage DESC
        LIMIT 30
    """)
    metadata["sku_names"] = skus

    # 5. Cloud distribution
    print("Querying cloud distribution...")
    clouds = execute_query(client, warehouse_id, """
        SELECT
            cloud,
            COUNT(*) as count,
            ROUND(SUM(usage_quantity), 2) as total_usage
        FROM system.billing.usage
        GROUP BY cloud
        ORDER BY count DESC
    """)
    metadata["clouds"] = clouds

    # 6. Usage units
    print("Querying usage units...")
    units = execute_query(client, warehouse_id, """
        SELECT
            usage_unit,
            COUNT(*) as count
        FROM system.billing.usage
        GROUP BY usage_unit
        ORDER BY count DESC
    """)
    metadata["usage_units"] = units

    # 7. Workspace count
    print("Querying workspace count...")
    workspaces = execute_query(client, warehouse_id, """
        SELECT
            COUNT(DISTINCT workspace_id) as workspace_count
        FROM system.billing.usage
    """)
    metadata["workspace_count"] = workspaces[0]["workspace_count"] if workspaces else 0

    # 8. Identity metadata patterns
    print("Querying identity metadata patterns...")
    identity_patterns = execute_query(client, warehouse_id, """
        SELECT
            CASE
                WHEN identity_metadata.run_as IS NOT NULL THEN 'has_run_as'
                ELSE 'no_run_as'
            END as run_as_status,
            CASE
                WHEN identity_metadata.owned_by IS NOT NULL THEN 'has_owned_by'
                ELSE 'no_owned_by'
            END as owned_by_status,
            COUNT(*) as count
        FROM system.billing.usage
        GROUP BY 1, 2
        ORDER BY count DESC
    """)
    metadata["identity_patterns"] = identity_patterns

    # 10. Custom tags usage
    print("Querying custom tags usage...")
    tags_usage = execute_query(client, warehouse_id, """
        SELECT
            CASE
                WHEN custom_tags IS NOT NULL AND SIZE(custom_tags) > 0 THEN 'has_tags'
                ELSE 'no_tags'
            END as tag_status,
            COUNT(*) as count
        FROM system.billing.usage
        GROUP BY 1
    """)
    metadata["custom_tags_usage"] = tags_usage

    # 11. Usage metadata resource types
    print("Querying usage_metadata resource types...")
    usage_metadata_resources = execute_query(client, warehouse_id, """
        SELECT
            CASE WHEN usage_metadata.cluster_id IS NOT NULL THEN 1 ELSE 0 END as has_cluster,
            CASE WHEN usage_metadata.job_id IS NOT NULL THEN 1 ELSE 0 END as has_job,
            CASE WHEN usage_metadata.warehouse_id IS NOT NULL THEN 1 ELSE 0 END as has_warehouse,
            CASE WHEN usage_metadata.instance_pool_id IS NOT NULL THEN 1 ELSE 0 END as has_pool,
            CASE WHEN usage_metadata.notebook_id IS NOT NULL THEN 1 ELSE 0 END as has_notebook,
            CASE WHEN usage_metadata.dlt_pipeline_id IS NOT NULL THEN 1 ELSE 0 END as has_pipeline,
            CASE WHEN usage_metadata.endpoint_id IS NOT NULL THEN 1 ELSE 0 END as has_endpoint,
            COUNT(*) as count
        FROM system.billing.usage
        GROUP BY 1, 2, 3, 4, 5, 6, 7
        ORDER BY count DESC
        LIMIT 20
    """)
    metadata["usage_metadata_resources"] = usage_metadata_resources

    # 12. Node types used
    print("Querying node types...")
    node_types = execute_query(client, warehouse_id, """
        SELECT
            usage_metadata.node_type as node_type,
            COUNT(*) as count,
            ROUND(SUM(usage_quantity), 2) as total_usage
        FROM system.billing.usage
        WHERE usage_metadata.node_type IS NOT NULL
        GROUP BY usage_metadata.node_type
        ORDER BY total_usage DESC
        LIMIT 15
    """)
    metadata["node_types"] = node_types

    # 13. Usage type breakdown
    print("Querying usage types...")
    usage_types = execute_query(client, warehouse_id, """
        SELECT
            usage_type,
            COUNT(*) as count,
            ROUND(SUM(usage_quantity), 2) as total_usage
        FROM system.billing.usage
        GROUP BY usage_type
        ORDER BY count DESC
    """)
    metadata["usage_types"] = usage_types

    # 14. Record type breakdown (for understanding retractions/restatements)
    print("Querying record type details...")
    record_type_details = execute_query(client, warehouse_id, """
        SELECT
            record_type,
            COUNT(*) as count,
            ROUND(SUM(usage_quantity), 2) as net_usage,
            MIN(usage_date) as first_date,
            MAX(usage_date) as last_date
        FROM system.billing.usage
        GROUP BY record_type
        ORDER BY count DESC
    """)
    metadata["record_type_details"] = record_type_details

    return metadata


def format_metadata_for_description(metadata: dict) -> str:
    """Format metadata into a structured description for Genie Space.

    Focus on data diversity - what kinds of values exist to help Genie
    understand the content.
    """

    lines = []

    # Header
    lines.append("# system.billing.usage Table Metadata")
    lines.append("")

    # Date coverage
    dr = metadata.get("date_range", {})
    if dr:
        lines.append("## Data Scope")
        lines.append(f"- Date range: {dr.get('min_date', 'N/A')} to {dr.get('max_date', 'N/A')}")
        lines.append(f"- Total records: {int(float(dr.get('total_records', 0))):,}")
        lines.append(f"- Workspaces: {metadata.get('workspace_count', 'N/A')}")
        lines.append("")

    # Record types with explanation
    if metadata.get("record_type_details"):
        lines.append("## Record Types")
        lines.append("ORIGINAL=normal usage, RETRACTION=negative qty to negate errors, RESTATEMENT=corrections")
        for rt in metadata["record_type_details"]:
            lines.append(f"- {rt['record_type']}: {int(float(rt['count'])):,} records")
        lines.append("")

    # Clouds
    if metadata.get("clouds"):
        lines.append("## Cloud Providers")
        cloud_list = [c['cloud'] for c in metadata["clouds"]]
        lines.append(f"Values: {', '.join(cloud_list)}")
        lines.append("")

    # Billing products - key for understanding what generates costs
    if metadata.get("billing_origin_products"):
        lines.append("## billing_origin_product Values")
        lines.append("Products generating billable usage:")
        for p in metadata["billing_origin_products"]:
            lines.append(f"- {p['billing_origin_product']}")
        lines.append("")

    # Usage types
    if metadata.get("usage_types"):
        lines.append("## usage_type Values")
        for ut in metadata["usage_types"]:
            if ut.get('usage_type'):
                lines.append(f"- {ut['usage_type']}")
        lines.append("")

    # SKUs - critical for cost analysis
    if metadata.get("sku_names"):
        lines.append("## sku_name Values (Top by Usage)")
        for sku in metadata["sku_names"]:
            lines.append(f"- {sku['sku_name']} ({sku['usage_unit']})")
        lines.append("")

    # Usage units
    if metadata.get("usage_units"):
        lines.append("## usage_unit Values")
        unit_list = [u['usage_unit'] for u in metadata["usage_units"]]
        lines.append(f"Values: {', '.join(unit_list)}")
        lines.append("")

    # Node types - instance type diversity
    if metadata.get("node_types"):
        lines.append("## Node Types (usage_metadata.node_type)")
        lines.append("Compute instance types used:")
        for nt in metadata["node_types"]:
            if nt.get('node_type'):
                lines.append(f"- {nt['node_type']}")
        lines.append("")

    # Usage metadata resources - what resources are tracked
    if metadata.get("usage_metadata_resources"):
        lines.append("## Resource Attribution (usage_metadata fields)")
        lines.append("Records are linked to resources via these IDs:")
        resource_counts = defaultdict(int)
        for r in metadata["usage_metadata_resources"]:
            count = int(float(r['count']))
            if r.get('has_cluster') == '1':
                resource_counts['cluster_id'] += count
            if r.get('has_job') == '1':
                resource_counts['job_id'] += count
            if r.get('has_warehouse') == '1':
                resource_counts['warehouse_id'] += count
            if r.get('has_pool') == '1':
                resource_counts['instance_pool_id'] += count
            if r.get('has_notebook') == '1':
                resource_counts['notebook_id'] += count
            if r.get('has_pipeline') == '1':
                resource_counts['dlt_pipeline_id'] += count
            if r.get('has_endpoint') == '1':
                resource_counts['endpoint_id'] += count
        for resource, count in sorted(resource_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                lines.append(f"- {resource}: {count:,} records have this ID populated")
        lines.append("")

    # Identity metadata - who runs workloads
    if metadata.get("identity_patterns"):
        lines.append("## Identity Tracking (identity_metadata)")
        lines.append("- run_as: user who executed the job")
        lines.append("- owned_by: warehouse owner")
        for ip in metadata["identity_patterns"]:
            lines.append(f"- {ip['run_as_status']}, {ip['owned_by_status']}: {int(float(ip['count'])):,} records")
        lines.append("")

    # Custom tags availability
    if metadata.get("custom_tags_usage"):
        lines.append("## Custom Tags Availability")
        for t in metadata["custom_tags_usage"]:
            pct = int(float(t['count']) / float(dr.get('total_records', 1)) * 100) if dr else 0
            lines.append(f"- {t['tag_status']}: {int(float(t['count'])):,} records ({pct}%)")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract metadata from system.billing.usage")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile name")
    parser.add_argument("--host", default=None, help="Databricks workspace host URL")
    parser.add_argument("--warehouse-id", default=None, help="SQL Warehouse ID to use")
    args = parser.parse_args()

    # Initialize client with optional profile
    if args.profile:
        client = WorkspaceClient(profile=args.profile)
    elif args.host:
        client = WorkspaceClient(host=args.host)
    else:
        client = WorkspaceClient()

    print(f"Connected to: {client.config.host}")

    # Get warehouse
    if args.warehouse_id:
        warehouse_id = args.warehouse_id
        print(f"Using specified warehouse: {warehouse_id}")
    else:
        warehouses = list(client.warehouses.list())
        if not warehouses:
            raise Exception("No SQL warehouses available")
        warehouse_id = warehouses[0].id
        print(f"Using warehouse: {warehouses[0].name} ({warehouse_id})")

    print("-" * 60)

    # Extract metadata
    print("Extracting metadata from system.billing.usage...")
    metadata = get_usage_metadata(client, warehouse_id)

    # Save raw metadata as JSON
    output_path = "usage_table_metadata.json"
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"\nRaw metadata saved to: {output_path}")

    # Format for description
    description = format_metadata_for_description(metadata)

    desc_path = "usage_table_description.md"
    with open(desc_path, "w") as f:
        f.write(description)
    print(f"Formatted description saved to: {desc_path}")

    print("\n" + "=" * 60)
    print("FORMATTED DESCRIPTION:")
    print("=" * 60)
    print(description)


if __name__ == "__main__":
    main()
