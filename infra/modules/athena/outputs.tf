output "workgroup_name" {
  description = "Athena workgroup name."
  value       = aws_athena_workgroup.this.name
}

output "results_output_location" {
  description = "Athena query results location."
  value       = aws_athena_workgroup.this.configuration[0].result_configuration[0].output_location
}
