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


def test_bundle_includes_the_laid_out_graph(seed_graph: KnowledgeGraph, tmp_path: Path) -> None:
    graph = _build(seed_graph, tmp_path)["graph"]  # the map draws from this, offline
    assert len(graph["nodes"]) == len(seed_graph.nodes())
    assert graph["edges"]
    assert {"id", "label", "domain", "x", "y", "degree"} <= graph["nodes"][0].keys()


def test_strict_is_confident_and_loose_only_ever_outranks(
    seed_graph: KnowledgeGraph, tmp_path: Path
) -> None:
    """Lowering the gate only ever *adds candidates*, as a property over every topic in the seed.

    This was pinned to `trojan_war` until ADR 0033, whose `Ancient Greece -> Renaissance humanism`
    edge gave Troy's war a confident journey — so the one hand-picked "speculative" topic stopped
    being speculative and the test broke on a seed improvement rather than a regression. Asserting
    over all topics keeps the same two claims without betting on any one topic's evidence level.

    It then asserted `strict_endpoints <= loose_endpoints` ("loosening never displaces a confident
    result"), which is **not** something the rubric promises and which ADR 0053 falsified the same
    way: `troy` gained its first confident journeys (via the new `aeneas -> troy` edge), and one of
    its speculative paths outscores them, so a fixed top-N legitimately drops the weakest confident
    card. Both lists are the top-N of the *same* ranking key over a widening candidate set, so the
    honest invariant is the one asserted here: a confident card leaves the top-N only when every
    card that replaced it scores at least as high — never because loosening the gate removed it.
    """
    data = _build(seed_graph, tmp_path)
    additive = []
    for topic in data["results"].values():
        strict, loose = topic["strict"]["journey"], topic["loose"]["journey"]
        assert all(not card["possibly"] for card in strict)  # strict = confident only
        strict_scores = {card["endpoint"]: card["score"] for card in strict}
        loose_endpoints = {card["endpoint"] for card in loose}
        assert len(loose) >= len(strict)  # the candidate set only ever widens
        cutoff = min((card["score"] for card in loose), default=0.0)
        for endpoint in strict_scores.keys() - loose_endpoints:
            # Displaced, not dropped: whatever took the slot outranks it on the shared key.
            assert strict_scores[endpoint] <= cutoff, endpoint
        additive.append(bool(loose_endpoints - strict_scores.keys()))
    # ...and on at least one topic it genuinely adds something, so the gate is not a no-op (which
    # "not fewer" alone would satisfy). Currently the mythic starts: troy, aeneas.
    assert any(additive)


def test_index_html_is_the_packaged_page(seed_graph: KnowledgeGraph, tmp_path: Path) -> None:
    _build(seed_graph, tmp_path)
    served = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    packaged = (Path(__file__).resolve().parent.parent / "sdb" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    assert served == packaged  # no separate template to drift from `sdb serve`
    assert "./data.json" in served  # the page probes for the static bundle
