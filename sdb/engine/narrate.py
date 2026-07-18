"""Narrator — compose a TIL from a path, with no LLM.

Deterministic and reproducible. The TIL is a *single quantized fact* (ADR 0028): one sentence that
states the connection. Its wording is the curated ``headline`` of the path's **payoff** (last) hop —
the hop that lands on the destination — a hand-written, evidence-faithful one-liner (ADR 0042), so a
card leads with a real fact ("Gutenberg's press ran on paper, a Chinese invention") rather than a
mechanically chained list of predicates. The per-hop chain is **not** restated here — every caller
(CLI, web, static site) already renders it as the curated evidence right above the TIL.

The mechanical relative-clause chain (:func:`_chain_narrative`) remains the guaranteed fallback for
any statement without a curated headline (e.g. harvested edges). A free/local LLM narrator is still
an optional later upgrade behind this same call signature.
"""

from __future__ import annotations

from sdb.constants import POSSIBLY_THRESHOLD
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED
from sdb.schema.models import Hop, Node, Path

# Node ``type`` words that denote a person or a personified being, so the relative clause reads
# "who" rather than "which". Matched word-wise against the (lower-cased) type, so compound types
# like "legendary emperor" or "legendary founder" resolve correctly. Anything unrecognised falls
# back to "which", which is right for the great majority of node types (places, works, states…).
_PERSONAL_TYPE_WORDS = frozenset(
    {
        "astronomer",
        "deity",
        "emperor",
        "empress",
        "explorer",
        "founder",
        "general",
        "hero",
        "inventor",
        "king",
        "maharaja",
        "mathematician",
        "monarch",
        "official",
        "pharaoh",
        "philosopher",
        "physicist",
        "poet",
        "polymath",
        "prophet",
        "queen",
        "ruler",
        "saint",
        "scholar",
        "statesman",
    }
)


def _relative_pronoun(node: Node) -> str:
    """Return "who" for a person or personified being, else "which" (deterministic type lookup)."""
    words = node.type.lower().replace("-", " ").split()
    return "who" if any(word in _PERSONAL_TYPE_WORDS for word in words) else "which"


def _phrase(hop: Hop) -> str:
    """The correctly-directed phrasing for this hop's predicate."""
    phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
    return phrases[hop.statement.predicate]


def _chain_narrative(graph: KnowledgeGraph, path: Path) -> str:
    """The mechanical relative-clause chain — the fallback when the payoff hop has no headline.

    The first hop is stated in full; each subsequent hop elides its subject into a relative clause
    ("Naruhito claimed descent from Jimmu, who claimed descent from Amaterasu"). Every node label on
    the path appears exactly once. Used verbatim for harvested/uncurated edges (ADR 0042).
    """
    first = path.hops[0]
    clauses = [
        f"{graph.node(first.from_id).label} {_phrase(first)} {graph.node(first.to_id).label}"
    ]
    for hop in path.hops[1:]:
        pronoun = _relative_pronoun(graph.node(hop.from_id))
        clauses.append(f"{pronoun} {_phrase(hop)} {graph.node(hop.to_id).label}")
    return f"{', '.join(clauses)}."


def narrate(graph: KnowledgeGraph, path: Path, trust: float) -> tuple[str, bool]:
    """Compose a TIL string for ``path`` as one quantized fact.

    Uses the curated ``headline`` of the path's payoff (last) hop — the hop that lands on the
    destination — so the card leads with a real, evidence-faithful fact (ADR 0042). Falls back to
    the mechanical predicate chain (:func:`_chain_narrative`) for any payoff statement without a
    curated headline.

    Returns:
        ``(text, possibly)`` where ``possibly`` is ``True`` (and the text is prefixed ``Possibly:``)
        when ``trust`` is below :data:`~sdb.constants.POSSIBLY_THRESHOLD`.
    """
    possibly = trust < POSSIBLY_THRESHOLD
    body = path.hops[-1].statement.headline.strip() or _chain_narrative(graph, path)
    prefix = "Possibly: " if possibly else "TIL: "
    return f"{prefix}{body}", possibly
