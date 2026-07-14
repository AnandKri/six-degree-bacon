"""End-to-end discovery over the seed graph: ranking, dedup, trust floor, errors."""

from __future__ import annotations

import pytest

from sdb.constants import MAX_HOPS_UNLIKELY, POSSIBLY_THRESHOLD, TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Archetype, Domain, Predicate, SourceType
from sdb.schema.models import DiscoveryResult, Node, Source, Statement


def _obvious_endpoint(graph: KnowledgeGraph, start_id: str) -> str:
    """The start's most co-occurring ("most obvious") node — its minimal endpoint_unexpectedness."""
    others = [node.id for node in graph.nodes() if node.id != start_id]
    return min(others, key=lambda nid: graph.endpoint_unexpectedness(start_id, nid))


def _assert_worlds_apart(
    graph: KnowledgeGraph, start_id: str, pairs: list[DiscoveryResult]
) -> None:
    """Property-based check that an UNLIKELY result set is genuinely "worlds apart", not obvious.

    Robust to seed growth (no hardcoded far labels): every pair is short, the start's single most
    co-occurring node is never surfaced, and the top pair is strictly more unexpected than it. A
    regression that let the archetype rank obvious co-occurring neighbours would fail this — unlike
    a "some endpoint is outside a hardcoded in-cluster set" check, which is satisfied by almost any
    node because endpoint-unexpectedness saturates for sparsely-linked starts.
    """
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    obvious = _obvious_endpoint(graph, start_id)
    assert obvious not in {result.path.node_ids[-1] for result in pairs}
    assert pairs[0].endpoint_unexpectedness > graph.endpoint_unexpectedness(start_id, obvious)


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
    # Default is the "wow with evidence" gate: every surfaced path clears POSSIBLY_THRESHOLD. Use
    # the *same* wide `top` for both calls so the comparison isolates the gate, not the result cap.
    confident = discover(seed_graph, "Roman Empire", top=99)
    assert confident
    assert all(result.trust >= POSSIBLY_THRESHOLD for result in confident)
    assert all(not result.possibly for result in confident)

    # Lowering the gate to the floor is strictly additive: it admits new (speculative) endpoints and
    # drops none of the confident ones — a real superset, not just "not fewer".
    speculative = discover(seed_graph, "Roman Empire", top=99, min_trust=TRUST_FLOOR)
    assert all(result.trust >= TRUST_FLOOR for result in speculative)
    confident_endpoints = {result.path.node_ids[-1] for result in confident}
    speculative_endpoints = {result.path.node_ids[-1] for result in speculative}
    assert confident_endpoints < speculative_endpoints  # strict superset


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
    # The UNLIKELY archetype must surface a genuinely improbable destination, not an obvious
    # co-occurring neighbour. Property-based (the exact tie winner grows with the seed): the most
    # co-occurring node is never surfaced, and the top pair is strictly more unexpected than it.
    pairs = discover(seed_graph, "Roman Empire", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "roman_empire", pairs)
    # Concretely, Latin — Rome's obvious directly-linked neighbour — never wins.
    assert seed_graph.node(pairs[0].path.node_ids[-1]).label != "Latin"


def test_bridge_connects_buddhism_to_the_greco_roman_world(seed_graph: KnowledgeGraph) -> None:
    # ADR 0011: the Hellenistic-India-Buddhism bridge stops Buddhism being stranded in an India-only
    # cluster — its improbable-pair partners are genuinely worlds-apart entities reached in a few
    # hops (now e.g. Thor, Aristotle), verified property-based rather than by a hardcoded label set.
    results = discover(seed_graph, "Buddhism", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "buddhism", results)


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
    # ADR 0018: the math lineage runs Algebra -> al-Khwarizmi -> al-Tusi -> ... tying the Islamic
    # Golden Age into the existing science subgraph. Assert the structural lineage (the al-Khwarizmi
    # -> al-Tusi bridge), not the exact terminus (the scoring may land on Euclid or Copernicus).
    algebra = discover(seed_graph, "Algebra", top=1)
    assert algebra
    assert {"al_khwarizmi", "al_tusi"} <= set(algebra[0].path.node_ids)

    # Baghdad reaches the wider Eurasian world through the Silk Road hub — at least one top journey
    # routes via it, so it is a bridge, not an island. `any` (not `all`) stays robust if a second
    # bridge out of Baghdad is ever seeded.
    baghdad = discover(seed_graph, "Baghdad", top=3)
    assert baghdad
    assert any("silk_road" in r.path.node_ids for r in baghdad)


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
    # island — it ties into three existing hubs. Japan's top journeys route out through one of its
    # bridges (Silk Road via Tang, or Buddhism via Zen), the structural claim rather than "some
    # endpoint is outside a hardcoded in-cluster set".
    japan_bridges = {"silk_road", "buddhism"}
    journeys = discover(seed_graph, "Japan", top=5)
    assert journeys
    assert any(japan_bridges & set(r.path.node_ids) for r in journeys)

    # Zen bridges the Buddhism hub to Japan, so it descends from Buddhism on the way to Japan.
    zen = discover(seed_graph, "Zen", top=5)
    assert zen
    assert any("buddhism" in r.path.node_ids for r in zen)

    # Confucius's improbable partners are genuinely worlds apart, not his obvious neighbours.
    pairs = discover(seed_graph, "Confucius", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "confucius", pairs)


def test_norse_celtic_cluster_connects_via_proto_indo_european(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0022: the Norse/Celtic myth cluster is not an island — both mythologies descend from
    # Proto-Indo-European (the hub that also anchors Mithra), and Thor is cognate with the Vedic
    # thunder-god Indra of the Rigveda, so the Norse pantheon reaches the wider Indo-European world
    # (India, the Rigveda, Buddhism), not just its own gods.
    # Thor's top journeys route through the cluster's bridge hubs — Proto-Indo-European, or the
    # Rigveda via the thunder-god cognate — the structural claim, not a hardcoded endpoint list.
    thor_bridges = {"proto_indo_european", "rigveda"}
    journeys = discover(seed_graph, "Thor", top=5)
    assert journeys
    assert any(thor_bridges & set(r.path.node_ids) for r in journeys)

    # Thor's improbable partners are genuinely worlds apart, not another Norse god.
    pairs = discover(seed_graph, "Thor", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "thor", pairs)

    # Both mythologies descend from Proto-Indo-European, so Celtic myth routes through that hub.
    celtic = discover(seed_graph, "Celtic mythology", top=3)
    assert celtic
    assert any("proto_indo_european" in r.path.node_ids for r in celtic)


def test_chinese_tech_cluster_connects_via_dynasties_and_silk_road(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0023: the Four Great Inventions (paper, printing, gunpowder, compass) tie into Han/Tang
    # China, the Silk Road, and Buddhism — not an island. Paper reaches the wider Eurasian world
    # through the Silk Road; woodblock printing descends from Buddhist demand for scriptures.
    # Paper's top journeys route out through the Silk Road hub — the structural bridge claim.
    paper = discover(seed_graph, "Paper", top=5)
    assert paper
    assert any("silk_road" in r.path.node_ids for r in paper)

    # Woodblock printing's improbable partners are genuinely worlds apart from a printing technique,
    # not another Chinese invention.
    pairs = discover(seed_graph, "Woodblock printing", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "woodblock_printing", pairs)


def test_west_africa_cluster_connects_via_the_islam_hub(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0024: the West African cluster (Mali, Mansa Musa, Timbuktu, trans-Saharan trade) is not an
    # island — the new Islam node bridges it into the existing graph (Islam succeeded Zoroastrianism
    # in Persia; the Abbasid caliphate belongs to it), so Mansa Musa reaches the wider world.
    # Mansa Musa's top journeys route through the new Islam hub — the bridge, not an island.
    musa = discover(seed_graph, "Mansa Musa", top=5)
    assert musa
    assert any("islam" in r.path.node_ids for r in musa)

    # The new Islam hub ties into the existing Persia/Zoroastrian thread (and thence the Silk Road).
    islam = discover(seed_graph, "Islam", top=5)
    assert islam
    reached: set[str] = set()
    for r in islam:
        reached |= set(r.path.node_ids)
    assert {"zoroastrianism", "persia", "silk_road"} & reached


def test_no_confident_connection_honestly_returns_nothing() -> None:
    # The project's honesty promise: a topic with only low-trust paths returns nothing at the
    # default gate. Uses a *constructed* graph (not a seed label, which drifts): a 3-hop chain of
    # Wikipedia-sourced edges has path trust 0.75**3 = 0.42 — below POSSIBLY_THRESHOLD (0.50) but
    # above TRUST_FLOOR (0.15). So the default gate returns [], while lowering the gate to the floor
    # surfaces the same path — proving the emptiness is the *gate*, not a missing connection.
    nodes = tuple(
        Node(id=f"n{i}", label=f"N{i}", domain=Domain.HISTORY, type="node") for i in range(4)
    )
    statements = tuple(
        Statement(
            subject=f"n{i}",
            predicate=Predicate.PART_OF,
            object=f"n{i + 1}",
            sources=(Source(id=f"s{i}", source_type=SourceType.WIKIPEDIA),),
        )
        for i in range(3)
    )
    graph = KnowledgeGraph(nodes, statements)

    assert discover(graph, "N0") == []  # nothing clears the default trust gate

    speculative = discover(graph, "N0", min_trust=TRUST_FLOOR)
    assert len(speculative) == 1  # the 3-hop path exists; it just isn't confident
    assert speculative[0].possibly  # and it is flagged speculative
    assert speculative[0].trust == pytest.approx(0.75**3)


def test_journey_and_unlikely_are_ranked_on_different_bases(seed_graph: KnowledgeGraph) -> None:
    # The two archetypes optimise different things, so each winner is scored on its own basis and
    # they disagree on the top destination for at least some starts. A swapped/collapsed `basis`
    # would make every start's tops coincide *and* fail the score-formula checks below.
    journey = discover(seed_graph, "Euclid", archetype=Archetype.JOURNEY, top=1)
    unlikely = discover(seed_graph, "Euclid", archetype=Archetype.UNLIKELY, top=1)
    assert journey and unlikely

    # Each winner is scored on, and by construction optimal for, its own declared basis.
    assert journey[0].score == pytest.approx(journey[0].surprise * journey[0].trust)
    assert unlikely[0].score == pytest.approx(
        unlikely[0].endpoint_unexpectedness * unlikely[0].trust
    )
    # The improbable pair is short by construction; the journey is a full fixed-length 3-hop chain.
    assert unlikely[0].path.length <= MAX_HOPS_UNLIKELY
    assert journey[0].path.length == 3

    # Behaviourally distinct: across several starts, at least one has different journey/pair tops
    # (they cannot all coincide unless the two bases are the same).
    def tops_differ(topic: str) -> bool:
        j = discover(seed_graph, topic, archetype=Archetype.JOURNEY, top=1)
        u = discover(seed_graph, topic, archetype=Archetype.UNLIKELY, top=1)
        return bool(j and u and j[0].path.node_ids[-1] != u[0].path.node_ids[-1])

    assert any(tops_differ(t) for t in ("Euclid", "Buddhism", "Silk Road", "Roman Empire"))
