"""Load the curated seed graph and its co-occurrence sidecar from JSON into validated models.

This module owns *every* path from on-disk JSON to a ready-to-query
:class:`~sdb.graph.build.KnowledgeGraph`. :func:`load_graph` used to live in :mod:`sdb.web`, which
left the CLI importing a graph loader from the *web* module to build a static site while
``discover`` re-implemented the same four lines inline — the same CLI/web drift
:mod:`sdb.serialize` exists to prevent. The seam between the two callers is real but smaller than it
looked: ``discover`` has to interpose the harvest merge between reading the seed and building the
graph, so it wants :func:`graph_from_seed`, while everything else wants :func:`load_graph`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sdb.graph.build import KnowledgeGraph
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


def _read(path: str | Path) -> dict[str, Any]:
    """Parse a co-occurrence sidecar into its raw JSON mapping."""
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def _links(data: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Extract the first-order ``links`` table from a parsed sidecar."""
    links: dict[str, list[str]] = data.get("links", {})
    return {node_id: tuple(linked) for node_id, linked in links.items()}


def _similarity(data: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Extract the second-order ``similarity`` table from a parsed sidecar."""
    similarity: dict[str, dict[str, float]] = data.get("similarity", {})
    return {left: dict(peers) for left, peers in similarity.items()}


def load_cooccurrence(path: str | Path) -> dict[str, tuple[str, ...]]:
    """Read a Wikipedia-link co-occurrence file into a ``{node_id: linked_node_ids}`` mapping.

    The file has the shape ``{"_comment": ..., "links": {node_id: [linked_node_ids, ...]},
    "similarity": ...}`` (see ``data/cooccurrence.json``); every other top-level key is ignored —
    read the second-order table with :func:`load_similarity`.
    """
    return _links(_read(path))


def load_similarity(path: str | Path) -> dict[str, dict[str, float]]:
    """Read the full-link Jaccard similarity table (ADR 0029) from a co-occurrence file.

    Shape: ``{"similarity": {node_id: {node_id: jaccard}}}``, each pair stored once. Returns an
    empty mapping when the file predates the table, which simply disables the second-order term.
    """
    return _similarity(_read(path))


def graph_from_seed(seed: SeedData, cooccurrence_path: str | Path) -> KnowledgeGraph:
    """Build a knowledge graph from an in-memory seed, attaching the co-occurrence sidecar.

    A missing sidecar is not an error: both co-occurrence tables become ``None`` and the
    endpoint-surprise term scores 0, so the engine still runs on ``seed.json`` alone.

    Use this (rather than :func:`load_graph`) when the seed has been transformed in memory first —
    ``sdb discover --harvest`` merges snapshots into it before building.

    Args:
        seed: The already-loaded (and possibly merged) seed data.
        cooccurrence_path: Path to the co-occurrence sidecar; may not exist.

    Returns:
        The graph, with co-occurrence attached when the sidecar is present.
    """
    path = Path(cooccurrence_path)
    if not path.exists():
        return KnowledgeGraph.from_seed(seed, None, None)
    # One read, both tables: the two public readers each parse the file, and this path needs both.
    data = _read(path)
    return KnowledgeGraph.from_seed(seed, _links(data), _similarity(data))


def load_graph(seed_path: str | Path, cooccurrence_path: str | Path) -> KnowledgeGraph:
    """Load a seed file and its co-occurrence sidecar into a ready-to-query knowledge graph.

    Args:
        seed_path: Path to the seed graph JSON.
        cooccurrence_path: Path to the co-occurrence sidecar; a missing file is tolerated.

    Returns:
        The loaded :class:`~sdb.graph.build.KnowledgeGraph`.
    """
    return graph_from_seed(load_seed(seed_path), cooccurrence_path)
