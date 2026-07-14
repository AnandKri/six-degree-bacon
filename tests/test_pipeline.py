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
    # Rome's most improbable short adjacencies are trans-Eurasian and tie at the top (Great Wall,
    # Buddhism, Baghdad, House of Wisdom — all 2 hops via the Silk Road, none co-occurring w/ Rome).
    # The exact tie winner is immaterial and grows with the seed, so the invariant is a *property*:
    # the top pair is short and far more unexpected than an obvious co-occurring neighbour.
    top = discover(seed_graph, "Roman Empire", archetype=Archetype.UNLIKELY)[0]
    endpoint = seed_graph.node(top.path.node_ids[-1]).label
    assert top.path.length <= MAX_HOPS_UNLIKELY
    assert endpoint != "Latin"  # not the obvious directly-linked neighbour
    latin_eu = seed_graph.endpoint_unexpectedness("roman_empire", "latin")
    assert top.endpoint_unexpectedness > latin_eu  # genuinely worlds-apart


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


def test_greece_cluster_connects_philosophy_to_the_east(seed_graph: KnowledgeGraph) -> None:
    # ADR 0016: the Ancient Greece cluster is a hub — Aristotle reaches the Eastern world (he
    # tutored Alexander -> India -> Buddhism -> Silk Road), not just Greek neighbours, and its
    # improbable pairs are short and genuinely worlds-apart.
    journeys = discover(seed_graph, "Aristotle", top=3)
    assert journeys
    endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in journeys}
    assert endpoints & {"Buddhism", "India", "Silk Road", "Persia"}

    pairs = discover(seed_graph, "Aristotle", archetype=Archetype.UNLIKELY, top=3)
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    # Its improbable partners are trans-cultural (India/Persia/Buddhism/Silk Road), not the obvious
    # Greek neighbours (Plato, Athens).
    pair_endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in pairs}
    assert pair_endpoints & {"India", "Persia", "Buddhism", "Silk Road"}


def test_egypt_cluster_is_connected_not_an_island(seed_graph: KnowledgeGraph) -> None:
    # ADR 0017: Cleopatra reaches the wider world via Alexandria (-> Alexander -> India ->
    # Buddhism), and Ancient Egypt bridges to Rome (annexed as a province) — not an island.
    cleopatra = discover(seed_graph, "Cleopatra", top=3)
    assert cleopatra
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in cleopatra} & {
        "Buddhism",
        "India",
        "Silk Road",
    }
    pairs = discover(seed_graph, "Ancient Egypt", archetype=Archetype.UNLIKELY, top=3)
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in pairs} & {
        "Mithraism",
        "Buddhism",
        "Persia",
    }


def test_islamic_cluster_bridges_greek_and_indian_science(seed_graph: KnowledgeGraph) -> None:
    # ADR 0018: the math lineage runs Algebra -> al-Khwarizmi -> al-Tusi -> Euclid, tying the
    # Islamic Golden Age into the existing Euclid science subgraph; Baghdad reaches the Silk Road.
    algebra = discover(seed_graph, "Algebra", top=1)
    assert algebra
    assert "Euclid" in [seed_graph.node(n).label for n in algebra[0].path.node_ids]

    # Baghdad reaches the wider Eurasian world through the Silk Road hub — every top journey routes
    # via the Silk Road, so it is a bridge, not an island (property-based, robust to the hop cap).
    baghdad = discover(seed_graph, "Baghdad", top=3)
    assert baghdad
    assert all("Silk Road" in [seed_graph.node(n).label for n in r.path.node_ids] for r in baghdad)


def test_scientific_revolution_extends_the_lineage_back_to_antiquity(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0019: the modern astronomers reach back across the 2000-year science lineage — Newton via
    # Euclid, Copernicus via al-Tusi (the Tusi couple) — into the Greek/Islamic world.
    newton = discover(seed_graph, "Isaac Newton", top=1)
    assert newton
    assert "Euclid" in [seed_graph.node(n).label for n in newton[0].path.node_ids]

    copernicus = discover(seed_graph, "Nicolaus Copernicus", top=1)
    assert copernicus
    assert "Nasir al-Din al-Tusi" in [seed_graph.node(n).label for n in copernicus[0].path.node_ids]


def test_east_asia_cluster_connects_via_china_buddhism_and_silk_road(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0020: the East Asia cluster (Confucius/Confucianism, Tang dynasty, Japan, Zen) is not an
    # island — it ties into three existing hubs. Japan reaches the wider Eurasian web (via Tang ->
    # China -> Silk Road, and via Zen -> Buddhism), not just its East-Asian neighbours.
    east_asia = {
        "Japan",
        "China",
        "Tang dynasty",
        "Zen",
        "Confucius",
        "Confucianism",
        "Great Wall of China",
        "Chang'an",
        "Qin dynasty",
        "Qin Shi Huang",
        "Han dynasty",
        "Zhang Qian",
    }
    journeys = discover(seed_graph, "Japan", top=5)
    assert journeys
    endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in journeys}
    # Japan's journeys leave the East-Asian neighbourhood entirely — it is a bridge, not an island.
    assert endpoints - east_asia

    # Zen bridges the Buddhism hub to Japan, so it descends from Buddhism on the way to Japan.
    zen = discover(seed_graph, "Zen", top=5)
    assert zen
    assert any("Buddhism" in [seed_graph.node(n).label for n in r.path.node_ids] for r in zen)

    # Confucius's improbable partners are worlds-apart (the Mediterranean / Indian / Persian world),
    # short, and more unexpected than his obvious neighbours (China, Confucianism) — property-based,
    # not a hardcoded label, since the top tie keeps shifting as the seed grows.
    pairs = discover(seed_graph, "Confucius", archetype=Archetype.UNLIKELY, top=3)
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    pair_endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in pairs}
    assert pair_endpoints - {"China", "Confucianism"}
    obvious = seed_graph.endpoint_unexpectedness("confucius", "china")
    for result in pairs:
        assert result.endpoint_unexpectedness >= obvious


def test_norse_celtic_cluster_connects_via_proto_indo_european(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0022: the Norse/Celtic myth cluster is not an island — both mythologies descend from
    # Proto-Indo-European (the hub that also anchors Mithra), and Thor is cognate with the Vedic
    # thunder-god Indra of the Rigveda, so the Norse pantheon reaches the wider Indo-European world
    # (India, the Rigveda, Buddhism), not just its own gods.
    norse = {"Odin", "Thor", "Loki", "Norse mythology", "Celtic mythology"}
    journeys = discover(seed_graph, "Thor", top=5)
    assert journeys
    endpoints = {seed_graph.node(r.path.node_ids[-1]).label for r in journeys}
    # Thor's journeys leave the Norse/PIE neighbourhood entirely — a bridge, not an island.
    assert endpoints - norse - {"Proto-Indo-European"}

    # Thor's improbable partners are the eastern Indo-European world (Rigveda/India), not another
    # Norse god — property-based, since the top tie keeps shifting as the seed grows.
    pairs = discover(seed_graph, "Thor", archetype=Archetype.UNLIKELY, top=3)
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in pairs} - norse

    # Both mythologies descend from Proto-Indo-European, so Celtic myth routes through that hub.
    celtic = discover(seed_graph, "Celtic mythology", top=3)
    assert celtic
    assert any(
        "Proto-Indo-European" in [seed_graph.node(n).label for n in r.path.node_ids] for r in celtic
    )


def test_chinese_tech_cluster_connects_via_dynasties_and_silk_road(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0023: the Four Great Inventions (paper, printing, gunpowder, compass) tie into Han/Tang
    # China, the Silk Road, and Buddhism — not an island. Paper reaches the wider Eurasian world
    # through the Silk Road; woodblock printing descends from Buddhist demand for scriptures.
    china_tech = {"Paper", "Cai Lun", "Woodblock printing", "Gunpowder", "Compass"}
    chinese_hubs = china_tech | {"Silk Road", "China", "Han dynasty", "Tang dynasty"}
    paper = discover(seed_graph, "Paper", top=5)
    assert paper
    # At least one Paper journey routes via the Silk Road hub, and its journeys leave the China/tech
    # neighbourhood entirely — a bridge, not an island.
    assert any("Silk Road" in [seed_graph.node(n).label for n in r.path.node_ids] for r in paper)
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in paper} - chinese_hubs

    # Woodblock printing's improbable partners are worlds apart from a printing technique (the
    # Buddhism hub it descends from, India), not another Chinese invention — property-based.
    pairs = discover(seed_graph, "Woodblock printing", archetype=Archetype.UNLIKELY, top=3)
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in pairs} - china_tech


def test_west_africa_cluster_connects_via_the_islam_hub(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0024: the West African cluster (Mali, Mansa Musa, Timbuktu, trans-Saharan trade) is not an
    # island — the new Islam node bridges it into the existing graph (Islam succeeded Zoroastrianism
    # in Persia; the Abbasid caliphate belongs to it), so Mansa Musa reaches the wider world.
    west_africa = {"Mali Empire", "Mansa Musa", "Timbuktu", "Trans-Saharan trade"}
    musa = discover(seed_graph, "Mansa Musa", top=5)
    assert musa
    # Mansa Musa routes through the Islam hub and lands outside West Africa entirely.
    assert any("Islam" in [seed_graph.node(n).label for n in r.path.node_ids] for r in musa)
    assert {seed_graph.node(r.path.node_ids[-1]).label for r in musa} - west_africa - {"Islam"}

    # The new Islam hub ties into the existing Persia/Zoroastrian thread (and thence the Silk Road).
    islam = discover(seed_graph, "Islam", top=5)
    assert islam
    reached: set[str] = set()
    for r in islam:
        reached |= {seed_graph.node(n).label for n in r.path.node_ids}
    assert {"Zoroastrianism", "Persia", "Silk Road"} & reached
