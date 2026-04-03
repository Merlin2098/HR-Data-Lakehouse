from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent


def resolve_project_path(path_value: str | Path) -> Path:
    """Resolve a project-relative path into an absolute path."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def ensure_parent_dir(path_value: str | Path) -> Path:
    """Create the parent directory for a local output path when needed."""
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
