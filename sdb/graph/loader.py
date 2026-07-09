"""Load the curated seed graph from a JSON file into validated models."""

from __future__ import annotations

from pathlib import Path

from sdb.schema.models import SeedData


def load_seed(path: str | Path) -> SeedData:
    """Read and validate a seed graph JSON file.

    Args:
        path: Path to a JSON document with ``nodes`` and ``statements`` arrays.

    Returns:
        The validated :class:`~sdb.schema.models.SeedData`.
    """
    text = Path(path).read_text(encoding="utf-8")
    return SeedData.model_validate_json(text)
