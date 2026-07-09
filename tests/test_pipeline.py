"""End-to-end discovery over the seed graph: ranking, dedup, trust floor, errors."""

from __future__ import annotations

import pytest

from sdb.constants import TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph


def test_topic_not_found_has_suggestions(seed_graph: KnowledgeGraph) -> None:
    with pytest.raises(TopicNotFoundError) as excinfo:
        discover(seed_graph, "Rmoan Empire")
    assert excinfo.value.suggestions


def test_discover_ranked_unique_endpoints_above_floor(seed_graph: KnowledgeGraph) -> None:
    results = discover(seed_graph, "Roman Empire", top=5)
    assert results

    surprises = [result.surprise for result in results]
    assert surprises == sorted(surprises, reverse=True)  # ranked by surprise, descending

    endpoints = [result.path.node_ids[-1] for result in results]
    assert len(endpoints) == len(set(endpoints))  # one best path per endpoint

    assert all(result.trust >= TRUST_FLOOR for result in results)
