from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.pipeline_runtime import (
    load_pipeline_context,
    parse_ingestion_date,
    run_parquet_to_parquet_pipeline,
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
    partition_by = list(
        context.pipeline_definition.get("target", {}).get("partition_by", ["year", "month", "day"])
    )
    result = run_parquet_to_parquet_pipeline(
        context,
        sql_variables={
            "year": ingestion_date.year,
            "month": ingestion_date.month,
            "day": ingestion_date.day,
        },
        partition_by=partition_by,
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
