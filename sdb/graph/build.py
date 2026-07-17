"""Build an in-memory knowledge graph and cache the derived features scoring needs.

The graph is an undirected :class:`networkx.MultiGraph` (parallel edges allowed, so two nodes can be
connected by several distinct statements). Each statement's original direction is preserved on the
edge so the narrator can phrase a traversal correctly.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence

import networkx as nx
from rapidfuzz import fuzz, process

from sdb.constants import (
    COOCCURRENCE_ALPHA,
    COOCCURRENCE_SIMILARITY_WEIGHT,
    DOMAIN_JUMP_ALPHA,
)
from sdb.schema.enums import Predicate
from sdb.schema.models import Node, SeedData, Statement


class GraphIntegrityError(ValueError):
    """Raised when the seed graph is malformed (duplicate ids, or a dangling endpoint)."""


class KnowledgeGraph:
    """A feature-annotated wrapper around a ``networkx.MultiGraph``."""

    def __init__(
        self,
        nodes: tuple[Node, ...],
        statements: tuple[Statement, ...],
        cooccurrence: Mapping[str, Sequence[str]] | None = None,
        similarity: Mapping[str, Mapping[str, float]] | None = None,
    ) -> None:
        """Build the graph from nodes and statements, validating integrity and caching features.

        Args:
            nodes: All nodes; ids must be unique.
            statements: All reified claims; every endpoint must reference an existing node id.
            cooccurrence: Optional ``{node_id: linked_node_ids}`` Wikipedia-link map powering the
                endpoint-surprise term. Entries for unknown ids are ignored; if omitted or empty,
                :meth:`endpoint_unexpectedness` returns ``0.0`` (the term is disabled).
            similarity: Optional ``{node_id: {node_id: jaccard}}`` overlap of the two articles' full
                outbound link sets (ADR 0029), stored once per pair. Powers the second-order "shared
                context" term; when absent that term is simply ``0`` and only direct link strength
                counts.

        Raises:
            GraphIntegrityError: On a duplicate node id or a statement with a dangling endpoint.
        """
        self._nodes: dict[str, Node] = {n.id: n for n in nodes}
        if len(self._nodes) != len(nodes):
            raise GraphIntegrityError("duplicate node id in seed graph")

        self._statements: tuple[Statement, ...] = tuple(statements)
        self._graph: nx.MultiGraph = nx.MultiGraph()
        self._graph.add_nodes_from(self._nodes)
        for st in self._statements:
            for endpoint in (st.subject, st.object):
                if endpoint not in self._nodes:
                    raise GraphIntegrityError(f"statement references unknown node id {endpoint!r}")
            self._graph.add_edge(st.subject, st.object, statement=st)

        # Cached derived features.
        self._predicate_counts: Counter[Predicate] = Counter(
            st.predicate for st in self._statements
        )
        # How often each predicate's edges cross a domain boundary — the base rate that tells a
        # tautological jump (`located_in` always lands in `geography`) from an informative one.
        self._predicate_jump_counts: Counter[Predicate] = Counter(
            st.predicate
            for st in self._statements
            if self._nodes[st.subject].domain != self._nodes[st.object].domain
        )
        self._total_edges: int = len(self._statements)
        self._build_cooccurrence(cooccurrence or {}, similarity or {})

    @classmethod
    def from_seed(
        cls,
        seed: SeedData,
        cooccurrence: Mapping[str, Sequence[str]] | None = None,
        similarity: Mapping[str, Mapping[str, float]] | None = None,
    ) -> KnowledgeGraph:
        """Build a graph from a :class:`~sdb.schema.models.SeedData` and optional co-occurrence."""
        return cls(seed.nodes, seed.statements, cooccurrence, similarity)

    def _build_cooccurrence(
        self,
        cooccurrence: Mapping[str, Sequence[str]],
        similarity: Mapping[str, Mapping[str, float]],
    ) -> None:
        """Cache the co-occurrence link sets, pair similarity, and per-start denominators.

        ``P(endpoint | start)`` is a smoothed conditional over *effective* co-occurrence strength:
        the direct link strength (0, 1, or 2 link directions) plus a second-order term for shared
        context — ``COOCCURRENCE_SIMILARITY_WEIGHT * jaccard`` over the two articles' full outbound
        link sets (ADR 0029). The per-start denominator ``Σₑ (effective_strength + alpha)`` is
        precomputed here (an O(N²) build-time pass; fine for a curated seed) so scoring stays O(1).
        """
        self._cooc_links: dict[str, frozenset[str]] = {
            node_id: frozenset(t for t in targets if t in self._nodes and t != node_id)
            for node_id, targets in cooccurrence.items()
            if node_id in self._nodes
        }
        self._has_cooccurrence: bool = any(self._cooc_links.values())

        # Pair similarity, symmetrised: the harvester stores each pair once (a < b).
        self._cooc_similarity: dict[frozenset[str], float] = {}
        for left, peers in similarity.items():
            if left not in self._nodes:
                continue
            for right, score in peers.items():
                if right in self._nodes and right != left and score:
                    self._cooc_similarity[frozenset((left, right))] = score

        node_count = len(self._nodes)
        self._cooc_denominator: dict[str, float] = {}
        for start in self._nodes:
            effective_sum = sum(
                self._effective_strength(start, other) for other in self._nodes if other != start
            )
            self._cooc_denominator[start] = COOCCURRENCE_ALPHA * (node_count - 1) + effective_sum

    def _link_strength(self, a: str, b: str) -> int:
        """Symmetric co-occurrence strength: the number of link directions present (0, 1, or 2)."""
        return int(b in self._cooc_links.get(a, frozenset())) + int(
            a in self._cooc_links.get(b, frozenset())
        )

    def _effective_strength(self, a: str, b: str) -> float:
        """Direct link strength plus a weighted second-order term for shared context (ADR 0029).

        Two articles that link the *same* other articles share context even if they never link each
        other, so a destination with more overlap is less surprising. Measured as Jaccard over each
        article's **full** outbound link set (not just the seed), which is what de-saturates the
        strength-0 bucket for peripheral nodes — it otherwise ties nearly every unlinked pair at the
        maximum unexpectedness. Falls back to 0 (direct strength only) without a similarity table.
        """
        jaccard = self._cooc_similarity.get(frozenset((a, b)), 0.0)
        return self._link_strength(a, b) + COOCCURRENCE_SIMILARITY_WEIGHT * jaccard

    def endpoint_unexpectedness(self, start: str, end: str) -> float:
        """``-log2 P(end | start)`` from Wikipedia-link co-occurrence; ``0.0`` if no data.

        A destination whose article co-occurs with the start (directly, or via shared context)
        scores low; a genuinely isolated one scores high. Returns ``0.0`` when co-occurrence data is
        absent or a node is unknown, so the term never destabilizes a graph built without it.
        """
        if not self._has_cooccurrence or start == end:
            return 0.0
        if start not in self._nodes or end not in self._nodes:
            return 0.0
        probability = (self._effective_strength(start, end) + COOCCURRENCE_ALPHA) / (
            self._cooc_denominator[start]
        )
        return -math.log2(probability)

    # --- accessors ---------------------------------------------------------
    def node(self, node_id: str) -> Node:
        """Return the node with ``node_id`` (raises ``KeyError`` if absent)."""
        return self._nodes[node_id]

    def has_node(self, node_id: str) -> bool:
        """Return whether a node with ``node_id`` exists."""
        return node_id in self._nodes

    def nodes(self) -> tuple[Node, ...]:
        """Return all nodes."""
        return tuple(self._nodes.values())

    @property
    def statements(self) -> tuple[Statement, ...]:
        """Return all statements."""
        return self._statements

    @property
    def total_edges(self) -> int:
        """Total number of edges (statements) in the graph."""
        return self._total_edges

    def degree(self, node_id: str) -> int:
        """Degree of a node, counting parallel edges (used for hub detection)."""
        return int(self._graph.degree(node_id))

    def rarity(self, predicate: Predicate) -> float:
        """Self-information of a predicate: ``-log2(count / total_edges)``.

        Rarer predicates carry more surprise. Returns ``0.0`` for an unseen predicate or an
        empty graph.
        """
        count = self._predicate_counts.get(predicate, 0)
        if count == 0 or self._total_edges == 0:
            return 0.0
        return -math.log2(count / self._total_edges)

    def domain_jump_weight(self, predicate: Predicate) -> float:
        """How *unexpected* a domain jump is on ``predicate`` — ``1 - P(jump | predicate)``.

        A jump is only surprising if the predicate did not already guarantee it. ``located_in``
        crosses into ``geography`` in 94% of the seed's such edges, so a jump there carries almost
        no information and scores ~0.07; ``follows`` jumps ~0% of the time, so a jump there is
        genuinely informative and scores ~0.92. The base rate is Laplace-smoothed
        (:data:`~sdb.constants.DOMAIN_JUMP_ALPHA`) and learned from this graph, mirroring
        :meth:`rarity`. Bounded ``[0, 1]``; an unseen predicate smooths to ``0.5``. See ADR 0034.
        """
        edges = self._predicate_counts.get(predicate, 0)
        jumps = self._predicate_jump_counts.get(predicate, 0)
        probability = (jumps + DOMAIN_JUMP_ALPHA) / (edges + 2 * DOMAIN_JUMP_ALPHA)
        return 1.0 - probability

    def incident(self, node_id: str) -> list[tuple[str, Statement, bool]]:
        """Return ``(neighbor_id, statement, is_reversed)`` for every edge at ``node_id``.

        ``is_reversed`` is ``True`` when ``node_id`` is the statement's *object* (i.e. we would
        traverse the directed statement backwards). The list is sorted for deterministic traversal.
        """
        out: list[tuple[str, Statement, bool]] = []
        for _u, neighbor, data in self._graph.edges(node_id, data=True):
            st: Statement = data["statement"]
            out.append((neighbor, st, node_id != st.subject))
        out.sort(
            key=lambda item: (item[0], item[1].predicate.value, item[1].object, item[1].subject)
        )
        return out

    def find_topic(self, query: str) -> str | None:
        """Resolve a free-text topic to a node id via exact (case-insensitive) match.

        A node's own id, label, or Wikidata QID wins outright over another node's *alias*, so a
        query that names one node (e.g. ``"Rome"``, the city) is never hijacked by an earlier node
        that merely lists it as an alias (``roman_empire``, aliased "Rome"). Only if nothing matches
        a primary field does an alias match apply. Returns ``None`` if nothing matches at all (see
        :meth:`suggest` for near-misses).
        """
        needle = query.strip().casefold()
        alias_hit: str | None = None
        for node in self._nodes.values():
            primary = [node.id, node.label]
            if node.wikidata_qid is not None:
                primary.append(node.wikidata_qid)
            if any(candidate.casefold() == needle for candidate in primary):
                return node.id
            if alias_hit is None and any(alias.casefold() == needle for alias in node.aliases):
                alias_hit = node.id
        return alias_hit

    def suggest(self, query: str, k: int = 3) -> list[str]:
        """Return up to ``k`` node labels closest to ``query`` (for 'did you mean' hints)."""
        labels = [node.label for node in self._nodes.values()]
        matches = process.extract(query, labels, scorer=fuzz.WRatio, limit=k)
        return [label for label, _score, _index in matches]
