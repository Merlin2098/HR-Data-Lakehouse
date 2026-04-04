from __future__ import annotations

from pathlib import Path

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import dataset_contract, expected_columns
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
    "source_file",
    "run_id",
    "processed_at_utc",
]

EXPECTED_GOLD_COLUMNS = [
    "employee_id",
    "ingestion_date",
    "year",
    "month",
    "day",
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
    "source_file",
    "run_id",
    "processed_at_utc",
]


def test_transformations_config_declares_bronze_to_silver_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    assert config["defaults"]["execution_mode"] == "local"
    assert config["defaults"]["engines"] == {"local": "duckdb", "aws": "glue_spark"}
    pipeline = config["pipelines"]["bronze_to_silver"]

    assert pipeline["source"]["local_uri"] == "data/HR-Employee-Attrition.csv"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/raw/"
    assert pipeline["target"]["format"] == "parquet"
    assert pipeline["target"]["layout"] == "dataset"
    assert pipeline["target"]["write_mode"] == "overwrite_full"
    assert pipeline["artifacts"]["query_path"] == "src/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["query_uri"] == "s3://{scripts_bucket}/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["contract_path"] == "src/configs/contracts.yaml"
    assert pipeline["artifacts"]["config_uri"] == "s3://{scripts_bucket}/configs/transformations.yaml"
    assert pipeline["target"]["local_uri"] == "data/output/silver/hr_employees"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/silver/hr_attrition/hr_employees/"


def test_transformations_config_declares_silver_to_gold_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["silver_to_gold"]

    assert pipeline["source"]["local_uri"] == "data/output/silver/hr_employees"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/silver/hr_attrition/hr_employees/"
    assert pipeline["target"]["local_uri"] == "data/output/gold/hr_attrition"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/gold/hr_attrition/hr_attrition/"
    assert pipeline["target"]["layout"] == "dataset"
    assert pipeline["target"]["write_mode"] == "overwrite_partition"
    assert pipeline["target"]["partition_style"] == "hive"
    assert pipeline["target"]["partition_by"] == ["year", "month", "day"]
    assert pipeline["artifacts"]["query_path"] == "src/queries/silver_to_gold.sql"


def test_transformations_config_declares_landing_to_bronze_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["landing_to_bronze"]

    assert pipeline["source"]["local_uri"] == "data/HR-Employee-Attrition.csv"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/landing/"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/raw/"
    assert pipeline["target"]["write_mode"] == "immutable"


def test_contract_matches_expected_silver_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "silver_hr_employees") == EXPECTED_COLUMNS


def test_contract_matches_expected_gold_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "gold_hr_attrition_fact") == EXPECTED_GOLD_COLUMNS


def test_contract_declares_quality_metadata_for_aws_style_execution() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))
    silver_contract = dataset_contract(contract, "silver_hr_employees")
    gold_contract = dataset_contract(contract, "gold_hr_attrition_fact")

    assert silver_contract["primary_key"] == ["employee_number"]
    assert gold_contract["primary_key"] == ["employee_id"]
    assert gold_contract["partition_columns"] == ["year", "month", "day"]


def test_event_driven_orchestration_replaces_scheduler_resources() -> None:
    orchestration_tf = Path(resolve_project_path("infra/modules/orchestration/main.tf")).read_text(encoding="utf-8")

    assert "aws_scheduler_schedule" not in orchestration_tf
    assert '"detail-type" = ["Object Created"]' in orchestration_tf
    assert 'wildcard = local.landing_object_pattern' in orchestration_tf
    assert 'states:StartExecution' in orchestration_tf


def test_data_lake_bucket_forwards_events_to_eventbridge() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")

    assert 'resource "aws_s3_bucket_notification" "data_lake_eventbridge"' in s3_tf
    assert "eventbridge = true" in s3_tf
