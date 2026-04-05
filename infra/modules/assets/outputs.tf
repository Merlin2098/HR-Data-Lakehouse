output "bronze_to_silver_script_key" {
  description = "S3 key for the bronze-to-silver Glue script."
  value       = aws_s3_object.assets["bronze_to_silver_script"].key
}

output "silver_to_gold_script_key" {
  description = "S3 key for the silver-to-gold Glue script."
  value       = aws_s3_object.assets["silver_to_gold_script"].key
}

output "config_key" {
  description = "S3 key for the pipeline configuration file."
  value       = aws_s3_object.assets["transformations"].key
}

output "contract_key" {
  description = "S3 key for the contract file."
  value       = aws_s3_object.assets["contracts"].key
}

output "bronze_to_silver_query_key" {
  description = "S3 key for the bronze-to-silver SQL query."
  value       = aws_s3_object.assets["bronze_to_silver_query"].key
}

output "silver_to_gold_query_key" {
  description = "S3 key for the silver-to-gold SQL query."
  value       = aws_s3_object.assets["silver_to_gold_query"].key
}

output "glue_runtime_package_key" {
  description = "S3 key for the shared Glue runtime package."
  value       = aws_s3_object.glue_runtime_package.key
}
