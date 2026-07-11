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

# Properties kept in the vocabulary but never harvested. "Described by source" (P1343) is Wikidata's
# *bibliographic* citation relation (an entity is described in reference work Y), carried in bulk to
# old public-domain encyclopedias (Brockhaus, Meyers, Nuttall…). That is pure clutter for path
# discovery and semantically unlike our content-oriented MENTIONED_IN, so we harvest neither it nor
# the reference works it drags in.
HARVEST_EXCLUDED_PROPERTIES: frozenset[str] = frozenset({"P1343"})

# Inverse of PREDICATE_WIKIDATA (predicates with a canonical Wikidata property) plus the aliases. A
# harvested statement whose property is absent here is outside our vocabulary and is skipped.
WIKIDATA_PREDICATE: dict[str, Predicate] = {
    pid: predicate for predicate, pid in PREDICATE_WIKIDATA.items() if pid is not None
} | HARVEST_PREDICATE_ALIASES

# The Wikidata properties we actually query and harvest (vocabulary minus the excluded clutter).
HARVEST_PROPERTIES: tuple[str, ...] = tuple(
    pid for pid in sorted(WIKIDATA_PREDICATE) if pid not in HARVEST_EXCLUDED_PROPERTIES
)

# Wikidata "instance of" (P31) class → thematic Domain. Deterministic and grown from the classes
# that actually recur near the seed's themes; anything unmapped falls back to DOMAIN_FALLBACK. Every
# QID here is verified against Wikidata (label in the comment) — a wrong QID silently mis-domains a
# whole class of nodes, the ADR 0008 failure mode. Extend as the harvest set grows.
INSTANCE_OF_DOMAIN: dict[str, Domain] = {
    # -- geography -----------------------------------------------------------------------------
    "Q6256": Domain.GEOGRAPHY,  # country
    "Q515": Domain.GEOGRAPHY,  # city
    "Q1549591": Domain.GEOGRAPHY,  # big city
    "Q5119": Domain.GEOGRAPHY,  # capital city
    "Q486972": Domain.GEOGRAPHY,  # human settlement
    "Q3957": Domain.GEOGRAPHY,  # small town
    "Q532": Domain.GEOGRAPHY,  # village
    "Q15284": Domain.GEOGRAPHY,  # municipality
    "Q34876": Domain.GEOGRAPHY,  # province
    "Q56061": Domain.GEOGRAPHY,  # administrative territorial entity
    "Q82794": Domain.GEOGRAPHY,  # geographic region
    "Q1620908": Domain.GEOGRAPHY,  # historical region
    "Q839954": Domain.GEOGRAPHY,  # archaeological site
    "Q4022": Domain.GEOGRAPHY,  # river
    "Q23397": Domain.GEOGRAPHY,  # lake
    "Q165": Domain.GEOGRAPHY,  # sea
    "Q23442": Domain.GEOGRAPHY,  # island
    "Q34763": Domain.GEOGRAPHY,  # peninsula
    "Q8502": Domain.GEOGRAPHY,  # mountain
    "Q46831": Domain.GEOGRAPHY,  # mountain range
    "Q39816": Domain.GEOGRAPHY,  # valley
    "Q8514": Domain.GEOGRAPHY,  # desert
    "Q107425": Domain.GEOGRAPHY,  # landscape
    # -- history -------------------------------------------------------------------------------
    "Q3624078": Domain.HISTORY,  # sovereign state
    "Q7275": Domain.HISTORY,  # state
    "Q417175": Domain.HISTORY,  # kingdom
    "Q3024240": Domain.HISTORY,  # historical country
    "Q28171280": Domain.HISTORY,  # ancient civilization
    "Q48349": Domain.HISTORY,  # empire
    "Q11514315": Domain.HISTORY,  # historical period
    "Q13418847": Domain.HISTORY,  # historical event
    "Q178561": Domain.HISTORY,  # battle
    "Q188055": Domain.HISTORY,  # siege
    "Q198": Domain.HISTORY,  # war
    "Q124734": Domain.HISTORY,  # rebellion
    "Q10931": Domain.HISTORY,  # revolution
    "Q131569": Domain.HISTORY,  # treaty
    "Q5": Domain.HISTORY,  # human
    # -- genealogy -----------------------------------------------------------------------------
    "Q7269": Domain.GENEALOGY,  # dynasty
    "Q164950": Domain.GENEALOGY,  # noble family
    # -- language ------------------------------------------------------------------------------
    "Q34770": Domain.LANGUAGE,  # language
    "Q25295": Domain.LANGUAGE,  # language family
    "Q33384": Domain.LANGUAGE,  # dialect
    "Q8192": Domain.LANGUAGE,  # writing system
    # -- religion ------------------------------------------------------------------------------
    "Q9174": Domain.RELIGION,  # religion
    "Q1530022": Domain.RELIGION,  # religious concept
    "Q13414953": Domain.RELIGION,  # religious denomination
    "Q1370598": Domain.RELIGION,  # structure of worship
    "Q44539": Domain.RELIGION,  # temple
    "Q16970": Domain.RELIGION,  # church building
    "Q44613": Domain.RELIGION,  # monastery
    # -- myth ----------------------------------------------------------------------------------
    "Q178885": Domain.MYTH,  # deity
    "Q22988604": Domain.MYTH,  # mythological figure
    "Q9134": Domain.MYTH,  # mythology
    "Q2239243": Domain.MYTH,  # mythical creature
    # -- science -------------------------------------------------------------------------------
    "Q11862829": Domain.SCIENCE,  # academic discipline
    "Q2465832": Domain.SCIENCE,  # branch of science
    "Q395": Domain.SCIENCE,  # mathematics
    "Q333": Domain.SCIENCE,  # astronomy
    "Q65943": Domain.SCIENCE,  # theorem
    "Q17737": Domain.SCIENCE,  # theory
    "Q3099911": Domain.SCIENCE,  # scientific instrument
    "Q62832": Domain.SCIENCE,  # observatory
    "Q47574": Domain.SCIENCE,  # unit of measurement
    # -- art -----------------------------------------------------------------------------------
    "Q735": Domain.ART,  # art
    "Q968159": Domain.ART,  # art movement
    "Q838948": Domain.ART,  # work of art
    "Q3305213": Domain.ART,  # painting
    "Q860861": Domain.ART,  # sculpture
    "Q2188189": Domain.ART,  # musical work
    "Q11424": Domain.ART,  # film
    # -- culture -------------------------------------------------------------------------------
    "Q41710": Domain.CULTURE,  # ethnic group
    "Q1002697": Domain.CULTURE,  # periodical / publication
    "Q571": Domain.CULTURE,  # book
    "Q47461344": Domain.CULTURE,  # written work
    # -- trade ---------------------------------------------------------------------------------
    "Q133311": Domain.TRADE,  # trade route
    "Q11446": Domain.TRADE,  # ship (proxy for trade artefacts)
    "Q28877": Domain.TRADE,  # good/s (commodity)
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


def temporal_extent(
    *,
    inception_year: int | None,
    birth_year: int | None,
    death_year: int | None,
    dissolved_year: int | None,
) -> tuple[int | None, int | None]:
    """Fold Wikidata's several date properties into one signed ``(start_year, end_year)`` extent.

    Start is inception (P571) for a thing or birth (P569) for a person; end is dissolution (P576)
    for a thing or death (P570) for a person. Inception/dissolution win if a pair somehow co-occurs,
    but it is effectively unambiguous: a person's item carries no P571/P576 and a place's no
    P569/P570, so at most one of each pair is set. This is what lets harvested *people* be dated at
    all (P571 alone left them undated) — the temporal-gap surprise term and the date validators both
    rely on it. Years are signed (BCE < 0).
    """
    start = inception_year if inception_year is not None else birth_year
    end = dissolved_year if dissolved_year is not None else death_year
    return start, end


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
