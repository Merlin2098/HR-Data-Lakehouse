from __future__ import annotations

from src.common.project_paths import resolve_project_path
from src.common.query_loader import load_sql_file


def test_bronze_to_silver_query_targets_expected_view_and_fields() -> None:
    sql_text = load_sql_file(resolve_project_path("src/queries/bronze_to_silver.sql"))

    assert "FROM bronze_hr_attrition" in sql_text
    assert "employee_number" in sql_text
    assert "monthly_income" in sql_text
    assert "attrition" in sql_text
    assert "{{source_file}}" in sql_text
    assert "{{run_id}}" in sql_text
    assert "{{processed_at_utc}}" in sql_text
    assert "data/" not in sql_text


def test_silver_to_gold_query_targets_expected_view_and_enrichment() -> None:
    sql_text = load_sql_file(resolve_project_path("src/queries/silver_to_gold.sql"))

    assert "FROM silver_hr_employees" in sql_text
    assert "employee_id" in sql_text
    assert "{{ingestion_date}}" in sql_text
    assert "{{year}}" in sql_text
    assert "{{month}}" in sql_text
    assert "{{day}}" in sql_text
    assert "{{run_id}}" in sql_text
    assert "{{processed_at_utc}}" in sql_text
    assert "source_file" in sql_text
    assert "very_high" in sql_text
