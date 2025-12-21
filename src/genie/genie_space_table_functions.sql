-- Databricks notebook source
-- MAGIC %md
-- MAGIC # SQL Functions for Managing Genie Space Tables
-- MAGIC
-- MAGIC **Architecture:**
-- MAGIC - Internal Python UDFs (`*_impl`) receive OAuth credentials as parameters
-- MAGIC - Public SQL wrapper functions inject secrets using `secret()` function
-- MAGIC - This keeps secret scope/key names hidden from callers
-- MAGIC
-- MAGIC **Prerequisites:**
-- MAGIC - Databricks SDK must be available (typically pre-installed)
-- MAGIC - Caller must have permissions to modify Genie Spaces
-- MAGIC - Service Principal credentials stored in secret scope `genie_oauth_spn`:
-- MAGIC   - `client_id`: The SPN client ID
-- MAGIC   - `secret`: The SPN client secret

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## DROP existing functions (required to change from Python UDF to SQL function)

-- COMMAND ----------

DROP FUNCTION IF EXISTS main_catalog.dev.add_table_to_genie_space

-- COMMAND ----------

DROP FUNCTION IF EXISTS main_catalog.dev.add_table_to_worldbank_genie_space

-- COMMAND ----------

DROP FUNCTION IF EXISTS main_catalog.dev.remove_table_from_genie_space

-- COMMAND ----------

DROP FUNCTION IF EXISTS main_catalog.dev.list_tables_in_genie_space

-- COMMAND ----------

DROP FUNCTION IF EXISTS main_catalog.dev.add_table_with_columns_to_genie_space

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## INTERNAL: _add_table_to_genie_space_impl

-- COMMAND ----------

CREATE OR REPLACE FUNCTION main_catalog.dev._add_table_to_genie_space_impl(
    space_id STRING,
    table_identifier STRING,
    client_id STRING,
    client_secret STRING
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Internal: Adds a table to a Genie Space. Use add_table_to_genie_space instead.'
AS $$
import json
import re
import requests
from databricks.sdk import WorkspaceClient

DATABRICKS_HOST = "https://dbc-930eaa5c-35a0.cloud.databricks.com"

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

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

# Use WorkspaceClient for auth, get token for REST calls
client = WorkspaceClient(host=DATABRICKS_HOST, client_id=client_id, client_secret=client_secret)
auth_headers = client.config.authenticate()
if callable(auth_headers):
    auth_headers = auth_headers()
token = auth_headers.get("Authorization", "").replace("Bearer ", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get space with serialized config via REST (SDK doesn't support include_serialized_space)
resp = requests.get(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    params={"include_serialized_space": "true"}
)
resp.raise_for_status()
space = resp.json()

updated_json, was_added = add_table_to_serialized_space(space.get("serialized_space"), table_identifier)
if not was_added:
    return f"INFO: Table '{table_identifier}' already exists in space"

# Update space via REST
update_resp = requests.patch(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    json={
        "title": space["title"],
        "description": space.get("description"),
        "warehouse_id": space.get("warehouse_id"),
        "serialized_space": updated_json
    }
)
update_resp.raise_for_status()
return f"SUCCESS: Added '{table_identifier}' to Genie Space"
$$

-- COMMAND ----------

-- Public wrapper that injects secrets
CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_to_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path: catalog.schema.table_name'
)
RETURNS STRING
COMMENT 'Adds a table to a Genie Space by space_id. Returns status message.'
RETURN SELECT main_catalog.dev._add_table_to_genie_space_impl(
    space_id,
    table_identifier,
    secret('genie_oauth_spn', 'client_id'),
    secret('genie_oauth_spn', 'secret')
)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## INTERNAL: _add_table_to_worldbank_genie_space_impl

-- COMMAND ----------

CREATE OR REPLACE FUNCTION main_catalog.dev._add_table_to_worldbank_genie_space_impl(
    table_identifier STRING,
    client_id STRING,
    client_secret STRING
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Internal: Adds a table to the World Bank Table Finder. Use add_table_to_worldbank_genie_space instead.'
AS $$
import json
import re
import requests
from databricks.sdk import WorkspaceClient

DATABRICKS_HOST = "https://dbc-930eaa5c-35a0.cloud.databricks.com"
GENIE_SPACE_TITLE = "World Bank Table Finder"

def validate_table_identifier(identifier: str) -> bool:
    pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, identifier))

def find_space_by_title(host, headers, title):
    resp = requests.get(f"{host}/api/2.0/genie/spaces", headers=headers)
    resp.raise_for_status()
    for space in resp.json().get("spaces", []):
        if space.get("title") == title:
            detail_resp = requests.get(
                f"{host}/api/2.0/genie/spaces/{space['space_id']}",
                headers=headers,
                params={"include_serialized_space": "true"}
            )
            detail_resp.raise_for_status()
            return detail_resp.json()
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

# Use WorkspaceClient for auth
client = WorkspaceClient(host=DATABRICKS_HOST, client_id=client_id, client_secret=client_secret)
auth_headers = client.config.authenticate()
if callable(auth_headers):
    auth_headers = auth_headers()
token = auth_headers.get("Authorization", "").replace("Bearer ", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

space = find_space_by_title(DATABRICKS_HOST, headers, GENIE_SPACE_TITLE)
if not space:
    return f"ERROR: Genie Space '{GENIE_SPACE_TITLE}' not found"

updated_json, was_added = add_table_to_serialized_space(space.get("serialized_space"), table_identifier)
if not was_added:
    return f"INFO: Table '{table_identifier}' already exists in space"

update_resp = requests.patch(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space['space_id']}",
    headers=headers,
    json={
        "title": space["title"],
        "description": space.get("description"),
        "warehouse_id": space.get("warehouse_id"),
        "serialized_space": updated_json
    }
)
update_resp.raise_for_status()
return f"SUCCESS: Added '{table_identifier}' to '{GENIE_SPACE_TITLE}'"
$$

-- COMMAND ----------

-- Public wrapper
CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_to_worldbank_genie_space(
    table_identifier STRING COMMENT 'Full Unity Catalog path: catalog.schema.table_name'
)
RETURNS STRING
COMMENT 'Adds a table to the World Bank Table Finder Genie Space.'
RETURN SELECT main_catalog.dev._add_table_to_worldbank_genie_space_impl(
    table_identifier,
    secret('genie_oauth_spn', 'client_id'),
    secret('genie_oauth_spn', 'secret')
)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## INTERNAL: _remove_table_from_genie_space_impl

-- COMMAND ----------

CREATE OR REPLACE FUNCTION main_catalog.dev._remove_table_from_genie_space_impl(
    space_id STRING,
    table_identifier STRING,
    client_id STRING,
    client_secret STRING
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Internal: Removes a table from a Genie Space.'
AS $$
import json
import re
import requests
from databricks.sdk import WorkspaceClient

DATABRICKS_HOST = "https://dbc-930eaa5c-35a0.cloud.databricks.com"

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

# Use WorkspaceClient for auth
client = WorkspaceClient(host=DATABRICKS_HOST, client_id=client_id, client_secret=client_secret)
auth_headers = client.config.authenticate()
if callable(auth_headers):
    auth_headers = auth_headers()
token = auth_headers.get("Authorization", "").replace("Bearer ", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get space via REST
resp = requests.get(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    params={"include_serialized_space": "true"}
)
resp.raise_for_status()
space = resp.json()

updated_json, was_removed = remove_table_from_serialized_space(space.get("serialized_space"), table_identifier)
if not was_removed:
    return f"INFO: Table '{table_identifier}' not found in space"

# Update space via REST
update_resp = requests.patch(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    json={
        "title": space["title"],
        "description": space.get("description"),
        "warehouse_id": space.get("warehouse_id"),
        "serialized_space": updated_json
    }
)
update_resp.raise_for_status()
return f"SUCCESS: Removed '{table_identifier}' from Genie Space"
$$

-- COMMAND ----------

-- Public wrapper
CREATE OR REPLACE FUNCTION main_catalog.dev.remove_table_from_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path to remove'
)
RETURNS STRING
COMMENT 'Removes a table from a Genie Space. Returns status message.'
RETURN SELECT main_catalog.dev._remove_table_from_genie_space_impl(
    space_id,
    table_identifier,
    secret('genie_oauth_spn', 'client_id'),
    secret('genie_oauth_spn', 'secret')
)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## INTERNAL: _list_tables_in_genie_space_impl

-- COMMAND ----------

CREATE OR REPLACE FUNCTION main_catalog.dev._list_tables_in_genie_space_impl(
    space_id STRING,
    client_id STRING,
    client_secret STRING
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Internal: Lists all tables in a Genie Space.'
AS $$
import json
import requests
from databricks.sdk import WorkspaceClient

DATABRICKS_HOST = "https://dbc-930eaa5c-35a0.cloud.databricks.com"

# Use WorkspaceClient for auth
client = WorkspaceClient(host=DATABRICKS_HOST, client_id=client_id, client_secret=client_secret)
auth_headers = client.config.authenticate()
if callable(auth_headers):
    auth_headers = auth_headers()
token = auth_headers.get("Authorization", "").replace("Bearer ", "")
headers = {"Authorization": f"Bearer {token}"}

# Get space with serialized config via REST
resp = requests.get(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    params={"include_serialized_space": "true"}
)
resp.raise_for_status()
space = resp.json()

serialized = space.get("serialized_space")
if not serialized:
    return "[]"

data = json.loads(serialized)
tables = data.get("data_sources", {}).get("tables", [])
identifiers = [t.get("identifier") for t in tables]
return json.dumps(identifiers)
$$

-- COMMAND ----------

-- Public wrapper
CREATE OR REPLACE FUNCTION main_catalog.dev.list_tables_in_genie_space(
    space_id STRING COMMENT 'The Genie Space ID'
)
RETURNS STRING
COMMENT 'Lists all tables in a Genie Space as JSON array.'
RETURN SELECT main_catalog.dev._list_tables_in_genie_space_impl(
    space_id,
    secret('genie_oauth_spn', 'client_id'),
    secret('genie_oauth_spn', 'secret')
)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## INTERNAL: _add_table_with_columns_to_genie_space_impl

-- COMMAND ----------

CREATE OR REPLACE FUNCTION main_catalog.dev._add_table_with_columns_to_genie_space_impl(
    space_id STRING,
    table_identifier STRING,
    column_configs STRING,
    client_id STRING,
    client_secret STRING
)
RETURNS STRING
LANGUAGE PYTHON
DETERMINISTIC
COMMENT 'Internal: Adds a table with column configs to a Genie Space.'
AS $$
import json
import re
import requests
from databricks.sdk import WorkspaceClient

DATABRICKS_HOST = "https://dbc-930eaa5c-35a0.cloud.databricks.com"

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

# Use WorkspaceClient for auth
client = WorkspaceClient(host=DATABRICKS_HOST, client_id=client_id, client_secret=client_secret)
auth_headers = client.config.authenticate()
if callable(auth_headers):
    auth_headers = auth_headers()
token = auth_headers.get("Authorization", "").replace("Bearer ", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get space via REST
resp = requests.get(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    params={"include_serialized_space": "true"}
)
resp.raise_for_status()
space = resp.json()

cols = parse_column_configs(column_configs) if column_configs else []
updated_json, _ = add_table_to_serialized_space(space.get("serialized_space"), table_identifier, cols)

# Update space via REST
update_resp = requests.patch(
    f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}",
    headers=headers,
    json={
        "title": space["title"],
        "description": space.get("description"),
        "warehouse_id": space.get("warehouse_id"),
        "serialized_space": updated_json
    }
)
update_resp.raise_for_status()
return f"SUCCESS: Added '{table_identifier}' with {len(cols)} column configs"
$$

-- COMMAND ----------

-- Public wrapper
CREATE OR REPLACE FUNCTION main_catalog.dev.add_table_with_columns_to_genie_space(
    space_id STRING COMMENT 'The Genie Space ID',
    table_identifier STRING COMMENT 'Full Unity Catalog path',
    column_configs STRING COMMENT 'Comma-separated column configs: name:get_examples:build_dictionary'
)
RETURNS STRING
COMMENT 'Adds a table with column configs to a Genie Space.'
RETURN SELECT main_catalog.dev._add_table_with_columns_to_genie_space_impl(
    space_id,
    table_identifier,
    column_configs,
    secret('genie_oauth_spn', 'client_id'),
    secret('genie_oauth_spn', 'secret')
)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Example Usage

-- COMMAND ----------

-- Add a simple table to specific space:
-- SELECT main_catalog.dev.add_table_to_genie_space(
--   '01234567-89ab-cdef-0123-456789abcdef',
--   'main_catalog.worldbank.gdp_data'
-- )

-- COMMAND ----------

-- Add a table to World Bank Table Finder:
-- SELECT main_catalog.dev.add_table_to_worldbank_genie_space('main_catalog.worldbank.gdp_data')

-- COMMAND ----------

-- Add table with column configs:
-- SELECT main_catalog.dev.add_table_with_columns_to_genie_space(
--   '<space_id>',
--   'main_catalog.worldbank.indicators',
--   'indicator_id:true:false,name:true:true'
-- )

-- COMMAND ----------

-- List current tables:
-- SELECT main_catalog.dev.list_tables_in_genie_space('<space_id>')

-- COMMAND ----------

-- Remove a table:
-- SELECT main_catalog.dev.remove_table_from_genie_space('<space_id>', 'main_catalog.worldbank.old_table')
