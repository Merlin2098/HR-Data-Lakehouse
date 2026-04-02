# ADR-001: HR Attrition Data Pipeline (AWS, S3 + Glue + Athena + Terraform)

- Status: Accepted
- Date: 2026-03-20
- Decision Makers: Data Engineering
- Tags: data-lake, aws, s3, glue, athena, parquet, terraform, analytics

---

## Context

Se requiere diseñar un sistema de datos que permita analizar la rotación de empleados (attrition) y sus factores asociados (salario, antigüedad, satisfacción, condiciones laborales y variables organizacionales).

El dataset de entrada corresponde a IBM HR Attrition (CSV) con múltiples columnas de características por empleado.

El objetivo es construir un pipeline en AWS que:
- Preserve la fuente original
- Aplique limpieza y tipado
- Modele los datos para análisis
- Permita consultas eficientes con Athena
- Sea reproducible mediante Terraform

---

## Decision

Se adopta una arquitectura de Data Lake en AWS con tres capas:

### 1. Bronze (Raw)
- Almacena datos originales sin transformación
- Formato: CSV
- Ubicación: S3

### 2. Silver (Processed)
- Limpieza, normalización y tipado
- Selección de columnas relevantes
- Conversión a Parquet
- Validaciones de esquema

### 3. Gold (Analytics)
- Tabla analítica optimizada (fact table extendida)
- Enriquecimiento semántico (labels Likert)
- Particionado por fecha de ingesta
- Formato Parquet optimizado para Athena

---

## Architecture Overview

Flujo:

Dataset (CSV)
    ↓
S3 Bronze (raw)
    ↓
AWS Glue (ETL)
    ↓
S3 Silver (Parquet, tipado)
    ↓
AWS Glue (transformación final)
    ↓
S3 Gold (Parquet, modelo analítico)
    ↓
Amazon Athena (consulta)

---

## Bronze Layer

- Datos inmutables
- Sin validación ni transformación
- Ejemplo:
  s3://hr-data-lake/raw/hr/YYYY/MM/DD/data.csv

---

## Silver Layer

### Transformaciones:
- Casting de tipos
- Normalización de columnas (snake_case)
- Normalización de valores (lowercase, trim)
- Eliminación de columnas irrelevantes
- Validaciones de esquema

### Esquema:

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

Formato: Parquet

---

## Gold Layer

### Tabla: gold_hr_attrition_fact

Incluye:
- Métricas
- Atributos analíticos
- Representación numérica y semántica

### Esquema:

- employee_id: integer
- ingestion_year: integer
- ingestion_month: integer
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

### Likert Mapping:

1 → low  
2 → medium  
3 → high  
4 → very_high  

### Partición:
- ingestion_year
- ingestion_month

---

## Technology Choices

### Amazon S3
- Data Lake escalable
- Bajo costo

### AWS Glue
- ETL serverless
- Integración con Data Catalog

### Amazon Athena
- Query serverless sobre S3
- Ideal para análisis exploratorio

### Parquet
- Formato columnar
- Mejor performance y compresión

### Terraform
- Infraestructura como código
- Reproducibilidad

---

## Alternatives Considered

### Usar CSV en todas las capas
- Rechazado por baja performance

### Modelo dimensional completo (fact + dims)
- Rechazado por complejidad innecesaria en Athena

### Uso de Redshift
- Rechazado para mantener arquitectura serverless

---

## Consequences

### Positivas
- Arquitectura simple y escalable
- Bajo costo operativo
- Fácil de extender a ingestion incremental
- Buen rendimiento en consultas

### Negativas
- Sin normalización estricta (fact extendida)
- Dependencia de buenas prácticas en S3

---

## Future Improvements

- Ingesta incremental vía API
- Orquestación con EventBridge / Step Functions
- Implementación de Slowly Changing Dimensions
- Dashboard (QuickSight / BI)

---

## Notes

Este diseño prioriza:
- Simplicidad
- Escalabilidad
- Claridad para análisis de negocio

