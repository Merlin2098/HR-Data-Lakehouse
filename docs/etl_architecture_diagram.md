# ETL Architecture Diagram

## Objective

This document shows the current ETL architecture diagram, both as a functional flow and as the surrounding AWS services that support it.

## 1. General ETL Flow

```mermaid
flowchart LR
    A["Landing CSV"] --> B["bronze_to_silver"]
    B --> C["Silver Parquet Dataset"]
    C --> D["silver_to_gold"]
    D --> E["Gold Parquet Dataset"]
    E --> F["Glue Catalog / Athena"]
```

## 2. Current AWS Architecture

```mermaid
flowchart TB
    U["Source CSV Upload"] --> S3L["S3 Data Lake Bucket<br/>bronze/hr_attrition/landing/"]
    S3L --> EV["S3 Object Created Event"]
    EV --> EB["EventBridge Rule"]
    EB --> SF["Step Functions State Machine"]

    SF --> J1["Glue Job<br/>bronze_to_silver"]
    S3L --> J1
    J1 --> S3S["S3 Data Lake Bucket<br/>silver/hr_employees/"]

    SF --> J2["Glue Job<br/>silver_to_gold"]
    S3S --> J2
    J2 --> S3G["S3 Data Lake Bucket<br/>gold/hr_attrition/"]

    SF --> ATHV["Athena Validation"]
    S3G --> GC["Glue Catalog"]
    S3S --> GC
    GC --> ATH["Athena Queries"]
    ATHV --> ATHR["S3 Athena Results Bucket"]

    SCR["S3 Scripts Bucket<br/>Python + YAML + SQL + Contracts"] --> J1
    SCR --> J2

    CW["CloudWatch Logs + Metrics"] --> SF
    CW --> J1
    CW --> J2

    SNS["SNS Alerts"] --> CW
    KMS["KMS Encryption"] --> S3L
    KMS --> S3S
    KMS --> S3G
    KMS --> SCR
    KMS --> ATHR
    IAM["IAM Roles / Policies"] --> SF
    IAM --> J1
    IAM --> J2
```

## 3. Layer Detail

```mermaid
flowchart LR
    L["Landing<br/>File arrival and trigger"] --> SI["Silver<br/>Curated and typed"]
    SI --> GO["Gold<br/>Analytical and partitioned"]
```

- `Landing`: entry point for the CSV file and pipeline trigger.
- `Silver`: cleans, types, and normalizes the data.
- `Gold`: enriches the data and publishes it for analytics.

## 4. Local Execution Diagram

```mermaid
flowchart LR
    CSV["data/HR-Employee-Attrition.csv"] --> R["run_local_pipeline.py"]
    R --> B2S["bronze_to_silver.py"]
    B2S --> SIL["data/output/silver/hr_employees/"]
    SIL --> S2G["silver_to_gold.py"]
    S2G --> GOL["data/output/gold/hr_attrition/"]
```

## 5. Assets and Logic Diagram

```mermaid
flowchart TB
    CFG["transformations.yaml"] --> RT["pipeline_runtime.py"]
    CON["contracts.yaml"] --> RT
    Q1["bronze_to_silver.sql"] --> RT
    Q2["silver_to_gold.sql"] --> RT
    RT --> E1["bronze_to_silver.py"]
    RT --> E2["silver_to_gold.py"]
```

This reflects the separation of responsibilities in the project:

- `YAML`: pipeline configuration
- `SQL`: transformation logic
- `Python`: execution, validation, and materialization

## 6. Summary

The current ETL architecture combines:

- a clear `medallion` flow
- local execution with `DuckDB`
- AWS execution modeled with `S3 + EventBridge + Step Functions + Glue`
- analytical consumption with `Glue Catalog + Athena`
- security and observability with `IAM + KMS + CloudWatch + SNS`

The diagram represents the target architecture currently implemented in code and IaC. The main AWS path has already been validated functionally, while deployment automation and broader operational hardening are still evolving.
