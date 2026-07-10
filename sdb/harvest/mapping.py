"""Deterministic mapping from raw Wikidata facts into the project's typed model.

This is the heart of Phase-1 trust grounding: a Wikidata statement's **rank** and whether it carries
**references** map — by a fixed, documented rule — onto a :class:`~sdb.schema.models.Source` whose
reliability the rubric in :mod:`sdb.constants` then scores. No LLM, no heuristics beyond the tables
below; the same inputs always yield the same source.
"""

from __future__ import annotations

from sdb.schema.enums import (
    PREDICATE_WIKIDATA,
    Domain,
    Predicate,
    SourceType,
    WikidataRank,
)
from sdb.schema.models import Source

# Additional Wikidata properties that map onto an *existing* predicate (many Wikidata properties
# express the same relation). These widen harvest recall without adding narration vocabulary; each
# must be a faithful subject→object match for its predicate's direction.
HARVEST_PREDICATE_ALIASES: dict[str, Predicate] = {
    "P17": Predicate.LOCATED_IN,  # country
    "P131": Predicate.LOCATED_IN,  # located in the administrative territorial entity
    "P463": Predicate.PART_OF,  # member of
}

# Inverse of PREDICATE_WIKIDATA (predicates with a canonical Wikidata property) plus the aliases. A
# harvested statement whose property is absent here is outside our vocabulary and is skipped.
WIKIDATA_PREDICATE: dict[str, Predicate] = {
    pid: predicate for predicate, pid in PREDICATE_WIKIDATA.items() if pid is not None
} | HARVEST_PREDICATE_ALIASES

# The Wikidata properties we harvest (the curated predicate set, as property ids).
HARVEST_PROPERTIES: tuple[str, ...] = tuple(sorted(WIKIDATA_PREDICATE))

# Wikidata "instance of" (P31) class → thematic Domain. Deterministic and intentionally small;
# anything unmapped falls back to DOMAIN_FALLBACK. Extend this table as the harvest set grows.
INSTANCE_OF_DOMAIN: dict[str, Domain] = {
    "Q6256": Domain.GEOGRAPHY,  # country
    "Q515": Domain.GEOGRAPHY,  # city
    "Q1549591": Domain.GEOGRAPHY,  # big city
    "Q5119": Domain.GEOGRAPHY,  # capital city
    "Q486972": Domain.GEOGRAPHY,  # human settlement
    "Q82794": Domain.GEOGRAPHY,  # geographic region
    "Q1620908": Domain.GEOGRAPHY,  # historical region
    "Q839954": Domain.GEOGRAPHY,  # archaeological site
    "Q4022": Domain.GEOGRAPHY,  # river
    "Q23442": Domain.GEOGRAPHY,  # island
    "Q8502": Domain.GEOGRAPHY,  # mountain
    "Q107425": Domain.GEOGRAPHY,  # landscape
    "Q3624078": Domain.HISTORY,  # sovereign state
    "Q3024240": Domain.HISTORY,  # historical country
    "Q28171280": Domain.HISTORY,  # ancient civilization
    "Q48349": Domain.HISTORY,  # empire
    "Q11514315": Domain.HISTORY,  # historical period
    "Q178561": Domain.HISTORY,  # battle
    "Q198": Domain.HISTORY,  # war
    "Q5": Domain.HISTORY,  # human
    "Q7269": Domain.GENEALOGY,  # dynasty
    "Q164950": Domain.GENEALOGY,  # noble family
    "Q34770": Domain.LANGUAGE,  # language
    "Q25295": Domain.LANGUAGE,  # language family
    "Q9174": Domain.RELIGION,  # religion
    "Q1530022": Domain.RELIGION,  # religious concept
    "Q178885": Domain.MYTH,  # deity
    "Q22988604": Domain.MYTH,  # mythological figure
    "Q41710": Domain.CULTURE,  # ethnic group
    "Q1002697": Domain.CULTURE,  # periodical / publication
    "Q571": Domain.CULTURE,  # book
    "Q47461344": Domain.CULTURE,  # written work
    "Q133311": Domain.TRADE,  # trade route
    "Q11446": Domain.TRADE,  # ship (proxy for trade artefacts)
}

# Domain assigned when no P31 class maps (broad, non-committal — never guesses a specific field).
DOMAIN_FALLBACK: Domain = Domain.CULTURE

# Rank strings as they appear in Wikidata's reified statement model.
_RANK_BY_NAME: dict[str, WikidataRank] = {
    "preferred": WikidataRank.PREFERRED,
    "normal": WikidataRank.NORMAL,
    "deprecated": WikidataRank.DEPRECATED,
}


def parse_rank(rank: str) -> WikidataRank:
    """Parse a Wikidata rank string (case-insensitive), defaulting to ``NORMAL`` if unknown.

    Wikidata's SPARQL model exposes rank either as a bare word (``preferred``) or as a full IRI
    ending in ``…#PreferredRank``; both forms are accepted.
    """
    token = rank.strip().rsplit("#", 1)[-1].removesuffix("Rank").strip().casefold()
    return _RANK_BY_NAME.get(token, WikidataRank.NORMAL)


def source_type_for_references(reference_count: int) -> SourceType:
    """A referenced Wikidata statement is ``WIKIDATA_WITH_REF``; an unreferenced one ``…_NO_REF``.

    This is the single rule that turns Wikidata's reference signal into a reliability tier (0.90 vs
    0.60 in the rubric, before the rank multiplier).
    """
    return SourceType.WIKIDATA_WITH_REF if reference_count > 0 else SourceType.WIKIDATA_NO_REF


def domain_for(instance_of: tuple[str, ...]) -> Domain:
    """Map a node's ``P31`` classes to a :class:`Domain`, taking the first that is known.

    Classes are consulted in order, so callers should pass the most specific class first. Falls back
    to :data:`DOMAIN_FALLBACK` when none is recognised.
    """
    for qid in instance_of:
        domain = INSTANCE_OF_DOMAIN.get(qid)
        if domain is not None:
            return domain
    return DOMAIN_FALLBACK


def make_source(
    subject_qid: str, pid: str, object_qid: str, rank: str, reference_count: int
) -> Source:
    """Build the deterministic :class:`Source` backing one harvested Wikidata statement.

    The id encodes the exact statement (subject, property, object) so the same Wikidata fact always
    yields the same, de-duplicable source record.
    """
    return Source(
        id=f"wd_{subject_qid}_{pid}_{object_qid}",
        source_type=source_type_for_references(reference_count),
        url=f"https://www.wikidata.org/wiki/{subject_qid}#{pid}",
        rank=parse_rank(rank),
    )
