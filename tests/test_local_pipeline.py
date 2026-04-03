from __future__ import annotations

from datetime import date
import shutil
import uuid

import pyarrow as pa
import pyarrow.dataset as ds

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


def clean_directory(path: str) -> None:
    directory = resolve_project_path(path)
    if directory.exists():
        shutil.rmtree(directory)


def unique_test_root(name: str):
    return resolve_project_path(f"data/output/test_runs/{name}_{uuid.uuid4().hex[:8]}")


def directory_partitioning():
    return ds.partitioning(
        pa.schema(
            [
                ("year", pa.int32()),
                ("month", pa.int32()),
                ("day", pa.int32()),
            ]
        ),
        flavor="hive",
    )


def test_bronze_to_silver_writes_expected_dataset_parquet() -> None:
    test_root = unique_test_root("bronze_to_silver")
    output_path = test_root / "hr_employees"

    result = run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        target_override=output_path,
    )

    dataset = ds.dataset(output_path, format="parquet")
    table = dataset.to_table()
    first_row = table.slice(0, 1).to_pylist()[0]

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_SILVER_COLUMNS
    assert output_path.is_dir()
    assert (output_path / "data_0.parquet").exists()
    assert table.column_names == EXPECTED_SILVER_COLUMNS
    assert first_row["department"] == "sales"
    assert first_row["job_role"] == "sales executive"
    assert isinstance(first_row["over_time"], bool)
    assert isinstance(first_row["attrition"], bool)
    assert first_row["source_file"] == "HR-Employee-Attrition.csv"
    assert first_row["run_id"]
    assert first_row["processed_at_utc"] is not None


def test_silver_to_gold_writes_partitioned_parquet() -> None:
    test_root = unique_test_root("silver_to_gold")
    silver_output = test_root / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

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

    dataset = ds.dataset(gold_output, format="parquet", partitioning=directory_partitioning())
    table = dataset.to_table()
    first_row = table.slice(0, 1).to_pylist()[0]

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_GOLD_COLUMNS
    assert sorted(dataset.schema.names) == sorted(EXPECTED_GOLD_COLUMNS)
    assert (gold_output / "year=2026" / "month=4" / "day=3").exists()
    assert (gold_output / "year=2026" / "month=4" / "day=3" / "data_0.parquet").exists()
    assert first_row["job_satisfaction_label"] in {"low", "medium", "high", "very_high"}
    assert first_row["employee_id"] > 0
    assert first_row["ingestion_date"].isoformat() == "2026-04-03"
    assert first_row["year"] == 2026
    assert first_row["month"] == 4
    assert first_row["day"] == 3
    assert first_row["source_file"] == "hr_employees"
    assert first_row["run_id"]
    assert first_row["processed_at_utc"] is not None


def test_full_runner_executes_bronze_to_gold_end_to_end() -> None:
    test_root = unique_test_root("full_pipeline")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

    result = run_local_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        silver_target_override=silver_output,
        gold_target_override=gold_output,
        ingestion_date_value="2025-12-15",
    )

    silver_table = ds.dataset(silver_output, format="parquet").to_table()
    gold_dataset = ds.dataset(gold_output, format="parquet", partitioning=directory_partitioning())
    gold_table = gold_dataset.to_table()

    assert result["engine"] == "duckdb"
    assert result["silver"]["columns"] == EXPECTED_SILVER_COLUMNS
    assert result["gold"]["columns"] == EXPECTED_GOLD_COLUMNS
    assert silver_table.num_rows > 0
    assert gold_table.num_rows > 0
    assert (gold_output / "year=2025" / "month=12" / "day=15").exists()
    assert gold_table.column("run_id").to_pylist()[0] == silver_table.column("run_id").to_pylist()[0]


def test_full_runner_defaults_to_today_when_ingestion_date_is_not_provided() -> None:
    test_root = unique_test_root("default_today")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

    result = run_local_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        silver_target_override=silver_output,
        gold_target_override=gold_output,
    )

    today = date.today()
    assert result["gold"]["ingestion_date"] == today.isoformat()
    assert (gold_output / f"year={today.year}" / f"month={today.month}" / f"day={today.day}").exists()


def test_gold_overwrite_partition_replaces_only_the_current_day() -> None:
    test_root = unique_test_root("overwrite_partition")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

    run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/HR-Employee-Attrition.csv"),
        target_override=silver_output,
    )
    run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-02",
    )
    run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-03",
    )
    run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-03",
    )

    previous_day_partition = gold_output / "year=2026" / "month=4" / "day=2"
    current_day_partition = gold_output / "year=2026" / "month=4" / "day=3"

    assert previous_day_partition.exists()
    assert current_day_partition.exists()
    assert len(list(previous_day_partition.glob("*.parquet"))) == 1
    assert len(list(current_day_partition.glob("*.parquet"))) == 1
