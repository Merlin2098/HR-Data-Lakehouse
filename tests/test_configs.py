from __future__ import annotations

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import expected_columns
from src.common.project_paths import resolve_project_path


EXPECTED_COLUMNS = [
    "employee_number",
    "department",
    "job_role",
    "job_level",
    "over_time",
    "monthly_income",
    "percent_salary_hike",
    "years_at_company",
    "years_since_last_promotion",
    "total_working_years",
    "job_satisfaction",
    "environment_satisfaction",
    "relationship_satisfaction",
    "work_life_balance",
    "attrition",
]

EXPECTED_GOLD_COLUMNS = [
    "employee_id",
    "ingestion_year",
    "ingestion_month",
    "department",
    "job_role",
    "job_level",
    "attrition",
    "monthly_income",
    "percent_salary_hike",
    "years_at_company",
    "years_since_last_promotion",
    "total_working_years",
    "over_time",
    "job_satisfaction_score",
    "environment_satisfaction_score",
    "relationship_satisfaction_score",
    "work_life_balance_score",
    "job_satisfaction_label",
    "environment_satisfaction_label",
    "relationship_satisfaction_label",
    "work_life_balance_label",
]


def test_transformations_config_declares_bronze_to_silver_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["bronze_to_silver"]

    assert pipeline["source"]["local_path"] == "data/HR-Employee-Attrition.csv"
    assert pipeline["target"]["format"] == "parquet"
    assert pipeline["artifacts"]["query_path"] == "src/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["contract_path"] == "src/configs/contracts.yaml"
    assert pipeline["target"]["local_path"] == "data/output/silver/hr_employees.parquet"


def test_transformations_config_declares_silver_to_gold_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["silver_to_gold"]

    assert pipeline["source"]["local_path"] == "data/output/silver/hr_employees.parquet"
    assert pipeline["target"]["local_path"] == "data/output/gold/hr_attrition"
    assert pipeline["target"]["partition_by"] == ["ingestion_year", "ingestion_month"]
    assert pipeline["artifacts"]["query_path"] == "src/queries/silver_to_gold.sql"


def test_contract_matches_expected_silver_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "silver_hr_employees") == EXPECTED_COLUMNS


def test_contract_matches_expected_gold_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "gold_hr_attrition_fact") == EXPECTED_GOLD_COLUMNS
