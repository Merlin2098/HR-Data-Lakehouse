from __future__ import annotations

import shutil

import pyarrow.parquet as pq

from src.common.project_paths import resolve_project_path
from src.glue.bronze_to_silver import run_pipeline


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


def test_local_pipeline_writes_expected_parquet() -> None:
    output_dir = resolve_project_path("data/output/test_runs")
    output_path = output_dir / "hr_attrition.parquet"

    if output_dir.exists():
        shutil.rmtree(output_dir)

    result = run_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=resolve_project_path("data/WA_Fn-UseC_-HR-Employee-Attrition.csv"),
        target_override=output_path,
    )

    table = pq.read_table(output_path)

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_COLUMNS
    assert table.column_names == EXPECTED_COLUMNS
    assert table.num_rows > 0
