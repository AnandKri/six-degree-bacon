"""End-to-end discovery over the seed graph: ranking, dedup, trust floor, errors."""

from __future__ import annotations

import pytest

from sdb.constants import POSSIBLY_THRESHOLD, TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph


def test_topic_not_found_has_suggestions(seed_graph: KnowledgeGraph) -> None:
    with pytest.raises(TopicNotFoundError) as excinfo:
        discover(seed_graph, "Rmoan Empire")
    assert excinfo.value.suggestions


def test_discover_ranked_by_wow_score_unique_endpoints(seed_graph: KnowledgeGraph) -> None:
    results = discover(seed_graph, "Roman Empire", top=5)
    assert results

    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)  # ranked by wow = surprise x trust, descending
    for result in results:
        assert result.score == pytest.approx(result.surprise * result.trust)

    endpoints = [result.path.node_ids[-1] for result in results]
    assert len(endpoints) == len(set(endpoints))  # one best path per endpoint


def test_default_gate_surfaces_only_confident_results(seed_graph: KnowledgeGraph) -> None:
    # Default is the "wow with evidence" gate: every surfaced path clears POSSIBLY_THRESHOLD.
    confident = discover(seed_graph, "Roman Empire", top=10)
    assert confident
    assert all(result.trust >= POSSIBLY_THRESHOLD for result in confident)
    assert all(not result.possibly for result in confident)

    # Lowering the gate admits speculative, lower-trust paths (down to the hard floor).
    speculative = discover(seed_graph, "Roman Empire", top=50, min_trust=TRUST_FLOOR)
    assert len(speculative) > len(confident)
    assert all(result.trust >= TRUST_FLOOR for result in speculative)
