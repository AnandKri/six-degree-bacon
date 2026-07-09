"""Template narrator — compose a TIL from a path, with no LLM.

This is deliberately deterministic. A free/local LLM narrator is an optional later upgrade behind
the same call signature; this template remains the guaranteed fallback.
"""

from __future__ import annotations

from sdb.constants import POSSIBLY_THRESHOLD
from sdb.graph.build import KnowledgeGraph
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED
from sdb.schema.models import Path


def narrate(graph: KnowledgeGraph, path: Path, trust: float) -> tuple[str, bool]:
    """Compose a TIL string for ``path``.

    Returns:
        ``(text, possibly)`` where ``possibly`` is ``True`` (and the text is prefixed ``Possibly:``)
        when ``trust`` is below :data:`~sdb.constants.POSSIBLY_THRESHOLD`.
    """
    possibly = trust < POSSIBLY_THRESHOLD

    fragments: list[str] = []
    for hop in path.hops:
        subject_label = graph.node(hop.from_id).label
        object_label = graph.node(hop.to_id).label
        phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
        fragments.append(f"{subject_label} {phrases[hop.statement.predicate]} {object_label}")

    start = graph.node(path.node_ids[0]).label
    end = graph.node(path.node_ids[-1]).label
    domains = {graph.node(node_id).domain for node_id in path.node_ids}

    chain = "; ".join(fragments)
    why = (
        f"It connects {start} to {end} across {len(domains)} domains "
        f"and {path.length} steps — an unexpected thread."
    )
    prefix = "Possibly: " if possibly else "TIL: "
    return f"{prefix}{chain}. {why}", possibly
