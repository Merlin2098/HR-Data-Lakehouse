from __future__ import annotations

import csv
from datetime import date
import shutil
import uuid

import pyarrow as pa
import pyarrow.dataset as ds

from src.common.pipeline_runtime import (
    PipelineContext,
    ensure_materialized_output,
    promote_spark_single_file_local,
    promote_spark_single_file_s3,
)
from src.common.project_paths import resolve_project_path
from src.common.resource_loader import list_resource_objects, resource_exists
from src.glue.bronze_to_silver import resolve_bronze_source_uri, run_pipeline as run_bronze_to_silver
from src.glue.gold_to_bi_export import run_pipeline as run_gold_to_bi_export
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

EXPECTED_BI_COLUMNS = EXPECTED_GOLD_COLUMNS.copy()
TEST_SOURCE_CSV = resolve_project_path("data/hr_attrition.csv")


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


def read_csv_rows(path):
    with resolve_project_path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_bronze_to_silver_preserves_exact_landing_object_uri_in_aws_mode() -> None:
    source_uri = "s3://demo-lake/bronze/hr_attrition/landing/HR-Employee-Attrition3.csv"

    assert resolve_bronze_source_uri(source_uri, "HR-Employee-Attrition3.csv") == source_uri


def test_bronze_to_silver_can_build_landing_object_uri_from_prefix() -> None:
    source_uri = "s3://demo-lake/bronze/hr_attrition/landing/"

    assert (
        resolve_bronze_source_uri(source_uri, "HR-Employee-Attrition3.csv")
        == "s3://demo-lake/bronze/hr_attrition/landing/HR-Employee-Attrition3.csv"
    )


def test_bronze_to_silver_writes_expected_dataset_parquet() -> None:
    test_root = unique_test_root("bronze_to_silver")
    output_path = test_root / "hr_employees"

    result = run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
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
    assert first_row["source_file"] == "hr_attrition.csv"
    assert first_row["run_id"]
    assert first_row["processed_at_utc"] is not None


def test_silver_to_gold_writes_partitioned_parquet() -> None:
    test_root = unique_test_root("silver_to_gold")
    silver_output = test_root / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

    run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
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
    assert first_row["source_file"] == "hr_attrition.csv"
    assert first_row["run_id"]
    assert first_row["processed_at_utc"] is not None


def test_gold_to_bi_export_writes_single_csv_snapshot() -> None:
    test_root = unique_test_root("gold_to_bi_export")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"
    bi_output = test_root / "bi" / "hr_attrition_snapshot.csv"

    run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
        target_override=silver_output,
    )
    gold_result = run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-03",
    )
    result = run_gold_to_bi_export(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=gold_result["target_uri"],
        target_override=bi_output,
        business_date_value="2026-04-03",
    )

    rows = read_csv_rows(bi_output)
    first_row = rows[0]

    assert result["engine"] == "duckdb"
    assert result["columns"] == EXPECTED_BI_COLUMNS
    assert bi_output.is_file()
    assert bi_output.suffix == ".csv"
    assert list(first_row.keys()) == EXPECTED_BI_COLUMNS
    assert first_row["ingestion_date"] == "2026-04-03"
    assert int(first_row["employee_id"]) > 0
    assert {row["ingestion_date"] for row in rows} == {"2026-04-03"}


def test_gold_to_bi_export_filters_to_requested_business_date_when_gold_has_history() -> None:
    test_root = unique_test_root("gold_to_bi_export_history")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"
    bi_output = test_root / "bi" / "hr_attrition_snapshot.csv"

    run_bronze_to_silver(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
        target_override=silver_output,
    )
    run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-02",
    )
    gold_result = run_silver_to_gold(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=silver_output,
        target_override=gold_output,
        ingestion_date_value="2026-04-03",
    )

    result = run_gold_to_bi_export(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=gold_result["target_uri"],
        target_override=bi_output,
        business_date_value="2026-04-03",
    )

    rows = read_csv_rows(bi_output)
    ingestion_dates = {row["ingestion_date"] for row in rows}
    employee_ids = [int(row["employee_id"]) for row in rows]

    assert result["business_date"] == "2026-04-03"
    assert ingestion_dates == {"2026-04-03"}
    assert len(employee_ids) == len(set(employee_ids))


def test_full_runner_executes_bronze_to_gold_end_to_end() -> None:
    test_root = unique_test_root("full_pipeline")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"
    bi_output = test_root / "bi" / "hr_attrition_snapshot.csv"

    result = run_local_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
        silver_target_override=silver_output,
        gold_target_override=gold_output,
        bi_target_override=bi_output,
        ingestion_date_value="2025-12-15",
    )

    silver_table = ds.dataset(silver_output, format="parquet").to_table()
    gold_dataset = ds.dataset(gold_output, format="parquet", partitioning=directory_partitioning())
    gold_table = gold_dataset.to_table()
    bi_rows = read_csv_rows(bi_output)

    assert result["engine"] == "duckdb"
    assert result["silver"]["columns"] == EXPECTED_SILVER_COLUMNS
    assert result["gold"]["columns"] == EXPECTED_GOLD_COLUMNS
    assert result["bi_export"]["columns"] == EXPECTED_BI_COLUMNS
    assert silver_table.num_rows > 0
    assert gold_table.num_rows > 0
    assert len(bi_rows) > 0
    assert (gold_output / "year=2025" / "month=12" / "day=15").exists()
    assert gold_table.column("run_id").to_pylist()[0] == silver_table.column("run_id").to_pylist()[0]
    assert bi_output.exists()
    assert list(bi_rows[0].keys()) == EXPECTED_BI_COLUMNS


def test_full_runner_defaults_to_today_when_ingestion_date_is_not_provided() -> None:
    test_root = unique_test_root("default_today")
    silver_output = test_root / "silver" / "hr_employees"
    gold_output = test_root / "gold" / "hr_attrition"

    result = run_local_pipeline(
        config_path=resolve_project_path("src/configs/transformations.yaml"),
        source_override=TEST_SOURCE_CSV,
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
        source_override=TEST_SOURCE_CSV,
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


class FakeS3Exceptions:
    class ClientError(Exception):
        pass


class FakeS3Paginator:
    def __init__(self, contents: list[str], expected_prefix: str):
        self.contents = contents
        self.expected_prefix = expected_prefix

    def paginate(self, *, Bucket: str, Prefix: str):
        assert Bucket == "demo-lake"
        assert Prefix == self.expected_prefix
        yield {"Contents": [{"Key": key} for key in self.contents]}


class FakeS3Client:
    exceptions = FakeS3Exceptions()

    def __init__(self, *, expected_prefix: str, contents: list[str]):
        self.expected_prefix = expected_prefix
        self.contents = contents

    def list_objects_v2(self, *, Bucket: str, Prefix: str, MaxKeys: int | None = None):
        assert Bucket == "demo-lake"
        assert Prefix == self.expected_prefix
        visible_objects = [key for key in self.contents if key.startswith(Prefix)]
        return {"KeyCount": min(len(visible_objects), MaxKeys or len(visible_objects))}

    def get_paginator(self, operation_name: str):
        assert operation_name == "list_objects_v2"
        return FakeS3Paginator(self.contents, self.expected_prefix)

    def head_object(self, *, Bucket: str, Key: str):
        raise self.exceptions.ClientError()


def test_resource_helpers_support_s3_partition_prefixes(monkeypatch) -> None:
    partition_prefix = "gold/hr_attrition/year=2026/month=4/day=4/"
    partition_object = f"{partition_prefix}part-00000.snappy.parquet"
    fake_client = FakeS3Client(expected_prefix=partition_prefix, contents=[partition_object])

    monkeypatch.setattr("src.common.resource_loader._s3_client", lambda: fake_client)

    partition_uri = "s3://demo-lake/gold/hr_attrition/year=2026/month=4/day=4"
    assert resource_exists(partition_uri, treat_as_prefix=True) is True
    assert list_resource_objects(partition_uri, treat_as_prefix=True) == [f"s3://demo-lake/{partition_object}"]


def test_ensure_materialized_output_treats_s3_partitions_as_prefixes(monkeypatch) -> None:
    calls: list[tuple[str, str, bool]] = []

    def fake_resource_exists(value, *, treat_as_prefix: bool = False):
        calls.append(("exists", str(value), treat_as_prefix))
        return True

    def fake_list_resource_objects(value, *, treat_as_prefix: bool = False):
        calls.append(("list", str(value), treat_as_prefix))
        return ["s3://demo-lake/gold/hr_attrition/year=2026/month=4/day=4/part-00000.snappy.parquet"]

    monkeypatch.setattr("src.common.pipeline_runtime.resource_exists", fake_resource_exists)
    monkeypatch.setattr("src.common.pipeline_runtime.list_resource_objects", fake_list_resource_objects)

    context = PipelineContext(
        pipeline_name="silver_to_gold",
        config_ref="src/configs/transformations.yaml",
        pipeline_definition={},
        query_ref="src/queries/silver_to_gold.sql",
        contract_ref="src/configs/contracts.yaml",
        source_uri="s3://demo-lake/silver/hr_employees/",
        target_uri="s3://demo-lake/gold/hr_attrition/",
        source_format="parquet",
        source_view_name="silver_hr_employees",
        target_dataset_name="gold_hr_attrition_fact",
        target_format="parquet",
        output_compression="snappy",
        write_mode="overwrite_partition",
        target_layout="dataset",
        partition_style="hive",
        execution_mode="aws",
        engine="glue_spark",
    )

    ensure_materialized_output(
        context,
        partition_by=["year", "month", "day"],
        partition_values={"year": 2026, "month": 4, "day": 4},
    )

    expected_partition_uri = "s3://demo-lake/gold/hr_attrition/year=2026/month=4/day=4"
    assert calls == [
        ("exists", expected_partition_uri, True),
        ("list", expected_partition_uri, True),
    ]


def test_promote_spark_single_file_local_supports_csv_parts() -> None:
    test_root = unique_test_root("spark_csv_local")
    staging_root = test_root / "stage"
    staging_root.mkdir(parents=True, exist_ok=True)
    staged_csv = staging_root / "part-00000.csv"
    staged_csv.write_text("employee_id,ingestion_date\n1,2026-04-03\n", encoding="utf-8")
    target_csv = test_root / "hr_attrition_snapshot.csv"

    promoted_path = promote_spark_single_file_local(staging_root, target_csv, "csv")

    assert promoted_path == str(target_csv)
    assert target_csv.read_text(encoding="utf-8") == "employee_id,ingestion_date\n1,2026-04-03\n"
    assert not staging_root.exists()


def test_promote_spark_single_file_s3_supports_csv_parts(monkeypatch) -> None:
    copied: list[tuple[str, str, str, str]] = []
    deleted: list[tuple[str, list[str]]] = []

    class FakeSparkS3Client:
        def copy_object(self, *, Bucket: str, Key: str, CopySource: dict[str, str]):
            copied.append((Bucket, Key, CopySource["Bucket"], CopySource["Key"]))

        def delete_objects(self, *, Bucket: str, Delete: dict[str, list[dict[str, str]]]):
            deleted.append((Bucket, [item["Key"] for item in Delete["Objects"]]))

    monkeypatch.setattr("src.common.pipeline_runtime.spark_runtime_s3_client", lambda: FakeSparkS3Client())
    monkeypatch.setattr(
        "src.common.pipeline_runtime.list_resource_objects",
        lambda value, *, treat_as_prefix=False: [
            "s3://demo-lake/bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/part-00000.csv",
            "s3://demo-lake/bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/_SUCCESS",
        ],
    )

    promote_spark_single_file_s3(
        "s3://demo-lake/bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/",
        "s3://demo-lake/bi/hr_attrition_snapshot/hr_attrition_snapshot.csv",
        "csv",
    )

    assert copied == [
        (
            "demo-lake",
            "bi/hr_attrition_snapshot/hr_attrition_snapshot.csv",
            "demo-lake",
            "bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/part-00000.csv",
        )
    ]
    assert deleted == [
        (
            "demo-lake",
            [
                "bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/part-00000.csv",
                "bi/hr_attrition_snapshot/hr_attrition_snapshot_spark_stage_abcd/_SUCCESS",
            ],
        )
    ]
