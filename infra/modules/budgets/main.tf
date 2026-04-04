locals {
  budget_name = coalesce(var.budget_name_override, "${var.name_prefix}-${var.environment}-monthly-cost")
}

resource "aws_budgets_budget" "monthly_cost" {
  account_id   = var.account_id
  name         = local.budget_name
  budget_type  = "COST"
  limit_amount = format("%.2f", var.monthly_budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [format("user:Environment$%s", var.environment)]
  }

  cost_types {
    include_credit             = false
    include_discount           = true
    include_other_subscription = true
    include_recurring          = true
    include_refund             = false
    include_subscription       = true
    include_support            = true
    include_tax                = true
    include_upfront            = true
    use_amortized              = true
    use_blended                = false
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [var.sns_topic_arn]
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [var.sns_topic_arn]
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [var.sns_topic_arn]
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [var.sns_topic_arn]
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
  }
}
