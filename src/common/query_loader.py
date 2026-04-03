from __future__ import annotations

from pathlib import Path


def load_sql_file(path_value: str | Path) -> str:
    """Load a SQL file and strip leading/trailing whitespace."""
    path = Path(path_value)
    return path.read_text(encoding="utf-8").strip()
