# ETL Architecture Overview

## Objective

This document describes how the ETL for the `HR Data Lakehouse` project is structured, how it runs locally, and how it operates today in AWS.

The goal is to clearly separate:

- the real ETL data flow
- the configuration that governs the logic
- the AWS services that provide execution, cataloging, security, and observability

## Overview

The project follows a `medallion` architecture with the current flow:

```text
Landing -> Silver -> Gold -> BI Export
```

In execution terms, the system operates in two modes:

- `local`, using `DuckDB`
- `aws`, using `Glue Spark`

Business logic does not live hardcoded in Python. It is split across:

- `YAML`: pipeline configuration
- `SQL`: data transformations
- `Python`: runtime, technical orchestration, validations, and materialization

## ETL Structure

### 1. Landing

This is the arrival zone for the source file and the pipeline trigger point in AWS.

- Locally, the base dataset is [HR-Employee-Attrition2.csv](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/data/HR-Employee-Attrition2.csv)
- In AWS, the file lands in the shared data lake bucket under the prefix `bronze/hr_attrition/landing/`
- The pipeline trigger is based on the creation of a CSV object in that prefix

Landing does not apply business transformations. It only represents the entry point.

### 2. Bronze

In AWS, bronze is reduced to the `landing` ingress zone.

- The CSV file lands in `bronze/hr_attrition/landing/`
- That same object acts as both the pipeline trigger and the exact source for `bronze_to_silver`
- There is no longer an additional physical promotion to a `raw` prefix

This simplifies the flow and removes a copy that added no transformation value.

### 3. Silver

Silver is the curated and typed layer.

The `bronze_to_silver` job:

- reads the CSV from the exact `landing` object
- cleans and normalizes strings
- performs type casting
- converts `Yes/No` values to booleans
- drops non-required columns
- writes Parquet with `snappy` compression

The current output is modeled as a non-partitioned Parquet dataset.

Logical dataset:

- `silver_hr_employees`

Included technical metadata:

- `source_file`
- `run_id`
- `processed_at_utc`

### 4. Gold

Gold is the analytical layer.

The `silver_to_gold` job:

- reads the silver dataset
- applies analytical enrichment
- generates Likert-style labels
- adds ingestion metadata
- writes partitioned Parquet in `Hive-style` format

The current partition scheme is:

```text
year=YYYY/month=M/day=D
```

Logical dataset:

- `gold_hr_attrition_fact`

Technical and operational metadata:

- `ingestion_date`
- `year`
- `month`
- `day`
- `source_file`
- `run_id`
- `processed_at_utc`

Write policy:

- `silver`: `overwrite_full`
- `gold`: `overwrite_partition`

That means silver is rebuilt fully on each run, while gold only replaces the processed-day partition.

### 5. BI Export

The project now adds a local BI snapshot export after gold.

The `gold_to_bi_export` job:

- reads the curated `gold` Parquet dataset
- preserves the current analytical schema as-is
- writes a single stable Parquet file for local desktop BI tools

Logical dataset:

- `bi_hr_attrition_snapshot`

Current AWS path:

```text
s3://<data_lake_bucket>/bi/hr_attrition_snapshot/hr_attrition_snapshot.parquet
```

Current local path:

```text
data/output/bi/hr_attrition_snapshot.parquet
```

Output behavior:

- format: Parquet
- layout: single file
- write mode: full overwrite snapshot
- intended consumption: local/manual

## Files That Govern the Pipeline

The main ETL artifacts live under `src/`:

- [transformations.yaml](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/configs/transformations.yaml): defines pipelines, sources, targets, write modes, layouts, and asset references
- [contracts.yaml](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/configs/contracts.yaml): defines silver and gold contracts, minimum quality rules, and operational metadata
- [bronze_to_silver.sql](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/queries/bronze_to_silver.sql): cleaning and typing
- [silver_to_gold.sql](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/queries/silver_to_gold.sql): analytical enrichment
- [gold_to_bi_export.sql](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/queries/gold_to_bi_export.sql): BI snapshot projection
- [pipeline_runtime.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/common/pipeline_runtime.py): shared runtime for local and AWS execution
- [bronze_to_silver.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/bronze_to_silver.py): curated transformation
- [silver_to_gold.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/silver_to_gold.py): analytical transformation
- [gold_to_bi_export.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/gold_to_bi_export.py): single-file BI snapshot export
- [retry_state_machine.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/retry_state_machine.py): manual retry helper for Step Functions

## Local Execution

Locally, the pipeline uses:

- `execution_mode: local`
- `engine: duckdb`

The main runner is:

- [run_local_pipeline.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/run_local_pipeline.py)

Local flow:

1. reads the CSV from `data/`
2. generates silver as a local Parquet dataset
3. generates gold as a partitioned local Parquet dataset
4. generates a single-file BI snapshot in local Parquet

This mode allows logic, contracts, and outputs to be validated without depending on AWS.

## AWS Execution

In AWS the pipeline operates with:

- `execution_mode: aws`
- `engine: glue_spark`

### ETL Trigger

Processing starts when a CSV is created in the landing prefix inside `bronze/` of the shared data lake bucket.

Current flow:

1. S3 receives the file in `bronze/hr_attrition/landing/`
2. S3 publishes the event to EventBridge
3. EventBridge filters `Object Created` for the correct bucket, prefix, and suffix
4. EventBridge starts the Step Functions state machine
5. Step Functions executes:
   - `bronze_to_silver`
   - `silver_to_gold`
   - `gold_to_bi_export`
   - `validate_catalog`

### AWS Services Around the ETL

#### S3

These buckets are used:

- `data_lake`
- `scripts`
- `athena-results`

Responsibilities:

- storage for ingest and curated datasets under `bronze/`, `silver/`, and `gold/`
- storage for SQL, YAML, and Python scripts
- Athena query results

Current AWS physical paths:

- `bronze/hr_attrition/landing/`
- `silver/hr_employees/`
- `gold/hr_attrition/`

#### AWS Glue

Glue is the cloud ETL engine.

Modeled jobs:

- `bronze_to_silver`
- `silver_to_gold`
- `gold_to_bi_export`

Responsibilities:

- execute the Python scripts
- run Spark transformations
- write Parquet datasets to S3

#### AWS Step Functions

This is the main orchestrator.

Responsibilities:

- order the pipeline sequence
- propagate execution parameters
- centralize control flow
- provide visibility into the state of each stage

#### Amazon EventBridge

This is used as the event-driven trigger mechanism.

Responsibilities:

- receive `Object Created` events from S3
- filter only relevant landing files
- start the state machine

#### Glue Catalog

This is used to register analytical datasets.

Responsibilities:

- expose silver and gold metadata
- serve as the Athena catalog

#### Athena

This is used for validation and analytical consumption.

Responsibilities:

- query silver and gold
- execute a final validation step at the end of the state machine

Local BI snapshot export:

- the active BI delivery path is the local BI snapshot export
- Athena remains in the runtime only for `validate_catalog`
- live connectors over Athena are intentionally deferred

#### CloudWatch and SNS

These are used for baseline observability.

Responsibilities:

- Glue and Step Functions logs
- basic alarms
- operational notifications

#### KMS

This is used for managed encryption.

Responsibilities:

- encrypt buckets and sensitive artifacts
- support the lakehouse security posture

## Implementation Status

The real current status is:

- the local flow is implemented and validated end to end
- the AWS path based on Glue, Step Functions, and EventBridge is implemented in code and infrastructure
- the AWS flow has already been validated functionally in the main `landing -> silver -> gold` chain
- the shared runtime and Glue assets are deployed through Terraform
- deployment automation, remote Terraform backend support, and operational hardening are still partial

In other words:

- `local`: validated
- `aws functional`: already exercised in the main pipeline
- `aws mature operations`: still evolving

## Summary

This project implements a `config-driven` ETL with:

- event-driven ingestion from `landing`
- a curated silver layer
- an analytical gold layer
- local support with DuckDB
- AWS support with Glue Spark
- orchestration with Step Functions
- event triggering with EventBridge
- cataloging with Glue Catalog
- final validation with Athena
- local BI snapshot export in Parquet

## Future features

Potential future BI integrations include:

- QuickSight in direct query mode over Athena
- Power BI through the Athena driver
- Tableau or similar desktop tools through live Athena connectivity

Those remain optional future features and are not part of the active runtime path today.

Note about `.tinker`:

- some detectors are still heuristic and may report spurious signals such as `airflow`, `ecs`, `ecr`, or `lambda`
- the source of truth for architecture remains the current repository under `src/`, `infra/`, `tests/`, and this documentation
