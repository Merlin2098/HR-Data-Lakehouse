# ADR-001: HR Attrition Data Pipeline (AWS, S3 + Glue + Athena + Terraform)

- Status: Accepted
- Date: 2026-03-20
- Decision Makers: Data Engineering
- Tags: data-lake, aws, s3, glue, athena, parquet, terraform, analytics

---

## Context

We need to design a data system that supports analysis of employee attrition and its related factors such as salary, tenure, satisfaction, working conditions, and organizational variables.

The input dataset is IBM HR Attrition (CSV) with multiple employee-level feature columns.

The goal is to build an AWS pipeline that:

- preserves the original source
- applies cleaning and typing
- models the data for analysis
- allows efficient Athena queries
- is reproducible through Terraform

---

## Decision

An AWS data lake architecture is adopted with three layers:

### 1. Bronze

- stores original data without transformation
- format: CSV
- location: S3

### 2. Silver

- cleaning, normalization, and typing
- selection of relevant columns
- conversion to Parquet
- schema validations

### 3. Gold

- optimized analytical table (extended fact table)
- semantic enrichment (Likert labels)
- partitioning by ingestion date
- Parquet format optimized for Athena

---

## Architecture Overview

Flow:

```text
Dataset (CSV)
    ↓
S3 Bronze / Landing
    ↓
AWS Glue
    ↓
S3 Silver (typed Parquet)
    ↓
AWS Glue (final transformation)
    ↓
S3 Gold (analytical Parquet)
    ↓
Amazon Athena
```

---

## Bronze Layer

- immutable source data
- no validation or transformation
- example:

```text
s3://hr-data-lake/bronze/hr_attrition/landing/data.csv
```

---

## Silver Layer

### Transformations

- type casting
- column normalization (`snake_case`)
- value normalization (`lowercase`, `trim`)
- removal of irrelevant columns
- schema validations

### Schema

- employee_number: integer
- department: string
- job_role: string
- job_level: integer
- over_time: boolean
- monthly_income: decimal(12,2)
- percent_salary_hike: integer
- years_at_company: integer
- years_since_last_promotion: integer
- total_working_years: integer
- job_satisfaction: integer
- environment_satisfaction: integer
- relationship_satisfaction: integer
- work_life_balance: integer
- attrition: boolean

Format: Parquet

---

## Gold Layer

### Table: `gold_hr_attrition_fact`

Includes:

- metrics
- analytical attributes
- numeric and semantic representation

### Schema

- employee_id: integer
- year: integer
- month: integer
- day: integer
- department: string
- job_role: string
- job_level: integer
- attrition: boolean
- monthly_income: decimal(12,2)
- percent_salary_hike: integer
- years_at_company: integer
- years_since_last_promotion: integer
- total_working_years: integer
- over_time: boolean
- job_satisfaction_score: integer
- environment_satisfaction_score: integer
- relationship_satisfaction_score: integer
- work_life_balance_score: integer
- job_satisfaction_label: string
- environment_satisfaction_label: string
- relationship_satisfaction_label: string
- work_life_balance_label: string

### Likert Mapping

1 → low  
2 → medium  
3 → high  
4 → very_high

### Partitioning

- year
- month
- day

---

## Technology Choices

### Amazon S3

- scalable data lake
- low cost

### AWS Glue

- serverless ETL
- integration with Data Catalog

### Amazon Athena

- serverless querying over S3
- ideal for exploratory analytics

### Parquet

- columnar format
- better performance and compression

### Terraform

- infrastructure as code
- reproducibility

---

## Alternatives Considered

### Use CSV in every layer

- rejected because of poor performance

### Full dimensional model (fact + dimensions)

- rejected due to unnecessary complexity for Athena

### Use Redshift

- rejected to keep the architecture serverless

---

## Consequences

### Positive

- simple and scalable architecture
- low operational cost
- easy to extend toward incremental ingestion
- good query performance

### Negative

- no strict normalization (extended fact table)
- dependence on good S3 practices

---

## Future Improvements

- incremental ingestion through an API
- orchestration with EventBridge / Step Functions
- implementation of Slowly Changing Dimensions
- dashboarding (QuickSight / BI)

---

## Notes

This design prioritizes:

- simplicity
- scalability
- clarity for business analysis
