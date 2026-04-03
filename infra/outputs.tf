output "bronze_bucket_name" {
  description = "Bronze bucket name."
  value       = module.s3.bronze_bucket_name
}

output "silver_bucket_name" {
  description = "Silver bucket name."
  value       = module.s3.silver_bucket_name
}

output "gold_bucket_name" {
  description = "Gold bucket name."
  value       = module.s3.gold_bucket_name
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
