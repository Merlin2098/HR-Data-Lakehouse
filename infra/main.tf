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

  bronze_to_silver_job_name = "${var.name_prefix}-${var.environment}-bronze-to-silver"
  script_key                = "glue/bronze_to_silver.py"
  config_key                = "configs/transformations.yaml"
  contract_key              = "configs/contracts.yaml"
  query_key                 = "queries/bronze_to_silver.sql"
}

module "s3" {
  source      = "./modules/s3"
  name_prefix = var.name_prefix
  environment = var.environment
  region      = data.aws_region.current.name
  account_id  = data.aws_caller_identity.current.account_id
  common_tags = local.resource_tags
}

module "iam" {
  source            = "./modules/iam"
  name_prefix       = var.name_prefix
  environment       = var.environment
  bronze_bucket_arn = module.s3.bronze_bucket_arn
  silver_bucket_arn = module.s3.silver_bucket_arn
  scripts_bucket_arn = module.s3.scripts_bucket_arn
  common_tags       = local.resource_tags
}

module "glue" {
  source         = "./modules/glue"
  job_name       = local.bronze_to_silver_job_name
  role_arn       = module.iam.glue_role_arn
  script_bucket  = module.s3.scripts_bucket_name
  script_key     = local.script_key
  config_key     = local.config_key
  contract_key   = local.contract_key
  query_key      = local.query_key
  bronze_bucket  = module.s3.bronze_bucket_name
  silver_bucket  = module.s3.silver_bucket_name
  common_tags    = local.resource_tags
}
