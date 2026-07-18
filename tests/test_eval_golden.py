"""Ranker-regression (golden) and narrative-faithfulness checks over the seed graph."""

from __future__ import annotations

import json
from pathlib import Path

from sdb.constants import TRUST_FLOOR
from sdb.engine.pipeline import discover
from sdb.graph.build import KnowledgeGraph

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden.json"


def test_golden_top_results(seed_graph: KnowledgeGraph) -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    for case in golden["cases"]:
        results = discover(seed_graph, case["topic"], top=case.get("top", 1))
        assert results, case["topic"]
        top = results[0]
        assert seed_graph.node(top.path.node_ids[-1]).label == case["expected_endpoint"]
        assert top.path.length == case["expected_hops"]
        assert top.possibly == case["expected_possibly"]


def test_planted_path_discoverable(seed_graph: KnowledgeGraph) -> None:
    # The planted 6-hop Rome -> China chain is low-trust and deep, so it surfaces only with the
    # lowered gate AND when the depth is explicitly allowed (the default cap is now 4 hops; the
    # engine still supports the full "six degrees" via max_hops). `top` spans every reachable
    # endpoint so seed growth (more endpoints) can't crowd the deep chain out of the window.
    results = discover(seed_graph, "Roman Empire", top=99, min_trust=TRUST_FLOOR, max_hops=6)
    by_endpoint = {seed_graph.node(r.path.node_ids[-1]).label: r for r in results}
    assert "Great Wall of China" in by_endpoint
    assert by_endpoint["Great Wall of China"].path.length == 6


def test_endpoint_surprise_demotes_obvious_destination(seed_graph: KnowledgeGraph) -> None:
    # The endpoint-surprise term (ADR 0003) must stop the obvious Rome->Latin pairing winning:
    # Latin is linked from the Roman Empire article, so unlinked endpoints now outrank it.
    results = discover(seed_graph, "Roman Empire", top=5)
    endpoints = [seed_graph.node(r.path.node_ids[-1]).label for r in results]
    assert endpoints[0] != "Latin"
    winner_unexpectedness = seed_graph.endpoint_unexpectedness(
        results[0].path.node_ids[0], results[0].path.node_ids[-1]
    )
    latin_unexpectedness = seed_graph.endpoint_unexpectedness("roman_empire", "latin")
    assert winner_unexpectedness > latin_unexpectedness


def test_narrative_faithfulness(seed_graph: KnowledgeGraph) -> None:
    # ADR 0042: the TIL is the curated `headline` of the path's payoff (last) hop, prefixed — not a
    # mechanical predicate chain. Verify the narrator surfaces that exact curated line on real seed
    # paths (and that it is non-empty; test_validate guards that every curated edge has one).
    results = discover(seed_graph, "Roman Empire", top=5)
    assert results
    for result in results:
        payoff = result.path.hops[-1].statement.headline.strip()
        assert payoff  # a curated headline exists for the payoff edge
        assert result.til == f"TIL: {payoff}"  # possibly=False at the default trust gate
