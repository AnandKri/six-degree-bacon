"""The multi-brain platform (ADR 0044): the registry, the multi-brain server, and the site build."""

from __future__ import annotations

import json
import threading
import urllib.request
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sdb.brains import BrainSpec, available_brains
from sdb.graph.loader import load_graph, load_seed
from sdb.schema.enums import Domain, Region
from sdb.site import build_multi_site
from sdb.web import _AppServer

_DATA = Path(__file__).resolve().parent.parent / "data"
_TC = _DATA / "brains" / "twentieth_century"


# --------------------------------------------------------------------------- registry


def test_available_brains_lists_main_first_then_discovered_brains() -> None:
    brains = available_brains(_DATA)
    assert brains[0].name == "main"  # the curated graph is always the default
    by_name = {b.name: b for b in brains}
    assert "twentieth_century" in by_name  # data/brains/* is discovered
    tc = by_name["twentieth_century"]
    assert tc.label == "20th Century"  # read from the brain's meta.json, not title-cased
    assert tc.seed_path.exists() and tc.cooccurrence_path.exists()


def test_available_brains_always_has_main_even_without_a_brains_dir(tmp_path: Path) -> None:
    (tmp_path / "seed.json").write_text('{"nodes": [], "statements": []}', encoding="utf-8")
    brains = available_brains(tmp_path)
    assert [b.name for b in brains] == ["main"]  # never empty; no data/brains/ is fine


# --------------------------------------------------------------------------- multi-brain server


@contextmanager
def _running(server: _AppServer) -> Iterator[_AppServer]:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(server: _AppServer, path: str) -> dict[str, object]:
    host, port = server.server_address[0], server.server_address[1]
    with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as resp:
        data: dict[str, object] = json.loads(resp.read().decode("utf-8"))
    return data


def _two_brain_server() -> _AppServer:
    main = load_graph(_DATA / "seed.json", _DATA / "cooccurrence.json")
    tc = load_graph(_TC / "seed.json", _TC / "cooccurrence.json")
    return _AppServer(
        ("127.0.0.1", 0),
        {"main": main, "twentieth_century": tc},
        {"main": "Old World", "twentieth_century": "20th Century"},
        ["main", "twentieth_century"],
        "main",
    )


def test_api_brains_lists_every_brain_in_order() -> None:
    with _running(_two_brain_server()) as server:
        payload = _get(server, "/api/brains")
        brains = payload["brains"]
        assert [b["name"] for b in brains] == ["main", "twentieth_century"]  # order preserved
        assert brains[1]["label"] == "20th Century"


def test_brain_query_selects_the_right_graph() -> None:
    with _running(_two_brain_server()) as server:
        # The 20th-century brain has its own, smaller node set; the default (no ?brain=) is main.
        tc_graph = _get(server, "/api/graph?brain=twentieth_century")
        default_graph = _get(server, "/api/graph")
        assert len(tc_graph["nodes"]) != len(default_graph["nodes"])  # distinct brains served

        # A topic that exists only in the 20th-century brain resolves there and nowhere else.
        beatles = _get(server, "/api/discover?brain=twentieth_century&topic=The%20Beatles&top=1")
        assert beatles["results"]["journey"]  # found in the 20th-century brain
        missing = _get(server, "/api/discover?topic=The%20Beatles&top=1")  # default = main
        assert missing["error"] == "not_found"  # the Beatles are not in the Old-World graph


def test_unknown_brain_falls_back_to_the_default() -> None:
    with _running(_two_brain_server()) as server:
        bogus = _get(server, "/api/discover?brain=nope&topic=Roman%20Empire&top=1")
        assert bogus["results"]["journey"]  # a bad ?brain= serves the default brain, never errors


# --------------------------------------------------------------------------- multi-brain site


def test_build_multi_site_writes_a_manifest_and_per_brain_bundles(tmp_path: Path) -> None:
    # Two brains pointing at the same (small) data exercise the multi-file layout quickly.
    brains = [
        BrainSpec("alpha", "Alpha", _TC / "seed.json", _TC / "cooccurrence.json"),
        BrainSpec("beta", "Beta", _TC / "seed.json", _TC / "cooccurrence.json"),
    ]
    out = tmp_path / "site"
    index_path = build_multi_site(brains, out)
    assert index_path == out / "index.html"
    assert (out / "data.json").exists()  # first brain keeps the canonical name (back-compat)
    assert (out / "data-beta.json").exists()  # the rest are suffixed
    assert (out / ".nojekyll").exists()

    manifest = json.loads((out / "brains.json").read_text(encoding="utf-8"))["brains"]
    assert [b["name"] for b in manifest] == ["alpha", "beta"]
    assert [b["file"] for b in manifest] == ["data.json", "data-beta.json"]


def test_build_multi_site_with_one_brain_is_the_plain_single_bundle(tmp_path: Path) -> None:
    brains = [BrainSpec("main", "Main", _TC / "seed.json", _TC / "cooccurrence.json")]
    out = tmp_path / "site"
    build_multi_site(brains, out)
    assert (out / "data.json").exists()
    assert not (out / "brains.json").exists()  # a single brain needs no manifest / switcher


# --------------------------------------------------------------------- 20th-century brain content


def test_twentieth_century_has_a_cold_war_cross_sphere_edge() -> None:
    """ADR 0045: the SOVIET region earns its keep only if some edge crosses the Western/Soviet Cold
    War fault line — a genuine cultural crossing the coarse WESTERN sphere could not express.

    Asserted structurally (a WESTERN <-> SOVIET edge exists, e.g. Apollo 11 inspired_by Sputnik, or
    Tetris influenced_by the computer), not by pinning a favoured discovered result.
    """
    seed = load_seed(_TC / "seed.json")
    by_id = {n.id: n for n in seed.nodes}
    assert any(n.region is Region.SOVIET for n in seed.nodes)  # the new sphere is populated
    cold_war = [
        s
        for s in seed.statements
        if {by_id[s.subject].region, by_id[s.object].region} == {Region.WESTERN, Region.SOVIET}
    ]
    assert cold_war  # at least one Western<->Soviet crossing the coarse WESTERN sphere can't score


def test_twentieth_century_modern_regions_are_populated_and_cross_a_culture() -> None:
    """ADR 0046: each modern region the 100-node expansion added must be **populated** and actually
    **cross a culture boundary** somewhere — a sphere with no nodes, or one that never crosses into
    another culture, is dead weight. Structural (region present + a cross-region edge exists), not a
    pinned discovered result.
    """
    seed = load_seed(_TC / "seed.json")
    by_id = {n.id: n for n in seed.nodes}
    present = {n.region for n in seed.nodes}
    for region in (Region.LATIN_AMERICAN, Region.SUB_SAHARAN, Region.CARIBBEAN):
        assert region in present, f"region unpopulated: {region}"
        crossing = [
            s
            for s in seed.statements
            if region in {by_id[s.subject].region, by_id[s.object].region}
            and by_id[s.subject].region != by_id[s.object].region
        ]
        assert crossing, f"region never crosses a culture: {region}"


def test_twentieth_century_pendant_bridging_tissue() -> None:
    """ADR 0049: the escape-edge pass (driven by the ADR 0047 connectivity sweep) gave previously
    degree-1 pendants a second edge that crosses into another discipline, so journeys through them
    can score a domain jump — median journey ``domain_jumps`` was 0.000 before this pass.

    Structural, per the truth hierarchy: assert the pendants now carry a second statement and that
    an art<->history escape edge wires the arts into the politics cluster — never a pinned result.
    """
    seed = load_seed(_TC / "seed.json")
    by_id = {n.id: n for n in seed.nodes}
    degree: Counter[str] = Counter()
    for s in seed.statements:
        degree[s.subject] += 1
        degree[s.object] += 1
    bridged = ("soviet_constructivism", "indian_classical_music", "jawaharlal_nehru", "mao_zedong")
    for nid in bridged:
        assert degree[nid] >= 2, f"pendant not bridged: {nid}"
    art_history = [
        s
        for s in seed.statements
        if {by_id[s.subject].domain, by_id[s.object].domain} == {Domain.ART, Domain.HISTORY}
    ]
    assert art_history  # at least one art<->history escape edge feeds the domain-jump term


def test_twentieth_century_node_pass_bridges() -> None:
    """ADR 0050: the node pass added a three-region Cold War hub (the Cuban Missile Crisis, touching
    LATIN_AMERICAN + WESTERN + SOVIET) and a South-Asian<->Western cinema bridge (Jean Renoir), each
    opening a marquee pendant onto a distant cluster.

    Structural — the hub's regional reach and the Renoir<->Ray crossing exist — not a pinned result.
    """
    seed = load_seed(_TC / "seed.json")
    by_id = {n.id: n for n in seed.nodes}
    assert "cuban_missile_crisis" in by_id and "jean_renoir" in by_id
    crisis_regions = {by_id["cuban_missile_crisis"].region}
    for s in seed.statements:
        if s.subject == "cuban_missile_crisis":
            crisis_regions.add(by_id[s.object].region)
        elif s.object == "cuban_missile_crisis":
            crisis_regions.add(by_id[s.subject].region)
    assert {Region.LATIN_AMERICAN, Region.WESTERN, Region.SOVIET} <= crisis_regions
    renoir_ray = any(
        {s.subject, s.object} == {"satyajit_ray", "jean_renoir"} for s in seed.statements
    )
    assert renoir_ray  # the Renoir node fixes the Satyajit Ray pendant across a culture boundary
