"""QID-validation guard: the resolver logic (offline) and per-brain structural integrity.

The structural guards below are parametrised over **every brain** — the main curated graph
(``data/seed.json``) and each brain under ``data/brains/*`` (ADR 0044). A "brain" is just a
``(seed, cooccurrence)`` pair, so every brain must satisfy the same curation contract (region +
active period on every node, evidence + headline on every statement, well-formed unique QIDs, no
dangling co-occurrence keys). Parametrising means a *new* brain inherits the whole contract free.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from sdb.graph.loader import load_cooccurrence, load_seed
from sdb.harvest.validate import validate_qids
from sdb.schema.enums import Domain
from sdb.schema.models import Node

_DATA = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = _DATA / "seed.json"
COOCCURRENCE_PATH = _DATA / "cooccurrence.json"


def _brains() -> list[tuple[str, Path, Path]]:
    """Every brain as ``(name, seed_path, cooccurrence_path)`` — main plus each data/brains/*."""
    brains = [("main", SEED_PATH, COOCCURRENCE_PATH)]
    brains_dir = _DATA / "brains"
    if brains_dir.exists():
        for directory in sorted(brains_dir.iterdir()):
            seed = directory / "seed.json"
            if seed.exists():
                brains.append((directory.name, seed, directory / "cooccurrence.json"))
    return brains


_BRAINS = _brains()
_SEED_PARAMS = [pytest.param(seed, id=name) for name, seed, _ in _BRAINS]
_BRAIN_PARAMS = [pytest.param(seed, cooc, id=name) for name, seed, cooc in _BRAINS]


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


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_curated_seed_qids_are_well_formed_and_unique(seed_path: Path) -> None:
    seed = load_seed(seed_path)
    qids = [n.wikidata_qid for n in seed.nodes if n.wikidata_qid is not None]
    assert all(re.fullmatch(r"Q\d+", qid) for qid in qids)  # no hallucinated non-QIDs
    assert len(qids) == len(set(qids))  # each Wikidata entity used once


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_every_curated_statement_carries_evidence(seed_path: Path) -> None:
    """Every hop now renders its curated justification, so a blank one is a hole in the card.

    `Statement.evidence` defaults to `""`, so nothing in the schema enforces this — the value of
    surfacing the prose (ADR 0037) rests entirely on the curation staying complete. Deliberately
    checks non-emptiness only: prose style is not asserted, since legitimate evidence starts
    lower-case ("al-Khwarizmi ...").
    """
    seed = load_seed(seed_path)
    missing = [
        f"{s.subject} --{s.predicate.value}--> {s.object}"
        for s in seed.statements
        if not s.evidence.strip()
    ]
    assert not missing, f"statements with no curated evidence: {missing}"


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_every_curated_statement_carries_a_headline(seed_path: Path) -> None:
    """ADR 0042: the TIL is the payoff hop's curated `headline`. A curated statement without one
    would fall back to the mechanical predicate chain — the weak line the headline replaces — so a
    blank is a visible regression on any card that edge lands. `Statement.headline` defaults to
    `""`, so the schema can't enforce this; guard it like `evidence`."""
    seed = load_seed(seed_path)
    missing = [
        f"{s.subject} --{s.predicate.value}--> {s.object}"
        for s in seed.statements
        if not s.headline.strip()
    ]
    assert not missing, f"statements with no curated headline: {missing}"


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_every_curated_node_carries_a_region(seed_path: Path) -> None:
    """Region is a scoring input (ADR 0039), so a curated node without one is a silent hole — it
    skips the region-jump term, under-counting its cultural surprise. `Node.region` defaults to
    `None` (harvested nodes may legitimately lack one), so the completeness of the *curated* seed is
    an invariant the schema can't enforce; this guards it, mirroring the evidence guard above."""
    seed = load_seed(seed_path)
    missing = [n.id for n in seed.nodes if n.region is None]
    assert not missing, f"curated nodes with no region: {missing}"


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_every_dated_curated_node_carries_an_active_period(seed_path: Path) -> None:
    """ADR 0041: ``midpoint_year`` (and thus the temporal_gap term + the FOLLOWS check) keys off the
    active period when present, so a *dated* curated node without one silently scores off its
    existence extent — the very distortion the axis removes (India's existence midpoint is a
    meaningless -638). Genuinely undated nodes (myth/abstract, e.g. Amaterasu) legitimately have
    neither extent, so the invariant is scoped to dated nodes; `active_*` defaults to `None`, so the
    schema can't enforce this — this guards it, mirroring the region/evidence guards above."""
    seed = load_seed(seed_path)
    missing = [
        n.id
        for n in seed.nodes
        if (n.start_year is not None or n.end_year is not None)
        and (n.active_start is None or n.active_end is None)
    ]
    assert not missing, f"dated curated nodes with no active period: {missing}"


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_curated_active_periods_are_well_ordered(seed_path: Path) -> None:
    """A disordered active interval (``active_start`` after ``active_end``) feeds a nonsense
    midpoint, so guard the ordering as the date-disorder validator guards the existence extent."""
    seed = load_seed(seed_path)
    disordered = [
        n.id
        for n in seed.nodes
        if n.active_start is not None and n.active_end is not None and n.active_start > n.active_end
    ]
    assert not disordered, f"curated nodes with active_start > active_end: {disordered}"


@pytest.mark.parametrize("seed_path", _SEED_PARAMS)
def test_region_is_an_axis_independent_of_domain(seed_path: Path) -> None:
    """ADR 0039: the region term earns its keep only if some edges cross a culture without crossing
    a domain — the cross-cultural, same-discipline hops the domain term is blind to (e.g. al-Tusi
    influenced_by Euclid: both `science`, Near-Eastern -> Western; or, in the 20th-century brain,
    The Magnificent Seven derived_from Seven Samurai: both `art`, Japanese -> Western). Asserted as
    a structural property of the seed, not by naming a favoured result."""
    seed = load_seed(seed_path)
    by_id = {n.id: n for n in seed.nodes}
    same_domain_cross_region = [
        s
        for s in seed.statements
        if by_id[s.subject].domain == by_id[s.object].domain
        and by_id[s.subject].region is not None
        and by_id[s.object].region is not None
        and by_id[s.subject].region != by_id[s.object].region
    ]
    assert same_domain_cross_region  # the region axis captures surprise the domain axis cannot


@pytest.mark.parametrize(("seed_path", "cooccurrence_path"), _BRAIN_PARAMS)
def test_cooccurrence_references_only_real_nodes(seed_path: Path, cooccurrence_path: Path) -> None:
    seed = load_seed(seed_path)
    cooccurrence = load_cooccurrence(cooccurrence_path)
    ids = {n.id for n in seed.nodes}
    assert set(cooccurrence) <= ids  # no dangling co-occurrence keys
    assert all(target in ids for targets in cooccurrence.values() for target in targets)
