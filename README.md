# HR Data Lakehouse

This repository now contains the phase-1 infrastructure foundation plus a local bronze-to-silver-to-gold pipeline for HR attrition analytics.

The current scope is intentionally small:

- Terraform infrastructure lives in `infra/`.
- Phase 1 provisions three S3 buckets (`bronze`, `silver`, `scripts`).
- A Glue execution role and one `bronze -> silver` Glue job are defined.
- The local application pipeline lives in `src/` with externalized YAML, SQL, and data contracts.

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

By default, the pipeline reads `data/HR-Employee-Attrition.csv`, writes silver parquet to `data/output/silver/hr_employees.parquet`, and writes gold parquet to `data/output/gold/hr_attrition/` using a numeric directory layout `year/month/day` such as `.../2026/4/3/`.
Gold uses the simpler daily overwrite model, so each run refreshes the partition for that processing day instead of accumulating multiple parquet files in the same folder.

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

Terraform phase-1 configuration is under `infra/` and is organized around three modules:

- `s3` for bronze, silver, and scripts buckets
- `iam` for the Glue execution role and policy
- `glue` for the single `bronze_to_silver` job

Script, SQL, and config uploads to S3 are intentionally deferred to the next phase so phase 1 stays focused on the minimum runnable foundation.
