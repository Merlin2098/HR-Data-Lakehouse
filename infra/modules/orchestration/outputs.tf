output "state_machine_arn" {
  description = "State machine ARN."
  value       = aws_sfn_state_machine.daily_medallion.arn
}

output "state_machine_name" {
  description = "State machine name."
  value       = aws_sfn_state_machine.daily_medallion.name
}

output "event_rule_name" {
  description = "EventBridge rule name."
  value       = aws_cloudwatch_event_rule.landing_object_created.name
}

output "event_target_id" {
  description = "EventBridge target identifier."
  value       = aws_cloudwatch_event_target.start_state_machine.target_id
}
