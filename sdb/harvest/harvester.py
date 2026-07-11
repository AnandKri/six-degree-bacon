"""Harvest a k-hop Wikidata neighbourhood into the typed :class:`~sdb.schema.models.SeedData`.

Breadth-first from a seed QID, following only the curated predicate set, this turns raw Wikidata
statements into reified :class:`~sdb.schema.models.Statement` records whose provenance carries the
deterministic rank/reference-derived reliability. Endpoints resolve to canonical Wikidata QIDs, so
``link_quality`` is ``1.0`` (no fuzzy entity linking needed).
"""

from __future__ import annotations

from sdb.harvest.client import EntityFacts, NeighborEdge, SparqlClient
from sdb.harvest.mapping import (
    HARVEST_EXCLUDED_PROPERTIES,
    WIKIDATA_PREDICATE,
    domain_for,
    make_source,
    temporal_extent,
)
from sdb.schema.models import Node, SeedData, Statement

HARVEST_LINK_QUALITY = 1.0  # QID-resolved endpoints are canonical; no fuzzy matching is involved.


def _is_harvestable(edge: NeighborEdge, subject: str) -> bool:
    """Whether an edge is a curated, non-excluded, non-self relation worth harvesting."""
    return (
        edge.property_pid in WIKIDATA_PREDICATE
        and edge.property_pid not in HARVEST_EXCLUDED_PROPERTIES
        and edge.target_qid != subject
    )


def harvest(
    client: SparqlClient,
    seed_qid: str,
    hops: int,
    *,
    max_neighbors: int | None = None,
) -> SeedData:
    """Harvest the neighbourhood within ``hops`` edges of ``seed_qid`` into a :class:`SeedData`.

    Args:
        client: The (live or offline) fact source.
        seed_qid: The Wikidata QID to start from (e.g. ``"Q2277"``).
        hops: Number of expansion rounds; ``hops=2`` reaches nodes two edges from the seed.
        max_neighbors: Optional per-node cap on curated edges (taken in the client's deterministic
            order) to keep high-degree hubs from exploding the harvest.

    Returns:
        A validated :class:`SeedData`; node ids are the QIDs, statements carry Wikidata-derived
        sources. The result is deterministic given the client's responses.
    """
    discovered: dict[str, None] = {seed_qid: None}  # insertion-ordered set of QIDs
    edges: list[tuple[str, NeighborEdge]] = []
    seen: set[tuple[str, str, str]] = set()
    frontier: list[str] = [seed_qid]

    for _ in range(hops):
        next_frontier: list[str] = []
        for subject in frontier:
            taken = 0
            ordered = sorted(
                client.neighbors(subject), key=lambda e: (e.property_pid, e.target_qid)
            )
            for edge in ordered:
                if not _is_harvestable(edge, subject):
                    continue
                if max_neighbors is not None and taken >= max_neighbors:
                    break
                taken += 1
                key = (subject, edge.property_pid, edge.target_qid)
                if key in seen:
                    continue
                seen.add(key)
                edges.append((subject, edge))
                if edge.target_qid not in discovered:
                    discovered[edge.target_qid] = None
                    next_frontier.append(edge.target_qid)
        frontier = next_frontier

    facts = client.entities(list(discovered))
    nodes = tuple(_node(facts.get(qid) or EntityFacts(qid=qid, label=qid)) for qid in discovered)
    statements = tuple(_statement(subject, edge) for subject, edge in edges)
    return SeedData(nodes=nodes, statements=statements)


def _node(facts: EntityFacts) -> Node:
    """Build a :class:`Node` from harvested entity facts.

    Domain comes from the P31→Domain table; the temporal extent folds inception/birth (start) and
    dissolution/death (end) so people are dated too. ``time_precision`` is left unset: it is not
    consumed by any score, and reading it would need a heavier per-statement precision query.
    """
    start_year, end_year = temporal_extent(
        inception_year=facts.inception_year,
        birth_year=facts.birth_year,
        death_year=facts.death_year,
        dissolved_year=facts.dissolved_year,
    )
    return Node(
        id=facts.qid,
        label=facts.label,
        domain=domain_for(facts.instance_of),
        type=facts.instance_of[0] if facts.instance_of else "entity",
        wikidata_qid=facts.qid,
        summary=facts.description,
        start_year=start_year,
        end_year=end_year,
        time_precision=None,
    )


def _statement(subject: str, edge: NeighborEdge) -> Statement:
    """Build a reified :class:`Statement` from a harvested edge, with its Wikidata source."""
    predicate = WIKIDATA_PREDICATE[edge.property_pid]
    source = make_source(
        subject, edge.property_pid, edge.target_qid, edge.rank, edge.reference_count
    )
    return Statement(
        subject=subject,
        predicate=predicate,
        object=edge.target_qid,
        sources=(source,),
        evidence=f"Wikidata: {subject} {edge.property_pid} {edge.target_qid}.",
        link_quality=HARVEST_LINK_QUALITY,
    )
