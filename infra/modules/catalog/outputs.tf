output "database_name" {
  description = "Glue Catalog database name."
  value       = aws_glue_catalog_database.lakehouse.name
}

output "silver_table_name" {
  description = "Silver table name."
  value       = aws_glue_catalog_table.silver.name
}

output "gold_table_name" {
  description = "Gold table name."
  value       = aws_glue_catalog_table.gold.name
}

output "quicksight_view_name" {
  description = "Athena view name intended for QuickSight direct query."
  value       = aws_glue_catalog_table.quicksight.name
}
