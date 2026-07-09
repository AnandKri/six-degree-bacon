"""Ranker-regression (golden) and narrative-faithfulness checks over the seed graph."""

from __future__ import annotations

import json
from pathlib import Path

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
    # The deliberately-planted 6-hop Rome -> China chain must remain discoverable.
    results = discover(seed_graph, "Roman Empire", top=20)
    by_endpoint = {seed_graph.node(r.path.node_ids[-1]).label: r for r in results}
    assert "Great Wall of China" in by_endpoint
    assert by_endpoint["Great Wall of China"].path.length == 6


def test_narrative_faithfulness(seed_graph: KnowledgeGraph) -> None:
    # Every node label on a discovered path must appear in its TIL text.
    results = discover(seed_graph, "Roman Empire", top=5)
    assert results
    for result in results:
        for node_id in result.path.node_ids:
            assert seed_graph.node(node_id).label in result.til
