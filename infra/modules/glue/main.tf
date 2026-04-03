locals {
  script_location = "s3://${var.script_bucket}/${var.script_key}"
  config_uri      = "s3://${var.script_bucket}/${var.config_key}"
  contract_uri    = "s3://${var.script_bucket}/${var.contract_key}"
  query_uri       = "s3://${var.script_bucket}/${var.query_key}"
  source_uri      = "s3://${var.bronze_bucket}/hr_attrition/raw/WA_Fn-UseC_-HR-Employee-Attrition.csv"
  target_uri      = "s3://${var.silver_bucket}/hr_attrition/silver/hr_attrition.parquet"
  temp_dir_uri    = "s3://${var.script_bucket}/glue-temp/${var.job_name}/"
}

resource "aws_glue_job" "bronze_to_silver" {
  name     = var.job_name
  role_arn = var.role_arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = local.script_location
  }

  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0
  tags              = var.common_tags

  execution_property {
    max_concurrent_runs = 1
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--TempDir"                         = local.temp_dir_uri
    "--config-uri"                      = local.config_uri
    "--contracts-uri"                   = local.contract_uri
    "--query-uri"                       = local.query_uri
    "--source-uri"                      = local.source_uri
    "--target-uri"                      = local.target_uri
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                  = "true"
  }
}
