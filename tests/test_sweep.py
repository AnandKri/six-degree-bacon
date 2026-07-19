"""The connectivity sweep (ADR 0051): the report's derived fields + its partition invariants."""

from __future__ import annotations

from pathlib import Path

from sdb.graph.loader import load_cooccurrence, load_graph
from sdb.sweep import SweepReport, connectivity_sweep, format_report

_TC = Path(__file__).resolve().parent.parent / "data" / "brains" / "twentieth_century"


def _report(**overrides: object) -> SweepReport:
    """A zeroed :class:`SweepReport` with fields overridden, for the pure derived-field tests."""
    fields: dict[str, object] = {
        "node_count": 0,
        "good_pairs": (),
        "obvious_pairs": (),
        "nothing_gated": (),
        "starved": (),
        "no_journey": (),
        "median_domain_jumps": 0.0,
        "median_region_jumps": 0.0,
        "median_combined": 0.0,
        "mean_combined": 0.0,
    }
    fields.update(overrides)
    return SweepReport(**fields)  # type: ignore[arg-type]


def test_good_fraction_and_format() -> None:
    report = _report(
        node_count=4, good_pairs=("a", "b", "c"), obvious_pairs=("d",), median_combined=1.1
    )
    assert report.good_fraction == 0.75
    text = format_report("Test", report)
    assert "3/4" in text and "75.0%" in text and "1.100" in text


def test_good_fraction_empty_brain_is_zero() -> None:
    assert _report().good_fraction == 0.0  # no division by zero on an empty brain


def test_connectivity_sweep_partitions_every_node() -> None:
    """The three top-pair buckets partition every node exactly once, and ``starved`` is the no-alt
    subset of {obvious, nothing_gated} — never a good start. These are invariants of the sweep
    logic, asserted against a real brain rather than pinned numbers (which shift with the seed).
    """
    graph = load_graph(_TC / "seed.json", _TC / "cooccurrence.json")
    links = load_cooccurrence(_TC / "cooccurrence.json")
    report = connectivity_sweep(graph, links)

    ids = {node.id for node in graph.nodes()}
    buckets = [set(report.good_pairs), set(report.obvious_pairs), set(report.nothing_gated)]
    assert set().union(*buckets) == ids  # every node classified
    assert sum(len(bucket) for bucket in buckets) == len(ids)  # disjoint
    assert report.node_count == len(ids)
    assert 0.0 <= report.good_fraction <= 1.0

    starved = set(report.starved)
    assert set(report.nothing_gated) <= starved  # a start with no gated pair is starved
    assert starved <= set(report.obvious_pairs) | set(report.nothing_gated)  # never a good start
    assert report.median_domain_jumps >= 0.0
    assert report.median_combined >= 0.0
