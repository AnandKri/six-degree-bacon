"""Merge a harvested neighbourhood into the curated graph, corroborating shared facts.

The curated ``data/seed.json`` stays authoritative; a harvest is *overlaid* onto it:

- **Node unification** — an overlay node is identified with a curated node when they share a
  Wikidata QID (the curated node, being richer, wins); otherwise it is added as a new node.
- **Fact corroboration** — an overlay statement with the same ``(subject, predicate, object)`` as a
  curated one contributes its source, so the noisy-OR trust in :mod:`sdb.engine.confidence` rises.
  Crucially, only *independent* evidence is added: a curated fact that already cites Wikidata is not
  double-counted by a harvested Wikidata source, but one sourced only from Wikipedia/books gains
  Wikidata as a genuine third corroborator.

Everything is deterministic given the two inputs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sdb.schema.enums import Predicate, SourceType
from sdb.schema.models import SeedData, Source, Statement

_WIKIDATA_SOURCE_TYPES = frozenset({SourceType.WIKIDATA_WITH_REF, SourceType.WIKIDATA_NO_REF})


@dataclass(frozen=True)
class MergeResult:
    """The merged graph plus a summary of what the overlay contributed."""

    seed: SeedData
    added_nodes: int
    added_statements: int
    corroborated: int


def _source_origin(source: Source) -> str:
    """The independent origin of a source; all Wikidata sources share one origin (no self-corr.)."""
    return "wikidata" if source.source_type in _WIKIDATA_SOURCE_TYPES else source.id


def _corroborate(statement: Statement, incoming: Iterable[Source]) -> tuple[Statement, bool]:
    """Return ``statement`` with new-origin incoming sources appended, and whether it changed."""
    origins = {_source_origin(source) for source in statement.sources}
    additions = tuple(s for s in incoming if _source_origin(s) not in origins)
    if not additions:
        return statement, False
    merged = statement.model_copy(update={"sources": (*statement.sources, *additions)})
    return merged, True


def merge_seeds(base: SeedData, overlay: SeedData) -> MergeResult:
    """Overlay ``overlay`` onto ``base``: unify nodes by QID and corroborate shared statements.

    Args:
        base: The authoritative curated graph.
        overlay: A harvested neighbourhood (node ids are Wikidata QIDs).

    Returns:
        A :class:`MergeResult` whose ``seed`` is the combined graph. ``base`` is never mutated.
    """
    qid_to_base = {n.wikidata_qid: n.id for n in base.nodes if n.wikidata_qid is not None}
    base_ids = {n.id for n in base.nodes}

    remap: dict[str, str] = {}
    added_nodes = []
    for node in overlay.nodes:
        if node.wikidata_qid is not None and node.wikidata_qid in qid_to_base:
            remap[node.id] = qid_to_base[node.wikidata_qid]  # unify onto the richer curated node
        elif node.id not in base_ids:
            remap[node.id] = node.id
            added_nodes.append(node)
        else:
            remap[node.id] = node.id  # id collision with a curated node; keep the curated one

    statements: list[Statement] = []
    index: dict[tuple[str, Predicate, str], int] = {}
    for statement in base.statements:
        key = (statement.subject, statement.predicate, statement.object)
        if key in index:  # collapse any exact-duplicate curated facts into one reified statement
            statements[index[key]], _ = _corroborate(statements[index[key]], statement.sources)
        else:
            index[key] = len(statements)
            statements.append(statement)

    corroborated = 0
    added_statements = 0
    for statement in overlay.statements:
        subject = remap.get(statement.subject, statement.subject)
        obj = remap.get(statement.object, statement.object)
        key = (subject, statement.predicate, obj)
        if key in index:
            merged_stmt, changed = _corroborate(statements[index[key]], statement.sources)
            statements[index[key]] = merged_stmt
            corroborated += changed
        else:
            index[key] = len(statements)
            statements.append(statement.model_copy(update={"subject": subject, "object": obj}))
            added_statements += 1

    merged = SeedData(nodes=(*base.nodes, *added_nodes), statements=tuple(statements))
    return MergeResult(
        seed=merged,
        added_nodes=len(added_nodes),
        added_statements=added_statements,
        corroborated=corroborated,
    )
