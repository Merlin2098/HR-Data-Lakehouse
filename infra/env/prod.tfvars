aws_region   = "us-east-1"
project_name = "hr-data-lakehouse"
environment  = "prod"
name_prefix  = "hr-lakehouse"
schedule_expression = "cron(0 9 * * ? *)"
athena_database_name = "hr_attrition_lakehouse_prod"
athena_workgroup_name = "hr-attrition-analytics-prod"
dataset_source_filename = "HR-Employee-Attrition.csv"
year_projection_range = "2024,2035"

common_tags = {
  Owner      = "data-engineering"
  CostCenter = "hr-analytics"
}
