from __future__ import annotations

from pathlib import Path

from src.common.resource_loader import load_text_resource


def load_sql_file(path_value: str | Path) -> str:
    """Load a SQL file and strip leading/trailing whitespace."""
    return load_text_resource(path_value)
