output "budget_name" {
  description = "Name of the monthly AWS Budget."
  value       = aws_budgets_budget.monthly_cost.name
}

output "budget_limit_amount" {
  description = "Monthly budget threshold in USD."
  value       = aws_budgets_budget.monthly_cost.limit_amount
}
