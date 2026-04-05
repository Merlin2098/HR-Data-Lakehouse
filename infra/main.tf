data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  mandatory_tags = {
    Project     = "HR_LakeHouse_Project"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = var.project_name
  }

  resource_tags = merge(local.mandatory_tags, var.common_tags)

  bronze_to_silver_job_name  = "${var.name_prefix}-${var.environment}-bronze-to-silver"
  silver_to_gold_job_name    = "${var.name_prefix}-${var.environment}-silver-to-gold"

  step_function_name = "${var.name_prefix}-${var.environment}-event-medallion"
  event_rule_name    = "${var.name_prefix}-${var.environment}-landing-created"
  event_target_id    = "${var.name_prefix}-${var.environment}-start-medallion"

  bronze_to_silver_log_group = "/aws/glue/${local.bronze_to_silver_job_name}"
  silver_to_gold_log_group   = "/aws/glue/${local.silver_to_gold_job_name}"
  step_functions_log_group   = "/aws/vendedlogs/states/${local.step_function_name}"
}

module "kms" {
  source      = "./modules/kms"
  name_prefix = var.name_prefix
  environment = var.environment
  common_tags = local.resource_tags
}

module "s3" {
  source      = "./modules/s3"
  name_prefix = var.name_prefix
  environment = var.environment
  region      = data.aws_region.current.name
  account_id  = data.aws_caller_identity.current.account_id
  kms_key_arn = module.kms.kms_key_arn
  scripts_bucket_reader_arns = concat(
    ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"],
    var.scripts_bucket_reader_arns,
  )
  quicksight_principal_arns = var.quicksight_principal_arns
  common_tags = local.resource_tags
}

module "assets" {
  source              = "./modules/assets"
  scripts_bucket_name = module.s3.scripts_bucket_name
  common_tags         = local.resource_tags
}

module "iam" {
  source                    = "./modules/iam"
  name_prefix               = var.name_prefix
  environment               = var.environment
  region                    = data.aws_region.current.name
  account_id                = data.aws_caller_identity.current.account_id
  data_lake_bucket_arn      = module.s3.data_lake_bucket_arn
  scripts_bucket_arn        = module.s3.scripts_bucket_arn
  athena_results_bucket_arn = module.s3.athena_results_bucket_arn
  kms_key_arn               = module.kms.kms_key_arn
  athena_workgroup_name     = var.athena_workgroup_name
  common_tags               = local.resource_tags
}

module "glue" {
  source                          = "./modules/glue"
  environment                     = var.environment
  bronze_to_silver_job_name       = local.bronze_to_silver_job_name
  silver_to_gold_job_name         = local.silver_to_gold_job_name
  role_arn                        = module.iam.glue_role_arn
  script_bucket                   = module.s3.scripts_bucket_name
  data_lake_bucket                = module.s3.data_lake_bucket_name
  config_key                      = module.assets.config_key
  contract_key                    = module.assets.contract_key
  bronze_to_silver_script_key     = module.assets.bronze_to_silver_script_key
  silver_to_gold_script_key       = module.assets.silver_to_gold_script_key
  bronze_to_silver_query_key      = module.assets.bronze_to_silver_query_key
  silver_to_gold_query_key        = module.assets.silver_to_gold_query_key
  glue_runtime_package_key        = module.assets.glue_runtime_package_key
  bronze_to_silver_log_group_name = local.bronze_to_silver_log_group
  silver_to_gold_log_group_name   = local.silver_to_gold_log_group
  kms_key_arn                     = module.kms.kms_key_arn
  common_tags                     = local.resource_tags
}

module "catalog" {
  source                = "./modules/catalog"
  database_name         = var.athena_database_name
  data_lake_bucket_name = module.s3.data_lake_bucket_name
  year_projection_range = var.year_projection_range
  common_tags           = local.resource_tags
}

module "athena" {
  source                = "./modules/athena"
  workgroup_name        = var.athena_workgroup_name
  athena_results_bucket = module.s3.athena_results_bucket_name
  kms_key_arn           = module.kms.kms_key_arn
  common_tags           = local.resource_tags
}

module "orchestration" {
  source                        = "./modules/orchestration"
  state_machine_name            = local.step_function_name
  event_rule_name               = local.event_rule_name
  event_target_id               = local.event_target_id
  step_functions_role_arn       = module.iam.step_functions_role_arn
  bronze_to_silver_job_name     = module.glue.bronze_to_silver_job_name
  silver_to_gold_job_name       = module.glue.silver_to_gold_job_name
  athena_workgroup_name         = module.athena.workgroup_name
  athena_database_name          = module.catalog.database_name
  gold_table_name               = module.catalog.gold_table_name
  data_lake_bucket_name         = module.s3.data_lake_bucket_name
  landing_prefix                = var.landing_prefix
  landing_suffix                = var.landing_suffix
  step_functions_log_group_name = local.step_functions_log_group
  athena_results_bucket_name    = module.s3.athena_results_bucket_name
  kms_key_arn                   = module.kms.kms_key_arn
  common_tags                   = local.resource_tags
}

module "observability" {
  source                = "./modules/observability"
  account_id            = data.aws_caller_identity.current.account_id
  kms_key_arn           = module.kms.kms_key_arn
  glue_job_names        = module.glue.job_names
  state_machine_name    = module.orchestration.state_machine_name
  state_machine_arn     = module.orchestration.state_machine_arn
  alert_email_endpoints = var.alert_email_endpoints
  common_tags           = local.resource_tags
}

module "budgets" {
  source                   = "./modules/budgets"
  account_id               = data.aws_caller_identity.current.account_id
  name_prefix              = var.name_prefix
  project_name             = var.project_name
  environment              = var.environment
  monthly_budget_limit_usd = var.monthly_budget_limit_usd
  sns_topic_arn            = module.observability.alerts_topic_arn
  budget_name_override     = var.budget_name_override
  common_tags              = local.resource_tags
}
