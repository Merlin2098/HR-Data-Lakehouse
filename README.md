# HR Data Lakehouse

This repository now contains a local bronze-to-silver-to-gold pipeline plus an AWS-oriented infrastructure definition for a production-style HR attrition lakehouse MVP.

The current scope now covers:

- Terraform infrastructure in `infra/`
- A shared `data_lake` S3 bucket with `bronze/`, `silver/`, and `gold/` prefixes, plus separate `scripts` and `athena-results` buckets
- KMS-backed encryption and hardened bucket defaults
- Glue jobs for `landing -> bronze`, `bronze -> silver`, and `silver -> gold`
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
- `src/glue/run_local_pipeline.py` for the full end-to-end local run

By default, the local pipeline reads `data/HR-Employee-Attrition.csv`, writes silver as a parquet dataset under `data/output/silver/hr_employees/`, and writes gold as a partitioned parquet dataset under `data/output/gold/hr_attrition/` using Hive-style folders such as `.../year=2026/month=4/day=3/`.
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

`landing_to_bronze -> bronze_to_silver -> silver_to_gold -> validate_catalog`

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
