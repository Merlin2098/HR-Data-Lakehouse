output "data_lake_bucket_name" {
  description = "Shared data lake bucket name."
  value       = module.s3.data_lake_bucket_name
}

output "scripts_bucket_name" {
  description = "Scripts bucket name."
  value       = module.s3.scripts_bucket_name
}

output "athena_results_bucket_name" {
  description = "Athena results bucket name."
  value       = module.s3.athena_results_bucket_name
}

output "kms_key_arn" {
  description = "Lakehouse KMS key ARN."
  value       = module.kms.kms_key_arn
}

output "glue_role_arn" {
  description = "Glue execution role ARN."
  value       = module.iam.glue_role_arn
}

output "glue_job_names" {
  description = "Glue job names for the medallion pipeline."
  value       = module.glue.job_names
}

output "athena_workgroup_name" {
  description = "Athena workgroup name."
  value       = module.athena.workgroup_name
}

output "catalog_database_name" {
  description = "Glue Catalog database name."
  value       = module.catalog.database_name
}

output "state_machine_arn" {
  description = "Step Functions state machine ARN."
  value       = module.orchestration.state_machine_arn
}

output "event_rule_name" {
  description = "EventBridge rule name that triggers the state machine from S3 events."
  value       = module.orchestration.event_rule_name
}

output "budget_name" {
  description = "Monthly AWS Budget name for the environment."
  value       = module.budgets.budget_name
}

output "budget_limit_amount" {
  description = "Monthly AWS Budget threshold amount in USD."
  value       = module.budgets.budget_limit_amount
}
