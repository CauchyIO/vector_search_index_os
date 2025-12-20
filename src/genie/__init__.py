"""
Databricks Genie Space configuration models.

This module provides Pydantic models for defining and managing
Genie Space configurations programmatically.

Example:
    from genie import GenieSpaceConfig, TableDataSource, ColumnConfig

    # Define a Genie Space
    space = GenieSpaceConfig(
        title="Sales Analytics",
        warehouse_id="your-warehouse-id",
        serialized_space=SerializedSpace(
            data_sources=DataSources(
                tables=[
                    TableDataSource(
                        identifier="catalog.schema.sales",
                        column_configs=[
                            ColumnConfig(column_name="region", get_example_values=True)
                        ]
                    )
                ]
            )
        )
    )

    # Create in workspace
    result = space.create(workspace_client)
"""

from .models import (
    # Base
    BaseGenieModel,
    # Column/Table configuration
    ColumnConfig,
    TableDataSource,
    DataSources,
    # Instructions
    TextInstruction,
    SqlFunction,
    Instructions,
    # Space configuration
    SerializedSpace,
    GenieSpaceConfig,
    # Convenience builders
    quick_table,
    quick_function,
)

__all__ = [
    # Base
    "BaseGenieModel",
    # Column/Table configuration
    "ColumnConfig",
    "TableDataSource",
    "DataSources",
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
