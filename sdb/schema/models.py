"""Pydantic data models — the statement-reified, Wikidata-aligned contract.

Reifying each claim as a :class:`Statement` (rather than putting provenance on a flat edge) is what
lets multiple independent sources corroborate the same fact, which the deterministic trust math in
:mod:`sdb.engine.confidence` depends on.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sdb.constants import SOURCE_RELIABILITY, WIKIDATA_RANK_MULTIPLIER
from sdb.schema.enums import (
    Archetype,
    Domain,
    Predicate,
    Region,
    SourceType,
    TimePrecision,
    WikidataRank,
)

# Statement rank refines reliability only for Wikidata sources (it is a Wikidata concept).
_RANKED_SOURCE_TYPES = frozenset({SourceType.WIKIDATA_WITH_REF, SourceType.WIKIDATA_NO_REF})


class Source(BaseModel):
    """A single provenance record backing a :class:`Statement`."""

    model_config = ConfigDict(frozen=True)

    id: str
    source_type: SourceType
    url: str | None = None
    rank: WikidataRank = WikidataRank.NORMAL

    @property
    def reliability(self) -> float:
        """Deterministic reliability (0..1) from the rubric.

        The base value comes from the source type; for Wikidata sources it is further multiplied by
        the statement-rank multiplier. Non-Wikidata sources ignore ``rank``.
        """
        base = SOURCE_RELIABILITY[self.source_type]
        if self.source_type in _RANKED_SOURCE_TYPES:
            return base * WIKIDATA_RANK_MULTIPLIER[self.rank]
        return base


class Node(BaseModel):
    """An entity in the graph. Year fields are signed (negative = BCE).

    A node carries **two** temporal axes (ADR 0041). ``start_year``/``end_year`` are the *existence*
    extent ("does this still exist?"). For a still-living civilisation ``end_year`` is the present,
    so the extent's midpoint describes nothing — India's is ``(-3300 + 2025) / 2 = -638``, an
    Iron-Age year it means nothing in. ``active_start``/``active_end`` are the *active period*: the
    floruit / era of peak influence — which is what the surprise rubric actually wants when it asks
    "when was this thing?". :attr:`midpoint_year` (and thus the ``temporal_gap`` term and the
    ``FOLLOWS`` check that read it) prefers the active period, falling back to the existence extent
    when it is absent. All curated nodes carry an active period; harvested nodes may not, and fall
    back.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    domain: Domain
    type: str
    region: Region | None = None
    wikidata_qid: str | None = None
    aliases: tuple[str, ...] = ()
    summary: str = ""
    start_year: int | None = None
    end_year: int | None = None
    active_start: int | None = None
    active_end: int | None = None
    time_precision: TimePrecision | None = None

    @staticmethod
    def _midpoint(start: int | None, end: int | None) -> float | None:
        """Midpoint of a signed-year interval, filling one open side from the other."""
        lo = start if start is not None else end
        hi = end if end is not None else start
        if lo is None or hi is None:
            return None
        return (lo + hi) / 2.0

    @property
    def active_midpoint(self) -> float | None:
        """Midpoint of the node's active period (floruit), or ``None`` if it has none."""
        return self._midpoint(self.active_start, self.active_end)

    @property
    def midpoint_year(self) -> float | None:
        """Representative year for temporal scoring: the active-period midpoint when present.

        Prefers the *active period* (:attr:`active_midpoint`) so a long-lived node reads its floruit
        rather than a midpoint stretched to the present (ADR 0041). Falls back to the *existence*
        extent (``start_year``/``end_year``) when no active period is curated, and is ``None`` when
        the node is wholly undated.
        """
        active = self.active_midpoint
        if active is not None:
            return active
        return self._midpoint(self.start_year, self.end_year)


class Statement(BaseModel):
    """A reified claim ``(subject) --predicate--> (object)`` with provenance.

    ``subject`` and ``object`` are :class:`Node` ids. ``link_quality`` (0..1) records how
    confidently the endpoints were resolved to those canonical ids (1.0 for hand-curated data).

    Two curated prose fields, both distinct in job (ADR 0042):

    - ``evidence`` — the fuller one-sentence *justification* for this specific claim, rendered under
      its hop so the chain reads as sourced evidence (ADR 0037).
    - ``headline`` — a tighter, self-contained one-fact line, a faithful compression of ``evidence``
      (so it inherits the same provenance). When this statement is a discovered path's *payoff*
      (last) hop, :func:`sdb.engine.narrate.narrate` uses it as the card's single quantized "TIL";
      the mechanical predicate chain remains the fallback for any statement without one.
    """

    model_config = ConfigDict(frozen=True)

    subject: str
    predicate: Predicate
    object: str
    sources: tuple[Source, ...]
    evidence: str = ""
    headline: str = ""
    link_quality: float = Field(default=1.0, ge=0.0, le=1.0)


class SeedData(BaseModel):
    """The on-disk seed graph: a list of nodes and a list of statements."""

    nodes: tuple[Node, ...]
    statements: tuple[Statement, ...]


class Hop(BaseModel):
    """One step along a discovered path.

    ``is_reversed`` is ``True`` when the (directed) statement was traversed object→subject, which
    the narrator uses to pick the correctly-directed phrasing.
    """

    model_config = ConfigDict(frozen=True)

    from_id: str
    to_id: str
    statement: Statement
    is_reversed: bool


class Path(BaseModel):
    """An ordered chain of nodes connected by hops."""

    model_config = ConfigDict(frozen=True)

    node_ids: tuple[str, ...]
    hops: tuple[Hop, ...]

    @property
    def length(self) -> int:
        """Number of hops (edges) in the path."""
        return len(self.hops)


class DiscoveryResult(BaseModel):
    """A ranked result: a path with its deterministic scores and a templated TIL.

    ``score`` is the archetype's ranking key: for :attr:`~sdb.schema.enums.Archetype.JOURNEY` it is
    the wow score ``surprise x trust``; for :attr:`~sdb.schema.enums.Archetype.UNLIKELY` it is
    ``endpoint_unexpectedness x trust`` (the improbability of the destination).
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    archetype: Archetype
    trust: float
    surprise: float
    endpoint_unexpectedness: float
    score: float
    til: str
    possibly: bool
