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

## How to Search

Use the `search_worldbank_tables` function to find tables by semantic similarity:

```sql
SELECT table_name, indicator_id, full_table_name, description, score
FROM main_catalog.dev.search_worldbank_tables('user query here')
ORDER BY score DESC
LIMIT 5
```

## Response Format

When presenting results to users:
1. Show the **indicator_id** (e.g., SP.POP.TOTL) as the primary identifier
2. Include the **full_table_name** so users can query the data directly
3. Summarize the **description** to explain what the table contains
4. If multiple tables match, rank by relevance score

## Example Queries

- "GDP growth" -> Find tables about economic growth
- "population demographics" -> Find population-related tables
- "CO2 emissions" -> Find environmental data tables
- "education enrollment" -> Find education statistics tables
- "poverty rates" -> Find poverty and inequality tables

## Important Notes

- Each table in the worldbank schema contains time series data (country, year, value)
- The indicator_id maps to World Bank indicator codes
- Use the full_table_name in your response so users can query the actual data

## Genie Space Management Functions

These functions allow managing tables in Genie Spaces:

### Add a table to this Genie Space
```sql
SELECT main_catalog.dev.add_table_to_worldbank_genie_space('main_catalog.worldbank.table_name')
```

### Add a table to any Genie Space by ID
```sql
SELECT main_catalog.dev.add_table_to_genie_space('<space_id>', 'catalog.schema.table')
```

### Add table with column configurations
```sql
SELECT main_catalog.dev.add_table_with_columns_to_genie_space(
  '<space_id>',
  'catalog.schema.table',
  'column1:true:false,column2:true:true'  -- name:get_examples:build_dictionary
)
```

### List tables in a Genie Space
```sql
SELECT main_catalog.dev.list_tables_in_genie_space('<space_id>')
```

### Remove a table from a Genie Space
```sql
SELECT main_catalog.dev.remove_table_from_genie_space('<space_id>', 'catalog.schema.table')
```"""
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
# REGISTRY OF ALL GENIE SPACES
# =============================================================================

GENIE_SPACES = [
    WORLDBANK_TABLE_FINDER,
    # WHO_DATA_EXPLORER,  # Uncomment to include
]

# Map of space names to configs for selective deployment
GENIE_SPACE_REGISTRY = {
    "worldbank_table_finder": WORLDBANK_TABLE_FINDER,
    "who_data_explorer": WHO_DATA_EXPLORER,
}
