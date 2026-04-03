from __future__ import annotations


def is_s3_uri(value: str) -> bool:
    """Return True when a string points to an S3 URI."""
    return value.startswith("s3://")


def build_s3_uri(bucket: str, key: str) -> str:
    """Build an S3 URI from a bucket name and object key."""
    return f"s3://{bucket}/{key.lstrip('/')}"


def split_s3_uri(uri: str) -> tuple[str, str]:
    """Split an S3 URI into bucket and key components."""
    if not is_s3_uri(uri):
        raise ValueError(f"Expected an S3 URI, got '{uri}'.")

    without_scheme = uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI '{uri}'.")
    return bucket, key
