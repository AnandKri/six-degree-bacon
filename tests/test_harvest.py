"""Harvester behaviour over a fake, offline SPARQL client: k-hop reach, mapping, dedup, capping."""

from __future__ import annotations

from pathlib import Path

from sdb.harvest.client import EntityFacts, FakeSparqlClient, NeighborEdge, _fold_entities
from sdb.harvest.harvester import harvest
from sdb.harvest.snapshot import load_snapshot, save_snapshot
from sdb.schema.enums import Domain, Predicate, SourceType


def _client() -> FakeSparqlClient:
    return FakeSparqlClient(
        edges={
            "Q1": (
                NeighborEdge("P361", "Q2", "preferred", 2),  # part_of, referenced
                NeighborEdge("P155", "Q3", "normal", 0),  # follows, unreferenced
                NeighborEdge(
                    "P1343", "Q9", "normal", 0
                ),  # described-by-source (bibliographic; excluded)
                NeighborEdge("P361", "Q1", "normal", 0),  # self-loop, must be skipped
            ),
            "Q2": (NeighborEdge("P276", "Q4", "normal", 1),),  # located_in, one hop deeper
            "Q3": (NeighborEdge("P361", "Q1", "normal", 0),),  # back-edge to an existing node
        },
        facts={
            "Q1": EntityFacts("Q1", "Rome", "capital", ("Q515",), -753),  # city -> geography
            "Q2": EntityFacts("Q2", "Latin", "language", ("Q34770",)),  # language
            "Q3": EntityFacts("Q3", "Republic", instance_of=("Q3624078",)),  # sovereign state
            "Q4": EntityFacts("Q4", "Italy", instance_of=("Q6256",)),  # country -> geography
            "Q9": EntityFacts("Q9", "Encyclopedia"),
        },
    )


def test_one_hop_maps_edges_to_statements() -> None:
    seed = harvest(_client(), "Q1", hops=1)
    node_ids = {n.id for n in seed.nodes}
    assert node_ids == {
        "Q1",
        "Q2",
        "Q3",
    }  # self-loop added nothing; Q9 (via excluded P1343) dropped

    by_object = {(s.subject, s.object): s for s in seed.statements}
    assert ("Q1", "Q1") not in by_object  # self-loop skipped
    part_of = by_object[("Q1", "Q2")]
    assert part_of.predicate is Predicate.PART_OF
    assert part_of.link_quality == 1.0  # QID endpoints are canonical
    # Referenced + preferred -> WIKIDATA_WITH_REF at full reliability.
    assert part_of.sources[0].source_type is SourceType.WIKIDATA_WITH_REF
    assert part_of.sources[0].reliability == 1.0 * 0.90


def test_two_hops_expand_frontier_and_dedup_back_edges() -> None:
    seed = harvest(_client(), "Q1", hops=2)
    node_ids = {n.id for n in seed.nodes}
    assert node_ids == {"Q1", "Q2", "Q3", "Q4"}  # Q4 reached at hop 2; Q9 excluded
    edges = {(s.subject, s.object) for s in seed.statements}
    assert ("Q2", "Q4") in edges  # deeper hop
    assert ("Q3", "Q1") in edges  # back-edge kept (distinct statement), no duplicate node


def test_node_enrichment_maps_domain_and_dates() -> None:
    nodes = {n.id: n for n in harvest(_client(), "Q1", hops=2).nodes}
    assert nodes["Q1"].domain is Domain.GEOGRAPHY  # city
    assert nodes["Q1"].start_year == -753
    assert nodes["Q1"].end_year is None  # a city has no dissolution/death date
    assert nodes["Q2"].domain is Domain.LANGUAGE
    assert nodes["Q1"].wikidata_qid == "Q1"


def test_people_and_dissolved_entities_get_full_extents() -> None:
    # A person is dated by birth/death (P569/P570); a state by inception/dissolution (P571/P576).
    client = FakeSparqlClient(
        edges={"Q100": (NeighborEdge("P737", "Q200", "normal", 1),)},  # influenced_by
        facts={
            "Q100": EntityFacts(
                "Q100", "Euclid", "mathematician", ("Q5",), birth_year=-323, death_year=-283
            ),
            "Q200": EntityFacts(
                "Q200",
                "Roman Empire",
                "empire",
                ("Q48349",),
                inception_year=-27,
                dissolved_year=476,
            ),
        },
    )
    nodes = {n.id: n for n in harvest(client, "Q100", hops=1).nodes}
    assert (nodes["Q100"].start_year, nodes["Q100"].end_year) == (-323, -283)  # birth, death
    assert nodes["Q100"].domain is Domain.HISTORY  # human
    assert (nodes["Q200"].start_year, nodes["Q200"].end_year) == (-27, 476)  # inception, dissolved
    assert nodes["Q200"].midpoint_year == (-27 + 476) / 2.0  # extent now feeds temporal surprise


def test_fold_entities_picks_earliest_start_latest_end_deterministically() -> None:
    # A multi-valued item (e.g. disputed birth) must fold the same regardless of SPARQL row order.
    def row(qid: str, key: str, value: str) -> dict[str, dict[str, str]]:
        return {"item": {"value": f"http://www.wikidata.org/entity/{qid}"}, key: {"value": value}}

    rows = [
        row("Q1", "birth", "-100"),
        row("Q1", "birth", "-90"),  # later birth claim; earliest must win
        row("Q1", "death", "-40"),
        row("Q1", "death", "-45"),  # earlier death claim; latest must win
    ]
    facts = _fold_entities(rows)
    assert (facts["Q1"].birth_year, facts["Q1"].death_year) == (-100, -40)
    assert _fold_entities(list(reversed(rows))) == facts  # order-independent


def test_described_by_source_clutter_is_excluded() -> None:
    # P1343 ("described by source") is bibliographic clutter: neither its edge nor the reference
    # work it drags in (Q9) is harvested, at any depth.
    seed = harvest(_client(), "Q1", hops=2)
    assert "Q9" not in {n.id for n in seed.nodes}
    assert all(s.predicate is not Predicate.MENTIONED_IN for s in seed.statements)


def test_max_neighbors_caps_structural_edges_deterministically() -> None:
    # With a cap of 1, the first structural edge in (property, target) order is kept.
    seed = harvest(_client(), "Q1", hops=1, max_neighbors=1)
    subjects_objects = {(s.subject, s.object) for s in seed.statements}
    assert subjects_objects == {("Q1", "Q3")}  # P155->Q3 sorts before P361->Q2


def test_snapshot_round_trips(tmp_path: Path) -> None:
    harvested = harvest(_client(), "Q1", hops=2)
    written = save_snapshot(harvested, tmp_path / "harvest" / "q1.json")
    assert written.exists()
    assert load_snapshot(written) == harvested  # pinned snapshot reproduces the harvest exactly
