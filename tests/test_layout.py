"""Deterministic layout: reproducibility, bounds, and the cohesion property (ADR 0030).

The claims are checked as invariants over the real seed plus small constructed graphs (no hardcoded
coordinates), matching the project's property-based style — a coordinate table would lock in noise.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping

from sdb.graph.build import KnowledgeGraph
from sdb.layout import VIEWBOX_MARGIN, VIEWBOX_SIZE, compute_layout
from sdb.schema.enums import Domain, Predicate, SourceType
from sdb.schema.models import Node, Source, Statement

Point = tuple[float, float]


def _node(node_id: str, domain: Domain = Domain.HISTORY) -> Node:
    return Node(id=node_id, label=node_id.title(), domain=domain, type="x")


def _stmt(subject: str, obj: str, predicate: Predicate = Predicate.PART_OF) -> Statement:
    return Statement(
        subject=subject,
        predicate=predicate,
        object=obj,
        sources=(Source(id="w", source_type=SourceType.WIKIPEDIA),),
    )


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pairwise(layout: Mapping[str, Point]) -> list[tuple[str, str, float]]:
    ids = list(layout)
    return [
        (ids[i], ids[j], _dist(layout[ids[i]], layout[ids[j]]))
        for i in range(len(ids))
        for j in range(i + 1, len(ids))
    ]


def _cohesion_ratio(layout: Mapping[str, Point], domain_of: Mapping[str, str]) -> float:
    """Mean intra-domain pairwise distance / mean inter-domain — < 1 means domains cluster."""
    intra = [d for a, b, d in _pairwise(layout) if domain_of[a] == domain_of[b]]
    inter = [d for a, b, d in _pairwise(layout) if domain_of[a] != domain_of[b]]
    return (sum(intra) / len(intra)) / (sum(inter) / len(inter))


# --- determinism -------------------------------------------------------------------------------
def test_layout_is_deterministic(seed_graph: KnowledgeGraph) -> None:
    first = compute_layout(seed_graph)
    second = compute_layout(seed_graph)
    assert first == second  # exact equality, not approx — reproducibility is the whole point
    assert json.dumps(first) == json.dumps(second)  # byte-stable serialization (ordered keys)


def test_layout_ignores_input_ordering() -> None:
    nodes = (
        _node("a", Domain.HISTORY),
        _node("b", Domain.HISTORY),
        _node("c", Domain.MYTH),
        _node("d", Domain.MYTH),
    )
    statements = (_stmt("a", "b"), _stmt("b", "c"), _stmt("c", "d"))
    forward = compute_layout(KnowledgeGraph(nodes, statements))
    reversed_ = compute_layout(KnowledgeGraph(tuple(reversed(nodes)), tuple(reversed(statements))))
    assert forward == reversed_  # the (domain, id) sort decides, not insertion / set order


# --- bounds & sanity ---------------------------------------------------------------------------
def test_coordinates_stay_within_the_inner_viewbox(seed_graph: KnowledgeGraph) -> None:
    lo, hi = VIEWBOX_MARGIN - 0.01, VIEWBOX_SIZE - VIEWBOX_MARGIN + 0.01
    for x, y in compute_layout(seed_graph).values():
        assert lo <= x <= hi and lo <= y <= hi


def test_coordinates_are_finite(seed_graph: KnowledgeGraph) -> None:
    assert all(
        math.isfinite(x) and math.isfinite(y) for x, y in compute_layout(seed_graph).values()
    )


def test_layout_covers_every_node_exactly_once(seed_graph: KnowledgeGraph) -> None:
    layout = compute_layout(seed_graph)
    assert set(layout) == {n.id for n in seed_graph.nodes()}


def test_precision_is_respected(seed_graph: KnowledgeGraph) -> None:
    for x, y in compute_layout(seed_graph).values():
        assert x == round(x, 2) and y == round(y, 2)


def test_no_collapse_and_fills_the_frame(seed_graph: KnowledgeGraph) -> None:
    layout = compute_layout(seed_graph)
    assert min(d for _a, _b, d in _pairwise(layout)) > 1.0  # no two nodes coincide
    xs = [p[0] for p in layout.values()]
    ys = [p[1] for p in layout.values()]
    inner = VIEWBOX_SIZE - 2 * VIEWBOX_MARGIN
    assert max(max(xs) - min(xs), max(ys) - min(ys)) == round(
        inner, 2
    )  # uniform scale fills a side


# --- the cohesion property (territories form) --------------------------------------------------
def test_same_domain_nodes_cluster(seed_graph: KnowledgeGraph) -> None:
    domain_of = {n.id: n.domain.value for n in seed_graph.nodes()}
    assert _cohesion_ratio(compute_layout(seed_graph), domain_of) < 0.75


def test_every_multi_node_domain_is_cohesive(seed_graph: KnowledgeGraph) -> None:
    # Aggregate cohesion can hide one scattered domain; check each |D| >= 3 domain against the
    # global mean. (Domains of 1-2 nodes, and trade's cross-cutting hubs, legitimately spread.)
    layout = compute_layout(seed_graph)
    domain_of = {n.id: n.domain.value for n in seed_graph.nodes()}
    global_mean = sum(d for _a, _b, d in _pairwise(layout)) / len(_pairwise(layout))
    by_domain: dict[str, list[Point]] = defaultdict(list)
    for node_id, point in layout.items():
        by_domain[domain_of[node_id]].append(point)
    for domain, points in by_domain.items():
        if len(points) < 3:
            continue
        dists = [
            _dist(points[i], points[j])
            for i in range(len(points))
            for j in range(i + 1, len(points))
        ]
        assert sum(dists) / len(dists) < global_mean, f"{domain} did not cluster"


def test_cohesion_term_is_necessary(seed_graph: KnowledgeGraph) -> None:
    # Negative control: with the force, domains cluster; disabling it, they do not.
    domain_of = {n.id: n.domain.value for n in seed_graph.nodes()}
    assert _cohesion_ratio(compute_layout(seed_graph), domain_of) < 0.75
    assert _cohesion_ratio(compute_layout(seed_graph, domain_cohesion=0.0), domain_of) > 0.75


def test_connected_nodes_are_closer_than_unconnected(seed_graph: KnowledgeGraph) -> None:
    layout = compute_layout(seed_graph)
    linked = {
        (s.subject, s.object) if s.subject < s.object else (s.object, s.subject)
        for s in seed_graph.statements
        if s.subject != s.object
    }
    edge_d = [_dist(layout[a], layout[b]) for a, b in linked]
    all_d = [d for _a, _b, d in _pairwise(layout)]
    assert sum(edge_d) / len(edge_d) < sum(all_d) / len(all_d)  # attraction still does its job


# --- edge cases --------------------------------------------------------------------------------
def test_empty_graph_returns_empty() -> None:
    assert compute_layout(KnowledgeGraph((), ())) == {}


def test_single_node_lands_at_centre() -> None:
    layout = compute_layout(KnowledgeGraph((_node("solo"),), ()))
    assert layout == {"solo": (VIEWBOX_SIZE / 2, VIEWBOX_SIZE / 2)}


def test_two_node_graph_produces_no_nan() -> None:
    layout = compute_layout(KnowledgeGraph((_node("a"), _node("b")), (_stmt("a", "b"),)))
    assert len(layout) == 2
    (ax, ay), (bx, by) = layout["a"], layout["b"]
    assert all(math.isfinite(v) for v in (ax, ay, bx, by))
    assert (ax, ay) != (bx, by)  # repulsion separates them


def test_single_node_domain_is_placed(seed_graph: KnowledgeGraph) -> None:
    layout = compute_layout(seed_graph)
    counts: dict[str, int] = defaultdict(int)
    for node in seed_graph.nodes():
        counts[node.domain.value] += 1
    singletons = [n.id for n in seed_graph.nodes() if counts[n.domain.value] == 1]
    assert singletons  # the seed has at least one single-node domain (art)
    for node_id in singletons:
        x, y = layout[node_id]
        assert math.isfinite(x) and math.isfinite(y)


def test_isolated_nodes_and_disconnected_components_stay_in_view() -> None:
    nodes = (
        _node("a"),
        _node("b"),
        _node("c"),  # component 1: a-b-c
        _node("d"),
        _node("e"),  # component 2: d-e
        _node("lonely"),  # isolate: no edges at all
    )
    statements = (_stmt("a", "b"), _stmt("b", "c"), _stmt("d", "e"))
    layout = compute_layout(KnowledgeGraph(nodes, statements))
    lo, hi = VIEWBOX_MARGIN - 0.01, VIEWBOX_SIZE - VIEWBOX_MARGIN + 0.01
    for x, y in layout.values():  # gravity keeps every island and isolate on-screen
        assert lo <= x <= hi and lo <= y <= hi


def test_parallel_edges_do_not_change_layout() -> None:
    nodes = (_node("a"), _node("b"), _node("c"))
    single = compute_layout(KnowledgeGraph(nodes, (_stmt("a", "b"), _stmt("b", "c"))))
    doubled = compute_layout(
        KnowledgeGraph(
            nodes, (_stmt("a", "b"), _stmt("a", "b", Predicate.FOLLOWS), _stmt("b", "c"))
        )
    )
    assert single == doubled  # layout expresses topology; corroboration is the trust score's job
