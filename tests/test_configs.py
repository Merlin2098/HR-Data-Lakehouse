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


def test_transformations_config_declares_bronze_to_silver_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["bronze_to_silver"]

    assert pipeline["source"]["local_path"] == "data/WA_Fn-UseC_-HR-Employee-Attrition.csv"
    assert pipeline["target"]["format"] == "parquet"
    assert pipeline["artifacts"]["query_path"] == "src/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["contract_path"] == "src/configs/contracts.yaml"


def test_contract_matches_expected_silver_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "silver_hr_attrition") == EXPECTED_COLUMNS
