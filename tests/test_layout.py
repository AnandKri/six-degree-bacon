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


def _hull(points: list[Point]) -> list[Point]:
    """Andrew's monotone-chain convex hull (counter-clockwise), matching the map's own hull."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])  # noqa: E731
    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _in_hull(p: Point, poly: list[Point]) -> bool:
    """True if p is strictly inside the convex (CCW) polygon — right of any edge means outside."""
    if len(poly) < 3:
        return False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) < 0:
            return False
    return True


def _foreign_intrusions(layout: Mapping[str, Point], domain_of: Mapping[str, str]) -> int:
    """Count how many nodes fall inside a *different* domain's territory hull.

    A direct, chaos-robust proxy for territory overlap: a hull that swallows foreign nodes is one
    the eye reads as overlapping. Fewer intrusions == cleaner, more separated territories.
    """
    by_domain: dict[str, list[Point]] = defaultdict(list)
    for node_id, point in layout.items():
        by_domain[domain_of[node_id]].append(point)
    hulls = {domain: _hull(points) for domain, points in by_domain.items()}
    return sum(
        1
        for node_id, point in layout.items()
        for domain, hull in hulls.items()
        if domain_of[node_id] != domain and _in_hull(point, hull)
    )


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


def test_separation_reduces_territory_overlap(seed_graph: KnowledgeGraph) -> None:
    """The separation force spreads territories apart, so fewer foreign nodes intrude on a hull.

    Negative control for ADR 0040's other lever: holding cohesion at the shipped default, turning
    the separation force off lets more nodes fall inside a *different* domain's territory (more
    visual overlap) than leaving it on. Measured on foreign-node intrusions — a chaos-robust proxy
    for hull overlap — rather than an absolute coordinate, matching this suite's property style.
    """
    domain_of = {n.id: n.domain.value for n in seed_graph.nodes()}
    with_separation = _foreign_intrusions(compute_layout(seed_graph), domain_of)
    without = _foreign_intrusions(compute_layout(seed_graph, domain_separation=0.0), domain_of)
    assert with_separation < without


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


def test_single_node_domain_is_placed() -> None:
    """A lone node in its domain still lands at a finite point.

    Its domain centroid *is* itself, so the cohesion force is exactly zero (`compute_layout` relies
    on that rather than special-casing) — the risk being a 0/0 in the force term. Built here rather
    than read off the seed: this asserted "the seed has a single-node domain (art)" until ADR 0033
    added three more artists, at which point a real invariant failed for a reason that had nothing
    to do with it. Any domain count in the seed is incidental; the property is not.
    """
    nodes = (
        _node("a", Domain.HISTORY),
        _node("b", Domain.HISTORY),
        _node("lonely", Domain.ART),  # the only node in its domain
    )
    graph = KnowledgeGraph(nodes, (_stmt("a", "b"), _stmt("b", "lonely")))
    layout = compute_layout(graph)
    counts: dict[str, int] = defaultdict(int)
    for node in graph.nodes():
        counts[node.domain.value] += 1
    singletons = [n.id for n in graph.nodes() if counts[n.domain.value] == 1]
    assert singletons == ["lonely"]
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
