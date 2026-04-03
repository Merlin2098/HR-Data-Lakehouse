output "alerts_topic_arn" {
  description = "SNS topic ARN for operational alerts."
  value       = aws_sns_topic.alerts.arn
}
