from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from src.common.project_paths import resolve_project_path
from src.common.s3_utils import build_s3_uri, is_s3_uri, split_s3_uri


def _s3_client():
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - exercised only in AWS mode
        raise RuntimeError("boto3 is required to access S3-backed resources.") from exc
    return boto3.client("s3")


def resolve_resource_reference(value: str | Path) -> str:
    text_value = str(value)
    if is_s3_uri(text_value):
        return text_value
    return str(resolve_project_path(text_value))


def load_text_resource(value: str | Path) -> str:
    resource_ref = resolve_resource_reference(value)
    if is_s3_uri(resource_ref):
        bucket, key = split_s3_uri(resource_ref)
        response = _s3_client().get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8").strip()

    return Path(resource_ref).read_text(encoding="utf-8").strip()


def load_yaml_resource(value: str | Path) -> dict[str, Any]:
    loaded = yaml.safe_load(load_text_resource(value)) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a mapping in {value}, got {type(loaded).__name__}.")
    return loaded


def resource_exists(value: str | Path) -> bool:
    resource_ref = resolve_resource_reference(value)
    if is_s3_uri(resource_ref):
        bucket, key = split_s3_uri(resource_ref)
        client = _s3_client()
        if key.endswith("/"):
            response = client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
            return response.get("KeyCount", 0) > 0
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except client.exceptions.ClientError:
            return False

    return Path(resource_ref).exists()


def list_resource_objects(value: str | Path) -> list[str]:
    resource_ref = resolve_resource_reference(value)
    if is_s3_uri(resource_ref):
        bucket, prefix = split_s3_uri(resource_ref)
        client = _s3_client()
        paginator = client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                keys.append(build_s3_uri(bucket, item["Key"]))
        return keys

    path = Path(resource_ref)
    if path.is_dir():
        return [str(item) for item in sorted(path.rglob("*")) if item.is_file()]
    return [str(path)]


def ensure_local_directory(value: str | Path) -> Path:
    path = resolve_project_path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_resource(source: str | Path, target: str | Path) -> str:
    source_ref = resolve_resource_reference(source)
    target_ref = resolve_resource_reference(target)

    if is_s3_uri(source_ref) and is_s3_uri(target_ref):
        source_bucket, source_key = split_s3_uri(source_ref)
        target_bucket, target_key = split_s3_uri(target_ref)
        _s3_client().copy_object(
            Bucket=target_bucket,
            Key=target_key,
            CopySource={"Bucket": source_bucket, "Key": source_key},
        )
        return target_ref

    if not is_s3_uri(source_ref) and not is_s3_uri(target_ref):
        target_path = Path(target_ref)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_ref, target_ref)
        return str(target_path)

    raise RuntimeError("Cross-environment copies are not supported. Source and target must both be local or both be S3.")
