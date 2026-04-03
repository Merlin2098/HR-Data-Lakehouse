from __future__ import annotations

import shutil

import pyarrow.dataset as ds
import pyarrow.parquet as pq

from src.common.project_paths import resolve_project_path
from src.glue.bronze_to_silver import run_pipeline as run_bronze_to_silver
from src.glue.run_local_pipeline import run_pipeline as run_local_pipeline
from src.glue.silver_to_gold import run_pipeline as run_silver_to_gold


EXPECTED_SILVER_COLUMNS = [
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


def clean_directory(path: str) -> None:
    directory = resolve_project_path(path)
    if directory.exists():
        shutil.rmtree(directory)


def test_bronze_to_silver_writes_expected_parquet() -> None:
    clean_directory("data/output/test_runs/bronze_to_silver")
    output_path = resolve_project_path("data/output/test_runs/bronze_to_silver/hr_employees.parquet")

    result = run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        target_override=output_path,
    )

    table = pq.read_table(output_path)
    first_row = table.slice(0, 1).to_pylist()[0]

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_SILVER_COLUMNS
    assert table.column_names == EXPECTED_SILVER_COLUMNS
    assert first_row["department"] == "sales"
    assert first_row["job_role"] == "sales executive"
    assert isinstance(first_row["over_time"], bool)
    assert isinstance(first_row["attrition"], bool)


def test_silver_to_gold_writes_partitioned_parquet() -> None:
    clean_directory("data/output/test_runs/silver_to_gold")
    silver_output = resolve_project_path("data/output/test_runs/silver_to_gold/hr_employees.parquet")
    gold_output = resolve_project_path("data/output/test_runs/silver_to_gold/gold/hr_attrition")

    run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        target_override=silver_output,
    )
    result = run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-03",
    )

    dataset = ds.dataset(gold_output, format="parquet", partitioning="hive")
    table = dataset.to_table()
    first_row = table.slice(0, 1).to_pylist()[0]

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_GOLD_COLUMNS
    assert sorted(dataset.schema.names) == sorted(EXPECTED_GOLD_COLUMNS)
    assert resolve_project_path(
        "data/output/test_runs/silver_to_gold/gold/hr_attrition/ingestion_year=2026/ingestion_month=4"
    ).exists()
    assert first_row["job_satisfaction_label"] in {"low", "medium", "high", "very_high"}
    assert first_row["employee_id"] > 0
    assert first_row["ingestion_year"] == 2026
    assert first_row["ingestion_month"] == 4


def test_full_runner_executes_bronze_to_gold_end_to_end() -> None:
    clean_directory("data/output/test_runs/full_pipeline")
    silver_output = resolve_project_path("data/output/test_runs/full_pipeline/silver/hr_employees.parquet")
    gold_output = resolve_project_path("data/output/test_runs/full_pipeline/gold/hr_attrition")

    result = run_local_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        silver_target_override=silver_output,
        gold_target_override=gold_output,
        ingestion_date_value="2025-12-15",
    )

    silver_table = pq.read_table(silver_output)
    gold_dataset = ds.dataset(gold_output, format="parquet", partitioning="hive")
    gold_table = gold_dataset.to_table()

    assert result["engine"] == "duckdb"
    assert result["silver"]["columns"] == EXPECTED_SILVER_COLUMNS
    assert result["gold"]["columns"] == EXPECTED_GOLD_COLUMNS
    assert silver_table.num_rows > 0
    assert gold_table.num_rows > 0
    assert resolve_project_path(
        "data/output/test_runs/full_pipeline/gold/hr_attrition/ingestion_year=2025/ingestion_month=12"
    ).exists()
