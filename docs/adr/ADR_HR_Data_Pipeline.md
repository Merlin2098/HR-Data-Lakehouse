# ADR-Architecture: Lakehouse Architecture Baseline

- Short Name: `lakehouse-architecture-baseline`

- Status: Accepted and implemented
- Date: 2026-03-20
- Last Reviewed: 2026-04-05
- Decision Makers: Data Engineering
- Tags: aws, s3, glue, step-functions, eventbridge, athena, parquet, terraform, lakehouse

---

## Context

The project needs a reproducible and low-operations analytics pipeline for HR attrition data that can:

- ingest a source CSV from S3
- normalize and type the data for analytical use
- publish a curated gold dataset optimized for Athena
- export a stable Parquet snapshot for local BI consumption
- be deployed and maintained through Terraform

The input dataset is the IBM HR Attrition CSV, and the implementation needs to work in two execution modes:

- `local`, using DuckDB for rapid validation
- `aws`, using Glue Spark for production-style execution

The architecture also needs baseline observability, encryption, event-driven orchestration, and a controlled contract between transformations and datasets.

---

## Decision

The project adopts a config-driven lakehouse architecture with the current runtime flow:

```text
Landing -> Silver -> Gold -> BI Export
```

The active AWS path is:

```text
S3 Landing -> EventBridge -> Step Functions -> Glue -> Athena validation
```

The implementation is intentionally split into:

- `YAML` for pipeline definitions
- `SQL` for transformations
- `Python` for orchestration, validation, and materialization
- `Terraform` for infrastructure and deployment

---

## Current Architecture

### 1. Landing

Landing is the ingress and trigger zone.

- In AWS, source files land under `bronze/hr_attrition/landing/`
- The same uploaded object is used directly by `bronze_to_silver`
- There is no longer a separate operational `raw` promotion step

This keeps the event-driven path simple and avoids duplicating the same CSV without transformation value.

### 2. Silver

Silver is the first curated layer.

The `bronze_to_silver` job:

- reads the exact landing object
- cleans and normalizes strings
- casts values to typed analytical columns
- converts `Yes/No` style fields into booleans
- drops unused fields
- writes a Parquet dataset to `silver/hr_employees/`

Technical lineage metadata included in silver:

- `source_file`
- `run_id`
- `processed_at_utc`

Write policy:

- `overwrite_full`

### 3. Gold

Gold is the analytical layer.

The `silver_to_gold` job:

- reads the silver Parquet dataset
- adds analytical enrichments and label mappings
- appends ingestion metadata
- writes partitioned Parquet to `gold/hr_attrition/`

Partition scheme:

- `year`
- `month`
- `day`

Technical metadata included in gold:

- `ingestion_date`
- `year`
- `month`
- `day`
- `source_file`
- `run_id`
- `processed_at_utc`

Write policy:

- `overwrite_partition`

### 4. BI Export

The project now includes an explicit BI export stage.

The `gold_to_bi_export` job:

- reads the curated `gold_hr_attrition_fact` dataset
- filters the export to the `business_date` of the current run
- materializes a single stable Parquet snapshot
- overwrites the same target on every successful execution

Current AWS target:

```text
s3://<data_lake_bucket>/bi/hr_attrition_snapshot/hr_attrition_snapshot.parquet
```

Current local target:

```text
data/output/bi/hr_attrition_snapshot.parquet
```

This snapshot is the current recommended BI delivery mechanism for local desktop tools.

---

## Orchestration and Runtime

### Event-driven execution in AWS

The AWS pipeline is triggered when a CSV is created in the landing prefix.

Execution flow:

1. S3 receives the object in `bronze/hr_attrition/landing/`
2. EventBridge filters the event
3. Step Functions starts the state machine
4. Step Functions normalizes the payload and preserves:
   - `bucket_name`
   - `object_key`
   - `source_uri`
   - `source_filename`
   - `business_date`
   - `run_id`
   - `event_time`
5. The state machine executes:
   - `bronze_to_silver`
   - `silver_to_gold`
   - `gold_to_bi_export`
   - `validate_catalog`

### Validation strategy

Dataset quality is enforced through contracts and runtime checks.

The pipeline validates:

- expected output columns
- primary keys where declared
- nullability and value-domain rules
- partition coherence for date-partitioned outputs

The final state-machine step also validates the Athena-facing gold table through a synchronous query execution.

---

## Technology Choices

### Amazon S3

Chosen for:

- durable and low-cost lake storage
- clean separation between landing, curated, and exported data
- native interoperability with Glue and Athena

### AWS Glue

Chosen for:

- serverless Spark execution
- direct integration with S3 and the Glue Catalog
- suitability for batch ETL without cluster management

### AWS Step Functions

Chosen for:

- explicit orchestration of ETL stages
- payload normalization and propagation
- synchronous Glue and Athena coordination
- operational visibility into end-to-end execution

### Amazon EventBridge

Chosen for:

- event-driven start from S3 object creation
- filtering by prefix and suffix before orchestration

### AWS Glue Catalog and Athena

Chosen for:

- serverless SQL access to curated data
- lightweight validation of analytical outputs
- compatibility with future BI integrations

### Parquet

Chosen for:

- columnar storage
- better compression
- lower scan costs in Athena
- good compatibility with desktop analytics tools

### Terraform

Chosen for:

- reproducible infrastructure
- explicit environment modeling
- version-controlled deployment of both platform and ETL assets

---

## Alternatives Considered

### Keep a separate `landing -> raw` copy stage

Rejected because it duplicated the same source file without adding transformation value. The pipeline now reads the landing object directly.

### Export BI data through Athena query results

Rejected as the primary strategy because the project already materializes Parquet through Glue, and Athena `SELECT` results default to CSV. A dedicated Parquet BI export from gold is simpler and more consistent with the lakehouse design.

### Use only live BI connectivity as the active path

Rejected for now because QuickSight and some service-based BI options introduce licensing or connector dependencies. The active path is a stable Parquet snapshot for local consumption, while live connectors remain future features.

### Full dimensional warehouse model

Rejected because it would add complexity beyond the needs of the current MVP and serverless Athena-centered analytics path.

---

## Consequences

### Positive

- simple event-driven ingestion model
- low-operations AWS execution path
- reproducible infrastructure and ETL asset deployment
- clear separation between configuration, SQL logic, and runtime code
- efficient analytical storage in Parquet
- stable local BI handoff through a single-file snapshot

### Negative

- the state machine runtime increases because the BI export is a third synchronous Glue stage
- the BI snapshot represents only the processed `business_date`, not the full historical gold dataset
- mature operational hardening is still evolving

---

## Implementation Status

The decision is no longer only architectural; it is already implemented in the repository.

Current state:

- local pipeline: validated end to end
- AWS pipeline: validated functionally end to end
- active runtime path: `landing -> silver -> gold -> bi_export -> validate_catalog`
- observability: CloudWatch Logs, CloudWatch Alarms, and SNS alerts are implemented
- security baseline: KMS-backed encryption and hardened buckets are implemented
- cost controls: AWS Budgets with SNS notifications are implemented
- Terraform lifecycle: deploy and destroy are intentionally optimized for demo use, including recursive Athena workgroup cleanup and destroy-friendly S3 bucket settings

Still evolving:

- broader operational hardening
- remote Terraform backend strategy
- CI/CD maturity beyond the current baseline workflow
- optional live BI connectors

---

## Future Features

Potential future additions include:

- live BI integrations over Athena such as QuickSight, Power BI, or Tableau
- richer curated BI exports or aggregated marts
- stronger deployment automation and environment promotion
- additional governance and operational guardrails

These are intentionally out of the active runtime path today.

---

## Notes

This ADR now reflects the implemented state of the repository as of 2026-04-05.

The source of truth for architecture is the code and IaC under:

- `src/`
- `infra/`
- `tests/`
- `docs/`
