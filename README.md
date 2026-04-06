# AWS Serverless Lakehouse (HR Analytics Pipeline)

End-to-end serverless data pipeline built on AWS using a medallion-style architecture, designed for scalable processing, cost optimization, and analytics-ready outputs.

## Problem

Organizations often rely on fragmented HR datasets stored in spreadsheets, which leads to:

- manual processing
- limited data validation
- weak analytical capabilities

This project shows how that scenario can be transformed into a cloud-native lakehouse pipeline.

## Architecture

![Architecture Diagram](./docs/architecture/assets/data-lakehouse-architecture.png)

The current project flow is:

- Landing as the event-driven ingestion zone
- Silver as the curated and typed layer
- Gold as the analytics-ready layer
- BI Export as a stable Parquet snapshot for local visualization

## How It Works

1. A new CSV file is uploaded to the landing prefix in S3.
2. EventBridge detects the object-created event.
3. Step Functions orchestrates the ETL workflow.
4. Glue runs the transformation stages:
   - `bronze_to_silver`
   - `silver_to_gold`
   - `gold_to_bi_export`
5. Athena validates the curated gold dataset.
6. A Parquet BI snapshot is left available for local visualization tools.

## Tech Stack

- AWS S3
- AWS Glue
- AWS Glue Data Catalog
- AWS Step Functions
- AWS EventBridge
- AWS Athena
- Terraform
- Python
- Parquet
- Tableau / local BI snapshot workflow

## Key Design Decisions

- event-driven architecture using S3 + EventBridge
- schema control through contracts and explicit catalog metadata
- separation between infrastructure and ETL assets
- snapshot-based BI consumption instead of live managed BI as the active path
- cost optimization by keeping the demo serverless and lightweight

See [docs/adr](./docs/adr) for the detailed decision records.

## Deployment

Infrastructure is managed with Terraform.

```bash
terraform init
terraform plan
terraform apply
```

Note: this project is designed for demo purposes. Resources can be destroyed after validation to avoid unnecessary cost.

---

## 8. Output / Results

Pending. This section is intentionally left for future completion once the final demo outputs are curated.

## Cost Optimization

- serverless architecture with pay-per-use services
- Parquet to reduce scan costs
- managed BI kept out of the active runtime path
- budget monitoring through AWS Budgets

## Future Improvements

- optional live BI integrations over Athena
- stronger CI/CD automation
- richer data quality monitoring
- broader production hardening
