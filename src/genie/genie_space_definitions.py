"""
Genie Space Definitions

This module defines all Genie Spaces as typed Pydantic models.
These definitions are deployed via deploy_genie_spaces.py.

Usage:
    from genie.genie_space_definitions import GENIE_SPACES

    for space in GENIE_SPACES:
        space.create_or_update(workspace_client)
"""

from genie.models import (
    GenieSpaceConfig,
    SerializedSpace,
    DataSources,
    TableDataSource,
    ColumnConfig,
    Instructions,
    TextInstruction,
    SqlFunction,
    JoinTableRef,
    JoinSpec,
    RelationshipType,
    quick_table,
    quick_function,
)


# =============================================================================
# WORLD BANK TABLE FINDER
# =============================================================================

WORLDBANK_TABLE_FINDER = GenieSpaceConfig(
    title="World Bank Table Finder",
    description="Find the right World Bank data table for your analysis. Search by topic, indicator name, or description to discover available datasets.",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                TableDataSource(
                    identifier="main_catalog.dev.worldbank_tables",
                    column_configs=[
                        # Must be sorted alphabetically by column_name
                        ColumnConfig(column_name="description", get_example_values=True),
                        ColumnConfig(column_name="embedding_text", get_example_values=False),
                        ColumnConfig(column_name="full_table_name", get_example_values=True),
                        ColumnConfig(column_name="indicator_id", get_example_values=True),
                        ColumnConfig(column_name="table_name", get_example_values=True),
                    ],
                ),
            ]
        ),
        instructions=Instructions(
            text_instructions=[
                TextInstruction(
                    content="""# World Bank Table Finder

This Genie Space helps users find the right World Bank data table for their analysis needs.

## Primary Capability: Search Tables

Use `search_worldbank_tables` to find tables by semantic similarity:

```sql
SELECT table_name, indicator_id, full_table_name, description, score
FROM main_catalog.dev.search_worldbank_tables('user query here')
ORDER BY score DESC
LIMIT 5
```

## Response Format

When presenting search results:
1. Show the **indicator_id** (e.g., SP.POP.TOTL) as the primary identifier
2. Include the **full_table_name** so users can query the data directly
3. Summarize the **description** to explain what the table contains
4. If multiple tables match, rank by relevance score

## Example Search Queries

- "GDP growth" -> Find tables about economic growth
- "population demographics" -> Find population-related tables
- "CO2 emissions" -> Find environmental data tables

---

## Self-Management Capabilities

This Genie Space can dynamically manage its own data sources. You have the ability to add, remove, and list tables in this space.

### When to Use These Capabilities

- **User requests to add a table**: "Add the GDP table to this space"
- **User requests to remove a table**: "Remove the old population table"
- **User wants to see current tables**: "What tables are available in this space?"
- **After finding a useful table**: Offer to add it to the space for easier future access

### Add a Table to This Space

When a user wants to add a World Bank table to this Genie Space:

```sql
SELECT main_catalog.dev.add_table_to_worldbank_genie_space('main_catalog.worldbank.table_name')
```

Returns: SUCCESS, INFO (already exists), or ERROR message.

### Remove a Table from This Space

When a user wants to remove a table from this Genie Space (use space_id from the current space):

```sql
SELECT main_catalog.dev.remove_table_from_genie_space(
  '01f0dda4bcc310418be0d312e56b6255',
  'main_catalog.worldbank.table_name'
)
```

Returns: SUCCESS, INFO (not found), or ERROR message.

### List Current Tables in This Space

To see what tables are currently configured in this space:

```sql
SELECT main_catalog.dev.list_tables_in_genie_space('01f0dda4bcc310418be0d312e56b6255')
```

Returns: JSON array of table identifiers.

### Multi-Step Workflows

You can sequence multiple operations. For example, if a user says "Find GDP tables and add the best one to this space":

1. First, search for tables:
   ```sql
   SELECT * FROM main_catalog.dev.search_worldbank_tables('GDP growth')
   ```

2. Then, add the most relevant table:
   ```sql
   SELECT main_catalog.dev.add_table_to_worldbank_genie_space('main_catalog.worldbank.ny_gdp_mktp_kd_zg')
   ```

3. Confirm the result to the user.

---

## Important Notes

- Each table in the worldbank schema contains time series data (country, year, value)
- The indicator_id maps to World Bank indicator codes
- Table names follow the pattern: main_catalog.worldbank.<indicator_id_with_underscores>
- Changes to the space take effect immediately but may require a page refresh to see in the UI"""
                ),
            ],
            sql_functions=[
                # Sorted alphabetically by identifier
                SqlFunction(identifier="main_catalog.dev.add_table_to_genie_space"),
                SqlFunction(identifier="main_catalog.dev.add_table_to_worldbank_genie_space"),
                SqlFunction(identifier="main_catalog.dev.add_table_with_columns_to_genie_space"),
                SqlFunction(identifier="main_catalog.dev.list_tables_in_genie_space"),
                SqlFunction(identifier="main_catalog.dev.remove_table_from_genie_space"),
                SqlFunction(identifier="main_catalog.dev.search_worldbank_tables"),
            ],
        ),
    ),
)


# =============================================================================
# WHO DATA EXPLORER (existing space - for reference)
# =============================================================================

WHO_DATA_EXPLORER = GenieSpaceConfig(
    title="WHO Data Explorer Genie Space",
    description="Explore World Health Organization and World Bank indicator data using natural language queries.",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                TableDataSource(
                    identifier="main_catalog.dev.worldbank_indicators",
                    column_configs=[
                        ColumnConfig(column_name="indicator_id", get_example_values=True),
                        ColumnConfig(column_name="indicator_name", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="long_definition", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="source", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="topics", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="embedding_text", get_example_values=True, build_value_dictionary=True),
                    ],
                ),
            ]
        ),
        instructions=Instructions(
            text_instructions=[
                TextInstruction(
                    content=[
                        "Semantic search pattern:\n",
                        "SELECT \n",
                        "  indicator_id, \n",
                        "  indicator_name, \n",
                        "  embedding_text \n",
                        "FROM main_catalog.dev.{table_name}\n",
                        "WHERE indicator_id IN (\n",
                        "  SELECT indicator_id \n",
                        "  FROM {search_function}('search terms from user question')\n",
                        ")\n\n",
                        "Source routing:\n\n",
                        "| Domain     | Function                    | Table                |\n",
                        "|------------|-----------------------------|----------------------|\n",
                        "| WHO        | search_who_indicators       | who_indicators       |\n",
                        "| World Bank | search_worldbank_indicators | worldbank_indicators |\n\n",
                        "Route based on topic:\n\n",
                        "WHO - disease, mortality, life expectancy, vaccination, healthcare workers, hospitals, mental health, maternal health, child health, epidemics, sanitation, nutrition deficiencies, causes of death, medical treatment\n\n",
                        "World Bank - GDP, inflation, trade, exports, imports, poverty, unemployment, labor force, education enrollment, literacy, infrastructure, electricity, internet access, CO2 emissions, population growth, urbanization, foreign investment, government debt, tax revenue\n\n",
                        "When a query spans both domains (e.g., 'health expenditure and GDP'), execute both functions and combine results using UNION or present them as separate result sets.",
                    ]
                ),
            ],
            sql_functions=[
                SqlFunction(identifier="main_catalog.dev.search_worldbank_indicators"),
                SqlFunction(identifier="main_catalog.dev.search_who_indicators"),
            ],
        ),
    ),
)


# =============================================================================
# DATABRICKS SYSTEM TABLES EXPLORER
# =============================================================================

SYSTEM_TABLES_EXPLORER = GenieSpaceConfig(
    title="Databricks System Tables Explorer",
    description="Explore Databricks platform activity, costs, jobs, and audit logs. Get insights into billing, job performance, access patterns, data lineage, ML experiments, and model serving across your account.",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                # -----------------------------------------------------------------
                # ACCESS SCHEMA - Audit, Lineage & Network (8 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.access.assistant_events",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="event_id", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.audit",
                    column_configs=[
                        ColumnConfig(column_name="action_name", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="audit_level", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="event_date", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                        ColumnConfig(column_name="service_name", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="source_ip_address", get_example_values=True),
                        ColumnConfig(column_name="user_identity", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.clean_room_events",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="clean_room_name", get_example_values=True),
                        ColumnConfig(column_name="event_id", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.column_lineage",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="entity_id", get_example_values=True),
                        ColumnConfig(column_name="entity_run_id", get_example_values=True),
                        ColumnConfig(column_name="entity_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="event_date", get_example_values=True),
                        ColumnConfig(column_name="source_column_name", get_example_values=True),
                        ColumnConfig(column_name="source_table_catalog", get_example_values=True),
                        ColumnConfig(column_name="source_table_name", get_example_values=True),
                        ColumnConfig(column_name="source_table_schema", get_example_values=True),
                        ColumnConfig(column_name="target_column_name", get_example_values=True),
                        ColumnConfig(column_name="target_table_catalog", get_example_values=True),
                        ColumnConfig(column_name="target_table_name", get_example_values=True),
                        ColumnConfig(column_name="target_table_schema", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.outbound_network",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="event_id", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.table_lineage",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="entity_id", get_example_values=True),
                        ColumnConfig(column_name="entity_run_id", get_example_values=True),
                        ColumnConfig(column_name="entity_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="event_date", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                        ColumnConfig(column_name="source_table_catalog", get_example_values=True),
                        ColumnConfig(column_name="source_table_name", get_example_values=True),
                        ColumnConfig(column_name="source_table_schema", get_example_values=True),
                        ColumnConfig(column_name="target_table_catalog", get_example_values=True),
                        ColumnConfig(column_name="target_table_name", get_example_values=True),
                        ColumnConfig(column_name="target_table_schema", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.access.workspaces_latest",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_name", get_example_values=True),
                        ColumnConfig(column_name="workspace_url", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # BILLING SCHEMA - Usage & Costs (2 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.billing.list_prices",
                    column_configs=[
                        ColumnConfig(column_name="cloud", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="currency_code", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="price_end_time", get_example_values=True),
                        ColumnConfig(column_name="price_start_time", get_example_values=True),
                        ColumnConfig(column_name="pricing", get_example_values=True),
                        ColumnConfig(column_name="sku_name", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="usage_unit", get_example_values=True, build_value_dictionary=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.billing.usage",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="billing_origin_product", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="cloud", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="custom_tags", get_example_values=True),
                        ColumnConfig(column_name="identity_metadata", get_example_values=True),
                        ColumnConfig(column_name="record_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="sku_name", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="usage_date", get_example_values=True),
                        ColumnConfig(column_name="usage_metadata", get_example_values=True),
                        ColumnConfig(column_name="usage_quantity", get_example_values=True),
                        ColumnConfig(column_name="usage_unit", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # COMPUTE SCHEMA - Clusters, Warehouses & Nodes (5 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.compute.clusters",
                    column_configs=[
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="cluster_id", get_example_values=True),
                        ColumnConfig(column_name="cluster_name", get_example_values=True),
                        ColumnConfig(column_name="cluster_source", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="creator_id", get_example_values=True),
                        ColumnConfig(column_name="delete_time", get_example_values=True),
                        ColumnConfig(column_name="driver_node_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="node_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="owned_by", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.compute.node_timeline",
                    column_configs=[
                        ColumnConfig(column_name="cluster_id", get_example_values=True),
                        ColumnConfig(column_name="instance_id", get_example_values=True),
                        ColumnConfig(column_name="node_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="start_time", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.compute.node_types",
                    column_configs=[
                        ColumnConfig(column_name="node_type", get_example_values=True, build_value_dictionary=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.compute.warehouse_events",
                    column_configs=[
                        ColumnConfig(column_name="cluster_count", get_example_values=True),
                        ColumnConfig(column_name="event_time", get_example_values=True),
                        ColumnConfig(column_name="event_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="warehouse_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.compute.warehouses",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="delete_time", get_example_values=True),
                        ColumnConfig(column_name="warehouse_id", get_example_values=True),
                        ColumnConfig(column_name="warehouse_name", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # LAKEFLOW SCHEMA - Jobs & Pipelines (6 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.lakeflow.job_run_timeline",
                    column_configs=[
                        ColumnConfig(column_name="cleanup_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="compute_ids", get_example_values=True),
                        ColumnConfig(column_name="execution_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="job_id", get_example_values=True),
                        ColumnConfig(column_name="period_end_time", get_example_values=True),
                        ColumnConfig(column_name="period_start_time", get_example_values=True),
                        ColumnConfig(column_name="queue_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="result_state", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="run_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="run_id", get_example_values=True),
                        ColumnConfig(column_name="run_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="setup_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="termination_code", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="trigger_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.lakeflow.job_task_run_timeline",
                    column_configs=[
                        ColumnConfig(column_name="cleanup_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="compute_ids", get_example_values=True),
                        ColumnConfig(column_name="execution_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="job_id", get_example_values=True),
                        ColumnConfig(column_name="job_run_id", get_example_values=True),
                        ColumnConfig(column_name="period_end_time", get_example_values=True),
                        ColumnConfig(column_name="period_start_time", get_example_values=True),
                        ColumnConfig(column_name="result_state", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="run_id", get_example_values=True),
                        ColumnConfig(column_name="setup_duration_seconds", get_example_values=True),
                        ColumnConfig(column_name="task_key", get_example_values=True),
                        ColumnConfig(column_name="termination_code", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.lakeflow.job_tasks",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="depends_on_task_keys", get_example_values=True),
                        ColumnConfig(column_name="job_id", get_example_values=True),
                        ColumnConfig(column_name="task_key", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.lakeflow.jobs",
                    column_configs=[
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="creator_id", get_example_values=True),
                        ColumnConfig(column_name="delete_time", get_example_values=True),
                        ColumnConfig(column_name="job_id", get_example_values=True),
                        ColumnConfig(column_name="name", get_example_values=True),
                        ColumnConfig(column_name="run_as", get_example_values=True),
                        ColumnConfig(column_name="tags", get_example_values=True),
                        ColumnConfig(column_name="trigger_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.lakeflow.pipelines",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="creator_id", get_example_values=True),
                        ColumnConfig(column_name="delete_time", get_example_values=True),
                        ColumnConfig(column_name="name", get_example_values=True),
                        ColumnConfig(column_name="pipeline_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # MLFLOW SCHEMA - Experiments & Runs (3 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.mlflow.experiments_latest",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="create_time", get_example_values=True),
                        ColumnConfig(column_name="delete_time", get_example_values=True),
                        ColumnConfig(column_name="experiment_id", get_example_values=True),
                        ColumnConfig(column_name="name", get_example_values=True),
                        ColumnConfig(column_name="update_time", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.mlflow.run_metrics_history",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="experiment_id", get_example_values=True),
                        ColumnConfig(column_name="metric_name", get_example_values=True),
                        ColumnConfig(column_name="metric_time", get_example_values=True),
                        ColumnConfig(column_name="metric_value", get_example_values=True),
                        ColumnConfig(column_name="record_id", get_example_values=True),
                        ColumnConfig(column_name="run_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.mlflow.runs_latest",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="created_by", get_example_values=True),
                        ColumnConfig(column_name="end_time", get_example_values=True),
                        ColumnConfig(column_name="experiment_id", get_example_values=True),
                        ColumnConfig(column_name="run_id", get_example_values=True),
                        ColumnConfig(column_name="run_name", get_example_values=True),
                        ColumnConfig(column_name="start_time", get_example_values=True),
                        ColumnConfig(column_name="status", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # QUERY SCHEMA - Query History (1 table)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.query.history",
                    column_configs=[
                        ColumnConfig(column_name="client_application", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="compute_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="end_time", get_example_values=True),
                        ColumnConfig(column_name="error_message", get_example_values=True),
                        ColumnConfig(column_name="executed_by", get_example_values=True),
                        ColumnConfig(column_name="execution_status", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="query_hash", get_example_values=True),
                        ColumnConfig(column_name="start_time", get_example_values=True),
                        ColumnConfig(column_name="statement_type", get_example_values=True, build_value_dictionary=True),
                        ColumnConfig(column_name="total_duration_ms", get_example_values=True),
                        ColumnConfig(column_name="warehouse_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                # -----------------------------------------------------------------
                # SERVING SCHEMA - Model Serving (2 tables)
                # -----------------------------------------------------------------
                TableDataSource(
                    identifier="system.serving.endpoint_usage",
                    column_configs=[
                        ColumnConfig(column_name="account_id", get_example_values=True),
                        ColumnConfig(column_name="databricks_request_id", get_example_values=True),
                        ColumnConfig(column_name="served_entity_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
                TableDataSource(
                    identifier="system.serving.served_entities",
                    column_configs=[
                        ColumnConfig(column_name="change_time", get_example_values=True),
                        ColumnConfig(column_name="endpoint_id", get_example_values=True),
                        ColumnConfig(column_name="served_entity_id", get_example_values=True),
                        ColumnConfig(column_name="workspace_id", get_example_values=True),
                    ],
                ),
            ]
        ),
        instructions=Instructions(
            text_instructions=[
                TextInstruction(
                    content="""# Databricks System Tables Explorer

This Genie Space provides comprehensive access to Databricks platform activity across your account: billing, jobs, pipelines, compute, audit logs, lineage, ML experiments, and model serving.

## Schema Overview (25 tables)

| Schema | Tables | Primary Use |
|--------|--------|-------------|
| access | audit, table_lineage, column_lineage, workspaces_latest, assistant_events, clean_room_events, outbound_network | Security, compliance, lineage |
| billing | usage, list_prices | Cost analysis, chargeback |
| compute | clusters, warehouses, warehouse_events, node_timeline, node_types | Infrastructure monitoring |
| lakeflow | jobs, job_tasks, job_run_timeline, job_task_run_timeline, pipelines | Job & pipeline performance |
| mlflow | experiments_latest, runs_latest, run_metrics_history | ML experiment tracking |
| query | history | Query performance analysis |
| serving | served_entities, endpoint_usage | Model serving metrics |

## Key Relationships

- **Billing → Jobs/Clusters/Warehouses**: usage.usage_metadata contains job_id, cluster_id, warehouse_id for cost attribution
- **Jobs → Tasks → Runs**: jobs.job_id → job_tasks.job_id → job_task_run_timeline.task_key
- **Jobs → Runs**: jobs.job_id → job_run_timeline.job_id → job_task_run_timeline.job_run_id
- **Warehouses → Events/Queries**: warehouses.warehouse_id → warehouse_events/query.history
- **Clusters → Nodes**: clusters.cluster_id → node_timeline.cluster_id → node_types.node_type
- **Lineage**: table_lineage ↔ column_lineage via entity_id, entity_run_id
- **MLflow**: experiments_latest → runs_latest → run_metrics_history via experiment_id, run_id
- **Serving**: served_entities ↔ endpoint_usage via served_entity_id

## Important Notes

- **Retention**: 365 days (most), 180 days (mlflow), 90 days (node_timeline, endpoint_usage)
- **Scope**: Account-level, multi-workspace data
- **Timeline tables**: Long-running jobs split into hourly rows
- **Billing**: usage_metadata fields populated based on compute type (job, cluster, warehouse, endpoint)"""
                ),
            ],
            sql_functions=[],
            join_specs=[
                # ----- BILLING RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.billing.list_prices"),
                    left_column="sku_name",
                    right_column="sku_name",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.lakeflow.jobs"),
                    left_column="usage_metadata.job_id",
                    right_column="job_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.compute.clusters"),
                    left_column="usage_metadata.cluster_id",
                    right_column="cluster_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.compute.warehouses"),
                    left_column="usage_metadata.warehouse_id",
                    right_column="warehouse_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.compute.node_types"),
                    left_column="usage_metadata.node_type",
                    right_column="node_type",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.serving.served_entities"),
                    left_column="usage_metadata.endpoint_id",
                    right_column="endpoint_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.billing.usage"),
                    right=JoinTableRef(identifier="system.lakeflow.pipelines"),
                    left_column="usage_metadata.dlt_pipeline_id",
                    right_column="pipeline_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                # ----- LAKEFLOW JOBS RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.lakeflow.jobs"),
                    right=JoinTableRef(identifier="system.lakeflow.job_tasks"),
                    left_column="job_id",
                    right_column="job_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.lakeflow.jobs"),
                    right=JoinTableRef(identifier="system.lakeflow.job_run_timeline"),
                    left_column="job_id",
                    right_column="job_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.lakeflow.job_run_timeline"),
                    right=JoinTableRef(identifier="system.lakeflow.job_task_run_timeline"),
                    left_column="run_id",
                    right_column="job_run_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.lakeflow.job_tasks"),
                    right=JoinTableRef(identifier="system.lakeflow.job_task_run_timeline"),
                    left_column="task_key",
                    right_column="task_key",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                # ----- COMPUTE RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.compute.warehouses"),
                    right=JoinTableRef(identifier="system.compute.warehouse_events"),
                    left_column="warehouse_id",
                    right_column="warehouse_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.compute.clusters"),
                    right=JoinTableRef(identifier="system.compute.node_timeline"),
                    left_column="cluster_id",
                    right_column="cluster_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.compute.clusters"),
                    right=JoinTableRef(identifier="system.compute.node_types"),
                    left_column="node_type",
                    right_column="node_type",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.compute.clusters"),
                    right=JoinTableRef(identifier="system.compute.node_types"),
                    left_column="driver_node_type",
                    right_column="node_type",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.compute.node_timeline"),
                    right=JoinTableRef(identifier="system.compute.node_types"),
                    left_column="node_type",
                    right_column="node_type",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                # ----- QUERY RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.query.history"),
                    right=JoinTableRef(identifier="system.compute.warehouse_events"),
                    left_column="warehouse_id",
                    right_column="warehouse_id",
                    relationship_type=RelationshipType.MANY_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.query.history"),
                    right=JoinTableRef(identifier="system.compute.warehouses"),
                    left_column="warehouse_id",
                    right_column="warehouse_id",
                    relationship_type=RelationshipType.MANY_TO_ONE,
                ),
                # ----- LINEAGE RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.access.table_lineage"),
                    right=JoinTableRef(identifier="system.access.column_lineage"),
                    left_column="entity_id",
                    right_column="entity_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                # ----- MLFLOW RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.mlflow.experiments_latest"),
                    right=JoinTableRef(identifier="system.mlflow.runs_latest"),
                    left_column="experiment_id",
                    right_column="experiment_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                JoinSpec(
                    left=JoinTableRef(identifier="system.mlflow.runs_latest"),
                    right=JoinTableRef(identifier="system.mlflow.run_metrics_history"),
                    left_column="run_id",
                    right_column="run_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
                # ----- SERVING RELATIONSHIPS -----
                JoinSpec(
                    left=JoinTableRef(identifier="system.serving.served_entities"),
                    right=JoinTableRef(identifier="system.serving.endpoint_usage"),
                    left_column="served_entity_id",
                    right_column="served_entity_id",
                    relationship_type=RelationshipType.ONE_TO_MANY,
                ),
            ],
        ),
    ),
)


# =============================================================================
# REGISTRY OF ALL GENIE SPACES
# =============================================================================

GENIE_SPACES = [
    WORLDBANK_TABLE_FINDER,
    # WHO_DATA_EXPLORER,  # Uncomment to include
    # SYSTEM_TABLES_EXPLORER,  # Uncomment to include
]

# Map of space names to configs for selective deployment
GENIE_SPACE_REGISTRY = {
    "worldbank_table_finder": WORLDBANK_TABLE_FINDER,
    "who_data_explorer": WHO_DATA_EXPLORER,
    "system_tables_explorer": SYSTEM_TABLES_EXPLORER,
}
