-- =============================================================================
-- SQL Functions for Managing Genie Space Tables
--
-- These functions use inlined Python to call the Databricks WorkspaceClient
-- and manage tables in Genie Spaces.
--
-- Prerequisites:
-- - Databricks SDK must be available (typically pre-installed)
-- - Caller must have permissions to modify Genie Spaces
-- - Ambient authentication (AAD/PAT) must be configured
-- =============================================================================


-- =============================================================================
-- FUNCTION: add_table_to_genie_space
--
-- Adds a table to a Genie Space by space_id. This is the more precise version
-- when you know the exact space_id.
--
-- Example:
--   SELECT main_catalog.dev.add_table_to_genie_space(
--     '01234567-89ab-cdef-0123-456789abcdef',
--     'main_catalog.worldbank.population_data'
--   )
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_to_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path: catalog.schema.table_name'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Adds a table to a Genie Space by space_id. Returns status message.'
AS $$
import json
import re
from databricks.sdk import WorkspaceClient

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def add_table_to_serialized_space(serialized_json: str, table_id: str) -> tuple:
    """Returns (updated_json, was_added)"""
    if serialized_json:
        data = json.loads(serialized_json)
    else:
        data = {"version": 1, "data_sources": {"tables": []}, "instructions": {}}

    if "data_sources" not in data:
        data["data_sources"] = {"tables": []}
    if "tables" not in data["data_sources"]:
        data["data_sources"]["tables"] = []

    existing = [t.get("identifier") for t in data["data_sources"]["tables"]]
    if table_id in existing:
        return None, False

    data["data_sources"]["tables"].append({
        "identifier": table_id,
        "column_configs": []
    })
    return json.dumps(data), True

if not validate_table_identifier(table_identifier):
    return f"ERROR: Invalid format. Expected 'catalog.schema.table', got '{table_identifier}'"

client = WorkspaceClient()
space = client.genie.get_space(space_id)

updated_json, was_added = add_table_to_serialized_space(space.serialized_space, table_identifier)
if not was_added:
    return f"INFO: Table '{table_identifier}' already exists in space"

client.genie.update_space(
    space_id=space_id,
    title=space.title,
    description=space.description,
    warehouse_id=space.warehouse_id,
    serialized_space=updated_json
)
return f"SUCCESS: Added '{table_identifier}' to Genie Space"
$$;


-- =============================================================================
-- FUNCTION: add_table_to_worldbank_genie_space
--
-- Convenience function that adds a table to the World Bank Table Finder space.
-- Finds the space by title automatically.
--
-- Example:
--   SELECT main_catalog.dev.add_table_to_worldbank_genie_space(
--     'main_catalog.worldbank.gdp_growth'
--   )
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_to_worldbank_genie_space(
    table_identifier STRING COMMENT 'Full Unity Catalog path: catalog.schema.table_name'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Adds a table to the Worldbank Table Finder Genie Space.'
AS $$
import json
import re
from databricks.sdk import WorkspaceClient

GENIE_SPACE_TITLE = "World Bank Table Finder"

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def find_space_by_title(client, title):
    spaces = client.genie.list_spaces()
    for space in spaces.spaces or []:
        if space.title == title:
            return space
    return None

def add_table_to_serialized_space(serialized_json: str, table_id: str) -> tuple:
    if serialized_json:
        data = json.loads(serialized_json)
    else:
        data = {"version": 1, "data_sources": {"tables": []}, "instructions": {}}

    if "data_sources" not in data:
        data["data_sources"] = {"tables": []}
    if "tables" not in data["data_sources"]:
        data["data_sources"]["tables"] = []

    existing = [t.get("identifier") for t in data["data_sources"]["tables"]]
    if table_id in existing:
        return None, False

    data["data_sources"]["tables"].append({
        "identifier": table_id,
        "column_configs": []
    })
    return json.dumps(data), True

if not validate_table_identifier(table_identifier):
    return f"ERROR: Invalid format. Expected 'catalog.schema.table', got '{table_identifier}'"

client = WorkspaceClient()
space = find_space_by_title(client, GENIE_SPACE_TITLE)
if not space:
    return f"ERROR: Genie Space '{GENIE_SPACE_TITLE}' not found"

updated_json, was_added = add_table_to_serialized_space(space.serialized_space, table_identifier)
if not was_added:
    return f"INFO: Table '{table_identifier}' already exists in space"

client.genie.update_space(
    space_id=space.space_id,
    title=space.title,
    description=space.description,
    warehouse_id=space.warehouse_id,
    serialized_space=updated_json
)
return f"SUCCESS: Added '{table_identifier}' to '{GENIE_SPACE_TITLE}'"
$$;


-- =============================================================================
-- FUNCTION: remove_table_from_genie_space
--
-- Removes a table from a Genie Space by space_id.
--
-- Example:
--   SELECT main_catalog.dev.remove_table_from_genie_space(
--     '01234567-89ab-cdef-0123-456789abcdef',
--     'main_catalog.worldbank.population_data'
--   )
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.remove_table_from_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path to remove'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Removes a table from a Genie Space. Returns status message.'
AS $$
import json
import re
from databricks.sdk import WorkspaceClient

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def remove_table_from_serialized_space(serialized_json: str, table_id: str) -> tuple:
    if not serialized_json:
        return None, False

    data = json.loads(serialized_json)
    tables = data.get("data_sources", {}).get("tables", [])
    original_count = len(tables)
    tables = [t for t in tables if t.get("identifier") != table_id]

    if len(tables) == original_count:
        return None, False

    data["data_sources"]["tables"] = tables
    return json.dumps(data), True

if not validate_table_identifier(table_identifier):
    return f"ERROR: Invalid format. Expected 'catalog.schema.table', got '{table_identifier}'"

client = WorkspaceClient()
space = client.genie.get_space(space_id)

updated_json, was_removed = remove_table_from_serialized_space(space.serialized_space, table_identifier)
if not was_removed:
    return f"INFO: Table '{table_identifier}' not found in space"

client.genie.update_space(
    space_id=space_id,
    title=space.title,
    description=space.description,
    warehouse_id=space.warehouse_id,
    serialized_space=updated_json
)
return f"SUCCESS: Removed '{table_identifier}' from Genie Space"
$$;


-- =============================================================================
-- FUNCTION: list_tables_in_genie_space
--
-- Lists all tables currently configured in a Genie Space.
--
-- Example:
--   SELECT main_catalog.dev.list_tables_in_genie_space(
--     '01234567-89ab-cdef-0123-456789abcdef'
--   )
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.list_tables_in_genie_space(
    space_id STRING COMMENT 'The Genie Space ID'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Lists all tables in a Genie Space as JSON array.'
AS $$
import json
from databricks.sdk import WorkspaceClient

client = WorkspaceClient()
space = client.genie.get_space(space_id)

if not space.serialized_space:
    return "[]"

data = json.loads(space.serialized_space)
tables = data.get("data_sources", {}).get("tables", [])
identifiers = [t.get("identifier") for t in tables]
return json.dumps(identifiers)
$$;


-- =============================================================================
-- FUNCTION: add_table_with_columns_to_genie_space
--
-- Adds a table to a Genie Space with specific column configurations.
-- Columns should be comma-separated, with optional flags:
--   column_name:examples:dictionary
--
-- Example:
--   SELECT main_catalog.dev.add_table_with_columns_to_genie_space(
--     '01234567-89ab-cdef-0123-456789abcdef',
--     'main_catalog.worldbank.indicators',
--     'indicator_id:true:false,indicator_name:true:true,description:true:false'
--   )
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_with_columns_to_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path',
    column_configs STRING COMMENT 'Comma-separated column configs: name:get_examples:build_dictionary'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Adds a table with column configs to a Genie Space.'
AS $$
import json
import re
from databricks.sdk import WorkspaceClient

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def parse_column_configs(config_str: str) -> list:
    configs = []
    for item in config_str.split(","):
        parts = item.strip().split(":")
        if len(parts) >= 1:
            col = {"column_name": parts[0]}
            if len(parts) >= 2:
                col["get_example_values"] = parts[1].lower() == "true"
            if len(parts) >= 3:
                col["build_value_dictionary"] = parts[2].lower() == "true"
            configs.append(col)
    return configs

def add_table_to_serialized_space(serialized_json: str, table_id: str, cols: list) -> tuple:
    if serialized_json:
        data = json.loads(serialized_json)
    else:
        data = {"version": 1, "data_sources": {"tables": []}, "instructions": {}}

    if "data_sources" not in data:
        data["data_sources"] = {"tables": []}
    if "tables" not in data["data_sources"]:
        data["data_sources"]["tables"] = []

    # Remove existing table if present (to allow updating column configs)
    data["data_sources"]["tables"] = [
        t for t in data["data_sources"]["tables"]
        if t.get("identifier") != table_id
    ]

    data["data_sources"]["tables"].append({
        "identifier": table_id,
        "column_configs": cols
    })
    return json.dumps(data), True

if not validate_table_identifier(table_identifier):
    return f"ERROR: Invalid format. Expected 'catalog.schema.table', got '{table_identifier}'"

client = WorkspaceClient()
space = client.genie.get_space(space_id)
cols = parse_column_configs(column_configs) if column_configs else []

updated_json, _ = add_table_to_serialized_space(space.serialized_space, table_identifier, cols)

client.genie.update_space(
    space_id=space_id,
    title=space.title,
    description=space.description,
    warehouse_id=space.warehouse_id,
    serialized_space=updated_json
)
return f"SUCCESS: Added '{table_identifier}' with {len(cols)} column configs"
$$;


-- =============================================================================
-- EXAMPLE USAGE
-- =============================================================================

-- Add a simple table:
-- SELECT main_catalog.dev.add_table_to_worldbank_genie_space('main_catalog.worldbank.gdp_data');

-- Add table with column configs:
-- SELECT main_catalog.dev.add_table_with_columns_to_genie_space(
--   '<space_id>',
--   'main_catalog.worldbank.indicators',
--   'indicator_id:true:false,name:true:true'
-- );

-- List current tables:
-- SELECT main_catalog.dev.list_tables_in_genie_space('<space_id>');

-- Remove a table:
-- SELECT main_catalog.dev.remove_table_from_genie_space('<space_id>', 'main_catalog.worldbank.old_table');
