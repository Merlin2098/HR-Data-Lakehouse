from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.pipeline_runtime import (
    default_processed_at_utc,
    default_run_id,
    load_pipeline_context,
    parse_ingestion_date,
    run_parquet_to_parquet_pipeline,
    source_file_name,
    sql_string_literal,
)


DEFAULT_CONFIG_PATH = "src/configs/transformations.yaml"
DEFAULT_PIPELINE_NAME = "silver_to_gold"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the silver-to-gold HR pipeline.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to the pipeline YAML file.")
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_NAME, help="Pipeline name inside the YAML config.")
    parser.add_argument("--query", help="Optional override for the SQL file path.")
    parser.add_argument("--contract", help="Optional override for the contract YAML path.")
    parser.add_argument("--source", help="Optional override for the source parquet path.")
    parser.add_argument("--target", help="Optional override for the gold output base directory.")
    parser.add_argument(
        "--ingestion-date",
        help="Optional ingestion date in ISO format (YYYY-MM-DD). Defaults to the current local date.",
    )
    return parser.parse_args()


def run_pipeline(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    source_override: str | Path | None = None,
    target_override: str | Path | None = None,
    query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
    ingestion_date_value: str | None = None,
    run_id: str | None = None,
    processed_at_utc: str | None = None,
) -> dict[str, object]:
    context = load_pipeline_context(
        config_path,
        pipeline_name,
        source_override=source_override,
        target_override=target_override,
        query_override=query_override,
        contract_override=contract_override,
    )
    ingestion_date = parse_ingestion_date(ingestion_date_value)
    resolved_run_id = run_id or default_run_id()
    resolved_processed_at_utc = processed_at_utc or default_processed_at_utc()
    resolved_source_file = source_file_name(context.source_uri)
    partition_by = list(
        context.pipeline_definition.get("target", {}).get("partition_by", ["year", "month", "day"])
    )
    result = run_parquet_to_parquet_pipeline(
        context,
        sql_variables={
            "year": ingestion_date.year,
            "month": ingestion_date.month,
            "day": ingestion_date.day,
            "ingestion_date": sql_string_literal(ingestion_date.isoformat()),
            "source_file": sql_string_literal(resolved_source_file),
            "run_id": sql_string_literal(resolved_run_id),
            "processed_at_utc": sql_string_literal(resolved_processed_at_utc),
        },
        partition_by=partition_by,
        partition_values={
            "year": ingestion_date.year,
            "month": ingestion_date.month,
            "day": ingestion_date.day,
        },
        quality_context={
            "year": ingestion_date.year,
            "month": ingestion_date.month,
            "day": ingestion_date.day,
            "ingestion_date": ingestion_date.isoformat(),
            "source_file": resolved_source_file,
            "run_id": resolved_run_id,
            "processed_at_utc": resolved_processed_at_utc,
        },
    )
    result["ingestion_date"] = ingestion_date.isoformat()
    return result


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        config_path=args.config,
        pipeline_name=args.pipeline,
        source_override=args.source,
        target_override=args.target,
        query_override=args.query,
        contract_override=args.contract,
        ingestion_date_value=args.ingestion_date,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
