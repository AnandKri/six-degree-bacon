"""The discovery pipeline: topic → ranked, narrated, sourced results."""

from __future__ import annotations

from sdb.constants import (
    MAX_HOPS_DEFAULT,
    MAX_HOPS_UNLIKELY,
    MIN_HOPS_DEFAULT,
    MIN_HOPS_UNLIKELY,
    POSSIBLY_THRESHOLD,
    TOP_DEFAULT,
    TRUST_FLOOR,
)
from sdb.engine.confidence import score_trust
from sdb.engine.narrate import narrate
from sdb.engine.surprise import score_surprise
from sdb.engine.traversal import find_paths
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import Archetype
from sdb.schema.models import DiscoveryResult


class TopicNotFoundError(LookupError):
    """Raised when a topic cannot be resolved to a node; carries near-miss suggestions."""

    def __init__(self, topic: str, suggestions: list[str]) -> None:
        """Store the unresolved ``topic`` and suggested alternatives."""
        self.topic = topic
        self.suggestions = suggestions
        super().__init__(f"topic not found: {topic!r}")


# The archetype vocabulary both front-ends expose as `--archetype` / `?archetype=`. Order is the
# order results are presented in, so it is a tuple, not a set. The improbable pair leads (ADR 0042):
# it already has the "one quantized fact" shape the product wants, so it is shown first / default.
ARCHETYPE_CHOICES: dict[str, tuple[Archetype, ...]] = {
    "journey": (Archetype.JOURNEY,),
    "unlikely": (Archetype.UNLIKELY,),
    "both": (Archetype.UNLIKELY, Archetype.JOURNEY),
}


def trust_gate(include_possibly: bool) -> float:
    """The minimum trust a path must clear to be surfaced.

    The default gate is :data:`~sdb.constants.POSSIBLY_THRESHOLD` (a genuine "wow with evidence"
    bar); ``include_possibly`` lowers it to :data:`~sdb.constants.TRUST_FLOOR`, below which a path
    is never shown at all.
    """
    return TRUST_FLOOR if include_possibly else POSSIBLY_THRESHOLD


def discover_all(
    graph: KnowledgeGraph,
    topic: str,
    *,
    archetype: str = "both",
    min_hops: int | None = None,
    max_hops: int | None = None,
    top: int = TOP_DEFAULT,
    min_trust: float = POSSIBLY_THRESHOLD,
) -> dict[Archetype, list[DiscoveryResult]]:
    """Run :func:`discover` for each archetype named by ``archetype``, keyed by archetype.

    Both front-ends offer the same journey/unlikely/both choice and then run the identical loop, so
    the loop lives here rather than being copied into each. An unrecognised name falls back to
    ``"both"`` — the web takes it straight from a query string.

    Returns:
        ``{archetype: results}`` in presentation order (dicts preserve insertion order).

    Raises:
        TopicNotFoundError: If ``topic`` does not resolve to a node.
    """
    archetypes = ARCHETYPE_CHOICES.get(archetype, ARCHETYPE_CHOICES["both"])
    return {
        each: discover(
            graph,
            topic,
            archetype=each,
            min_hops=min_hops,
            max_hops=max_hops,
            top=top,
            min_trust=min_trust,
        )
        for each in archetypes
    }


def _hop_range(archetype: Archetype, min_hops: int | None, max_hops: int | None) -> tuple[int, int]:
    """Resolve the hop range for an archetype, honouring explicit overrides."""
    if archetype is Archetype.UNLIKELY:
        lo, hi = MIN_HOPS_UNLIKELY, MAX_HOPS_UNLIKELY
    else:
        lo, hi = MIN_HOPS_DEFAULT, MAX_HOPS_DEFAULT
    return (min_hops if min_hops is not None else lo, max_hops if max_hops is not None else hi)


def discover(
    graph: KnowledgeGraph,
    topic: str,
    *,
    archetype: Archetype = Archetype.JOURNEY,
    min_hops: int | None = None,
    max_hops: int | None = None,
    top: int = TOP_DEFAULT,
    min_trust: float = POSSIBLY_THRESHOLD,
) -> list[DiscoveryResult]:
    """Discover the highest-scoring paths from ``topic`` for a given archetype.

    ``JOURNEY`` scores each path ``surprise x trust`` over the ``MIN_HOPS_DEFAULT..
    MAX_HOPS_DEFAULT`` range; ``UNLIKELY`` (the improbable adjacency) scores
    ``endpoint_unexpectedness x trust`` over the shorter ``MIN_HOPS_UNLIKELY..MAX_HOPS_UNLIKELY``
    range, so the improbability of the *destination* rather than the distance decides it. The two
    ranges are disjoint by construction, which is what stops both archetypes returning the same
    path (ADR 0027). The figures live in :mod:`sdb.constants` and are deliberately not repeated
    here — restating them is how this docstring came to claim the pre-ADR-0021/0027 ranges.

    Results are ranked by that score and deduplicated to the best path per endpoint. Paths below
    ``min_trust`` are dropped — the default (:data:`~sdb.constants.POSSIBLY_THRESHOLD`) is the "wow
    with evidence" gate; lower it to :data:`~sdb.constants.TRUST_FLOOR` to include speculative
    ``Possibly:`` paths.

    Raises:
        TopicNotFoundError: If ``topic`` does not resolve to a node.
    """
    source = graph.find_topic(topic)
    if source is None:
        raise TopicNotFoundError(topic, graph.suggest(topic))

    low, high = _hop_range(archetype, min_hops, max_hops)
    best_by_endpoint: dict[str, DiscoveryResult] = {}
    for path in find_paths(graph, source, low, high):
        trust = score_trust(graph, path).total
        if trust < min_trust:
            continue
        surprise = score_surprise(graph, path).total
        endpoint_unexpectedness = graph.endpoint_unexpectedness(source, path.node_ids[-1])
        basis = endpoint_unexpectedness if archetype is Archetype.UNLIKELY else surprise
        til, possibly = narrate(graph, path, trust)
        result = DiscoveryResult(
            path=path,
            archetype=archetype,
            trust=trust,
            surprise=surprise,
            endpoint_unexpectedness=endpoint_unexpectedness,
            score=basis * trust,
            til=til,
            possibly=possibly,
        )
        endpoint = path.node_ids[-1]
        incumbent = best_by_endpoint.get(endpoint)
        if incumbent is None or (result.score, result.trust) > (
            incumbent.score,
            incumbent.trust,
        ):
            best_by_endpoint[endpoint] = result

    ranked = sorted(
        best_by_endpoint.values(),
        key=lambda result: (result.score, result.trust),
        reverse=True,
    )
    return ranked[:top]
