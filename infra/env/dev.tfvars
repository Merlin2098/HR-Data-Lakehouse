aws_region   = "us-east-1"
project_name = "hr-data-lakehouse"
environment  = "dev"
name_prefix  = "hr-lakehouse"
schedule_expression = "cron(0 11 * * ? *)"
athena_database_name = "hr_attrition_lakehouse_dev"
athena_workgroup_name = "hr-attrition-analytics-dev"
dataset_source_filename = "HR-Employee-Attrition.csv"
year_projection_range = "2024,2035"

common_tags = {
  Owner      = "data-engineering"
  CostCenter = "hr-analytics"
}
