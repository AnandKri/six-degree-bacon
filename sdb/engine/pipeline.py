"""The discovery pipeline: topic → ranked, narrated, sourced results."""

from __future__ import annotations

from sdb.constants import (
    MAX_HOPS_DEFAULT,
    MIN_HOPS_DEFAULT,
    TOP_DEFAULT,
    TRUST_FLOOR,
)
from sdb.engine.confidence import score_trust
from sdb.engine.narrate import narrate
from sdb.engine.surprise import score_surprise
from sdb.engine.traversal import enumerate_paths
from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import DiscoveryResult


class TopicNotFoundError(LookupError):
    """Raised when a topic cannot be resolved to a node; carries near-miss suggestions."""

    def __init__(self, topic: str, suggestions: list[str]) -> None:
        """Store the unresolved ``topic`` and suggested alternatives."""
        self.topic = topic
        self.suggestions = suggestions
        super().__init__(f"topic not found: {topic!r}")


def discover(
    graph: KnowledgeGraph,
    topic: str,
    *,
    min_hops: int = MIN_HOPS_DEFAULT,
    max_hops: int = MAX_HOPS_DEFAULT,
    top: int = TOP_DEFAULT,
) -> list[DiscoveryResult]:
    """Discover the most surprising, sufficiently-trusted paths from ``topic``.

    Candidates below :data:`~sdb.constants.TRUST_FLOOR` are dropped; the rest are ranked by surprise
    (trust breaks ties) and deduplicated to the single best path per endpoint.

    Raises:
        TopicNotFoundError: If ``topic`` does not resolve to a node.
    """
    source = graph.find_topic(topic)
    if source is None:
        raise TopicNotFoundError(topic, graph.suggest(topic))

    best_by_endpoint: dict[str, DiscoveryResult] = {}
    for path in enumerate_paths(graph, source, min_hops, max_hops):
        trust = score_trust(graph, path)
        if trust.total < TRUST_FLOOR:
            continue
        surprise = score_surprise(graph, path)
        til, possibly = narrate(graph, path, trust.total)
        result = DiscoveryResult(
            path=path,
            trust=trust.total,
            surprise=surprise.total,
            til=til,
            possibly=possibly,
        )
        endpoint = path.node_ids[-1]
        incumbent = best_by_endpoint.get(endpoint)
        if incumbent is None or (result.surprise, result.trust) > (
            incumbent.surprise,
            incumbent.trust,
        ):
            best_by_endpoint[endpoint] = result

    ranked = sorted(
        best_by_endpoint.values(),
        key=lambda result: (result.surprise, result.trust),
        reverse=True,
    )
    return ranked[:top]
