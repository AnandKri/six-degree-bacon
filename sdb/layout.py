"""Deterministic force-directed layout for the bird's-eye map (ADR 0030).

The map view needs 2-D coordinates for every node, grouped so that same-domain nodes form visible
territories (à la musicmap.info) while edges pull related nodes together. This is computed here — a
pure, dependency-free (no numpy) force-directed layout that is **byte-identical every run, on every
platform**, so the map is as reproducible as every score in the engine.

Determinism is a proof, not a hope: every operation is one of ``+ - * / sqrt``, all of which
IEEE-754 mandates be correctly rounded (unlike ``sin``/``cos``, which libm implementations may round
differently — so the initial ring is a *square* perimeter, computed with arithmetic alone). Nodes
are visited in a fixed ``(domain, id)`` order — never dict/set iteration order, never ``hash()`` —
and coordinates are rounded to :data:`COORDINATE_PRECISION` places. Layout affects *pixels only*; it
can never change a trust or surprise score, so a hypothetical last-bit drift would nudge a
coordinate, not a result.

The algorithm is Fruchterman-Reingold (all-pairs repulsion ``k^2/d`` + edge attraction ``d^2/k``)
plus two shaping forces: a **domain-centroid cohesion** that draws each node toward the mean
position of its domain (what forms territories, and why a 63%-cross-domain graph clusters), and a
weak **gravity** toward the origin that keeps disconnected components and isolates in frame. Cost is
O(N^2 * iterations); at the seed's 88 nodes this is well under a second, run once at ``sdb serve``
startup and once per ``sdb build-site``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Domain

# --- Layout constants (presentation only; affect no score) -------------------------------------
VIEWBOX_SIZE = 1000.0  # coordinates are normalized into [0, VIEWBOX_SIZE]
VIEWBOX_MARGIN = 30.0  # keep nodes this far from the viewBox edge
LAYOUT_ITERATIONS = 320  # cohesion plateaus by ~100; 3x headroom (see ADR 0030)
DOMAIN_COHESION = 2.4  # a domain pulls as hard as ~2.4 edges (ADR 0040 raised it from 1.0). ADR
#   0030 swept cohesion *alone* and found >2 blobs; with DOMAIN_SEPARATION now sharing the work the
#   operating point moved — 2.4 tightens territories without collapsing them (every domain still
#   passes the per-domain cohesion test; edge/all length ratio 0.40 > the 0.34 baseline, i.e.
#   bridges are expressed, not sucked in — the blob signature is the ratio *dropping*, and it rose).
DOMAIN_SEPARATION = 8.0  # centroid-vs-centroid repulsion that spreads whole territories apart so
#   their hulls stop overlapping (ADR 0040). With cohesion it cuts hull overlap ~33%->~16% while
#   keeping cross-domain edges expressed; the exact value is one point in a robustly-good band (the
#   layout is chaotic — ADR 0030 — so no decimal is "optimal", the region is what's earned)
GRAVITY = 0.012  # centre-ward pull; the disconnected-component / isolate fix, not decoration
INITIAL_TEMPERATURE_FRACTION = 0.06  # T0 = fraction * VIEWBOX_SIZE; linear cooling to 0
INIT_RADIUS = 350.0  # half-size of the square-perimeter seed ring
INIT_RADIUS_JITTER = 0.25  # golden-ratio radial modulation, to break symmetric equilibria
GOLDEN_RATIO_CONJUGATE = 0.6180339887498949  # φ⁻¹, a low-discrepancy sequence with no PRNG
MIN_SEPARATION_SQUARED = 1e-6  # floor on squared distance, so coincident nodes never divide by zero
COORDINATE_PRECISION = 2  # rounding places — cosmetic (payload size / tidy SVG), not the guard


def _square_perimeter(fraction: float) -> tuple[float, float]:
    """Map ``fraction`` in ``[0, 1)`` to a point on a centred square of half-size ``INIT_RADIUS``.

    A closed loop, like a circle, but computed with only ``+ - * /`` so the initial positions are
    bit-identical across platforms (``sin``/``cos`` are not IEEE-correctly-rounded).
    """
    side_position = fraction * 4.0
    side = int(side_position)
    along = side_position - side
    r = INIT_RADIUS
    span = 2.0 * r * along
    if side == 0:
        return (-r + span, -r)
    if side == 1:
        return (r, -r + span)
    if side == 2:
        return (r - span, r)
    return (-r, r - span)


def _initial_positions(ordered_ids: list[str]) -> tuple[list[float], list[float]]:
    """Seed positions on the square perimeter in ``(domain, id)`` order, so domains start as arcs.

    A golden-ratio radial jitter (deterministic, no PRNG) nudges each node off the exact perimeter,
    breaking the symmetric configurations a force layout can otherwise stall in.
    """
    count = len(ordered_ids)
    xs: list[float] = [0.0] * count
    ys: list[float] = [0.0] * count
    for i in range(count):
        modulation = 1.0 - INIT_RADIUS_JITTER * ((i * GOLDEN_RATIO_CONJUGATE) % 1.0)
        px, py = _square_perimeter(i / count)
        xs[i] = px * modulation
        ys[i] = py * modulation
    return xs, ys


def _unique_edges(graph: KnowledgeGraph, index: Mapping[str, int]) -> list[tuple[int, int]]:
    """Undirected edge index-pairs, de-duplicated (parallel statements collapse) and self-loop-free.

    Layout expresses topology; corroboration (a second statement for the same pair) is the trust
    score's concern, so a pair is pulled together the same whether one edge or three connect it.
    """
    pairs: set[tuple[int, int]] = set()
    for statement in graph.statements:
        a, b = index[statement.subject], index[statement.object]
        if a != b:
            pairs.add((a, b) if a < b else (b, a))
    return sorted(pairs)


def compute_layout(
    graph: KnowledgeGraph,
    *,
    iterations: int = LAYOUT_ITERATIONS,
    domain_cohesion: float = DOMAIN_COHESION,
    domain_separation: float = DOMAIN_SEPARATION,
    viewbox: float = VIEWBOX_SIZE,
    margin: float = VIEWBOX_MARGIN,
    precision: int = COORDINATE_PRECISION,
) -> dict[str, tuple[float, float]]:
    """Compute deterministic 2-D coordinates for every node, clustered by domain.

    Args:
        graph: The knowledge graph to lay out.
        iterations: Number of cooling iterations (the default is well past convergence).
        domain_cohesion: Strength of the same-domain pull; ``0.0`` disables territory formation
            (used as a negative control in the tests).
        domain_separation: Strength of the centroid-vs-centroid push that spreads territories apart
            so their hulls stop overlapping (ADR 0040); ``0.0`` disables it (negative control).
        viewbox: Coordinates are normalized into ``[0, viewbox]`` on both axes.
        margin: Minimum distance kept between nodes and the viewBox edge.
        precision: Decimal places coordinates are rounded to.

    Returns:
        A mapping ``{node_id: (x, y)}`` in ``(domain, id)`` insertion order, so ``json.dumps`` of it
        is byte-stable. Empty for an empty graph; a lone node lands at the centre.
    """
    domain_index = {domain: i for i, domain in enumerate(Domain)}
    ordered = sorted(graph.nodes(), key=lambda n: (domain_index[n.domain], n.id))
    ordered_ids = [n.id for n in ordered]
    count = len(ordered_ids)
    if count == 0:
        return {}
    if count == 1:
        return {ordered_ids[0]: (round(viewbox / 2, precision), round(viewbox / 2, precision))}

    index = {node_id: i for i, node_id in enumerate(ordered_ids)}
    edges = _unique_edges(graph, index)

    members_by_domain: dict[Domain, list[int]] = {}
    for i, node in enumerate(ordered):
        members_by_domain.setdefault(node.domain, []).append(i)

    xs, ys = _initial_positions(ordered_ids)
    ideal = math.sqrt(viewbox * viewbox / count)  # Fruchterman-Reingold ideal edge length k
    temperature0 = INITIAL_TEMPERATURE_FRACTION * viewbox

    for step in range(iterations):
        temperature = temperature0 * (1.0 - step / iterations)
        dx = [0.0] * count
        dy = [0.0] * count

        # Repulsion between every pair: f = k² / d.
        for i in range(count):
            xi, yi = xs[i], ys[i]
            for j in range(i + 1, count):
                ddx = xi - xs[j]
                ddy = yi - ys[j]
                dist2 = ddx * ddx + ddy * ddy
                if dist2 < MIN_SEPARATION_SQUARED:
                    dist2 = MIN_SEPARATION_SQUARED
                dist = math.sqrt(dist2)
                force = (ideal * ideal) / dist
                fx = ddx / dist * force
                fy = ddy / dist * force
                dx[i] += fx
                dy[i] += fy
                dx[j] -= fx
                dy[j] -= fy

        # Attraction along each unique edge: f = d² / k.
        for a, b in edges:
            ddx = xs[a] - xs[b]
            ddy = ys[a] - ys[b]
            dist = math.sqrt(ddx * ddx + ddy * ddy) + 1e-9
            force = (dist * dist) / ideal
            fx = ddx / dist * force
            fy = ddy / dist * force
            dx[a] -= fx
            dy[a] -= fy
            dx[b] += fx
            dy[b] += fy

        # Domain-centroid cohesion: f = domain_cohesion * d^2 / k toward the domain's mean position.
        # A single-node domain has centroid == itself, so its force is exactly zero (no special
        # case is needed for it).
        for members in members_by_domain.values():
            size = len(members)
            if size < 2:
                continue
            cx = sum(xs[i] for i in members) / size
            cy = sum(ys[i] for i in members) / size
            for i in members:
                ddx = cx - xs[i]
                ddy = cy - ys[i]
                dist = math.sqrt(ddx * ddx + ddy * ddy)
                if dist < 1e-9:
                    continue
                force = domain_cohesion * (dist * dist) / ideal
                dx[i] += ddx / dist * force
                dy[i] += ddy / dist * force

        # Domain-centroid separation: repel each domain's centroid from every other, then push the
        # whole domain by that one vector (the same displacement to every member). The counterpart
        # to cohesion — cohesion tightens a territory, separation spreads territories apart so their
        # convex hulls stop overlapping (ADR 0040). Rigid per domain, so internal shape is intact;
        # inverse-distance (k^2/d, the node-repulsion law at territory scale) so far-apart domains
        # barely feel it and only the cramped centre is pried open. Iterate the sorted-domain order
        # already fixed by `members_by_domain`, so this stays deterministic.
        if domain_separation > 0.0:
            centroids = []
            for members in members_by_domain.values():
                size = len(members)
                cx = sum(xs[i] for i in members) / size
                cy = sum(ys[i] for i in members) / size
                centroids.append((members, cx, cy))
            for p in range(len(centroids)):
                members_p, cxp, cyp = centroids[p]
                for query in range(p + 1, len(centroids)):
                    members_q, cxq, cyq = centroids[query]
                    ddx = cxp - cxq
                    ddy = cyp - cyq
                    dist2 = ddx * ddx + ddy * ddy
                    if dist2 < MIN_SEPARATION_SQUARED:
                        dist2 = MIN_SEPARATION_SQUARED
                    dist = math.sqrt(dist2)
                    force = domain_separation * (ideal * ideal) / dist
                    fx = ddx / dist * force
                    fy = ddy / dist * force
                    for i in members_p:
                        dx[i] += fx
                        dy[i] += fy
                    for i in members_q:
                        dx[i] -= fx
                        dy[i] -= fy

        # Gravity toward the origin: keeps islands and isolates from being repelled out of frame.
        for i in range(count):
            dist = math.sqrt(xs[i] * xs[i] + ys[i] * ys[i])
            if dist > 1e-9:
                force = GRAVITY * dist
                dx[i] -= xs[i] / dist * force
                dy[i] -= ys[i] / dist * force

        # Apply the cooled displacement (capped at the current temperature).
        for i in range(count):
            disp = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i])
            if disp > 1e-9:
                capped = min(disp, temperature)
                xs[i] += dx[i] / disp * capped
                ys[i] += dy[i] / disp * capped

    return _normalize(ordered_ids, xs, ys, viewbox, margin, precision)


def _normalize(
    ordered_ids: list[str],
    xs: list[float],
    ys: list[float],
    viewbox: float,
    margin: float,
    precision: int,
) -> dict[str, tuple[float, float]]:
    """Fit positions into ``[margin, viewbox - margin]`` with a single uniform scale, then round.

    One scale for both axes (never per-axis) so clusters keep their shape rather than stretch into
    ellipses. Adding ``0.0`` after rounding collapses a ``-0.0`` (which ``round`` can produce) to
    ``0.0``, keeping the JSON serialization byte-stable.
    """
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny, 1e-9)
    inner = viewbox - 2.0 * margin
    scale = inner / span
    offset_x = margin + (inner - (maxx - minx) * scale) / 2.0
    offset_y = margin + (inner - (maxy - miny) * scale) / 2.0
    layout: dict[str, tuple[float, float]] = {}
    for i, node_id in enumerate(ordered_ids):
        x = round((xs[i] - minx) * scale + offset_x, precision) + 0.0
        y = round((ys[i] - miny) * scale + offset_y, precision) + 0.0
        layout[node_id] = (x, y)
    return layout
