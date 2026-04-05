# HR Data Lakehouse

This repository now contains a local bronze-to-silver-to-gold pipeline plus a BI snapshot export and an AWS-oriented infrastructure definition for a production-style HR attrition lakehouse MVP.

Current status:

- local pipeline: validated end to end
- AWS pipeline: validated functionally for the main `landing -> silver -> gold` path
- deploy automation, remote Terraform backend, and broader operational hardening: still partial

The current scope now covers:

- Terraform infrastructure in `infra/`
- A shared `data_lake` S3 bucket with `bronze/`, `silver/`, and `gold/` prefixes, plus separate `scripts` and `athena-results` buckets
- KMS-backed encryption and hardened bucket defaults
- Glue jobs for `landing -> silver`, `silver -> gold`, and `gold -> bi_export`
- Step Functions orchestration triggered by `S3 Object Created` events through EventBridge
- Glue Catalog + Athena workgroup for analytics
- CloudWatch/SNS observability scaffolding
- AWS Budgets per environment with SNS cost alerts
- A local application pipeline in `src/` with externalized YAML, SQL, and data contracts

## Repository layout

```text
infra/
  modules/
    glue/
    iam/
    s3/
  env/
src/
  common/
  configs/
  glue/
  queries/
tests/
docs/
```

## Local pipeline

The local pipeline uses:

- `src/configs/transformations.yaml` for pipeline configuration
- `src/configs/contracts.yaml` for silver and gold data contracts
- `src/queries/bronze_to_silver.sql` for cleaning and typing
- `src/queries/silver_to_gold.sql` for enrichment and partition-ready analytics
- `src/glue/bronze_to_silver.py` for the silver stage
- `src/glue/silver_to_gold.py` for the gold stage
- `src/glue/gold_to_bi_export.py` for the BI snapshot stage
- `src/glue/run_local_pipeline.py` for the full end-to-end local run

By default, the local pipeline reads `data/HR-Employee-Attrition3.csv`, writes silver as a parquet dataset under `data/output/silver/hr_employees/`, writes gold as a partitioned parquet dataset under `data/output/gold/hr_attrition/` using Hive-style folders such as `.../year=2026/month=4/day=3/`, and exports a stable BI snapshot to `data/output/bi/hr_attrition_snapshot.parquet`.
Gold uses a daily partition overwrite model, so each run refreshes only the partition for that processing day instead of rewriting the full dataset.

Both silver and gold now include technical metadata to simulate production-style lineage:

- `source_file`
- `run_id`
- `processed_at_utc`

Gold also includes `ingestion_date` alongside the `year/month/day` partition columns.

The shared config in `src/configs/transformations.yaml` now supports both:

- `execution_mode: local` with `engine: duckdb`
- `execution_mode: aws` with `engine: glue_spark`

AWS jobs are designed to read config, contracts, and SQL assets from the `scripts` bucket and operate on S3 URIs directly.

Run it with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe src\glue\bronze_to_silver.py
```

Run only the gold stage with an explicit ingestion date:

```powershell
.\.venv\Scripts\python.exe src\glue\silver_to_gold.py --ingestion-date 2026-04-03
```

Run the full local pipeline:

```powershell
.\.venv\Scripts\python.exe src\glue\run_local_pipeline.py --ingestion-date 2026-04-03
```

If you omit `--ingestion-date`, the pipeline uses the local current date automatically.

Run the unit tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

## Terraform notes

The Terraform configuration under `infra/` now models an AWS production-style MVP with these modules:

- `kms`
- `s3`
- `assets`
- `iam`
- `glue`
- `catalog`
- `athena`
- `orchestration`
- `observability`
- `budgets`

Glue assets are uploaded to S3 through Terraform, and the state machine orchestrates the medallion flow when a new CSV lands in the `bronze/` landing prefix inside the shared data lake bucket:

`bronze_to_silver -> silver_to_gold -> gold_to_bi_export -> validate_catalog`

Automatic trigger in AWS:

1. Upload a CSV to `s3://<data_lake_bucket>/bronze/hr_attrition/landing/<file>.csv`
2. EventBridge forwards the S3 event to Step Functions
3. The state machine normalizes the filename from the last path segment, preserves the execution payload across Glue tasks, and starts the Glue chain directly from the uploaded landing object

Manual retry for an existing landing object:

```powershell
$env:AWS_PROFILE="admin2"
$stateMachineArn = terraform -chdir=infra output -raw state_machine_arn
.\.venv\Scripts\python.exe src\glue\retry_state_machine.py `
  --state-machine-arn $stateMachineArn `
  --source-uri "s3://hr-lakehouse-dev-184670914470-us-east-1-data-lake/bronze/hr_attrition/landing/HR-Employee-Attrition3.csv" `
  --business-date 2026-04-04
```

The retry helper does not upload files. It only starts a new Step Functions execution for an object that already exists in S3, and it derives `source_filename` from the final key segment automatically.
In AWS, `landing` now acts only as the drop zone and event trigger; there is no physical promotion copy into `raw` before `bronze_to_silver`.

The current recommended BI consumption path is to download the exported Parquet snapshot from:

`s3://<data_lake_bucket>/bi/hr_attrition_snapshot/hr_attrition_snapshot.parquet`

That snapshot represents the `business_date` processed by the most recent successful run, and it can be opened locally in the desktop visualization tool of your choice. Live Athena-driven connectors such as QuickSight, Power BI ODBC, or Tableau live queries are treated as future features rather than part of the active runtime path.

Terraform local usage is documented in [terraform_usage.md](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/docs/terraform_usage.md).

Recommended local flow:

```powershell
$env:AWS_PROFILE="your-profile"
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file="env/dev.tfvars"
```

You can also create a local non-versioned `infra/env/local.auto.tfvars` from [local.auto.tfvars.example](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/local.auto.tfvars.example) if you prefer not to export `AWS_PROFILE` in every session.

This repository now includes a base GitHub Actions workflow at [.github/workflows/terraform.yml](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/.github/workflows/terraform.yml) for `fmt`, `init`, `validate`, and `plan`. It runs on `push` to `main`, on `pull_request`, and on `workflow_dispatch`, and is designed to use OIDC/assume-role when available, falling back to AWS secrets if needed.

The automatic `plan` remains intentionally scoped to `dev`. `prod` stays manual for now so the demo can show CI validation clearly without introducing environment-approval complexity.

AWS cost control is also modeled in Terraform through a monthly budget per environment, with `80%` and `100%` alerts for both actual and forecasted spend routed to the shared SNS alerts topic.
The shared SNS topic now supports optional email subscriptions via Terraform, but each recipient must still confirm the subscription manually from the AWS email they receive.
For demo operability, the `scripts` bucket now uses `SSE-S3 (AES256)` and grants read-only inspection access to the account root principal plus configured reader ARNs such as `admin2`, while `data_lake` remains protected with `SSE-KMS`.
Terraform also materializes `.keep` placeholders in the main medallion prefixes of `data_lake`, so `bronze`, `silver`, and `gold` are visible in S3 before the first Glue run. The ETL still owns the real dataset contents. The current AWS physical layout keeps `bronze/hr_attrition/landing/` as the event-driven ingress path, and normalizes the curated layers to `silver/hr_employees/` and `gold/hr_attrition/`.
