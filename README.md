# HR Data Lakehouse

This repository now contains the phase-1 foundation for an AWS serverless lakehouse focused on HR attrition analytics.

The current scope is intentionally small:

- Terraform infrastructure lives in `infra/`.
- Phase 1 provisions three S3 buckets (`bronze`, `silver`, `scripts`).
- A Glue execution role and one `bronze -> silver` Glue job are defined.
- The local application scaffold lives in `src/` with externalized YAML, SQL, and data contracts.

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

## Local pipeline scaffold

The local scaffold uses:

- `src/configs/transformations.yaml` for pipeline configuration
- `src/configs/contracts.yaml` for the silver dataset contract
- `src/queries/bronze_to_silver.sql` for the transformation logic
- `src/glue/bronze_to_silver.py` as the executable entrypoint

By default, the script reads the HR attrition CSV from `data/` and writes a parquet file under `data/output/silver/`.

Run it with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe src\glue\bronze_to_silver.py
```

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
