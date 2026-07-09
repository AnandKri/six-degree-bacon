"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_seed

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"


@pytest.fixture(scope="session")
def seed_graph() -> KnowledgeGraph:
    """The curated Phase-0 knowledge graph, loaded once per test session."""
    return KnowledgeGraph.from_seed(load_seed(SEED_PATH))
