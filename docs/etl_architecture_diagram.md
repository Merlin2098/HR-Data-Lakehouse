# ETL Architecture Diagram

## Objetivo

Este documento muestra el diagrama de la arquitectura actual del ETL, tanto en su flujo funcional como en los servicios AWS que lo soportan alrededor.

## 1. Flujo general del ETL

```mermaid
flowchart LR
    A["Landing CSV"] --> B["landing_to_bronze"]
    B --> C["Bronze Raw CSV"]
    C --> D["bronze_to_silver"]
    D --> E["Silver Parquet Dataset"]
    E --> F["silver_to_gold"]
    F --> G["Gold Parquet Dataset"]
    G --> H["Glue Catalog / Athena"]
```

## 2. Arquitectura AWS actual

```mermaid
flowchart TB
    U["Source CSV Upload"] --> S3L["S3 Data Lake Bucket<br/>bronze/hr_attrition/landing/"]
    S3L --> EV["S3 Object Created Event"]
    EV --> EB["EventBridge Rule"]
    EB --> SF["Step Functions State Machine"]

    SF --> J1["Glue Job<br/>landing_to_bronze"]
    J1 --> S3B["S3 Data Lake Bucket<br/>bronze/hr_attrition/raw/ingestion_date=YYYY-MM-DD/"]

    SF --> J2["Glue Job<br/>bronze_to_silver"]
    S3B --> J2
    J2 --> S3S["S3 Data Lake Bucket<br/>silver/hr_employees/"]

    SF --> J3["Glue Job<br/>silver_to_gold"]
    S3S --> J3
    J3 --> S3G["S3 Data Lake Bucket<br/>gold/hr_attrition/"]

    SF --> ATHV["Athena Validation"]
    S3G --> GC["Glue Catalog"]
    S3S --> GC
    GC --> ATH["Athena Queries"]
    ATHV --> ATHR["S3 Athena Results Bucket"]

    SCR["S3 Scripts Bucket<br/>Python + YAML + SQL + Contracts"] --> J1
    SCR --> J2
    SCR --> J3

    CW["CloudWatch Logs + Metrics"] --> SF
    CW --> J1
    CW --> J2
    CW --> J3

    SNS["SNS Alerts"] --> CW
    KMS["KMS Encryption"] --> S3L
    KMS --> S3B
    KMS --> S3S
    KMS --> S3G
    KMS --> SCR
    KMS --> ATHR
    IAM["IAM Roles / Policies"] --> SF
    IAM --> J1
    IAM --> J2
    IAM --> J3
```

## 3. Detalle de las layers

```mermaid
flowchart LR
    L["Landing<br/>Archivo recibido"] --> BR["Bronze<br/>Raw e inmutable"]
    BR --> SI["Silver<br/>Curado y tipado"]
    SI --> GO["Gold<br/>Analitico y particionado"]
```

- `Landing`: punto de entrada del archivo CSV.
- `Bronze`: conserva el raw por fecha de ingesta.
- `Silver`: limpia, tipa y normaliza la data.
- `Gold`: enriquece la data y la publica para analitica.

## 4. Diagrama de ejecucion local

```mermaid
flowchart LR
    CSV["data/HR-Employee-Attrition.csv"] --> R["run_local_pipeline.py"]
    R --> B2S["bronze_to_silver.py"]
    B2S --> SIL["data/output/silver/hr_employees/"]
    SIL --> S2G["silver_to_gold.py"]
    S2G --> GOL["data/output/gold/hr_attrition/"]
```

## 5. Diagrama de assets y logica

```mermaid
flowchart TB
    CFG["transformations.yaml"] --> RT["pipeline_runtime.py"]
    CON["contracts.yaml"] --> RT
    Q1["bronze_to_silver.sql"] --> RT
    Q2["silver_to_gold.sql"] --> RT
    RT --> E1["landing_to_bronze.py"]
    RT --> E2["bronze_to_silver.py"]
    RT --> E3["silver_to_gold.py"]
```

Esto refleja la separacion de responsabilidades del proyecto:

- `YAML`: configuracion del pipeline
- `SQL`: logica de transformacion
- `Python`: ejecucion, validacion y materializacion

## 6. Resumen

La arquitectura actual del ETL combina:

- un flujo `medallion` claro
- ejecucion local con `DuckDB`
- ejecucion AWS modelada con `S3 + EventBridge + Step Functions + Glue`
- consumo analitico con `Glue Catalog + Athena`
- seguridad y observabilidad con `IAM + KMS + CloudWatch + SNS`

El diagrama representa la arquitectura objetivo actualmente implementada en codigo e IaC, aunque la validacion real en AWS sigue pendiente.
