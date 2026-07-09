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

from sdb.constants import COOCCURRENCE_ALPHA
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
    ) -> None:
        """Build the graph from nodes and statements, validating integrity and caching features.

        Args:
            nodes: All nodes; ids must be unique.
            statements: All reified claims; every endpoint must reference an existing node id.
            cooccurrence: Optional ``{node_id: linked_node_ids}`` Wikipedia-link map powering the
                endpoint-surprise term. Entries for unknown ids are ignored; if omitted or empty,
                :meth:`endpoint_unexpectedness` returns ``0.0`` (the term is disabled).

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
        self._total_edges: int = len(self._statements)
        self._build_cooccurrence(cooccurrence or {})

    @classmethod
    def from_seed(
        cls, seed: SeedData, cooccurrence: Mapping[str, Sequence[str]] | None = None
    ) -> KnowledgeGraph:
        """Build a graph from a :class:`~sdb.schema.models.SeedData` and optional co-occurrence."""
        return cls(seed.nodes, seed.statements, cooccurrence)

    def _build_cooccurrence(self, cooccurrence: Mapping[str, Sequence[str]]) -> None:
        """Cache the directed link sets and per-start denominators for the endpoint term.

        ``P(endpoint | start)`` is a smoothed conditional over co-occurrence *strength* — the number
        of link directions between the two articles (0, 1, or 2). The per-start denominator is the
        sum of ``strength + alpha`` over all other nodes, precomputed here so scoring is O(1).
        """
        self._cooc_links: dict[str, frozenset[str]] = {
            node_id: frozenset(t for t in targets if t in self._nodes and t != node_id)
            for node_id, targets in cooccurrence.items()
            if node_id in self._nodes
        }
        self._has_cooccurrence: bool = any(self._cooc_links.values())

        inbound: Counter[str] = Counter()
        for targets in self._cooc_links.values():
            inbound.update(targets)

        node_count = len(self._nodes)
        self._cooc_denominator: dict[str, float] = {}
        for node_id in self._nodes:
            strength_sum = len(self._cooc_links.get(node_id, frozenset())) + inbound[node_id]
            self._cooc_denominator[node_id] = COOCCURRENCE_ALPHA * (node_count - 1) + strength_sum

    def _link_strength(self, a: str, b: str) -> int:
        """Symmetric co-occurrence strength: the number of link directions present (0, 1, or 2)."""
        return int(b in self._cooc_links.get(a, frozenset())) + int(
            a in self._cooc_links.get(b, frozenset())
        )

    def endpoint_unexpectedness(self, start: str, end: str) -> float:
        """``-log2 P(end | start)`` from Wikipedia-link co-occurrence; ``0.0`` if no data.

        A destination whose article co-occurs with the start (linked) scores low; an unlinked one
        scores high. Returns ``0.0`` when co-occurrence data is absent or a node is unknown, so the
        term never destabilizes a graph built without it.
        """
        if not self._has_cooccurrence or start == end:
            return 0.0
        if start not in self._nodes or end not in self._nodes:
            return 0.0
        strength = self._link_strength(start, end)
        probability = (strength + COOCCURRENCE_ALPHA) / self._cooc_denominator[start]
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

        Matches against node id, label, Wikidata QID, and aliases. Returns ``None`` if nothing
        matches (see :meth:`suggest` for near-misses).
        """
        needle = query.strip().casefold()
        for node in self._nodes.values():
            candidates = [node.id, node.label, *node.aliases]
            if node.wikidata_qid is not None:
                candidates.append(node.wikidata_qid)
            if any(candidate.casefold() == needle for candidate in candidates):
                return node.id
        return None

    def suggest(self, query: str, k: int = 3) -> list[str]:
        """Return up to ``k`` node labels closest to ``query`` (for 'did you mean' hints)."""
        labels = [node.label for node in self._nodes.values()]
        matches = process.extract(query, labels, scorer=fuzz.WRatio, limit=k)
        return [label for label, _score, _index in matches]
