# Indicator Vector Search

Vector Search index over global indicator metadata for natural language discovery.

## Data Sources

| Source | Table | Indicators |
|--------|-------|------------|
| World Bank | `worldbank_indicators` | ~20k |
| UN SDG | `unsdg_indicators` | ~250 |
| IMF | `imf_indicators` | ~15k |
| Data.gov | `datagov_indicators` | ~5k |
| HDX | `hdx_indicators` | ~5k |
| CBS Netherlands | `cbs_indicators` | ~4k |

## Setup

```bash
# Deploy
databricks bundle deploy

# Load data (run notebooks in explorations/)
# 1. load_worldbank_metadata.ipynb (World Bank)
# 2. load_unsdg_metadata.ipynb
# 3. load_imf_metadata.ipynb
# 4. load_datagov_metadata.ipynb
# 5. load_hdx_metadata.ipynb
# 6. load_cbs_metadata.ipynb (CBS Netherlands)

# Create Vector Search index
# Run vector_search_setup.ipynb
```

## Query

```sql
SELECT * FROM VECTOR_SEARCH(
    index => 'main_catalog.dev.worldbank_indicators_index',
    query => 'poverty and inequality',
    num_results => 10
)
```
