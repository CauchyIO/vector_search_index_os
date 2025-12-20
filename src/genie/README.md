# Genie Space Pydantic Models

This module provides typed Pydantic models for defining and managing Databricks Genie Space configurations programmatically.

## Overview

Genie Spaces are AI-powered natural language interfaces to Unity Catalog data. These models allow you to:

- Define Genie Space configurations as code
- Version control your Genie Space configurations
- Migrate spaces between workspaces (dev → prod)
- Validate configurations before deployment

## Model Hierarchy

```
GenieSpaceConfig                 # Top-level configuration
├── space_id                     # Unique identifier (set after creation)
├── title                        # Display name
├── description                  # Optional description
├── warehouse_id                 # SQL warehouse for queries
├── source_workspace             # Source URL (for migrations)
└── serialized_space             # SerializedSpace
    ├── version                  # Schema version (currently 1)
    ├── data_sources             # DataSources
    │   └── tables[]             # List[TableDataSource]
    │       ├── identifier       # "catalog.schema.table"
    │       └── column_configs[] # List[ColumnConfig]
    │           ├── column_name
    │           ├── get_example_values
    │           └── build_value_dictionary
    └── instructions             # Instructions
        ├── text_instructions[]  # List[TextInstruction]
        │   ├── id
        │   └── content
        └── sql_functions[]      # List[SqlFunction]
            ├── id
            └── identifier       # "catalog.schema.function"
```

## Installation

Ensure pydantic is installed:

```bash
uv pip install pydantic
```

## Usage Examples

### 1. Load an Existing Genie Space from JSON

```python
from genie import GenieSpaceConfig

# Load from a JSON file
space = GenieSpaceConfig.from_json_file("genie_space.json")

print(f"Title: {space.title}")
print(f"Tables: {len(space.serialized_space.data_sources.tables)}")

# Access table details
for table in space.serialized_space.data_sources.tables:
    print(f"  - {table.identifier}")
    print(f"    Catalog: {table.catalog}")
    print(f"    Schema: {table.schema_name}")
    print(f"    Table: {table.table_name}")
```

### 2. Create a New Genie Space from Scratch

```python
from genie import (
    GenieSpaceConfig,
    SerializedSpace,
    DataSources,
    Instructions,
    TableDataSource,
    ColumnConfig,
    TextInstruction,
    SqlFunction,
)

space = GenieSpaceConfig(
    title="Sales Analytics Assistant",
    description="AI assistant for sales data analysis",
    warehouse_id="your-warehouse-id",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                TableDataSource(
                    identifier="main_catalog.sales.orders",
                    column_configs=[
                        ColumnConfig(
                            column_name="order_status",
                            get_example_values=True,
                            build_value_dictionary=True,
                        ),
                        ColumnConfig(
                            column_name="region",
                            get_example_values=True,
                            build_value_dictionary=True,
                        ),
                        ColumnConfig(
                            column_name="order_date",
                            get_example_values=True,
                        ),
                    ],
                ),
                TableDataSource(
                    identifier="main_catalog.sales.customers",
                    column_configs=[
                        ColumnConfig(
                            column_name="customer_segment",
                            get_example_values=True,
                            build_value_dictionary=True,
                        ),
                    ],
                ),
            ]
        ),
        instructions=Instructions(
            text_instructions=[
                TextInstruction(
                    content=[
                        "When analyzing sales data:\n",
                        "- Always filter by date range if not specified\n",
                        "- Format currency values with $ and 2 decimal places\n",
                        "- Group by region when showing totals\n",
                    ]
                ),
            ],
            sql_functions=[
                SqlFunction(identifier="main_catalog.sales.calculate_revenue"),
                SqlFunction(identifier="main_catalog.sales.get_top_customers"),
            ],
        ),
    ),
)

# Export to JSON file for version control
space.to_json_file("genie_spaces/sales_assistant.json")
```

### 3. Using Convenience Builders

For quick configuration, use the helper functions:

```python
from genie import (
    GenieSpaceConfig,
    SerializedSpace,
    DataSources,
    Instructions,
    quick_table,
    quick_function,
)

space = GenieSpaceConfig(
    title="Quick Setup Example",
    warehouse_id="warehouse-123",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                # Quick way to define a table with column configs
                quick_table(
                    catalog="main_catalog",
                    schema="analytics",
                    table="events",
                    example_columns=["event_type", "user_id", "timestamp"],
                    dictionary_columns=["event_type"],
                ),
                quick_table(
                    catalog="main_catalog",
                    schema="analytics",
                    table="users",
                    example_columns=["country", "plan_type"],
                    dictionary_columns=["country", "plan_type"],
                ),
            ]
        ),
        instructions=Instructions(
            sql_functions=[
                quick_function("main_catalog", "analytics", "search_events"),
                quick_function("main_catalog", "analytics", "aggregate_metrics"),
            ]
        ),
    ),
)
```

### 4. Import from Databricks SDK

```python
from databricks.sdk import WorkspaceClient
from genie import GenieSpaceConfig

# Get space from Databricks
ws = WorkspaceClient()
sdk_space = ws.genie.get_space(
    space_id="your-space-id",
    include_serialized_space=True,
)

# Convert to Pydantic model
space = GenieSpaceConfig.from_sdk(
    sdk_space,
    source_workspace="https://your-workspace.cloud.databricks.com",
)

# Now you can modify, validate, and export
space.title = "Updated Title"
space.to_json_file("exported_space.json")
```

### 5. Deploy to Databricks

```python
from databricks.sdk import WorkspaceClient
from genie import GenieSpaceConfig

# Load configuration
space = GenieSpaceConfig.from_json_file("genie_spaces/sales_assistant.json")

# Set target warehouse
space.warehouse_id = "target-warehouse-id"

# Deploy (creates if new, updates if exists)
ws = WorkspaceClient(host="https://target-workspace.cloud.databricks.com")
result = space.create_or_update(ws)

print(f"Deployed space: {result.space_id}")
```

### 6. Migrate Between Workspaces

```python
from databricks.sdk import WorkspaceClient
from genie import GenieSpaceConfig

# Source workspace
source_ws = WorkspaceClient(host="https://dev.cloud.databricks.com")

# Export from source
sdk_space = source_ws.genie.get_space(
    space_id="source-space-id",
    include_serialized_space=True,
)
space = GenieSpaceConfig.from_sdk(sdk_space, source_workspace=source_ws.config.host)

# Save for version control
space.to_json_file("migrations/sales_space.json")

# Target workspace
target_ws = WorkspaceClient(host="https://prod.cloud.databricks.com")

# Get target warehouse
warehouses = list(target_ws.warehouses.list())
space.warehouse_id = warehouses[0].id

# Clear space_id to create new (or keep to update existing)
space.space_id = None

# Deploy to target
result = space.create_or_update(target_ws)
print(f"Created in target: {result.space_id}")
```

## JSON File Format

The exported JSON format matches the structure used for version control:

```json
{
  "space_id": "01f0d8eb90771a3ea44202866b79cb57",
  "title": "WHO Data Explorer Genie Space",
  "description": "AI assistant for health data",
  "source_workspace": "https://dev.cloud.databricks.com",
  "warehouse_id": "785fcb451a18a6d9",
  "serialized_space": {
    "version": 1,
    "data_sources": {
      "tables": [
        {
          "identifier": "main_catalog.dev.indicators",
          "column_configs": [
            {
              "column_name": "indicator_name",
              "get_example_values": true,
              "build_value_dictionary": true
            }
          ]
        }
      ]
    },
    "instructions": {
      "text_instructions": [
        {
          "id": "01f0d8edb8001d59a0f5c9c49259f6bc",
          "content": ["Instruction text here..."]
        }
      ],
      "sql_functions": [
        {
          "id": "01f0d8ebb1f41c6e9da767ce1e8f0279",
          "identifier": "main_catalog.dev.search_indicators"
        }
      ]
    }
  }
}
```

## Column Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `column_name` | str | Name of the column (required) |
| `get_example_values` | bool | Fetch example values for AI context |
| `build_value_dictionary` | bool | Build a dictionary for filtering/autocomplete |

**Recommendations:**
- Enable `get_example_values` for columns users will query by
- Enable `build_value_dictionary` for categorical columns with limited values
- Skip both for high-cardinality columns (IDs, timestamps) unless needed

## API Reference

### GenieSpaceConfig

Main configuration class.

**Methods:**
- `from_json(json_str)` - Parse from JSON string
- `from_json_file(path)` - Load from file
- `from_sdk(genie_space, source_workspace)` - Convert from SDK object
- `to_json(indent=2)` - Serialize to JSON string
- `to_json_file(path)` - Write to file
- `get_serialized_space_json()` - Get inner config as JSON for API
- `create(workspace_client)` - Create new space
- `update(workspace_client)` - Update existing space
- `create_or_update(workspace_client)` - Upsert by title match

### Convenience Functions

- `quick_table(catalog, schema, table, columns, example_columns, dictionary_columns)` - Quick table builder
- `quick_function(catalog, schema, function)` - Quick function reference

## Integration with dbrcdk

These models follow the same patterns as the `dbrcdk` package for Unity Catalog governance. You can use them together:

```python
from dbrcdk.models import Catalog, Schema, Function
from genie import GenieSpaceConfig, quick_table, quick_function

# Define your catalog structure with dbrcdk
catalog = Catalog(name="analytics")
schema = Schema(name="sales", catalog=catalog)

# Reference the same tables in your Genie Space
space = GenieSpaceConfig(
    title="Sales Assistant",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                quick_table(
                    catalog.name,
                    schema.name,
                    "orders",
                    example_columns=["status"],
                )
            ]
        )
    )
)
```
