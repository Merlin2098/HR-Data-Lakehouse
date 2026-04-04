# ETL Architecture Overview

## Objetivo

Este documento describe como esta estructurado el ETL del proyecto `HR Data Lakehouse`, cuales son sus capas, como se ejecuta localmente y como esta modelado para AWS alrededor del pipeline.

La idea es separar claramente:

- el flujo de datos del ETL
- la configuracion que gobierna la logica
- los servicios AWS que habilitan la ejecucion, catalogo, seguridad y observabilidad

## Vista General

El proyecto sigue una arquitectura `medallion` con el flujo:

```text
Landing -> Bronze -> Silver -> Gold
```

En terminos de ejecucion, el sistema esta pensado para dos modos:

- `local`, usando `DuckDB`
- `aws`, usando `Glue Spark`

La logica de negocio no vive hardcodeada en Python. Se divide de esta manera:

- `YAML`: configuracion del pipeline
- `SQL`: transformaciones de datos
- `Python`: runtime, orquestacion tecnica, validaciones y materializacion

## Estructura del ETL

### 1. Landing

Es la zona de llegada del archivo fuente.

- En local, el dataset base es [HR-Employee-Attrition.csv](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/data/HR-Employee-Attrition.csv)
- En AWS, el archivo llega al bucket compartido de data lake bajo el prefijo `bronze/hr_attrition/landing/`
- El trigger del pipeline se basa en la creacion de un objeto CSV en ese prefijo

Landing no aplica transformaciones de negocio. Solo representa el punto de entrada.

### 2. Bronze

Bronze representa la capa raw e inmutable.

- El job `landing_to_bronze` promueve el archivo desde landing a una ubicacion raw
- La convencion es `raw/ingestion_date=YYYY-MM-DD/<filename>`
- El archivo no se transforma; solo se preserva como evidencia de la carga del dia

Esto permite que bronze actue como fuente de verdad operativa para reprocesos.

### 3. Silver

Silver es la capa curada y tipada.

El job `bronze_to_silver`:

- lee el CSV raw
- limpia y normaliza strings
- hace casteos de tipos
- convierte `Yes/No` a booleanos
- descarta columnas no requeridas
- escribe Parquet con compresion `snappy`

La salida actual se modela como dataset Parquet no particionado.

Dataset logico:

- `silver_hr_employees`

Metadata tecnica incluida:

- `source_file`
- `run_id`
- `processed_at_utc`

### 4. Gold

Gold es la capa analitica.

El job `silver_to_gold`:

- lee el dataset silver
- aplica enriquecimiento analitico
- genera labels tipo Likert
- agrega metadata de ingesta
- escribe Parquet particionado en formato `Hive-style`

La particion actual es:

```text
year=YYYY/month=M/day=D
```

Dataset logico:

- `gold_hr_attrition_fact`

Metadata tecnica y operativa:

- `ingestion_date`
- `year`
- `month`
- `day`
- `source_file`
- `run_id`
- `processed_at_utc`

Politica de escritura:

- `silver`: `overwrite_full`
- `gold`: `overwrite_partition`

Eso significa que silver se reconstruye completo por corrida, mientras que gold solo reemplaza la particion del dia procesado.

## Archivos que gobiernan el pipeline

Los artefactos principales del ETL estan en `src/`:

- [transformations.yaml](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/configs/transformations.yaml): define pipelines, fuentes, targets, write modes, layouts y referencias a assets
- [contracts.yaml](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/configs/contracts.yaml): define contratos de silver y gold, calidad minima y metadata operativa
- [bronze_to_silver.sql](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/queries/bronze_to_silver.sql): limpieza y tipado
- [silver_to_gold.sql](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/queries/silver_to_gold.sql): enriquecimiento analitico
- [pipeline_runtime.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/common/pipeline_runtime.py): runtime comun para local y AWS
- [landing_to_bronze.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/landing_to_bronze.py): promocion raw
- [bronze_to_silver.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/bronze_to_silver.py): transformacion curada
- [silver_to_gold.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/silver_to_gold.py): transformacion analitica

## Ejecucion Local

En local el pipeline usa:

- `execution_mode: local`
- `engine: duckdb`

El runner principal es:

- [run_local_pipeline.py](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/src/glue/run_local_pipeline.py)

Flujo local:

1. lee el CSV de `data/`
2. genera silver como dataset Parquet local
3. genera gold como dataset Parquet particionado local

Este modo permite validar logica, contratos y outputs sin depender de AWS.

## Ejecucion AWS

En AWS el pipeline esta modelado para usar:

- `execution_mode: aws`
- `engine: glue_spark`

### Trigger del ETL

El procesamiento se gatilla cuando se crea un CSV en el prefijo de landing dentro de `bronze/` del bucket compartido de data lake.

Flujo esperado:

1. S3 recibe el archivo en `bronze/hr_attrition/landing/`
2. S3 publica el evento hacia EventBridge
3. EventBridge filtra `Object Created` para el bucket/prefijo/sufijo correcto
4. EventBridge inicia la state machine de Step Functions
5. Step Functions ejecuta:
   - `landing_to_bronze`
   - `bronze_to_silver`
   - `silver_to_gold`
   - `validate_catalog`

### Servicios AWS alrededor del ETL

#### S3

Se usan estos buckets:

- `data_lake`
- `scripts`
- `athena-results`

Responsabilidades:

- almacenamiento raw y curado por prefijos `bronze/`, `silver/` y `gold/`
- almacenamiento de scripts SQL/YAML/Python
- resultados de consultas Athena

Rutas fisicas AWS actuales:

- `bronze/hr_attrition/landing/`
- `bronze/hr_attrition/raw/`
- `silver/hr_employees/`
- `gold/hr_attrition/`

#### AWS Glue

Glue es el motor ETL en nube.

Jobs modelados:

- `landing_to_bronze`
- `bronze_to_silver`
- `silver_to_gold`

Responsabilidades:

- ejecutar los scripts Python
- correr transformaciones sobre Spark
- escribir datasets Parquet en S3

#### AWS Step Functions

Es el orquestador principal.

Responsabilidades:

- ordenar la secuencia del pipeline
- propagar parametros de ejecucion
- centralizar control de flujo
- dar visibilidad del estado de cada etapa

#### Amazon EventBridge

Se usa como mecanismo de disparo por evento.

Responsabilidades:

- recibir eventos `Object Created` desde S3
- filtrar solo archivos relevantes del landing
- iniciar la state machine

#### Glue Catalog

Se usa para registrar datasets analiticos.

Responsabilidades:

- exponer metadatos de silver y gold
- servir de catalogo para Athena

#### Athena

Se usa para validacion y consumo analitico.

Responsabilidades:

- consultar silver y gold
- ejecutar una validacion final al cierre de la state machine

#### CloudWatch y SNS

Se usan para observabilidad base.

Responsabilidades:

- logs de Glue y Step Functions
- alarmas basicas
- notificaciones operativas

#### KMS

Se usa para cifrado administrado.

Responsabilidades:

- cifrado de buckets S3
- cifrado de logs y componentes asociados

#### IAM

Se usa para permisos y control de acceso.

Responsabilidades:

- rol de Glue
- rol de Step Functions
- permisos least-privilege entre buckets, catalogo, logs y Athena

## Modulos Terraform relacionados

La infraestructura se organiza en `infra/modules/` con estos modulos principales:

- `kms`
- `s3`
- `assets`
- `iam`
- `glue`
- `catalog`
- `athena`
- `orchestration`
- `observability`

Su funcion combinada es:

- provisionar los servicios
- subir assets del pipeline a S3
- conectar trigger, ejecucion, catalogo y monitoreo

## Validaciones del runtime

El runtime no solo transforma datos; tambien valida condiciones minimas:

- esquema exacto contra contrato
- claves requeridas
- rangos de scores
- valores permitidos para labels
- consistencia entre `ingestion_date` y particiones

Esto ayuda a que el pipeline se comporte mas como un entorno productivo y no solo como una demo de transformacion.

## Estado actual del sistema

Hoy el sistema esta en este punto:

- el pipeline local esta implementado y validado
- el runtime AWS esta implementado en codigo
- la infraestructura Terraform esta modelada
- el trigger por `S3 Object Created` esta definido en IaC
- la ejecucion real en AWS aun no ha sido validada con `terraform apply` y corridas reales

En otras palabras:

- el diseño y el codigo del ETL ya existen
- la validacion operativa en AWS sigue pendiente

## Resumen

El ETL del proyecto esta estructurado como una plataforma `SQL-first` y `config-driven` con separacion clara entre:

- ingestión raw
- transformacion curada
- dataset analitico
- orquestacion
- catalogo
- seguridad
- observabilidad

Localmente corre con `DuckDB`. En AWS esta diseñado para correr con `S3 + EventBridge + Step Functions + Glue + Catalog + Athena + CloudWatch/SNS + KMS + IAM`.
