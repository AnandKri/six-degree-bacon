"""Pin a harvest to a local JSON snapshot so it is reproducible offline.

Snapshots live under ``data/harvest/`` (git-ignored): the network is consulted once, the result is
frozen to disk, and every later run — including the test suite — reads the frozen file. A snapshot
is just a :class:`~sdb.schema.models.SeedData` document, so it loads through the same validated path
as the curated seed graph.
"""

from __future__ import annotations

from pathlib import Path

from sdb.schema.models import SeedData

DEFAULT_HARVEST_DIR = Path("data/harvest")


def save_snapshot(seed: SeedData, path: str | Path) -> Path:
    """Write ``seed`` to ``path`` as indented JSON, creating parent directories as needed.

    Returns the path written, for convenience.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(seed.model_dump_json(indent=2), encoding="utf-8")
    return destination


def load_snapshot(path: str | Path) -> SeedData:
    """Load a harvest snapshot (a :class:`SeedData` JSON document) with validation."""
    return SeedData.model_validate_json(Path(path).read_text(encoding="utf-8"))
