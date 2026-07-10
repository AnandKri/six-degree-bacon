"""Merging a harvest into the curated graph: QID unification, breadth, and corroboration."""

from __future__ import annotations

from sdb.engine.confidence import statement_confidence
from sdb.graph.build import KnowledgeGraph
from sdb.harvest.merge import merge_seeds
from sdb.schema.enums import Domain, Predicate, SourceType, WikidataRank
from sdb.schema.models import Node, SeedData, Source, Statement


def _node(node_id: str, qid: str, label: str) -> Node:
    return Node(id=node_id, label=label, domain=Domain.HISTORY, type="x", wikidata_qid=qid)


def _stmt(subject: str, predicate: Predicate, obj: str, sources: tuple[Source, ...]) -> Statement:
    return Statement(subject=subject, predicate=predicate, object=obj, sources=sources)


_WIKIPEDIA = Source(id="w_ab", source_type=SourceType.WIKIPEDIA)
_WIKIDATA_PREFERRED = Source(
    id="wd_ab", source_type=SourceType.WIKIDATA_WITH_REF, rank=WikidataRank.PREFERRED
)


def _base() -> SeedData:
    return SeedData(
        nodes=(_node("a", "Q1", "A"), _node("b", "Q2", "B")),
        statements=(
            _stmt("a", Predicate.PART_OF, "b", (_WIKIPEDIA,)),  # Wikipedia only -> corroboratable
            _stmt("a", Predicate.FOLLOWS, "b", (_WIKIPEDIA, _WIKIDATA_PREFERRED)),  # has Wikidata
        ),
    )


def _overlay() -> SeedData:
    wd = Source(id="wd_new", source_type=SourceType.WIKIDATA_NO_REF)
    return SeedData(
        nodes=(_node("Q1", "Q1", "A"), _node("Q2", "Q2", "B"), _node("Q3", "Q3", "C")),
        statements=(
            _stmt("Q1", Predicate.PART_OF, "Q2", (wd,)),  # matches base s1 -> corroborates
            _stmt("Q1", Predicate.FOLLOWS, "Q2", (wd,)),  # matches base s2 -> guard blocks
            _stmt("Q1", Predicate.LOCATED_IN, "Q3", (wd,)),  # new node + new fact
        ),
    )


def test_merge_unifies_nodes_by_qid_and_adds_new_ones() -> None:
    result = merge_seeds(_base(), _overlay())
    ids = [n.id for n in result.seed.nodes]
    assert ids == ["a", "b", "Q3"]  # Q1/Q2 unified onto curated a/b; Q3 is new
    assert result.added_nodes == 1
    assert result.added_statements == 1  # only the located_in->Q3 fact is new


def test_independent_source_corroborates_and_raises_confidence() -> None:
    base, result = _base(), merge_seeds(_base(), _overlay())
    assert result.corroborated == 1  # part_of gains Wikidata; follows is guarded

    g_before = KnowledgeGraph.from_seed(base)
    g_after = KnowledgeGraph.from_seed(result.seed)
    before = {(s.subject, s.predicate, s.object): s for s in base.statements}
    after = {(s.subject, s.predicate, s.object): s for s in result.seed.statements}

    part_of = ("a", Predicate.PART_OF, "b")
    assert len(after[part_of].sources) == 2  # Wikipedia + harvested Wikidata
    assert statement_confidence(g_after, after[part_of]) > statement_confidence(
        g_before, before[part_of]
    )


def test_existing_wikidata_source_is_not_double_counted() -> None:
    result = merge_seeds(_base(), _overlay())
    follows = next(s for s in result.seed.statements if s.predicate is Predicate.FOLLOWS)
    # The base 'follows' fact already cites Wikidata, so the harvested Wikidata source is redundant.
    assert len(follows.sources) == 2


def test_base_is_not_mutated() -> None:
    base = _base()
    merge_seeds(base, _overlay())
    assert len(base.nodes) == 2
    assert len(base.statements[0].sources) == 1  # the Wikipedia-only fact is untouched
