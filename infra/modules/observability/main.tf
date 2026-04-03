resource "aws_sns_topic" "alerts" {
  name              = "${var.state_machine_name}-alerts"
  kms_master_key_id = var.kms_key_arn
  tags              = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "glue_job_failures" {
  for_each = toset(var.glue_job_names)

  alarm_name          = "${each.value}-failed-jobs"
  alarm_description   = "Alerts when the Glue job reports failed runs."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "glue.driver.aggregate.numFailedTasks"
  namespace           = "Glue"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    JobName = each.value
    Type    = "count"
  }
}

resource "aws_cloudwatch_metric_alarm" "state_machine_failures" {
  alarm_name          = "${var.state_machine_name}-executions-failed"
  alarm_description   = "Alerts when the state machine execution fails."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    StateMachineArn = var.state_machine_arn
  }
}
