output "state_machine_arn" {
  description = "State machine ARN."
  value       = aws_sfn_state_machine.daily_medallion.arn
}

output "state_machine_name" {
  description = "State machine name."
  value       = aws_sfn_state_machine.daily_medallion.name
}

output "scheduler_name" {
  description = "EventBridge Scheduler name."
  value       = aws_scheduler_schedule.daily_pipeline.name
}
