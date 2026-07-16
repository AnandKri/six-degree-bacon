"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_cooccurrence, load_seed, load_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = DATA_DIR / "seed.json"
COOCCURRENCE_PATH = DATA_DIR / "cooccurrence.json"


@pytest.fixture(scope="session")
def seed_graph() -> KnowledgeGraph:
    """The curated knowledge graph with its co-occurrence *and* similarity sidecar, loaded once."""
    return KnowledgeGraph.from_seed(
        load_seed(SEED_PATH),
        load_cooccurrence(COOCCURRENCE_PATH),
        load_similarity(COOCCURRENCE_PATH),
    )
