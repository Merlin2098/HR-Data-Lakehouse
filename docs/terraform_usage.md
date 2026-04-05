# Terraform Usage

## Objective

This document defines how to use Terraform in this repository in a way that is:

- local-friendly for manual testing
- reusable for other developers
- compatible with future CI/CD execution

## Principles

- The repository defines infrastructure, not credentials.
- AWS credentials are never versioned.
- A local profile is an optional convenience, not a system dependency.
- CI/CD must not depend on local profiles.

## Terraform Structure

The root module lives in:

- [main.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/main.tf)

The main files are:

- [provider.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/provider.tf)
- [variables.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/variables.tf)
- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

The current topology uses:

- one `data_lake` bucket per environment with `bronze/`, `silver/`, and `gold/` prefixes
- one separate bucket for `scripts`
- one separate bucket for `athena-results`
- one monthly AWS Budget per environment for spend tracking

Operational note about buckets:

- `data_lake` and `athena-results` continue to use `SSE-KMS`
- `scripts` uses `SSE-S3 (AES256)` to make manual inspection easier during demos
- the account root principal and the ARNs declared in `scripts_bucket_reader_arns` have read-only access to the `scripts` bucket
- Terraform creates `.keep` placeholders in the operational medallion prefixes of the `data_lake` bucket
- those placeholders only make the base structure visible and do not replace real data ingestion
- the curated AWS physical paths are normalized as `silver/hr_employees/` and `gold/hr_attrition/`
- `landing` acts as the drop zone and trigger path; there is no additional operational copy in `raw`

## Pipeline Trigger and Retry

Automatic AWS trigger:

- upload a CSV to `s3://<data_lake_bucket>/bronze/hr_attrition/landing/<file>.csv`
- EventBridge detects `Object Created`
- Step Functions normalizes the payload and executes:
  - `bronze_to_silver`
  - `silver_to_gold`
  - `validate_catalog`
- each Glue task preserves `business_date`, `run_id`, and `source_filename` at the root payload and attaches its result in dedicated subfields
- `bronze_to_silver` processes the exact landing object that triggered the event

Manual retry without re-upload:

- get the state machine ARN:

```powershell
$env:AWS_PROFILE="admin2"
terraform -chdir=infra output -raw state_machine_arn
```

- reprocess an object that already exists in S3:

```powershell
$env:AWS_PROFILE="admin2"
$stateMachineArn = terraform -chdir=infra output -raw state_machine_arn
.\.venv\Scripts\python.exe src\glue\retry_state_machine.py `
  --state-machine-arn $stateMachineArn `
  --source-uri "s3://hr-lakehouse-dev-184670914470-us-east-1-data-lake/bronze/hr_attrition/landing/HR-Employee-Attrition.csv" `
  --business-date 2026-04-04
```

Operational notes:

- the helper builds the manual input expected by `NormalizeManualInput`
- `source_filename` is derived from the last S3 key segment
- `business_date` is controlled explicitly and is not inferred from the file name
- if you omit `--run-id`, the helper generates a new one
- if you omit `--event-time`, the helper uses the current UTC timestamp
- the file is not uploaded again; the object must already exist in `landing`
- manual retry does not depend on a `raw` prefix either

## Options for Local Authentication

### Recommended option: `AWS_PROFILE`

This is the preferred way to work locally:

```powershell
$env:AWS_PROFILE="admin2"
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file="env/dev.tfvars"
```

Advantages:

- keeps versioned files clean
- each developer can use their own profile
- mirrors the expected AWS SDK and CLI behavior

### Optional option: `local.auto.tfvars`

If you want to avoid exporting variables in every session, you can create a local unversioned file:

- `infra/env/local.auto.tfvars`

Use this template:

- [local.auto.tfvars.example](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/local.auto.tfvars.example)

Example:

```hcl
aws_profile = "admin2"
aws_region  = "us-east-1"
```

That file is ignored by Git so it does not pollute the repository.

## Command Convention

### Windows PowerShell

Use this form for `-var-file`:

```powershell
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file="env/dev.tfvars"
```

### Linux/macOS

```bash
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file=env/dev.tfvars
```

## Minimum Prerequisite

Before running `terraform plan`, this command must work:

```powershell
aws sts get-caller-identity --region us-east-1
```

If that fails, Terraform will fail too because of credentials.

## CI/CD

The intended CI/CD strategy is:

- `terraform fmt -check`
- `terraform init -backend=false`
- `terraform validate`
- `terraform plan -var-file=env/dev.tfvars`

Current workflow triggers:

- `push` to `main`
- `pull_request`
- `workflow_dispatch`

Recommended authentication:

- `OIDC + assume role` in AWS

Acceptable fallback:

- temporary credentials injected as pipeline secrets

`aws_profile` must not be used inside the CI/CD pipeline.
The automatic GitHub Actions `plan` is intentionally scoped to `dev`; `prod` remains manual at this stage.

## Basic FinOps

Spend control is defined in:

- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

Relevant variables:

- `monthly_budget_limit_usd`
- `alert_email_endpoints`

Current behavior:

- one monthly budget per environment
- alerts at `80%` and `100%`
- tracking for `actual spend` and `forecasted spend`
- alert delivery to the SNS topic from the observability module
- optional email subscriptions managed with Terraform

Notes:

- the budget monitors spend; it does not block deployments
- environment separation depends on the `Environment` tag
- for tag filtering to work in AWS Budgets, the `Environment` cost allocation tag must be enabled in Billing
- SNS emails require manual confirmation after `apply`
- the SNS topic is encrypted with KMS, which is why explicit policies exist for SNS and Budgets

## Backend

In this iteration the repository is prepared for:

- local testing
- CI/CD validation

using:

```text
-backend=false
```

Remote backend support for shared state remains a future phase.

## Lock File

The Terraform lock file is versioned here:

- [infra/.terraform.lock.hcl](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/.terraform.lock.hcl)

This helps the team and CI/CD use consistent provider versions.
