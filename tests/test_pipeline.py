"""End-to-end discovery over the seed graph: ranking, dedup, trust floor, errors."""

from __future__ import annotations

import pytest

from sdb.constants import (
    MAX_HOPS_UNLIKELY,
    MIN_HOPS_DEFAULT,
    POSSIBLY_THRESHOLD,
    TRUST_FLOOR,
)
from sdb.engine.pipeline import (
    TopicNotFoundError,
    discover,
    discover_all,
    trust_gate,
)
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

    Robust to seed growth (no hardcoded far labels): every pair is short, and the *winner* is
    neither the start's single most co-occurring node nor less unexpected than it. A regression that
    let the archetype rank obvious co-occurring neighbours first would fail this — unlike a "some
    endpoint is outside a hardcoded in-cluster set" check, which is satisfied by almost any node
    because endpoint-unexpectedness saturates for sparsely-linked starts.

    Deliberately asserts on the winner rather than the whole list: a start with few 1-2 hop
    neighbours has a small candidate pool, so an obvious node can legitimately appear far down a
    `top=n` list. What must never happen is it *winning*.
    """
    assert pairs
    for result in pairs:
        assert result.path.length <= MAX_HOPS_UNLIKELY
    obvious = _obvious_endpoint(graph, start_id)
    assert pairs[0].path.node_ids[-1] != obvious
    assert pairs[0].endpoint_unexpectedness > graph.endpoint_unexpectedness(start_id, obvious)


def test_topic_not_found_has_suggestions(seed_graph: KnowledgeGraph) -> None:
    with pytest.raises(TopicNotFoundError) as excinfo:
        discover(seed_graph, "Rmoan Empire")
    assert excinfo.value.suggestions


def test_trust_gate_picks_the_documented_thresholds() -> None:
    assert trust_gate(include_possibly=False) == POSSIBLY_THRESHOLD
    assert trust_gate(include_possibly=True) == TRUST_FLOOR


def test_discover_all_dispatches_both_archetypes_like_the_per_archetype_call(
    seed_graph: KnowledgeGraph,
) -> None:
    # The shared dispatch both front-ends use must agree, key-for-key, with calling `discover` per
    # archetype — that equivalence is the whole point of hoisting the loop out of the CLI and web.
    both = discover_all(seed_graph, "Roman Empire", archetype="both", top=3)
    # The improbable pair leads (ADR 0042): it is shown first / default.
    assert list(both) == [Archetype.UNLIKELY, Archetype.JOURNEY]  # presentation order preserved
    for archetype, results in both.items():
        expected = discover(seed_graph, "Roman Empire", archetype=archetype, top=3)
        assert [r.path.node_ids for r in results] == [r.path.node_ids for r in expected]


def test_discover_all_narrows_to_one_archetype_and_falls_back_on_junk(
    seed_graph: KnowledgeGraph,
) -> None:
    # A single-archetype request returns just that key; an unrecognised name falls back to "both"
    # (the web hands it straight from a query string, so junk must not crash).
    only = discover_all(seed_graph, "Roman Empire", archetype="unlikely", top=1)
    assert list(only) == [Archetype.UNLIKELY]

    junk = discover_all(seed_graph, "Roman Empire", archetype="nonsense", top=1)
    assert list(junk) == [Archetype.UNLIKELY, Archetype.JOURNEY]


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
    """ADR 0019: the modern astronomers reach back across the ~2000-year science lineage.

    Asserted as the *structural* claim — a top journey travels centuries back into antiquity — not
    by naming who it reaches. This previously pinned `"Nasir al-Din al-Tusi" in copernicus[0]`,
    i.e. a named favourite at rank 1, and that is exactly how it went wrong: when ADR 0033 added a
    true `copernicus part_of renaissance` edge, this test failed, and the edge was deleted to make
    it pass. Deleting true data to protect a favoured result inverts the whole project — data and
    the rubric are the truth, and a test may only verify what the rubric claims. The real defect was
    in the rubric (fixed in ADR 0034/0035), and the edge is now restored.
    """
    for astronomer in ("Isaac Newton", "Nicolaus Copernicus"):
        journeys = discover(seed_graph, astronomer, top=3)
        assert journeys, astronomer
        modern = seed_graph.find_topic(astronomer)
        assert modern is not None
        origin = seed_graph.node(modern).midpoint_year
        assert origin is not None
        # Some surfaced journey reaches a figure at least five centuries older — the lineage is
        # traversable back into the ancient/medieval world, whoever happens to rank first today.
        reach = min(
            (seed_graph.node(n).midpoint_year or origin)
            for result in journeys
            for n in result.path.node_ids
        )
        assert origin - reach >= 500, f"{astronomer} reached only back to {reach}"


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


def test_divine_descent_cluster_links_monarchs_to_mythic_ancestors(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0026: the divine-descent cluster rides `claimed_descent_from` to connect modern monarchs
    # to mythic ancestors, anchoring on nodes the graph already had — Odin (Norse cluster) and Japan
    # (via Shinto). These are the lineage TILs: Elizabeth II's line runs back to Odin, and the
    # Japanese imperial line to the sun goddess Amaterasu.
    elizabeth = discover(seed_graph, "Elizabeth II", top=3)
    assert elizabeth
    assert any("odin" in r.path.node_ids for r in elizabeth)

    naruhito = discover(seed_graph, "Naruhito", top=3)
    assert naruhito
    assert any("amaterasu" in r.path.node_ids for r in naruhito)

    # The Shinto bridge keeps the Japanese line attached to the existing Japan/East-Asia cluster.
    jimmu = discover(seed_graph, "Jimmu", top=5)
    assert jimmu
    reached: set[str] = set()
    for result in jimmu:
        reached |= set(result.path.node_ids)
    assert "japan" in reached


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
    # The two archetypes optimise different things, so each winner is scored on its own basis. A
    # swapped/collapsed `basis` (JOURNEY ranked by endpoint-unexpectedness, say) would fail these
    # score-formula checks even though each archetype still returns paths.
    journey = discover(seed_graph, "Euclid", archetype=Archetype.JOURNEY, top=1)
    unlikely = discover(seed_graph, "Euclid", archetype=Archetype.UNLIKELY, top=1)
    assert journey and unlikely

    assert journey[0].score == pytest.approx(journey[0].surprise * journey[0].trust)
    assert unlikely[0].score == pytest.approx(
        unlikely[0].endpoint_unexpectedness * unlikely[0].trust
    )
    # The improbable pair is short by construction; the journey is a full fixed-length 3-hop chain.
    assert unlikely[0].path.length <= MAX_HOPS_UNLIKELY
    assert journey[0].path.length == 3


def test_archetypes_never_return_the_same_path(seed_graph: KnowledgeGraph) -> None:
    # ADR 0027: the two archetypes are different delights (ADR 0007), so surfacing one path twice
    # under two labels is a bug — it happened for Roman Empire and Christianity while the ranges
    # overlapped at 3 hops. The journey [3,3] and the pair [1,2] are now disjoint by construction;
    # this locks that invariant (widening MAX_HOPS_UNLIKELY back to 3 would fail here).
    assert MAX_HOPS_UNLIKELY < MIN_HOPS_DEFAULT  # the ranges cannot overlap
    for topic in ("Roman Empire", "Christianity", "Great Wall of China", "Buddhism", "Silk Road"):
        journey = discover(seed_graph, topic, archetype=Archetype.JOURNEY, top=1)
        unlikely = discover(seed_graph, topic, archetype=Archetype.UNLIKELY, top=1)
        if journey and unlikely:
            assert journey[0].path.node_ids != unlikely[0].path.node_ids, topic


def test_renaissance_cluster_connects_via_antiquity_byzantium_and_chinese_paper(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0033: the Renaissance cluster is not an island — it re-enters the graph through three
    # independent bridges, asserted structurally (which hub is on the route) rather than by
    # hardcoded endpoint, since the seed's winners shift as it grows.
    renaissance_bridges = {"plato", "ancient_greece", "fall_of_constantinople", "printing_press"}
    journeys = discover(seed_graph, "Renaissance", top=5)
    assert journeys
    assert any(renaissance_bridges & set(r.path.node_ids) for r in journeys)

    # The classical bridge: humanism revived Plato (Ficino's Florentine Academy), so the culture
    # cluster reaches back into antiquity rather than terminating in Florence.
    humanism = discover(seed_graph, "Renaissance humanism", top=5)
    assert humanism
    assert any({"plato", "ancient_greece"} & set(r.path.node_ids) for r in humanism)

    # The cross-cultural bridge, and the cluster's best TIL: Gutenberg's press ran on paper — a
    # Chinese invention — so Europe's printing revolution routes back to China and the Silk Road.
    press = discover(seed_graph, "Printing press", top=5)
    assert press
    assert any("paper" in r.path.node_ids for r in press)


def test_renaissance_cluster_relieves_the_starved_classical_starts(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0033: `plato` and `constantinople` were "starved" — every destination within the pair's
    # 1-2 hop range was one their own Wikipedia article already links, so their top improbable pair
    # was a foregone conclusion (Plato -> Alexander, Constantinople -> Constantine). The cluster
    # gives each a genuinely unlinked destination to reach. This is the measured payoff, so it is
    # locked: `_assert_worlds_apart` requires the obvious neighbour not to *win*.
    for topic, node_id in (("Plato", "plato"), ("Constantinople", "constantinople")):
        pairs = discover(seed_graph, topic, archetype=Archetype.UNLIKELY, top=5)
        _assert_worlds_apart(seed_graph, node_id, pairs)


def test_south_southeast_asia_cluster_bridges_hellenistic_and_indo_european(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0038: the South/SE Asia cluster (Hinduism, Sanskrit, Maurya, Ashoka, Chola, Srivijaya,
    # Khmer, Angkor Wat, Borobudur) is not an island — it re-enters the graph through independent
    # bridges, asserted structurally (which hub is on the route) rather than by a hardcoded
    # endpoint, since the seed's winners shift as it grows.

    # Hellenistic bridge: Chandragupta founded the Maurya Empire in the wake of Alexander's Indus
    # campaign, so the Indian empire reaches the Greek world rather than terminating in India.
    maurya = discover(seed_graph, "Maurya Empire", top=5)
    assert maurya
    assert any("alexander_the_great" in r.path.node_ids for r in maurya)

    # The Indo-European language bridge — the cluster's best structural link: Sanskrit descends from
    # Proto-Indo-European, so the classical language of India reaches the Norse/Latin family (e.g.
    # Sanskrit → Proto-Indo-European → Norse mythology).
    sanskrit = discover(seed_graph, "Sanskrit", top=5)
    assert sanskrit
    assert any("proto_indo_european" in r.path.node_ids for r in sanskrit)

    # The maritime-trade bridge: the Chola and Srivijaya thalassocracies reach the wider Eurasian
    # world through the Silk Road hub, not just their own waters.
    for topic in ("Chola dynasty", "Srivijaya"):
        journeys = discover(seed_graph, topic, top=5)
        assert journeys, topic
        assert any("silk_road" in r.path.node_ids for r in journeys), topic

    # Angkor Wat's improbable partners are genuinely worlds apart from a Cambodian temple, not its
    # in-cluster neighbours — it reaches the Vedic/Indo-European myth world through Hinduism.
    pairs = discover(seed_graph, "Angkor Wat", archetype=Archetype.UNLIKELY, top=5)
    _assert_worlds_apart(seed_graph, "angkor_wat", pairs)


def test_culture_domain_is_populated_and_holds_no_harvest_fallout(
    seed_graph: KnowledgeGraph,
) -> None:
    # ADR 0032 split the harvest fallback out of `culture` into `other` precisely so a curated
    # culture cluster could land in a clean realm; ADR 0033 then populated it. Together they mean:
    # `culture` has real nodes, and no curated node ever carries the unclassified bucket.
    domains = {node.domain for node in seed_graph.nodes()}
    assert Domain.CULTURE in domains
    assert Domain.OTHER not in domains  # `other` is harvest-only, never curated
