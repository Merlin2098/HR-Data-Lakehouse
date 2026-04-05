locals {
  silver_table_name = "silver_hr_employees"
  gold_table_name   = "gold_hr_attrition_fact"
  quicksight_view_name = "vw_quicksight_hr_attrition"

  quicksight_view_glue_columns = [
    { name = "employee_id", type = "int" },
    { name = "ingestion_date", type = "date" },
    { name = "year", type = "int" },
    { name = "month", type = "int" },
    { name = "day", type = "int" },
    { name = "department", type = "string" },
    { name = "job_role", type = "string" },
    { name = "job_level", type = "int" },
    { name = "attrition", type = "boolean" },
    { name = "monthly_income", type = "decimal(12,2)" },
    { name = "percent_salary_hike", type = "int" },
    { name = "years_at_company", type = "int" },
    { name = "years_since_last_promotion", type = "int" },
    { name = "total_working_years", type = "int" },
    { name = "over_time", type = "boolean" },
    { name = "job_satisfaction_score", type = "int" },
    { name = "environment_satisfaction_score", type = "int" },
    { name = "relationship_satisfaction_score", type = "int" },
    { name = "work_life_balance_score", type = "int" },
    { name = "job_satisfaction_label", type = "string" },
    { name = "environment_satisfaction_label", type = "string" },
    { name = "relationship_satisfaction_label", type = "string" },
    { name = "work_life_balance_label", type = "string" },
    { name = "source_file", type = "string" },
    { name = "run_id", type = "string" },
    { name = "processed_at_utc", type = "timestamp" },
  ]

  quicksight_view_presto_columns = [
    { name = "employee_id", type = "integer" },
    { name = "ingestion_date", type = "date" },
    { name = "year", type = "integer" },
    { name = "month", type = "integer" },
    { name = "day", type = "integer" },
    { name = "department", type = "varchar" },
    { name = "job_role", type = "varchar" },
    { name = "job_level", type = "integer" },
    { name = "attrition", type = "boolean" },
    { name = "monthly_income", type = "decimal(12,2)" },
    { name = "percent_salary_hike", type = "integer" },
    { name = "years_at_company", type = "integer" },
    { name = "years_since_last_promotion", type = "integer" },
    { name = "total_working_years", type = "integer" },
    { name = "over_time", type = "boolean" },
    { name = "job_satisfaction_score", type = "integer" },
    { name = "environment_satisfaction_score", type = "integer" },
    { name = "relationship_satisfaction_score", type = "integer" },
    { name = "work_life_balance_score", type = "integer" },
    { name = "job_satisfaction_label", type = "varchar" },
    { name = "environment_satisfaction_label", type = "varchar" },
    { name = "relationship_satisfaction_label", type = "varchar" },
    { name = "work_life_balance_label", type = "varchar" },
    { name = "source_file", type = "varchar" },
    { name = "run_id", type = "varchar" },
    { name = "processed_at_utc", type = "timestamp" },
  ]

  quicksight_view_sql = <<-SQL
    SELECT
      employee_id,
      ingestion_date,
      year,
      month,
      day,
      department,
      job_role,
      job_level,
      attrition,
      monthly_income,
      percent_salary_hike,
      years_at_company,
      years_since_last_promotion,
      total_working_years,
      over_time,
      job_satisfaction_score,
      environment_satisfaction_score,
      relationship_satisfaction_score,
      work_life_balance_score,
      job_satisfaction_label,
      environment_satisfaction_label,
      relationship_satisfaction_label,
      work_life_balance_label,
      source_file,
      run_id,
      processed_at_utc
    FROM "${var.database_name}"."${local.gold_table_name}"
  SQL
}

resource "aws_glue_catalog_database" "lakehouse" {
  name = var.database_name
}

resource "aws_glue_catalog_table" "silver" {
  name          = local.silver_table_name
  database_name = aws_glue_catalog_database.lakehouse.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification = "parquet"
    EXTERNAL       = "TRUE"
  }

  storage_descriptor {
    location      = "s3://${var.data_lake_bucket_name}/silver/hr_employees/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "employee_number"
      type = "int"
    }
    columns {
      name = "department"
      type = "string"
    }
    columns {
      name = "job_role"
      type = "string"
    }
    columns {
      name = "job_level"
      type = "int"
    }
    columns {
      name = "over_time"
      type = "boolean"
    }
    columns {
      name = "monthly_income"
      type = "decimal(12,2)"
    }
    columns {
      name = "percent_salary_hike"
      type = "int"
    }
    columns {
      name = "years_at_company"
      type = "int"
    }
    columns {
      name = "years_since_last_promotion"
      type = "int"
    }
    columns {
      name = "total_working_years"
      type = "int"
    }
    columns {
      name = "job_satisfaction"
      type = "int"
    }
    columns {
      name = "environment_satisfaction"
      type = "int"
    }
    columns {
      name = "relationship_satisfaction"
      type = "int"
    }
    columns {
      name = "work_life_balance"
      type = "int"
    }
    columns {
      name = "attrition"
      type = "boolean"
    }
    columns {
      name = "source_file"
      type = "string"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "processed_at_utc"
      type = "timestamp"
    }
  }
}

resource "aws_glue_catalog_table" "gold" {
  name          = local.gold_table_name
  database_name = aws_glue_catalog_database.lakehouse.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification              = "parquet"
    EXTERNAL                    = "TRUE"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = var.year_projection_range
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/hr_attrition/year=$${year}/month=$${month}/day=$${day}/"
  }

  partition_keys {
    name = "year"
    type = "int"
  }
  partition_keys {
    name = "month"
    type = "int"
  }
  partition_keys {
    name = "day"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.data_lake_bucket_name}/gold/hr_attrition/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "employee_id"
      type = "int"
    }
    columns {
      name = "ingestion_date"
      type = "date"
    }
    columns {
      name = "department"
      type = "string"
    }
    columns {
      name = "job_role"
      type = "string"
    }
    columns {
      name = "job_level"
      type = "int"
    }
    columns {
      name = "attrition"
      type = "boolean"
    }
    columns {
      name = "monthly_income"
      type = "decimal(12,2)"
    }
    columns {
      name = "percent_salary_hike"
      type = "int"
    }
    columns {
      name = "years_at_company"
      type = "int"
    }
    columns {
      name = "years_since_last_promotion"
      type = "int"
    }
    columns {
      name = "total_working_years"
      type = "int"
    }
    columns {
      name = "over_time"
      type = "boolean"
    }
    columns {
      name = "job_satisfaction_score"
      type = "int"
    }
    columns {
      name = "environment_satisfaction_score"
      type = "int"
    }
    columns {
      name = "relationship_satisfaction_score"
      type = "int"
    }
    columns {
      name = "work_life_balance_score"
      type = "int"
    }
    columns {
      name = "job_satisfaction_label"
      type = "string"
    }
    columns {
      name = "environment_satisfaction_label"
      type = "string"
    }
    columns {
      name = "relationship_satisfaction_label"
      type = "string"
    }
    columns {
      name = "work_life_balance_label"
      type = "string"
    }
    columns {
      name = "source_file"
      type = "string"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "processed_at_utc"
      type = "timestamp"
    }
  }
}

resource "aws_glue_catalog_table" "quicksight" {
  name          = local.quicksight_view_name
  database_name = aws_glue_catalog_database.lakehouse.name
  table_type    = "VIRTUAL_VIEW"

  parameters = {
    presto_view = "true"
    comment     = "QuickSight-facing Athena view over gold_hr_attrition_fact"
  }

  view_expanded_text = "/* Presto View */"
  view_original_text = "/* Presto View: ${base64encode(jsonencode({
    catalog     = "awsdatacatalog"
    schema      = aws_glue_catalog_database.lakehouse.name
    columns     = local.quicksight_view_presto_columns
    originalSql = trimspace(local.quicksight_view_sql)
  }))} */"

  storage_descriptor {
    dynamic "columns" {
      for_each = local.quicksight_view_glue_columns

      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}
