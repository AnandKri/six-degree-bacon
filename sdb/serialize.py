"""Shared JSON serialization for :class:`~sdb.schema.models.DiscoveryResult`.

The CLI (``discover --json``) and the web API render the same result object and had drifted into two
near-identical serializers, each with its own copy of the source de-duplication — so a new field on
``DiscoveryResult`` had to be remembered in two places. This module owns the part they agree on.

What they legitimately *don't* share stays with each caller: the CLI adds ``rank`` and a flat
``path`` of labels, the web adds a per-hop ``chain`` with phrasing for the card. Rounding is a
parameter rather than a fixed choice because the two surfaces have different jobs — the CLI's
``--json`` is machine-facing and keeps 4 dp, the web card is display-facing and keeps 2-3 dp.

:func:`result_core` deliberately omits ``sources``, which each caller appends last via
:func:`source_dicts` — the *logic* (de-duplication) is shared, only the placement is the caller's.
Both payloads have always ended with ``sources``, and keeping it that way makes this refactor
byte-identical on both surfaces rather than merely equivalent.
"""

from __future__ import annotations

from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import DiscoveryResult, Source


def unique_sources(result: DiscoveryResult) -> list[Source]:
    """Collect the distinct sources (by id) used across all hops, in first-seen order.

    Args:
        result: The discovery result whose path's sources to collect.

    Returns:
        Each distinct source once, ordered by where it first appears along the path.
    """
    seen: dict[str, Source] = {}
    for hop in result.path.hops:
        for source in hop.statement.sources:
            seen.setdefault(source.id, source)
    return list(seen.values())


def source_dicts(result: DiscoveryResult) -> list[dict[str, str | None]]:
    """Render the result's distinct sources as ``{id, type, url}`` dicts, in first-seen order.

    Args:
        result: The discovery result whose sources to render.

    Returns:
        One JSON-friendly dict per distinct source.
    """
    return [
        {"id": source.id, "type": source.source_type.value, "url": source.url}
        for source in unique_sources(result)
    ]


def result_core(
    graph: KnowledgeGraph,
    result: DiscoveryResult,
    *,
    score_dp: int,
    trust_dp: int,
    metric_dp: int,
) -> dict[str, object]:
    """Build the result fields the CLI and the web API agree on.

    Callers add their own extras on top (the CLI's ``rank``/``path``, the web's ``chain``), then
    ``sources`` last via :func:`source_dicts` — see the module docstring.

    Args:
        graph: The knowledge graph the result came from, used to resolve node labels.
        result: The discovery result to serialize.
        score_dp: Decimal places for ``score``.
        trust_dp: Decimal places for ``trust``.
        metric_dp: Decimal places for ``surprise`` and ``endpoint_unexpectedness``.

    Returns:
        A JSON-friendly dict of the shared fields, without ``sources``.
    """
    return {
        "archetype": result.archetype.value,
        "topic": graph.node(result.path.node_ids[0]).label,
        "endpoint": graph.node(result.path.node_ids[-1]).label,
        "hops": result.path.length,
        "score": round(result.score, score_dp),
        "trust": round(result.trust, trust_dp),
        "surprise": round(result.surprise, metric_dp),
        "endpoint_unexpectedness": round(result.endpoint_unexpectedness, metric_dp),
        "possibly": result.possibly,
        "til": result.til,
    }
