"""QID-validation guard: the resolver logic (offline) and seed structural integrity."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from sdb.graph.loader import load_cooccurrence, load_seed
from sdb.harvest.validate import validate_qids
from sdb.schema.enums import Domain
from sdb.schema.models import Node

_DATA = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = _DATA / "seed.json"
COOCCURRENCE_PATH = _DATA / "cooccurrence.json"


class _FakeResolver:
    def __init__(self, mapping: dict[str, str | None]) -> None:
        self._mapping = mapping

    def qids_for(self, titles: Sequence[str]) -> dict[str, str | None]:
        return {title: self._mapping.get(title) for title in titles}


def _node(node_id: str, label: str, qid: str | None) -> Node:
    return Node(id=node_id, label=label, domain=Domain.HISTORY, type="x", wikidata_qid=qid)


def test_validate_flags_wrong_and_unresolved_qids() -> None:
    nodes = [
        _node("a", "Correct", "Q1"),
        _node("b", "Wrong", "Q2"),  # resolver says Q999
        _node("c", "Missing", "Q3"),  # resolver can't resolve
        _node("d", "NoQid", None),  # skipped
    ]
    resolver = _FakeResolver({"Correct": "Q1", "Wrong": "Q999", "Missing": None})
    mismatches = validate_qids(nodes, resolver)
    flagged = {m.node_id: m.resolved_qid for m in mismatches}
    assert flagged == {"b": "Q999", "c": None}  # a matches, d is skipped


def test_curated_seed_qids_are_well_formed_and_unique() -> None:
    seed = load_seed(SEED_PATH)
    qids = [n.wikidata_qid for n in seed.nodes if n.wikidata_qid is not None]
    assert all(re.fullmatch(r"Q\d+", qid) for qid in qids)  # no hallucinated non-QIDs
    assert len(qids) == len(set(qids))  # each Wikidata entity used once


def test_cooccurrence_references_only_real_nodes() -> None:
    seed = load_seed(SEED_PATH)
    cooccurrence = load_cooccurrence(COOCCURRENCE_PATH)
    ids = {n.id for n in seed.nodes}
    assert set(cooccurrence) <= ids  # no dangling co-occurrence keys
    assert all(target in ids for targets in cooccurrence.values() for target in targets)
