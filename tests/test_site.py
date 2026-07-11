"""Static-site export: a deterministic, offline pre-render of every topic's results."""

from __future__ import annotations

import json
from pathlib import Path

from sdb.graph.build import KnowledgeGraph
from sdb.site import build_site


def _build(graph: KnowledgeGraph, tmp_path: Path) -> dict[str, object]:
    out = tmp_path / "site"
    index_path = build_site(graph, out)
    assert index_path == out / "index.html"
    assert (out / "index.html").exists()
    assert (out / ".nojekyll").exists()  # GitHub Pages: serve files verbatim
    return json.loads((out / "data.json").read_text(encoding="utf-8"))


def test_bundle_covers_every_topic_with_both_toggle_states(
    seed_graph: KnowledgeGraph, tmp_path: Path
) -> None:
    data = _build(seed_graph, tmp_path)
    assert len(data["index"]) == len(seed_graph.nodes())  # every node is browsable/resolvable
    assert {"id", "label", "qid", "aliases"} <= data["index"][0].keys()

    entry = data["results"]["roman_empire"]
    assert {"strict", "loose"} == entry.keys()  # both UI toggle states are precomputed
    assert entry["strict"]["journey"]  # a confident journey exists at the default gate
    assert entry["strict"]["journey"][0]["sources"]  # sourced, like the live payload


def test_strict_is_confident_and_loose_is_a_superset(
    seed_graph: KnowledgeGraph, tmp_path: Path
) -> None:
    data = _build(seed_graph, tmp_path)
    # Speculative topic: the strict gate may show fewer journeys than the loose one, never more.
    strict = data["results"]["trojan_war"]["strict"]["journey"]
    loose = data["results"]["trojan_war"]["loose"]["journey"]
    assert all(not card["possibly"] for card in strict)  # strict = confident only
    assert len(loose) >= len(strict)


def test_index_html_is_the_packaged_page(seed_graph: KnowledgeGraph, tmp_path: Path) -> None:
    _build(seed_graph, tmp_path)
    served = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    packaged = (Path(__file__).resolve().parent.parent / "sdb" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    assert served == packaged  # no separate template to drift from `sdb serve`
    assert "./data.json" in served  # the page probes for the static bundle
