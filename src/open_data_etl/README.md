# open_data_etl

ETL notebooks for loading open data metadata and setting up vector search indexes.

## Notebooks

Data loading:
- `load_worldbank_metadata.ipynb`: Fetches World Bank indicator metadata (~20k indicators)
- `load_unsdg_metadata.ipynb`: Fetches UN SDG indicator metadata (~250 indicators)
- `load_datagov_metadata.ipynb`: Fetches US government dataset metadata from Data.gov (~5k datasets)
- `load_hdx_metadata.ipynb`: Fetches humanitarian dataset metadata from HDX (~5k datasets)
- `load_cbs_metadata.ipynb`: Fetches CBS Netherlands statistical table metadata (~4k tables)
- `load_who_metadata.ipynb`: Fetches WHO Global Health Observatory indicator metadata (~2k indicators)

Setup notebook:
- `vector_search_setup.ipynb`: Creates the Vector Search endpoint and managed embedding index. Run after loading indicator metadata.
