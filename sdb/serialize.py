"""Shared JSON serialization for :class:`~sdb.schema.models.DiscoveryResult`.

The CLI (``discover --json``) and the web API render the same result object and had drifted into two
near-identical serializers, each with its own copy of the source de-duplication — so a new field on
``DiscoveryResult`` had to be remembered in two places. This module owns the part they agree on.

What they legitimately *don't* share stays with each caller: the CLI adds ``rank`` and a flat
``path`` of labels. Rounding is a parameter rather than a fixed choice because the two surfaces
have different jobs — the CLI's ``--json`` is machine-facing and keeps 4 dp, the web card is
display-facing and keeps 2-3 dp.

:func:`result_core` deliberately omits ``sources``, which each caller appends last via
:func:`source_dicts` — the *logic* (de-duplication) is shared, only the placement is the caller's.
Both payloads have always ended with ``sources``, and keeping it that way makes this refactor
byte-identical on both surfaces rather than merely equivalent.

:func:`hop_dicts` renders the ``chain`` — the per-hop evidence. It was the web's private payload
until the curated ``Statement.evidence`` prose shipped (ADR 0037); the moment both front-ends
needed it, it became exactly the kind of field this module exists to keep from reaching one surface
and missing the other.
"""

from __future__ import annotations

from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED
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


def hop_dicts(graph: KnowledgeGraph, result: DiscoveryResult) -> list[dict[str, str]]:
    """Render the path as one dict per hop, in the direction each hop was traversed.

    Each step is ``{from, from_id, phrase, to, to_id, evidence}``. ``phrase`` is the correctly
    directed predicate phrasing; ``evidence`` is the curated one-sentence justification for that
    specific claim (:attr:`~sdb.schema.models.Statement.evidence`) — the thing that makes the chain
    read as sourced evidence rather than a mechanical list of predicates (ADR 0037). It is ``""``
    for any statement without curated prose, which callers must tolerate.

    The ``*_id`` node ids let the map light the discovered route in place (join a hop back to a map
    node); the labels are what a card renders.

    Args:
        graph: The knowledge graph the result came from, used to resolve node labels.
        result: The discovery result whose path to render.

    Returns:
        One JSON-friendly dict per hop, in path order.
    """
    steps: list[dict[str, str]] = []
    for hop in result.path.hops:
        phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
        steps.append(
            {
                "from": graph.node(hop.from_id).label,
                "from_id": hop.from_id,
                "phrase": phrases[hop.statement.predicate],
                "to": graph.node(hop.to_id).label,
                "to_id": hop.to_id,
                "evidence": hop.statement.evidence,
            }
        )
    return steps


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
