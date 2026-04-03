locals {
  config_uri                  = "s3://${var.script_bucket}/${var.config_key}"
  contract_uri                = "s3://${var.script_bucket}/${var.contract_key}"
  landing_script_location     = "s3://${var.script_bucket}/${var.landing_script_key}"
  bronze_script_location      = "s3://${var.script_bucket}/${var.bronze_to_silver_script_key}"
  gold_script_location        = "s3://${var.script_bucket}/${var.silver_to_gold_script_key}"
  bronze_query_uri            = "s3://${var.script_bucket}/${var.bronze_to_silver_query_key}"
  gold_query_uri              = "s3://${var.script_bucket}/${var.silver_to_gold_query_key}"

  bronze_raw_root_uri         = "s3://${var.bronze_bucket}/hr_attrition/raw/"
  silver_dataset_uri          = "s3://${var.silver_bucket}/hr_attrition/silver/hr_employees/"
  gold_dataset_uri            = "s3://${var.gold_bucket}/hr_attrition/gold/hr_attrition/"

  temp_dir_prefix = "glue-temp"
}

resource "aws_cloudwatch_log_group" "landing_to_bronze" {
  name              = var.landing_log_group_name
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "bronze_to_silver" {
  name              = var.bronze_to_silver_log_group_name
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "silver_to_gold" {
  name              = var.silver_to_gold_log_group_name
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn
  tags              = var.common_tags
}

resource "aws_glue_job" "landing_to_bronze" {
  name     = var.landing_to_bronze_job_name
  role_arn = var.role_arn

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = local.landing_script_location
  }

  max_capacity = 0.0625
  timeout      = 10
  max_retries  = 0
  tags         = var.common_tags

  default_arguments = {
    "--target-uri"        = local.bronze_raw_root_uri
  }
}

resource "aws_glue_job" "bronze_to_silver" {
  name     = var.bronze_to_silver_job_name
  role_arn = var.role_arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = local.bronze_script_location
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 15
  max_retries       = 0
  tags              = var.common_tags

  execution_property {
    max_concurrent_runs = 1
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--TempDir"                          = "s3://${var.script_bucket}/${local.temp_dir_prefix}/${var.bronze_to_silver_job_name}/"
    "--config-uri"                       = local.config_uri
    "--contracts-uri"                    = local.contract_uri
    "--query-uri"                        = local.bronze_query_uri
    "--source-uri"                       = local.bronze_raw_root_uri
    "--target-uri"                       = local.silver_dataset_uri
    "--execution-mode"                   = "aws"
    "--engine"                           = "glue_spark"
    "--enable-continuous-cloudwatch-log" = "true"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.bronze_to_silver.name
    "--enable-metrics"                   = "true"
  }
}

resource "aws_glue_job" "silver_to_gold" {
  name     = var.silver_to_gold_job_name
  role_arn = var.role_arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = local.gold_script_location
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 15
  max_retries       = 0
  tags              = var.common_tags

  execution_property {
    max_concurrent_runs = 1
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--TempDir"                          = "s3://${var.script_bucket}/${local.temp_dir_prefix}/${var.silver_to_gold_job_name}/"
    "--config-uri"                       = local.config_uri
    "--contracts-uri"                    = local.contract_uri
    "--query-uri"                        = local.gold_query_uri
    "--source-uri"                       = local.silver_dataset_uri
    "--target-uri"                       = local.gold_dataset_uri
    "--execution-mode"                   = "aws"
    "--engine"                           = "glue_spark"
    "--enable-continuous-cloudwatch-log" = "true"
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.silver_to_gold.name
    "--enable-metrics"                   = "true"
  }
}
