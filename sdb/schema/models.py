"""Pydantic data models — the statement-reified, Wikidata-aligned contract.

Reifying each claim as a :class:`Statement` (rather than putting provenance on a flat edge) is what
lets multiple independent sources corroborate the same fact, which the deterministic trust math in
:mod:`sdb.engine.confidence` depends on.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sdb.constants import SOURCE_RELIABILITY, WIKIDATA_RANK_MULTIPLIER
from sdb.schema.enums import Domain, Predicate, SourceType, TimePrecision, WikidataRank

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
    """An entity in the graph. ``start_year``/``end_year`` are signed (negative = BCE)."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    domain: Domain
    type: str
    wikidata_qid: str | None = None
    aliases: tuple[str, ...] = ()
    summary: str = ""
    start_year: int | None = None
    end_year: int | None = None
    time_precision: TimePrecision | None = None

    @property
    def midpoint_year(self) -> float | None:
        """Midpoint of the node's temporal extent, or ``None`` if undated."""
        start = self.start_year if self.start_year is not None else self.end_year
        end = self.end_year if self.end_year is not None else self.start_year
        if start is None or end is None:
            return None
        return (start + end) / 2.0


class Statement(BaseModel):
    """A reified claim ``(subject) --predicate--> (object)`` with provenance.

    ``subject`` and ``object`` are :class:`Node` ids. ``link_quality`` (0..1) records how
    confidently the endpoints were resolved to those canonical ids (1.0 for hand-curated data).
    """

    model_config = ConfigDict(frozen=True)

    subject: str
    predicate: Predicate
    object: str
    sources: tuple[Source, ...]
    evidence: str = ""
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
    """A ranked result: a path with its deterministic scores and a templated TIL."""

    model_config = ConfigDict(frozen=True)

    path: Path
    trust: float
    surprise: float
    til: str
    possibly: bool
