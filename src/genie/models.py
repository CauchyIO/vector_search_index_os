"""
Pydantic models for Databricks Genie Space configuration.

This module provides typed Pydantic models for defining and managing
Genie Space configurations. These models wrap the Databricks SDK's
GenieSpace dataclass and provide:
- Type-safe configuration definition
- JSON serialization/deserialization
- Validation of configuration structure
- Conversion to/from SDK types

IMPORTANT - Genie API Requirements:
-----------------------------------
The Databricks Genie API has specific requirements for the serialized_space JSON:

1. sql_functions MUST include an 'id' field (32-char hex string)
2. sql_functions MUST be sorted by (id, identifier) tuple
3. text_instructions should NOT include an 'id' field (API generates it)
4. column_configs should be sorted alphabetically by column_name

This module handles these requirements automatically:
- SqlFunction generates deterministic IDs using MD5 hash of identifier
- Instructions.to_dict() sorts sql_functions by (id, identifier)

To fetch an existing space's config for reference:
    space = client.genie.get_space(space_id, include_serialized_space=True)

Usage:
    from genie.models import GenieSpaceConfig, TableDataSource, ColumnConfig

    # Define a Genie Space
    space = GenieSpaceConfig(
        title="My Analytics Space",
        warehouse_id="abc123",
        serialized_space=SerializedSpace(
            data_sources=DataSources(
                tables=[
                    TableDataSource(
                        identifier="catalog.schema.table",
                        column_configs=[
                            ColumnConfig(column_name="id", get_example_values=True)
                        ]
                    )
                ]
            )
        )
    )

    # Export to JSON
    json_str = space.to_json()

    # Import from SDK
    space = GenieSpaceConfig.from_sdk(sdk_genie_space)
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


# =============================================================================
# BASE CONFIGURATION
# =============================================================================

class BaseGenieModel(BaseModel):
    """
    Base model for all Genie Space configuration objects.

    Provides standard Pydantic v2 configuration for consistent behavior.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        populate_by_name=True,
        use_enum_values=False,
        str_strip_whitespace=True,
        extra="allow",  # Allow extra fields for forward compatibility
    )


# =============================================================================
# COLUMN CONFIGURATION
# =============================================================================

class ColumnConfig(BaseGenieModel):
    """
    Configuration for a single column in a Genie Space table.

    Defines how Genie should handle the column for AI-powered queries.

    Attributes:
        column_name: Name of the column in the source table
        get_example_values: Whether to fetch example values for AI context
        build_value_dictionary: Whether to build a value dictionary for filtering
    """
    column_name: str = Field(
        ...,
        description="Name of the column in the source table"
    )
    get_example_values: Optional[bool] = Field(
        None,
        description="Whether to fetch example values for AI context"
    )
    build_value_dictionary: Optional[bool] = Field(
        None,
        description="Whether to build a value dictionary for filtering"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {"column_name": self.column_name}
        if self.get_example_values is not None:
            result["get_example_values"] = self.get_example_values
        if self.build_value_dictionary is not None:
            result["build_value_dictionary"] = self.build_value_dictionary
        return result


# =============================================================================
# TABLE DATA SOURCE
# =============================================================================

class TableDataSource(BaseGenieModel):
    """
    Configuration for a table data source in a Genie Space.

    Defines a Unity Catalog table that Genie can query against.

    Attributes:
        identifier: Full Unity Catalog path (catalog.schema.table)
        column_configs: List of column configurations
    """
    identifier: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$',
        description="Full Unity Catalog path (catalog.schema.table)"
    )
    column_configs: List[ColumnConfig] = Field(
        default_factory=list,
        description="Column-specific configurations"
    )

    @computed_field
    @property
    def catalog(self) -> str:
        """Extract catalog name from identifier."""
        return self.identifier.split(".")[0]

    @computed_field
    @property
    def schema_name(self) -> str:
        """Extract schema name from identifier."""
        return self.identifier.split(".")[1]

    @computed_field
    @property
    def table_name(self) -> str:
        """Extract table name from identifier."""
        return self.identifier.split(".")[2]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {"identifier": self.identifier}
        if self.column_configs:
            result["column_configs"] = [c.to_dict() for c in self.column_configs]
        return result


# =============================================================================
# DATA SOURCES
# =============================================================================

class DataSources(BaseGenieModel):
    """
    Container for all data sources in a Genie Space.

    Attributes:
        tables: List of table data sources
    """
    tables: List[TableDataSource] = Field(
        default_factory=list,
        description="Table data sources for the Genie Space"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Note: Tables are sorted by identifier as required by the Genie API.
        """
        sorted_tables = sorted(self.tables, key=lambda t: t.identifier)
        return {
            "tables": [t.to_dict() for t in sorted_tables]
        }


# =============================================================================
# TEXT INSTRUCTION
# =============================================================================

class TextInstruction(BaseGenieModel):
    """
    A text instruction for Genie to follow when generating responses.

    Instructions guide Genie's behavior for natural language queries.

    Note: Unlike sql_functions, text_instructions should NOT include an 'id'
    field when serialized - the Genie API generates it. The id field here
    is only used internally for deduplication.

    Attributes:
        id: Internal identifier (NOT serialized - API generates its own)
        content: Instruction text (can be a string or list of strings)
    """
    id: Optional[str] = Field(
        default=None,
        description="Unique instruction identifier"
    )
    content: Union[str, List[str]] = Field(
        ...,
        description="Instruction text or list of text segments"
    )

    @model_validator(mode='before')
    @classmethod
    def generate_id_if_missing(cls, data: Any) -> Any:
        """Generate a deterministic ID if not provided.

        Uses a hash of the content to ensure consistent ordering.
        """
        if isinstance(data, dict) and not data.get('id'):
            import hashlib
            content = data.get('content', '')
            if isinstance(content, list):
                content = ''.join(content)
            # Use first 32 chars of content hash for deterministic ID
            data['id'] = hashlib.md5(content[:100].encode()).hexdigest()
        return data

    @property
    def content_text(self) -> str:
        """Get content as a single string."""
        if isinstance(self.content, list):
            return "".join(self.content)
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        # Note: Do NOT include 'id' field - Genie API generates it
        return {
            "content": self.content if isinstance(self.content, list) else [self.content]
        }


# =============================================================================
# SQL FUNCTION REFERENCE
# =============================================================================

class SqlFunction(BaseGenieModel):
    """
    Reference to a SQL function available in the Genie Space.

    SQL functions can be invoked by Genie to perform complex operations.

    IMPORTANT: The Genie API requires:
    - Each sql_function MUST have an 'id' field (32-char hex string)
    - sql_functions MUST be sorted by (id, identifier) tuple
    - Without these, the API returns "Internal Error" with no details

    This class auto-generates deterministic IDs using MD5 hash of the identifier,
    and Instructions.to_dict() handles the sorting.

    Attributes:
        id: Unique function reference identifier (auto-generated using MD5 of identifier)
        identifier: Full Unity Catalog path to the function (catalog.schema.function)
    """
    id: Optional[str] = Field(
        default=None,
        description="Unique function reference identifier"
    )
    identifier: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$',
        description="Full Unity Catalog path to the function"
    )

    @model_validator(mode='before')
    @classmethod
    def generate_id_if_missing(cls, data: Any) -> Any:
        """Generate a deterministic UUID-format ID based on identifier.

        The Genie API requires sql_functions to be sorted by (id, identifier).
        We use MD5 hash of identifier to generate a deterministic 32-char hex ID.
        """
        if isinstance(data, dict) and not data.get('id'):
            import hashlib
            identifier = data.get('identifier', '')
            # MD5 hash produces 32 hex chars, same format as Databricks UUIDs
            data['id'] = hashlib.md5(identifier.encode()).hexdigest()
        return data

    @computed_field
    @property
    def catalog(self) -> str:
        """Extract catalog name from identifier."""
        return self.identifier.split(".")[0]

    @computed_field
    @property
    def schema_name(self) -> str:
        """Extract schema name from identifier."""
        return self.identifier.split(".")[1]

    @computed_field
    @property
    def function_name(self) -> str:
        """Extract function name from identifier."""
        return self.identifier.split(".")[2]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        # Include id field - API requires it for sorting when multiple functions
        return {
            "id": self.id,
            "identifier": self.identifier
        }


# =============================================================================
# JOIN SPECIFICATIONS
# =============================================================================

class JoinTableRef(BaseGenieModel):
    """
    Reference to a table in a join specification.

    Attributes:
        identifier: Full Unity Catalog path (catalog.schema.table)
        alias: Optional alias for use in join SQL
    """
    identifier: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$',
        description="Full Unity Catalog path (catalog.schema.table)"
    )
    alias: Optional[str] = Field(
        default=None,
        description="Alias for use in join SQL"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {"identifier": self.identifier}
        if self.alias:
            result["alias"] = self.alias
        return result


class RelationshipType:
    """Relationship types for join specifications."""
    MANY_TO_MANY = "MANY_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    ONE_TO_ONE = "ONE_TO_ONE"


class JoinSpec(BaseGenieModel):
    """
    Specification for a join between two tables.

    Defines how Genie should join tables together when querying.

    Attributes:
        id: Unique join identifier (auto-generated)
        left: Left table reference
        right: Right table reference
        left_column: Column name on the left table
        right_column: Column name on the right table
        relationship_type: Type of relationship (MANY_TO_MANY, MANY_TO_ONE, etc.)
    """
    id: Optional[str] = Field(
        default=None,
        description="Unique join identifier"
    )
    left: JoinTableRef = Field(
        ...,
        description="Left table in the join"
    )
    right: JoinTableRef = Field(
        ...,
        description="Right table in the join"
    )
    left_column: str = Field(
        ...,
        description="Column name on the left table"
    )
    right_column: str = Field(
        ...,
        description="Column name on the right table"
    )
    relationship_type: str = Field(
        default=RelationshipType.MANY_TO_ONE,
        description="Type of relationship (MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE)"
    )

    @model_validator(mode='after')
    def generate_id_if_missing(self) -> "JoinSpec":
        """Generate a deterministic ID based on table identifiers."""
        if not self.id:
            import hashlib
            join_key = f"{self.left.identifier}:{self.right.identifier}:{self.left_column}:{self.right_column}"
            object.__setattr__(self, 'id', hashlib.md5(join_key.encode()).hexdigest())
        return self

    def _get_alias(self, table_ref: JoinTableRef) -> str:
        """Get alias for a table reference, defaulting to table name."""
        if table_ref.alias:
            return table_ref.alias
        # Default to the table name (last part of identifier)
        return table_ref.identifier.split(".")[-1]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        left_alias = self._get_alias(self.left)
        right_alias = self._get_alias(self.right)

        # Build SQL in the format Genie expects:
        # ["`left_alias`.`left_col` = `right_alias`.`right_col`", "--rt=FROM_RELATIONSHIP_TYPE_XXX--"]
        sql = [
            f"`{left_alias}`.`{self.left_column}` = `{right_alias}`.`{self.right_column}`",
            f"--rt=FROM_RELATIONSHIP_TYPE_{self.relationship_type}--",
        ]

        return {
            "id": self.id,
            "left": {
                "identifier": self.left.identifier,
                "alias": left_alias,
            },
            "right": {
                "identifier": self.right.identifier,
                "alias": right_alias,
            },
            "sql": sql,
        }


# =============================================================================
# INSTRUCTIONS
# =============================================================================

class Instructions(BaseGenieModel):
    """
    Container for all instructions in a Genie Space.

    Attributes:
        text_instructions: Text-based instructions for Genie
        sql_functions: SQL functions available to Genie
        join_specs: Join specifications for table relationships
    """
    text_instructions: List[TextInstruction] = Field(
        default_factory=list,
        description="Text instructions for Genie behavior"
    )
    sql_functions: List[SqlFunction] = Field(
        default_factory=list,
        description="SQL functions available to Genie"
    )
    join_specs: List[JoinSpec] = Field(
        default_factory=list,
        description="Join specifications for table relationships"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self.text_instructions:
            # Keep original order
            result["text_instructions"] = [i.to_dict() for i in self.text_instructions]
        if self.sql_functions:
            # Sort by (id, identifier) as required by Genie API
            sorted_functions = sorted(self.sql_functions, key=lambda x: (x.id or "", x.identifier))
            result["sql_functions"] = [f.to_dict() for f in sorted_functions]
        if self.join_specs:
            # Sort by id as required by Genie API
            sorted_joins = sorted(self.join_specs, key=lambda x: x.id or "")
            result["join_specs"] = [j.to_dict() for j in sorted_joins]
        return result


# =============================================================================
# SERIALIZED SPACE (inner content)
# =============================================================================

class SerializedSpace(BaseGenieModel):
    """
    The serialized content of a Genie Space.

    This represents the inner structure that gets serialized to JSON
    when creating or updating a Genie Space via the API.

    Attributes:
        version: Schema version (currently 1)
        data_sources: Data sources configuration
        instructions: Instructions for Genie
    """
    version: int = Field(
        default=1,
        ge=1,
        description="Schema version number"
    )
    data_sources: DataSources = Field(
        default_factory=DataSources,
        description="Data sources for the space"
    )
    instructions: Instructions = Field(
        default_factory=Instructions,
        description="Instructions for Genie behavior"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "data_sources": self.data_sources.to_dict(),
            "instructions": self.instructions.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "SerializedSpace":
        """Parse from JSON string."""
        data = json.loads(json_str)
        return cls.model_validate(data)


# =============================================================================
# GENIE SPACE CONFIG (main entry point)
# =============================================================================

class GenieSpaceConfig(BaseGenieModel):
    """
    Complete configuration for a Databricks Genie Space.

    This is the main model for defining a Genie Space. It wraps all
    the configuration needed to create or update a space via the API.

    Attributes:
        space_id: Unique space identifier (set after creation)
        title: Display title for the space
        description: Optional description
        warehouse_id: SQL warehouse to use for queries
        source_workspace: Source workspace URL (for migrations)
        serialized_space: The space configuration content

    Example:
        ```python
        space = GenieSpaceConfig(
            title="Sales Analytics",
            warehouse_id="abc123",
            serialized_space=SerializedSpace(
                data_sources=DataSources(
                    tables=[
                        TableDataSource(
                            identifier="main.sales.transactions",
                            column_configs=[
                                ColumnConfig(
                                    column_name="amount",
                                    get_example_values=True
                                )
                            ]
                        )
                    ]
                ),
                instructions=Instructions(
                    text_instructions=[
                        TextInstruction(
                            content="Always format currency with 2 decimal places"
                        )
                    ]
                )
            )
        )

        # Export for version control
        space.to_json_file("genie_spaces/sales.json")

        # Create via SDK
        sdk_space = space.create(workspace_client)
        ```
    """
    space_id: Optional[str] = Field(
        default=None,
        description="Unique space identifier (set after creation)"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display title for the Genie Space"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="Optional description"
    )
    warehouse_id: Optional[str] = Field(
        default=None,
        description="SQL warehouse ID for queries"
    )
    source_workspace: Optional[str] = Field(
        default=None,
        description="Source workspace URL (for migration tracking)"
    )
    serialized_space: SerializedSpace = Field(
        default_factory=SerializedSpace,
        description="The space configuration content"
    )

    # ----- Serialization Methods -----

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON export.

        Returns a structure suitable for version control and migration.
        """
        result = {
            "title": self.title,
            "serialized_space": self.serialized_space.to_dict(),
        }
        if self.space_id:
            result["space_id"] = self.space_id
        if self.description:
            result["description"] = self.description
        if self.warehouse_id:
            result["warehouse_id"] = self.warehouse_id
        if self.source_workspace:
            result["source_workspace"] = self.source_workspace
        return result

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_json_file(self, file_path: str) -> None:
        """Write configuration to a JSON file."""
        from pathlib import Path
        Path(file_path).write_text(self.to_json())

    @classmethod
    def from_json(cls, json_str: str) -> "GenieSpaceConfig":
        """Parse from JSON string."""
        data = json.loads(json_str)
        return cls.model_validate(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> "GenieSpaceConfig":
        """Load configuration from a JSON file."""
        from pathlib import Path
        content = Path(file_path).read_text()
        return cls.from_json(content)

    # ----- SDK Integration Methods -----

    @classmethod
    def from_sdk(cls, genie_space: Any, source_workspace: Optional[str] = None) -> "GenieSpaceConfig":
        """
        Create a GenieSpaceConfig from a Databricks SDK GenieSpace object.

        Args:
            genie_space: databricks.sdk.service.dashboards.GenieSpace object
            source_workspace: Optional source workspace URL

        Returns:
            GenieSpaceConfig instance
        """
        serialized_data = {}
        if genie_space.serialized_space:
            serialized_data = json.loads(genie_space.serialized_space)

        return cls(
            space_id=genie_space.space_id,
            title=genie_space.title,
            description=genie_space.description,
            warehouse_id=genie_space.warehouse_id,
            source_workspace=source_workspace,
            serialized_space=SerializedSpace.model_validate(serialized_data) if serialized_data else SerializedSpace(),
        )

    def get_serialized_space_json(self) -> str:
        """
        Get the serialized_space as a JSON string for API calls.

        This is the format expected by the Databricks SDK's
        create_space and update_space methods.
        """
        return self.serialized_space.to_json()

    def create(self, workspace_client: Any) -> Any:
        """
        Create this Genie Space in the target workspace.

        Args:
            workspace_client: Databricks WorkspaceClient instance

        Returns:
            Created GenieSpace SDK object

        Raises:
            ValueError: If warehouse_id is not set
        """
        if not self.warehouse_id:
            raise ValueError("warehouse_id is required to create a Genie Space")

        result = workspace_client.genie.create_space(
            title=self.title,
            description=self.description,
            warehouse_id=self.warehouse_id,
            serialized_space=self.get_serialized_space_json(),
        )
        self.space_id = result.space_id
        return result

    def update(self, workspace_client: Any) -> Any:
        """
        Update this Genie Space in the target workspace.

        Args:
            workspace_client: Databricks WorkspaceClient instance

        Returns:
            Updated GenieSpace SDK object

        Raises:
            ValueError: If space_id is not set
        """
        if not self.space_id:
            raise ValueError("space_id is required to update a Genie Space")

        return workspace_client.genie.update_space(
            space_id=self.space_id,
            title=self.title,
            description=self.description,
            warehouse_id=self.warehouse_id,
            serialized_space=self.get_serialized_space_json(),
        )

    def create_or_update(self, workspace_client: Any, match_by_title: bool = True) -> Any:
        """
        Create or update this Genie Space in the target workspace.

        If a space with the same title exists, it will be updated.
        Otherwise, a new space will be created.

        Args:
            workspace_client: Databricks WorkspaceClient instance
            match_by_title: If True, match existing spaces by title

        Returns:
            Created or updated GenieSpace SDK object
        """
        if match_by_title and not self.space_id:
            # Search for existing space with same title
            spaces = workspace_client.genie.list_spaces()
            for space in spaces.spaces or []:
                if space.title == self.title:
                    self.space_id = space.space_id
                    break

        if self.space_id:
            return self.update(workspace_client)
        return self.create(workspace_client)


# =============================================================================
# CONVENIENCE BUILDERS
# =============================================================================

def quick_table(
    catalog: str,
    schema: str,
    table: str,
    columns: Optional[List[str]] = None,
    example_columns: Optional[List[str]] = None,
    dictionary_columns: Optional[List[str]] = None,
) -> TableDataSource:
    """
    Quickly create a TableDataSource with common column configurations.

    Args:
        catalog: Catalog name
        schema: Schema name
        table: Table name
        columns: All columns to include (with default settings)
        example_columns: Columns to get example values for
        dictionary_columns: Columns to build dictionaries for

    Returns:
        Configured TableDataSource

    Example:
        table = quick_table(
            "main", "sales", "orders",
            example_columns=["status", "region"],
            dictionary_columns=["status"]
        )
    """
    identifier = f"{catalog}.{schema}.{table}"

    column_configs = []
    all_columns = set(columns or []) | set(example_columns or []) | set(dictionary_columns or [])

    for col in all_columns:
        config = ColumnConfig(
            column_name=col,
            get_example_values=col in (example_columns or []),
            build_value_dictionary=col in (dictionary_columns or []),
        )
        column_configs.append(config)

    return TableDataSource(
        identifier=identifier,
        column_configs=column_configs,
    )


def quick_function(catalog: str, schema: str, function: str) -> SqlFunction:
    """
    Quickly create a SqlFunction reference.

    Args:
        catalog: Catalog name
        schema: Schema name
        function: Function name

    Returns:
        Configured SqlFunction
    """
    return SqlFunction(identifier=f"{catalog}.{schema}.{function}")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Base
    "BaseGenieModel",
    # Column/Table configuration
    "ColumnConfig",
    "TableDataSource",
    "DataSources",
    # Join specifications
    "JoinTableRef",
    "JoinSpec",
    "RelationshipType",
    # Instructions
    "TextInstruction",
    "SqlFunction",
    "Instructions",
    # Space configuration
    "SerializedSpace",
    "GenieSpaceConfig",
    # Convenience builders
    "quick_table",
    "quick_function",
]
