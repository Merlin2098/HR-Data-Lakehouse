# 🧠 Data Pipeline Design — HR Attrition Lakehouse

---

# 🎯 Objective

Design a **config-driven, cloud-native data pipeline** using Medallion Architecture:

* Bronze → raw ingestion
* Silver → cleaned and structured data
* Gold → enriched analytical dataset

---

# 🧱 1. High-Level Flow

```text
CSV (raw, all columns as string)
        ↓
[S3 - Bronze]
        ↓
Glue ETL
        ↓
Cast + cleaning + normalization
        ↓
Parquet
        ↓
[S3 - Silver]
        ↓
Glue ETL (enrichment)
        ↓
Business logic + feature engineering
        ↓
Parquet (partitioned)
        ↓
[S3 - Gold]
```

📌 Basado en flujo definido en el PDF (página 1)

---

# 🥉 2. Bronze Layer (Raw)

## 🎯 Purpose

Store raw data exactly as received.

---

## Characteristics

* Format: CSV
* Schema: ❌ Not enforced (all string)
* Transformations: ❌ None

---

## Example

```text
s3://<bucket>/bronze/hr_attrition/raw.csv
```

---

## Key Principle

> Bronze = source of truth (immutable)

---

# 🥈 3. Silver Layer (Cleaned & Structured)

## 🎯 Purpose

Standardize, clean, and type data.

---

## Transformations

From PDF (página 1):

* Cast types
* Normalize strings (lowercase, trim)
* Convert booleans:
  * Yes → true
  * No → false
* Drop unnecessary columns

---

## Data Model

### Table: `silver_hr_employees`

| Column                     | Type          | Description          |
| -------------------------- | ------------- | -------------------- |
| employee_number            | integer       | Primary key          |
| department                 | string        | normalized           |
| job_role                   | string        | normalized           |
| job_level                  | integer       |                      |
| over_time                  | boolean       | Yes/No → true/false |
| monthly_income             | decimal(12,2) |                      |
| percent_salary_hike        | integer       |                      |
| years_at_company           | integer       |                      |
| years_since_last_promotion | integer       |                      |
| total_working_years        | integer       |                      |
| job_satisfaction           | integer       | range [1-4]          |
| environment_satisfaction   | integer       | range [1-4]          |
| relationship_satisfaction  | integer       | range [1-4]          |
| work_life_balance          | integer       | range [1-4]          |
| attrition                  | boolean       | Yes/No → true/false |

📌 Basado en catálogo Silver (página 1)

---

## Output Format

* Format: Parquet
* Compression: Snappy
* Structure: columnar (Athena optimized)

---

## Example Path

```text
s3://<bucket>/silver/hr_attrition/data.parquet
```

---

# 🥇 4. Gold Layer (Enriched / Analytics)

## 🎯 Purpose

Create a dataset ready for analytics and BI.

---

## Table: `gold_hr_attrition_fact`

### Core Structure

#### Identifiers

* employee_id (int)

#### Ingestion partition

* ingestion_year (int)
* ingestion_month (int)

#### Organizational context

* department (string)
* job_role (string)
* job_level (int)

#### Main event

* attrition (boolean)

#### Compensation

* monthly_income (decimal)
* percent_salary_hike (int)

#### Experience

* years_at_company (int)
* years_since_last_promotion (int)
* total_working_years (int)

#### Work conditions

* over_time (boolean)

#### Satisfaction (numeric)

* job_satisfaction_score (int)
* environment_satisfaction_score (int)
* relationship_satisfaction_score (int)
* work_life_balance_score (int)

#### Satisfaction (categorical)

* job_satisfaction_label (string)
* environment_satisfaction_label (string)
* relationship_satisfaction_label (string)
* work_life_balance_label (string)

📌 Basado en esquema Gold (página 2)

---

# 🧠 5. Enrichment Logic (Gold)

## Likert → Label Mapping

```text
1 → low
2 → medium
3 → high
4 → very_high
```

📌 Definido en lógica de enriquecimiento (página 3)

---

## Rule

Apply mapping to all satisfaction columns.

---

# 🪣 6. Storage Strategy (S3)

## Partitioning

```text
s3://hr-data-lake/analytics/hr_attrition/
    ingestion_year=YYYY/
        ingestion_month=MM/
            data.parquet
```

📌 Basado en ubicación S3 (página 3)

---

## Benefits

* Optimized Athena queries
* Partition pruning
* Cost reduction

---

# ⚙️ 7. Format Strategy

| Layer  | Schema      | Format  |
| ------ | ----------- | ------- |
| Bronze | Not defined | CSV     |
| Silver | Typed       | Parquet |
| Gold   | Optimized   | Parquet |

📌 Resumen del PDF (página 3)

---

# 🔄 8. Pipeline Execution Logic

---

## Step 1 — Bronze → Silver

* Read CSV (all string)
* Apply:
  * casting
  * cleaning
  * normalization
* Output → Parquet

---

## Step 2 — Silver → Gold

* Read Parquet (typed data)
* Apply:
  * enrichment (labels)
  * partition columns
* Output → partitioned Parquet

---

# 🧩 9. Design Principles

---

## 1. Separation of concerns

* YAML → business rules
* SQL → transformations
* Python → execution

---

## 2. Data contracts

* Silver defines schema
* Gold defines business semantics

---

## 3. Idempotency

* Pipelines can run multiple times safely

---

## 4. Engine-agnostic design

* Works with:
  * Glue (Spark)
  * Athena
  * DuckDB (local)

---

# 🚀 10. Final Insight

This pipeline is not just ETL.

It is:

> A reproducible, config-driven data platform
> where logic is externalized and execution is scalable

---
