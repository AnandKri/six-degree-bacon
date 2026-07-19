"""The connectivity sweep — ADR 0047's grow-vs-stop instrument, as a committed, tested tool.

ADR 0047 decided a brain grows by *connective tissue*, not node count, and that the decision to grow
or stop turns on two measured metrics. ADR 0049 and 0050 were each driven by running that measure
from a throwaway script; this module is its reproducible successor (ADR 0051).

For every start node in a brain it asks the two questions the stopping rule turns on:

1. **Improbable pair** — does the top gated ``UNLIKELY`` result land somewhere the start does *not*
   directly co-occur (a "good, non-obvious" pair), or only on an obvious directly-linked neighbour?
   And is *any* gated pair non-obvious at all (else the start is "starved" — its whole 1-2 hop
   neighbourhood is its own cluster, the degree-limited case ADR 0044 named).
2. **Journey** — how much cross-domain + cross-region surprise does the top ``JOURNEY`` carry? The
   median across starts is the second metric, and in a journey-led brain (temporal term quiet) it
   is *the* health signal.

Deterministic: it runs the ordinary :func:`~sdb.engine.pipeline.discover` over committed
co-occurrence, so it reproduces by hand and needs no network.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sdb.engine.pipeline import discover
from sdb.engine.surprise import score_surprise
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Archetype

_SWEEP_TOP = 25  # how many gated pairs to inspect per start when judging "is any pair non-obvious"


@dataclass(frozen=True)
class SweepReport:
    """Aggregate connectivity metrics for one brain — ADR 0047's grow-vs-stop signals.

    ``good_pairs``, ``obvious_pairs`` and ``nothing_gated`` partition every node (a node's top
    improbable pair is non-obvious, obvious, or absent); ``starved`` is the subset with *no* gated
    non-obvious pair anywhere in its neighbourhood, so it always sits within the union of
    ``obvious_pairs`` and ``nothing_gated`` and contains every ``nothing_gated`` node. Node ids, not
    counts, so a caller can name the pendants.
    """

    node_count: int
    good_pairs: tuple[str, ...]
    obvious_pairs: tuple[str, ...]
    nothing_gated: tuple[str, ...]
    starved: tuple[str, ...]
    no_journey: tuple[str, ...]
    median_domain_jumps: float
    median_region_jumps: float
    median_combined: float
    mean_combined: float

    @property
    def good_fraction(self) -> float:
        """Fraction of starts whose top improbable pair is gated and non-obvious (metric 1)."""
        return len(self.good_pairs) / self.node_count if self.node_count else 0.0


def _directly_cooccurs(links: Mapping[str, Sequence[str]], a: str, b: str) -> bool:
    """``link_strength >= 1``: either article links the other (the "obvious destination" test)."""
    return b in links.get(a, ()) or a in links.get(b, ())


def connectivity_sweep(
    graph: KnowledgeGraph,
    cooccurrence: Mapping[str, Sequence[str]],
    *,
    top: int = _SWEEP_TOP,
) -> SweepReport:
    """Run the per-start sweep over ``graph`` and return its aggregate :class:`SweepReport`.

    ``cooccurrence`` is the raw first-order link table (``load_cooccurrence``) — the same one the
    graph scores against — used here only to tell an *obvious* directly-linked destination from a
    genuinely non-obvious one.
    """
    good: list[str] = []
    obvious: list[str] = []
    nothing_gated: list[str] = []
    starved: list[str] = []
    no_journey: list[str] = []
    domain_jumps: list[float] = []
    region_jumps: list[float] = []

    for node in graph.nodes():
        nid = node.id
        pairs = discover(graph, nid, archetype=Archetype.UNLIKELY, top=top)
        if not pairs:
            nothing_gated.append(nid)
            starved.append(nid)
        else:
            top_end = pairs[0].path.node_ids[-1]
            (obvious if _directly_cooccurs(cooccurrence, nid, top_end) else good).append(nid)
            if all(_directly_cooccurs(cooccurrence, nid, p.path.node_ids[-1]) for p in pairs):
                starved.append(nid)

        journeys = discover(graph, nid, archetype=Archetype.JOURNEY, top=1)
        if journeys:
            surprise = score_surprise(graph, journeys[0].path)
            domain_jumps.append(surprise.domain_jumps)
            region_jumps.append(surprise.region_jumps)
        else:
            no_journey.append(nid)

    combined = [d + r for d, r in zip(domain_jumps, region_jumps, strict=True)]
    return SweepReport(
        node_count=len(good) + len(obvious) + len(nothing_gated),
        good_pairs=tuple(good),
        obvious_pairs=tuple(obvious),
        nothing_gated=tuple(nothing_gated),
        starved=tuple(starved),
        no_journey=tuple(no_journey),
        median_domain_jumps=statistics.median(domain_jumps) if domain_jumps else 0.0,
        median_region_jumps=statistics.median(region_jumps) if region_jumps else 0.0,
        median_combined=statistics.median(combined) if combined else 0.0,
        mean_combined=statistics.mean(combined) if combined else 0.0,
    )


def format_report(label: str, report: SweepReport) -> str:
    """Render a :class:`SweepReport` as a plain-text block for ``sdb sweep``."""
    n = report.node_count
    lines = [
        f"=== {label} — {n} nodes ===",
        "  IMPROBABLE PAIR (archetype=UNLIKELY, gated)",
        f"    good non-obvious top pair : {len(report.good_pairs):>3}/{n}  "
        f"({report.good_fraction:6.1%})   [ADR 0047 metric 1]",
        f"    obvious (direct) top pair : {len(report.obvious_pairs):>3}/{n}",
        f"    nothing gated             : {len(report.nothing_gated):>3}/{n}",
        f"    truly starved (no alt)    : {len(report.starved):>3}/{n}",
        "  JOURNEY (archetype=JOURNEY, gated)",
        f"    median domain_jumps       : {report.median_domain_jumps:.3f}",
        f"    median region_jumps       : {report.median_region_jumps:.3f}",
        f"    median (domain+region)    : {report.median_combined:.3f}   [ADR 0047 metric 2]",
        f"    mean   (domain+region)    : {report.mean_combined:.3f}",
    ]
    if report.starved:
        lines.append("    starved starts: " + ", ".join(report.starved))
    return "\n".join(lines)
