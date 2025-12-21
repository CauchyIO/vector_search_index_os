# Open Data Vector Search

A collection of ETLs that download metadata from open data sources and register them as Vector Search indexes in Databricks for natural language discovery. Enables AI-powered semantic search across global open datasets using Databricks Vector Search with managed embeddings.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                  │
│  World Bank │ UN SDG │ IMF │ Data.gov │ HDX │ CBS │ WHO             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ETL Notebooks                                     │
│         Download metadata & write to Delta tables                    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Databricks Vector Search                            │
│      Managed embeddings │ Delta Sync │ SQL search functions          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Genie Space                                     │
│        Natural language queries │ Domain routing │ AI chat           │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Sources

| Source | Table | Records | Description |
|--------|-------|---------|-------------|
| World Bank | `worldbank_indicators` | ~20k | Economic, development, and social indicators |
| UN SDG | `unsdg_indicators` | ~250 | Sustainable Development Goal indicators |
| IMF | `imf_indicators` | ~15k | International Monetary Fund economic data |
| Data.gov | `datagov_indicators` | ~5k | US government open datasets |
| HDX | `hdx_indicators` | ~5k | Humanitarian Data Exchange datasets |
| CBS Netherlands | `cbs_indicators` | ~4k | Dutch statistical tables |
| WHO | `who_indicators` | ~2k | Global Health Observatory indicators |

## Project Structure

```
vector_search_index_os/
├── databricks.yml              # Databricks Asset Bundle config
├── src/
│   ├── open_data_etl/          # ETL notebooks
│   │   ├── load_*.ipynb        # Data loading notebooks (one per source)
│   │   └── vector_search_setup.ipynb
│   └── genie/
│       ├── genie_space.json    # Exported Genie Space config
│       └── databricks_genie.ipynb
├── resources/                  # Job definitions (YAML)
├── data/                       # Parquet exports for seeding
└── tests/                      # Pytest configuration
```

## Prerequisites

- Python 3.10+
- Databricks CLI configured with workspace access
- Databricks workspace with Vector Search enabled

## Deployment

Deploy using Databricks Asset Bundles:

```bash
# Deploy to development (default)
databricks bundle deploy -t dev

# Deploy to production
databricks bundle deploy -t prod

# Deploy to secondary dev workspace
databricks bundle deploy -t dev2
```

### Deployment Targets

| Target | Workspace | Catalog | Schema |
|--------|-----------|---------|--------|
| `dev` (default) | dbc-930eaa5c-35a0 | main_catalog | dev |
| `prod` | dbc-930eaa5c-35a0 | main_catalog | prod |
| `dev2` | dbc-c7690892-938f | main_catalog | dev |

## Setup

### 1. Load Data

Run the ETL notebooks in `src/open_data_etl/` to fetch metadata from each source:

```bash
# Run via Databricks UI or Jobs
load_worldbank_metadata.ipynb
load_unsdg_metadata.ipynb
load_imf_metadata.ipynb
load_datagov_metadata.ipynb
load_hdx_metadata.ipynb
load_cbs_metadata.ipynb
load_who_metadata.ipynb
```

### 2. Create Vector Search Indexes

Run `vector_search_setup.ipynb` which:
1. Creates/verifies the Vector Search endpoint
2. Enables Change Data Feed on source tables
3. Creates managed embedding indexes
4. Registers SQL search functions

### 3. (Optional) Import Seed Data

If you want to start with pre-loaded data:

```bash
# Run import_tables_from_parquet.ipynb
# Uses Parquet files in data/ directory
```

## Usage

### SQL Query

```sql
SELECT * FROM VECTOR_SEARCH(
    index => 'main_catalog.dev.worldbank_indicators_index',
    query => 'poverty and inequality',
    num_results => 10
)
```

### Search Functions

```sql
-- Search World Bank indicators
SELECT * FROM main_catalog.dev.search_worldbank_indicators('economic growth')

-- Search WHO indicators
SELECT * FROM main_catalog.dev.search_who_indicators('vaccination rates')
```

## Genie Space

The project includes a Genie Space for natural language queries across the data sources. The Genie Space provides:

- **Semantic search** across indicator metadata
- **Domain routing** to automatically select the right data source
- **AI-powered chat** interface for data discovery

### Domain Routing

Queries are automatically routed based on topic:

| Domain | Topics |
|--------|--------|
| **WHO** | disease, mortality, life expectancy, vaccination, healthcare workers, hospitals, mental health, maternal/child health, epidemics, sanitation, nutrition |
| **World Bank** | GDP, inflation, trade, poverty, unemployment, education, literacy, infrastructure, electricity, internet, CO2 emissions, population, urbanization, foreign investment |

Cross-domain queries (e.g., "health expenditure and GDP") search both sources and combine results.

### Genie Migration

Export/import Genie Space configurations between workspaces using `src/genie/databricks_genie.ipynb`.

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest tests/
```

## License

MIT License - see LICENSE file
