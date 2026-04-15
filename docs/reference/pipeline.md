# HR Attrition Pipeline

## Objective

This document summarizes the current pipeline design for the HR attrition lakehouse and reflects the repository as it exists today.

The active medallion flow is:

```text
Landing -> Silver -> Gold -> BI Export
```

In AWS, `landing` is the bronze ingress zone and trigger path. There is no longer a separate `raw` promotion stage.

## High-Level Flow

```text
CSV uploaded to landing
        |
        v
S3 Object Created -> EventBridge -> Step Functions
        |
        v
bronze_to_silver
        |
        v
silver/hr_employees/ (Parquet)
        |
        v
silver_to_gold
        |
        v
gold/hr_attrition/year=YYYY/month=M/day=D/ (Parquet)
        |
        v
gold_to_bi_export
        |
        v
bi/hr_attrition_snapshot/hr_attrition_snapshot.csv
        |
        v
validate_catalog
```

## Landing / Bronze

Purpose:

- Receive the source CSV file.
- Trigger the state machine in AWS.
- Act as the exact source object for `bronze_to_silver`.

Current AWS path:

```text
s3://<data_lake_bucket>/bronze/hr_attrition/landing/<file>.csv
```

Characteristics:

- Format: CSV
- Business transformations: none
- Trigger mode: event-driven
- Physical copy to `raw`: removed from the current design

## Silver

Purpose:

- Clean, type, and normalize the source dataset.
- Produce an analytics-friendly parquet dataset.

Current dataset:

- Logical name: `silver_hr_employees`
- Physical path: `s3://<data_lake_bucket>/silver/hr_employees/`

Key transformations:

- string cleanup and normalization
- numeric casts
- `Yes` / `No` normalization to booleans
- metadata injection for lineage

Technical metadata columns:

- `source_file`
- `run_id`
- `processed_at_utc`

Output characteristics:

- Format: Parquet
- Compression: Snappy
- Layout: dataset
- Write mode: full overwrite per run

## Gold

Purpose:

- Build the analytical fact dataset used for downstream querying.
- Add ingestion metadata and business-friendly labels.

Current dataset:

- Logical name: `gold_hr_attrition_fact`
- Physical base path: `s3://<data_lake_bucket>/gold/hr_attrition/`

Key enrichments:

- Likert score to label mapping
- ingestion metadata columns
- curated analytical shape for Athena and BI

Partitioning:

```text
year=YYYY/month=M/day=D
```

Technical metadata columns:

- `ingestion_date`
- `year`
- `month`
- `day`
- `source_file`
- `run_id`
- `processed_at_utc`

Output characteristics:

- Format: Parquet
- Layout: partitioned dataset
- Write mode: overwrite current partition only

## BI Export

Purpose:

- Produce a stable single-file CSV snapshot for local BI tools.
- Avoid dependence on live Athena drivers or licensed BI services in the core project path.

Current dataset:

- Logical name: `bi_hr_attrition_snapshot`
- Physical path: `s3://<data_lake_bucket>/bi/hr_attrition_snapshot/hr_attrition_snapshot.csv`

Output characteristics:

- Format: CSV
- Layout: single file
- Write mode: full overwrite snapshot

## Runtime Model

The project supports two execution modes from the same configuration:

- `local` with `duckdb`
- `aws` with `glue_spark`

The business logic is externalized into:

- `src/configs/transformations.yaml`
- `src/configs/contracts.yaml`
- `src/queries/bronze_to_silver.sql`
- `src/queries/silver_to_gold.sql`
- `src/queries/gold_to_bi_export.sql`

Python is responsible for runtime orchestration, validation, and materialization.

## AWS Status

Current operational status:

- local pipeline: validated
- AWS pipeline: validated functionally for the main `landing -> silver -> gold` path and ready to extend with a BI export stage
- CI/CD and fully automated deploy flow: still partial
- remote Terraform backend and production-grade deployment automation: still pending

## Notes

- `docs/architecture/assets/data-lakehouse-architecture.png` is not the source of truth for this document.
- Some `.tinker` detector outputs are heuristic and may still over-report technologies such as `airflow`, `ecs`, `ecr`, or `lambda`. The repository structure under `src/`, `infra/`, and `tests/` remains the authoritative technical source.
