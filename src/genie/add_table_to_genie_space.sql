-- =============================================================================
-- SQL Function: add_table_to_worldbank_genie_space
--
-- Purpose: Adds a table to the Worldbank Genie Space via the Databricks SDK
-- Usage: SELECT main_catalog.dev.add_table_to_worldbank_genie_space('catalog.schema.table_name')
-- =============================================================================

CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_to_worldbank_genie_space(
    table_identifier STRING COMMENT 'Full Unity Catalog path: catalog.schema.table_name'
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Adds a table to the Worldbank Table Finder Genie Space. Returns status message.'
AS $$
import json
import re
from databricks.sdk import WorkspaceClient

# Configuration
GENIE_SPACE_TITLE = "World Bank Table Finder"

def validate_table_identifier(identifier: str) -> bool:
    """Validate that the table identifier follows catalog.schema.table pattern."""
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def find_genie_space_by_title(client: WorkspaceClient, title: str):
    """Find a Genie Space by title."""
    spaces = client.genie.list_spaces()
    for space in spaces.spaces or []:
        if space.title == title:
            return space
    return None

def add_table_to_space(serialized_space_json: str, table_identifier: str) -> str:
    """Add a table to the serialized space configuration."""
    if serialized_space_json:
        space_data = json.loads(serialized_space_json)
    else:
        space_data = {"version": 1, "data_sources": {"tables": []}, "instructions": {}}

    # Ensure data_sources.tables exists
    if "data_sources" not in space_data:
        space_data["data_sources"] = {"tables": []}
    if "tables" not in space_data["data_sources"]:
        space_data["data_sources"]["tables"] = []

    # Check if table already exists
    existing_tables = [t.get("identifier") for t in space_data["data_sources"]["tables"]]
    if table_identifier in existing_tables:
        return None  # Table already exists

    # Add the new table with basic column config
    new_table = {
        "identifier": table_identifier,
        "column_configs": []  # Will use defaults
    }
    space_data["data_sources"]["tables"].append(new_table)

    return json.dumps(space_data)

# Main execution
if not validate_table_identifier(table_identifier):
    return f"ERROR: Invalid table identifier format. Expected 'catalog.schema.table', got '{table_identifier}'"

# Initialize WorkspaceClient (uses ambient authentication)
client = WorkspaceClient()

# Find the Genie Space
genie_space = find_genie_space_by_title(client, GENIE_SPACE_TITLE)
if not genie_space:
    return f"ERROR: Genie Space '{GENIE_SPACE_TITLE}' not found"

# Add table to the space configuration
updated_serialized = add_table_to_space(genie_space.serialized_space, table_identifier)
if updated_serialized is None:
    return f"INFO: Table '{table_identifier}' already exists in the Genie Space"

# Update the Genie Space
client.genie.update_space(
    space_id=genie_space.space_id,
    title=genie_space.title,
    description=genie_space.description,
    warehouse_id=genie_space.warehouse_id,
    serialized_space=updated_serialized
)

return f"SUCCESS: Added table '{table_identifier}' to Genie Space '{GENIE_SPACE_TITLE}'"
$$;

-- Grant execute permission (adjust principal as needed)
-- GRANT EXECUTE ON FUNCTION main_catalog.dev.add_table_to_worldbank_genie_space TO `users`;
