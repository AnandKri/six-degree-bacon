"""End-to-end discovery over the seed graph: ranking, dedup, trust floor, errors."""

from __future__ import annotations

import pytest

from sdb.constants import MAX_HOPS_UNLIKELY, POSSIBLY_THRESHOLD, TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Archetype


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


def test_unlikely_archetype_is_short_and_scored_by_improbability(
    seed_graph: KnowledgeGraph,
) -> None:
    results = discover(seed_graph, "Roman Empire", archetype=Archetype.UNLIKELY, top=5)
    assert results
    for result in results:
        assert result.archetype is Archetype.UNLIKELY
        assert result.path.length <= MAX_HOPS_UNLIKELY  # short by construction
        # Ranked by the improbability of the destination, not the length of the route.
        assert result.score == pytest.approx(result.endpoint_unexpectedness * result.trust)
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)


def test_improbable_pair_is_worlds_apart_not_an_obvious_neighbour(
    seed_graph: KnowledgeGraph,
) -> None:
    # Rome's most improbable short adjacencies are trans-Eurasian and tie at the top: the Great Wall
    # of China, Buddhism and Zhang Qian all connect in 2 hops via the Silk Road and none co-occur
    # with Rome. Which one wins the exact tie is immaterial; the invariant is that the top pair is
    # short and genuinely worlds-apart, not an obvious co-occurring neighbour like Latin.
    top = discover(seed_graph, "Roman Empire", archetype=Archetype.UNLIKELY)[0]
    endpoint = seed_graph.node(top.path.node_ids[-1]).label
    assert top.path.length <= MAX_HOPS_UNLIKELY
    assert endpoint in {"Great Wall of China", "Buddhism", "Zhang Qian"}
    # It beats an obvious short neighbour: Rome -> Rome's directly-co-occurring city Latin.
    assert top.endpoint_unexpectedness > seed_graph.endpoint_unexpectedness("roman_empire", "latin")


def test_bridge_connects_buddhism_to_the_greco_roman_world(seed_graph: KnowledgeGraph) -> None:
    # ADR 0011: the Hellenistic-India-Buddhism bridge makes Buddhism's improbable-pair partners
    # genuinely worlds-apart entities reached in <=2 hops via the Silk Road (Persia, Alexander the
    # Great, the Great Wall), rather than leaving Buddhism stranded in an India-only cluster.
    results = discover(seed_graph, "Buddhism", archetype=Archetype.UNLIKELY, top=3)
    assert results
    for result in results:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in results}
    assert endpoints & {"Persia", "Alexander the Great", "Great Wall of China"}
