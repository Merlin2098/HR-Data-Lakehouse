aws_region               = "us-east-1"
project_name             = "hr-data-lakehouse"
environment              = "prod"
name_prefix              = "hr-lakehouse"
athena_database_name     = "hr_attrition_lakehouse_prod"
athena_workgroup_name    = "hr-attrition-analytics-prod"
monthly_budget_limit_usd = 100
alert_email_endpoints    = []
landing_prefix           = "bronze/hr_attrition/landing/"
landing_suffix           = ".csv"
year_projection_range    = "2024,2035"

common_tags = {
  Owner      = "data-engineering"
  CostCenter = "hr-analytics"
}
