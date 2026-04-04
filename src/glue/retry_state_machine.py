from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _bootstrap_src_package() -> None:
    bootstrap_script_path = Path(__file__).resolve()
    for candidate in (bootstrap_script_path.parent, *bootstrap_script_path.parents):
        if (candidate / "src" / "__init__.py").exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.append(candidate_str)
            return


try:
    from src.common.project_paths import ensure_src_package_importable
except ModuleNotFoundError:
    _bootstrap_src_package()
    from src.common.project_paths import ensure_src_package_importable

ensure_src_package_importable(__file__)

from src.common.pipeline_runtime import default_run_id, parse_ingestion_date
from src.common.s3_utils import build_s3_uri, split_s3_uri

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start a manual Step Functions retry for a file that already exists in the landing prefix."
    )
    parser.add_argument("--state-machine-arn", help="Explicit Step Functions state machine ARN.")
    parser.add_argument("--state-machine-name", help="Optional Step Functions state machine name to resolve via AWS API.")
    parser.add_argument("--source-uri", help="S3 URI of the landing object to retry, for example s3://bucket/prefix/file.csv.")
    parser.add_argument("--bucket", help="S3 bucket containing the existing landing object.")
    parser.add_argument("--object-key", help="S3 object key of the existing landing object.")
    parser.add_argument("--business-date", help="Business date in ISO format. Defaults to the current local date.")
    parser.add_argument("--run-id", help="Explicit run identifier. Defaults to a generated UUID-like value.")
    parser.add_argument("--event-time", help="Explicit event timestamp in ISO-8601 UTC format.")
    parser.add_argument("--execution-name", help="Optional Step Functions execution name.")
    args = parser.parse_args()

    if not args.state_machine_arn and not args.state_machine_name:
        parser.error("Provide --state-machine-arn or --state-machine-name.")

    has_source_uri = bool(args.source_uri)
    has_bucket_key = bool(args.bucket and args.object_key)
    if has_source_uri == has_bucket_key:
        parser.error("Provide either --source-uri or the pair --bucket and --object-key.")

    return args


def default_event_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_source_location(args: argparse.Namespace) -> tuple[str, str, str, str]:
    if args.source_uri:
        bucket_name, object_key = split_s3_uri(args.source_uri)
        source_uri = args.source_uri
    else:
        bucket_name = str(args.bucket).strip()
        object_key = str(args.object_key).lstrip("/")
        source_uri = build_s3_uri(bucket_name, object_key)

    source_filename = object_key.rsplit("/", 1)[-1]
    return bucket_name, object_key, source_uri, source_filename


def resolve_state_machine_arn(client: Any, *, state_machine_arn: str | None, state_machine_name: str | None) -> str:
    if state_machine_arn:
        return state_machine_arn

    paginator = client.get_paginator("list_state_machines")
    for page in paginator.paginate():
        for state_machine in page.get("stateMachines", []):
            if state_machine.get("name") == state_machine_name:
                return str(state_machine["stateMachineArn"])

    raise ValueError(f"State machine named '{state_machine_name}' was not found.")


def build_retry_payload(args: argparse.Namespace) -> dict[str, str]:
    bucket_name, object_key, source_uri, source_filename = normalize_source_location(args)
    business_date = parse_ingestion_date(args.business_date).isoformat()

    return {
        "bucket_name": bucket_name,
        "object_key": object_key,
        "source_uri": source_uri,
        "source_filename": source_filename,
        "business_date": business_date,
        "run_id": args.run_id or default_run_id(),
        "event_time": args.event_time or default_event_time(),
    }


def start_manual_retry(args: argparse.Namespace) -> dict[str, Any]:
    stepfunctions = boto3.client("stepfunctions")
    payload = build_retry_payload(args)
    state_machine_arn = resolve_state_machine_arn(
        stepfunctions,
        state_machine_arn=args.state_machine_arn,
        state_machine_name=args.state_machine_name,
    )

    start_execution_args: dict[str, Any] = {
        "stateMachineArn": state_machine_arn,
        "input": json.dumps(payload),
    }
    if args.execution_name:
        start_execution_args["name"] = args.execution_name

    response = stepfunctions.start_execution(**start_execution_args)
    started_at = response.get("startDate")
    return {
        "state_machine_arn": state_machine_arn,
        "execution_arn": response["executionArn"],
        "start_date": started_at.isoformat() if started_at else None,
        "input": payload,
    }


def main() -> None:
    args = parse_args()
    result = start_manual_retry(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
