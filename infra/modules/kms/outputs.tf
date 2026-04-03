output "kms_key_arn" {
  description = "KMS key ARN."
  value       = aws_kms_key.lakehouse.arn
}

output "kms_key_id" {
  description = "KMS key ID."
  value       = aws_kms_key.lakehouse.key_id
}

output "kms_alias_name" {
  description = "KMS alias name."
  value       = aws_kms_alias.lakehouse.name
}
