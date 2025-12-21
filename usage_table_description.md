# system.billing.usage Table Metadata

## Data Scope
- Date range: 2025-09-25 to 2025-12-21
- Total records: 1,458
- Workspaces: 1

## Record Types
ORIGINAL=normal usage, RETRACTION=negative qty to negate errors, RESTATEMENT=corrections
- ORIGINAL: 1,458 records

## Cloud Providers
Values: AWS

## billing_origin_product Values
Products generating billable usage:
- DEFAULT_STORAGE
- VECTOR_SEARCH
- INTERACTIVE
- NETWORKING
- PREDICTIVE_OPTIMIZATION
- APPS
- AI_GATEWAY
- DLT
- MODEL_SERVING
- SQL

## usage_type Values
- API_OPERATION
- COMPUTE_TIME
- NETWORK_BYTE
- STORAGE_SPACE
- TOKEN

## sku_name Values (Top by Usage)
- PREMIUM_SERVERLESS_REAL_TIME_INFERENCE_US_EAST_OHIO (DBU)
- PREMIUM_DATABRICKS_STORAGE_US_EAST_OHIO (DSU)
- PREMIUM_ALL_PURPOSE_SERVERLESS_COMPUTE_US_EAST_OHIO (DBU)
- PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO (DBU)
- PREMIUM_SERVERLESS_SQL_COMPUTE_US_EAST_OHIO (DBU)
- PUBLIC_CONNECTIVITY_DATA_PROCESSED_US_EAST_OHIO (GB)
- INTERNET_EGRESS_FROM_US_EAST_OHIO (GB)
- INTER_REGION_EGRESS_FROM_US_EAST_OHIO (GB)

## usage_unit Values
Values: DSU, DBU, GB

## Node Types (usage_metadata.node_type)
Compute instance types used:
- db.xxsmall

## Resource Attribution (usage_metadata fields)
Records are linked to resources via these IDs:
- endpoint_id: 232 records have this ID populated
- notebook_id: 170 records have this ID populated
- dlt_pipeline_id: 47 records have this ID populated
- warehouse_id: 10 records have this ID populated

## Identity Tracking (identity_metadata)
- run_as: user who executed the job
- owned_by: warehouse owner
- no_run_as, no_owned_by: 1,203 records
- has_run_as, no_owned_by: 245 records
- no_run_as, has_owned_by: 10 records

## Custom Tags Availability
- no_tags: 1,430 records (98%)
- has_tags: 28 records (1%)
