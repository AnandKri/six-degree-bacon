"""Controlled vocabularies for the knowledge graph, aligned to Wikidata where possible.

These enums are leaf definitions with no dependencies on the rest of the package, so they can be
imported freely (the scoring rubric in :mod:`sdb.constants` is keyed by them).
"""

from __future__ import annotations

from enum import StrEnum


class Domain(StrEnum):
    """Thematic domain of a node — the axis whose *changes* make a path surprising.

    ``OTHER`` is the deliberate "not yet classified" bucket for harvested nodes whose ``P31`` class
    is unmapped (:data:`sdb.harvest.mapping.DOMAIN_FALLBACK`); it is never a curated node's domain.
    Keeping it distinct from a real domain is what stops unclassified harvest fallout from inflating
    a substantive domain's territory — see ADR 0032.

    Order is load-bearing: :func:`sdb.layout.compute_layout` seeds positions by ``(domain, id)``
    using this enum's ordinal, so a new member must be **appended**, never inserted, or every
    existing map shifts (ADR 0030's byte-identical guarantee).
    """

    MYTH = "myth"
    HISTORY = "history"
    GENEALOGY = "genealogy"
    TRADE = "trade"
    LANGUAGE = "language"
    GEOGRAPHY = "geography"
    CULTURE = "culture"
    RELIGION = "religion"
    SCIENCE = "science"
    ART = "art"
    OTHER = "other"


class Region(StrEnum):
    """Macro-cultural sphere of a node — the *cultural/regional* axis, distinct from ``Domain``.

    ``Domain`` models a node's *discipline* (science, history, religion...), so a
    Polish -> Persian -> Greek -> Indian science lineage crosses **zero** domains and its cultural
    surprise is invisible to :func:`sdb.engine.surprise._domain_jumps`. ``Region`` supplies the
    missing axis: a *region jump* is a hop between two mutually-foreign civilisations, scored by an
    independent, additive surprise term (ADR 0039) that mirrors ADR 0034's domain-jump weighting.

    Granularity is **civilisational**, deliberately coarse: the Greco-Roman-Byzantine-Renaissance
    continuum is a single ``WESTERN`` sphere, because the Renaissance revived antiquity — moving
    Rome -> Ancient Greece is staying inside one ancestral tradition, not crossing into a foreign
    culture. A finer split let a Western-canon walking tour (Rome -> Greece -> Renaissance -> Plato)
    farm three "cultural" crossings while a genuinely trans-Eurasian route banked fewer; the
    macro-sphere model reflects real cultural distance instead (measured in ADR 0039).

    A node's region is the culture it is *rooted in* (a religion's birthplace, a person's home),
    not everywhere it later spread; a trans-cultural route takes its heartland (the Silk Road is
    ``CENTRAL_ASIAN``). Unlike :class:`Domain` this enum feeds no layout, so members may be added in
    any order.
    """

    WESTERN = "western"  # Greco-Roman-Byzantine-European continuum
    NORSE_GERMANIC = "norse_germanic"
    NEAR_EASTERN = "near_eastern"  # Persia, Mesopotamia, the Islamic Middle East, the Levant
    EGYPTIAN = "egyptian"
    SOUTH_ASIAN = "south_asian"
    SOUTHEAST_ASIAN = "southeast_asian"
    SINITIC = "sinitic"  # the Chinese cultural sphere
    JAPANESE = "japanese"
    WEST_AFRICAN = "west_african"
    CENTRAL_ASIAN = "central_asian"  # the Eurasian steppe / Silk Road heartland


class Predicate(StrEnum):
    """Relationship types, mapped to Wikidata properties where one exists.

    The Wikidata property id (or ``None`` for project-specific predicates) is in
    :data:`PREDICATE_WIKIDATA`; human-readable phrasings for the narrator are in
    :data:`PREDICATE_PHRASE` / :data:`PREDICATE_PHRASE_REVERSED`.
    """

    INFLUENCED_BY = "influenced_by"
    FOLLOWS = "follows"
    PART_OF = "part_of"
    LOCATED_IN = "located_in"
    NAMED_AFTER = "named_after"
    DERIVED_FROM = "derived_from"
    CLAIMED_DESCENT_FROM = "claimed_descent_from"
    MYTHOLOGICALLY_RELATED_TO = "mythologically_related_to"
    ON_TRADE_ROUTE = "on_trade_route"
    MENTIONED_IN = "mentioned_in"
    INSPIRED_BY = "inspired_by"
    CONNECTED_VIA_TRADE = "connected_via_trade"


PREDICATE_WIKIDATA: dict[Predicate, str | None] = {
    Predicate.INFLUENCED_BY: "P737",  # influenced by
    Predicate.FOLLOWS: "P155",  # follows
    Predicate.PART_OF: "P361",  # part of
    Predicate.LOCATED_IN: "P276",  # location
    Predicate.NAMED_AFTER: "P138",  # named after
    Predicate.DERIVED_FROM: "P144",  # based on / derived from
    Predicate.MENTIONED_IN: "P1343",  # described by source
    Predicate.INSPIRED_BY: "P941",  # inspired by
    Predicate.CLAIMED_DESCENT_FROM: None,  # project-specific
    Predicate.MYTHOLOGICALLY_RELATED_TO: None,
    Predicate.ON_TRADE_ROUTE: None,
    Predicate.CONNECTED_VIA_TRADE: None,
}

PREDICATE_PHRASE: dict[Predicate, str] = {
    Predicate.INFLUENCED_BY: "was influenced by",
    Predicate.FOLLOWS: "followed",
    Predicate.PART_OF: "was part of",
    Predicate.LOCATED_IN: "was located in",
    Predicate.NAMED_AFTER: "was named after",
    Predicate.DERIVED_FROM: "derived from",
    Predicate.CLAIMED_DESCENT_FROM: "claimed descent from",
    Predicate.MYTHOLOGICALLY_RELATED_TO: "is mythologically related to",
    Predicate.ON_TRADE_ROUTE: "sat on",
    Predicate.MENTIONED_IN: "was mentioned in",
    Predicate.INSPIRED_BY: "was inspired by",
    Predicate.CONNECTED_VIA_TRADE: "was connected via trade to",
}

PREDICATE_PHRASE_REVERSED: dict[Predicate, str] = {
    Predicate.INFLUENCED_BY: "influenced",
    Predicate.FOLLOWS: "was followed by",
    Predicate.PART_OF: "contained",
    Predicate.LOCATED_IN: "was the location of",
    Predicate.NAMED_AFTER: "gave its name to",
    Predicate.DERIVED_FROM: "gave rise to",
    Predicate.CLAIMED_DESCENT_FROM: "is claimed as an ancestor of",
    Predicate.MYTHOLOGICALLY_RELATED_TO: "is mythologically related to",
    Predicate.ON_TRADE_ROUTE: "ran through",
    Predicate.MENTIONED_IN: "mentions",
    Predicate.INSPIRED_BY: "inspired",
    Predicate.CONNECTED_VIA_TRADE: "was connected via trade to",
}


class SourceType(StrEnum):
    """Provenance categories; each maps to a fixed reliability in the rubric."""

    WIKIDATA_WITH_REF = "wikidata_with_ref"
    WIKIDATA_NO_REF = "wikidata_no_ref"
    WIKIPEDIA = "wikipedia"
    DBPEDIA_INFERRED = "dbpedia_inferred"
    SECONDARY_BOOK = "secondary_book"
    OPEN_TEXT = "open_text"
    MYTH_LEGEND = "myth_legend"


class WikidataRank(StrEnum):
    """Wikidata statement rank, refining a source's reliability."""

    PREFERRED = "preferred"
    NORMAL = "normal"
    DEPRECATED = "deprecated"


class TimePrecision(StrEnum):
    """Precision of a node's temporal extent."""

    YEAR = "year"
    DECADE = "decade"
    CENTURY = "century"
    MILLENNIUM = "millennium"
    CIRCA = "circa"


class Archetype(StrEnum):
    """A shape of "wow" a result can have — the two are ranked on their own scales.

    ``JOURNEY`` is the cross-domain chain, scored by ``surprise x trust``. ``UNLIKELY`` is the
    *improbable adjacency* — a short link between two entities that feel worlds apart — scored by
    ``endpoint_unexpectedness x trust`` so the improbability of the *destination*, not the length of
    the route, decides it (see ADR 0007).
    """

    JOURNEY = "journey"
    UNLIKELY = "unlikely"
