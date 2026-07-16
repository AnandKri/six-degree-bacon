"""Load the curated seed graph and its co-occurrence sidecar from JSON into validated models."""

from __future__ import annotations

import json
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


def load_cooccurrence(path: str | Path) -> dict[str, tuple[str, ...]]:
    """Read a Wikipedia-link co-occurrence file into a ``{node_id: linked_node_ids}`` mapping.

    The file has the shape ``{"_comment": ..., "links": {node_id: [linked_node_ids, ...]},
    "similarity": ...}`` (see ``data/cooccurrence.json``); every other top-level key is ignored —
    read the second-order table with :func:`load_similarity`.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    links: dict[str, list[str]] = data.get("links", {})
    return {node_id: tuple(linked) for node_id, linked in links.items()}


def load_similarity(path: str | Path) -> dict[str, dict[str, float]]:
    """Read the full-link Jaccard similarity table (ADR 0029) from a co-occurrence file.

    Shape: ``{"similarity": {node_id: {node_id: jaccard}}}``, each pair stored once. Returns an
    empty mapping when the file predates the table, which simply disables the second-order term.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    similarity: dict[str, dict[str, float]] = data.get("similarity", {})
    return {left: dict(peers) for left, peers in similarity.items()}
