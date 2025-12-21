# Genie Space Management

This module provides tools for defining and deploying Databricks Genie Spaces as code.

## Overview

- `models.py` - Pydantic models for type-safe Genie Space configuration
- `genie_space_definitions.py` - Genie Space definitions (add your spaces here)
- `deploy_genie_spaces.py` - CLI tool to deploy spaces to Databricks
- `genie_space_table_functions.sql` - SQL functions for managing Genie Space tables at runtime
- `extract_usage_metadata.py` - Extract metadata from tables for enriching Genie Space descriptions

## Quick Start

```bash
# Deploy all spaces in GENIE_SPACES list
uv run python src/genie/deploy_genie_spaces.py -p <profile>

# Deploy specific space
uv run python src/genie/deploy_genie_spaces.py -p <profile> -s worldbank_table_finder

# Dry run (show what would be deployed)
uv run python src/genie/deploy_genie_spaces.py -p <profile> --dry-run

# List available spaces
uv run python src/genie/deploy_genie_spaces.py --list
```

## Defining a Genie Space

```python
from genie.models import (
    GenieSpaceConfig,
    SerializedSpace,
    DataSources,
    TableDataSource,
    ColumnConfig,
    Instructions,
    TextInstruction,
    SqlFunction,
)

MY_SPACE = GenieSpaceConfig(
    title="My Analytics Space",
    description="Description shown to users",
    serialized_space=SerializedSpace(
        data_sources=DataSources(
            tables=[
                TableDataSource(
                    identifier="catalog.schema.table",
                    column_configs=[
                        # Sort alphabetically by column_name
                        ColumnConfig(column_name="col1", get_example_values=True),
                        ColumnConfig(column_name="col2", build_value_dictionary=True),
                    ],
                ),
            ]
        ),
        instructions=Instructions(
            text_instructions=[
                TextInstruction(content="Instructions for the AI assistant..."),
            ],
            sql_functions=[
                # Sort alphabetically by identifier
                SqlFunction(identifier="catalog.schema.my_function"),
            ],
        ),
    ),
)
```

## Genie API Requirements

The Databricks Genie API has specific (undocumented) requirements:

### sql_functions
- **MUST include an `id` field** - 32-character hex string
- **MUST be sorted by `(id, identifier)` tuple**
- Without proper IDs and sorting, the API returns "Internal Error"

The models handle this automatically:
- `SqlFunction` generates deterministic IDs using MD5 hash of the identifier
- `Instructions.to_dict()` sorts functions by `(id, identifier)`

### text_instructions
- Should **NOT** include an `id` field - the API generates it
- Content can be a string or list of strings

### column_configs
- Should be sorted alphabetically by `column_name`
- The API may reject unsorted columns

### Fetching Existing Space Config

To see how an existing space is configured:

```python
from databricks.sdk import WorkspaceClient

client = WorkspaceClient(profile='my-profile')
space = client.genie.get_space(
    space_id='your-space-id',
    include_serialized_space=True  # Required to get the config!
)
print(space.serialized_space)
```

## SQL Functions for Runtime Management

The `genie_space_table_functions.sql` file defines SQL functions that can be called from within a Genie Space to manage tables dynamically:

```sql
-- Add a table to a Genie Space
SELECT main_catalog.dev.add_table_to_genie_space('<space_id>', 'catalog.schema.table')

-- Add table with column configurations
SELECT main_catalog.dev.add_table_with_columns_to_genie_space(
  '<space_id>',
  'catalog.schema.table',
  'col1:true:false,col2:true:true'  -- name:get_examples:build_dictionary
)

-- List tables in a Genie Space
SELECT main_catalog.dev.list_tables_in_genie_space('<space_id>')

-- Remove a table from a Genie Space
SELECT main_catalog.dev.remove_table_from_genie_space('<space_id>', 'catalog.schema.table')
```

## Enriching Genie Space with Table Metadata

Genie Spaces work best when they understand not just the schema of a table, but the actual data within it. For tables with categorical columns (like `sku_name` or `billing_origin_product`), knowing which values exist helps Genie generate accurate queries.

The `extract_usage_metadata.py` script queries a table to discover its data diversity—what values appear in each column, how they're distributed, and which fields are populated. This information can then be incorporated into the Genie Space description or instructions, giving the AI assistant context about what the data actually contains rather than just its structure.

## Troubleshooting

### "Internal Error" on deploy
- Check that sql_functions have proper IDs (32-char hex)
- Ensure sql_functions are sorted by (id, identifier)
- Try deploying with a single function first to isolate the issue

### "sql_functions must be sorted by (id, identifier)"
- The models should handle this automatically
- If you see this error, check that you're using the latest models.py

### Space updates fail but creates work
- Existing space may be in a corrupted state
- Try creating a new space with a different title
- Delete the old space via UI if needed
