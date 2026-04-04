# Terraform Usage

## Objetivo

Este documento define como usar Terraform en este repo de forma:

- local-friendly para pruebas manuales
- reusable para otros developers
- compatible con una futura ejecucion por CI/CD

## Principios

- El repo define infraestructura, no credenciales.
- Las credenciales AWS nunca se versionan.
- El perfil local es una comodidad opcional, no una dependencia del sistema.
- CI/CD no debe depender de perfiles locales.

## Estructura Terraform

El root module vive en:

- [main.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/main.tf)

Los archivos principales estan en:

- [provider.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/provider.tf)
- [variables.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/variables.tf)
- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

La topologia actual usa:

- 1 bucket `data_lake` por entorno con prefijos `bronze/`, `silver/` y `gold/`
- 1 bucket separado para `scripts`
- 1 bucket separado para `athena-results`
- 1 AWS Budget mensual por entorno para seguimiento de gasto

Nota operativa sobre buckets:

- `data_lake` y `athena-results` siguen con `SSE-KMS`
- `scripts` usa `SSE-S3 (AES256)` para facilitar inspeccion manual en demo
- `root` de la cuenta y los ARNs declarados en `scripts_bucket_reader_arns` tienen acceso de solo lectura al bucket `scripts`
- Terraform crea placeholders `.keep` en los prefijos medallion operativos del bucket `data_lake`
- esos placeholders solo hacen visible la estructura base y no reemplazan la carga de datos reales
- las rutas fisicas curadas en AWS estan normalizadas como `silver/hr_employees/` y `gold/hr_attrition/`

## Trigger y retry del pipeline

Trigger automatico en AWS:

- subir un CSV a `s3://<data_lake_bucket>/bronze/hr_attrition/landing/<archivo>.csv`
- EventBridge detecta `Object Created`
- Step Functions normaliza el payload y ejecuta:
  - `landing_to_bronze`
  - `bronze_to_silver`
  - `silver_to_gold`
  - `validate_catalog`
- cada task Glue conserva `business_date`, `run_id` y `source_filename` en el payload raiz y adjunta su resultado en subcampos dedicados

Retry manual sin reupload:

- obtener el ARN de la state machine:

```powershell
$env:AWS_PROFILE="admin2"
terraform -chdir=infra output -raw state_machine_arn
```

- reprocesar un objeto ya existente en S3:

```powershell
$env:AWS_PROFILE="admin2"
$stateMachineArn = terraform -chdir=infra output -raw state_machine_arn
.\.venv\Scripts\python.exe src\glue\retry_state_machine.py `
  --state-machine-arn $stateMachineArn `
  --source-uri "s3://hr-lakehouse-dev-184670914470-us-east-1-data-lake/bronze/hr_attrition/landing/HR-Employee-Attrition.csv" `
  --business-date 2026-04-04
```

Notas operativas:

- el helper construye el input manual esperado por `NormalizeManualInput`
- `source_filename` se deriva del ultimo segmento del key S3
- `business_date` se controla de forma explicita y no se infiere del nombre del archivo
- si omites `--run-id`, el helper genera uno nuevo
- si omites `--event-time`, el helper usa el timestamp UTC actual
- no se vuelve a subir el archivo; el objeto debe existir previamente en `landing`

## Opciones para autenticacion local

### Opcion recomendada: `AWS_PROFILE`

Esta es la forma preferida para trabajar localmente:

```powershell
$env:AWS_PROFILE="admin2"
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file="env/dev.tfvars"
```

Ventajas:

- no ensucia archivos versionados
- cada developer puede usar su propio perfil
- se parece al comportamiento esperado en AWS SDK/CLI

### Opcion opcional: `local.auto.tfvars`

Si quieres evitar exportar variables en cada sesion, puedes crear un archivo local no versionado:

- `infra/env/local.auto.tfvars`

Toma como base:

- [local.auto.tfvars.example](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/local.auto.tfvars.example)

Ejemplo:

```hcl
aws_profile = "admin2"
aws_region  = "us-east-1"
```

Ese archivo esta ignorado por Git para no contaminar el repo.

## Convencion de comandos

### Windows PowerShell

Usa esta forma para `-var-file`:

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

## Prerrequisito minimo

Antes de correr `terraform plan`, esta llamada debe funcionar:

```powershell
aws sts get-caller-identity --region us-east-1
```

Si eso falla, Terraform tambien fallara por credenciales.

## CI/CD

La estrategia esperada para CI/CD es:

- `terraform fmt -check`
- `terraform init -backend=false`
- `terraform validate`
- `terraform plan -var-file=env/dev.tfvars`

Triggers actuales del workflow:

- `push` a `main`
- `pull_request`
- `workflow_dispatch`

Autenticacion recomendada:

- `OIDC + assume role` en AWS

Fallback aceptable:

- credenciales temporales inyectadas como secrets del pipeline

No se debe usar `aws_profile` dentro del pipeline CI/CD.
El `plan` automatico de GitHub Actions esta acotado a `dev`; `prod` sigue siendo manual en esta etapa.

## FinOps basico

El control de gasto se define en:

- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

Variables relevantes:

- `monthly_budget_limit_usd`
- `alert_email_endpoints`

Comportamiento actual:

- 1 budget mensual por entorno
- alertas al `80%` y `100%`
- seguimiento de `actual spend` y `forecasted spend`
- envio de alertas al SNS del modulo de observabilidad
- suscripciones opcionales por email administradas con Terraform

Notas:

- el budget monitorea gasto, no bloquea despliegues
- la separacion por entorno depende del tag `Environment`
- para que el filtro por tag sea efectivo en AWS Budgets, el cost allocation tag `Environment` debe estar activado en Billing
- los correos SNS requieren confirmacion manual despues del `apply`
- el topic SNS esta cifrado con KMS, por eso existen policies explicitas para SNS y Budgets

## Backend

En esta iteracion el repositorio queda preparado para:

- pruebas locales
- validacion por CI/CD

usando:

```text
-backend=false
```

El backend remoto para state compartido queda como siguiente fase.

## Lock file

El lock file de Terraform se versiona en:

- [infra/.terraform.lock.hcl](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/.terraform.lock.hcl)

Esto ayuda a que el equipo y CI/CD usen versiones consistentes de providers.
