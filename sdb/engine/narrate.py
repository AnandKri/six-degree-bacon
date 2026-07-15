"""Template narrator — compose a TIL from a path, with no LLM.

This is deliberately deterministic. A free/local LLM narrator is an optional later upgrade behind
the same call signature; this template remains the guaranteed fallback.

The TIL is a *single quantized claim* (ADR 0028): one sentence that states the connection, with the
repeated subject elided into relative clauses. The hop-by-hop chain is **not** restated here — every
caller (CLI, web, static site) already renders it as the evidence right above the TIL, so reciting
it again added noise rather than information.
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


def narrate(graph: KnowledgeGraph, path: Path, trust: float) -> tuple[str, bool]:
    """Compose a TIL string for ``path`` as one sentence stating the connection.

    The first hop is stated in full; each subsequent hop elides its subject into a relative clause,
    so the result reads as a single fact ("Naruhito claimed descent from Jimmu, who claimed descent
    from Amaterasu") rather than a list of mechanical steps. Every node label on the path still
    appears exactly once.

    Returns:
        ``(text, possibly)`` where ``possibly`` is ``True`` (and the text is prefixed ``Possibly:``)
        when ``trust`` is below :data:`~sdb.constants.POSSIBLY_THRESHOLD`.
    """
    possibly = trust < POSSIBLY_THRESHOLD

    first = path.hops[0]
    clauses = [
        f"{graph.node(first.from_id).label} {_phrase(first)} {graph.node(first.to_id).label}"
    ]
    for hop in path.hops[1:]:
        pronoun = _relative_pronoun(graph.node(hop.from_id))
        clauses.append(f"{pronoun} {_phrase(hop)} {graph.node(hop.to_id).label}")

    prefix = "Possibly: " if possibly else "TIL: "
    return f"{prefix}{', '.join(clauses)}.", possibly
