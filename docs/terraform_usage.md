# Terraform Usage

## Objetivo

Este documento define como usar Terraform en este repo de forma:

- local-friendly para pruebas manuales
- reusable para otros developers
- compatible con una futura ejecución por CI/CD

## Principios

- El repo define infraestructura, no credenciales.
- Las credenciales AWS nunca se versionan.
- El perfil local es una comodidad opcional, no una dependencia del sistema.
- CI/CD no debe depender de perfiles locales.

## Estructura Terraform

El root module vive en:

- [main.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/main.tf)

Los archivos principales están en:

- [provider.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/provider.tf)
- [variables.tf](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/variables.tf)
- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

La topología actual usa:

- 1 bucket `data_lake` por entorno con prefijos `bronze/`, `silver/` y `gold/`
- 1 bucket separado para `scripts`
- 1 bucket separado para `athena-results`
- 1 AWS Budget mensual por entorno para seguimiento de gasto

## Opciones para autenticación local

### Opción recomendada: `AWS_PROFILE`

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

### Opción opcional: `local.auto.tfvars`

Si quieres evitar exportar variables en cada sesión, puedes crear un archivo local no versionado:

- `infra/env/local.auto.tfvars`

Toma como base:

- [local.auto.tfvars.example](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/local.auto.tfvars.example)

Ejemplo:

```hcl
aws_profile = "admin2"
aws_region  = "us-east-1"
```

Ese archivo está ignorado por Git para no contaminar el repo.

## Convención de comandos

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

## Prerrequisito mínimo

Antes de correr `terraform plan`, esta llamada debe funcionar:

```powershell
aws sts get-caller-identity --region us-east-1
```

Si eso falla, Terraform también fallará por credenciales.

## CI/CD

La estrategia esperada para CI/CD es:

- `terraform fmt -check`
- `terraform init -backend=false`
- `terraform validate`
- `terraform plan -var-file=env/dev.tfvars`

Autenticación recomendada:

- `OIDC + assume role` en AWS

Fallback aceptable:

- credenciales temporales inyectadas como secrets del pipeline

No se debe usar `aws_profile` dentro del pipeline CI/CD.

## FinOps bÃ¡sico

El control de gasto se define en:

- [dev.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/dev.tfvars)
- [prod.tfvars](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/env/prod.tfvars)

Variable relevante:

- `monthly_budget_limit_usd`
- `alert_email_endpoints`

Comportamiento actual:

- 1 budget mensual por entorno
- alertas al `80%` y `100%`
- seguimiento de `actual spend` y `forecasted spend`
- envÃ­o de alertas al SNS del mÃ³dulo de observabilidad
- suscripciones opcionales por email administradas con Terraform

Notas:

- el budget monitorea gasto, no bloquea despliegues
- la separaciÃ³n por entorno depende del tag `Environment`
- para que el filtro por tag sea efectivo en AWS Budgets, el cost allocation tag `Environment` debe estar activado en Billing
- los correos SNS requieren confirmaciÃ³n manual despuÃ©s del `apply`
- el topic SNS estÃ¡ cifrado con KMS, por eso existen policies explÃ­citas para SNS y Budgets

## Backend

En esta iteración el repositorio queda preparado para:

- pruebas locales
- validación por CI/CD

usando:

```text
-backend=false
```

El backend remoto para state compartido queda como siguiente fase.

## Lock file

El lock file de Terraform se versiona en:

- [infra/.terraform.lock.hcl](C:/Users/User/Documents/VS%20Code/HR%20Data%20Lakehouse/infra/.terraform.lock.hcl)

Esto ayuda a que el equipo y CI/CD usen versiones consistentes de providers.
