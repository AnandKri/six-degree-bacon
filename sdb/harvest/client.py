"""Clients that fetch raw Wikidata facts for the harvester.

The harvester depends only on the :class:`SparqlClient` protocol, so the live
:class:`WikidataClient` (which talks to the public SPARQL endpoint) and the offline
:class:`FakeSparqlClient` (canned data, used by the tests and by snapshot replay) are
interchangeable. All returned records are plain, frozen dataclasses — no live query objects escape
this module.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from sdb.harvest.mapping import HARVEST_PROPERTIES

_ENDPOINT = "https://query.wikidata.org/sparql"
_USER_AGENT = "six-degree-bacon/0.1 (https://github.com/AnandKri/six-degree-bacon)"
_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class NeighborEdge:
    """One curated Wikidata statement leaving a subject: ``subject --property--> target``.

    ``rank`` is the raw Wikidata rank word and ``reference_count`` the number of references on the
    statement; together they determine the harvested source's reliability (see
    :mod:`sdb.harvest.mapping`).
    """

    property_pid: str
    target_qid: str
    rank: str
    reference_count: int


@dataclass(frozen=True)
class EntityFacts:
    """The descriptive facts needed to build a :class:`~sdb.schema.models.Node` for one item.

    The four date fields are the raw Wikidata signals (all signed, negative = BCE); the harvester
    folds them into one ``(start_year, end_year)`` extent via
    :func:`~sdb.harvest.mapping.temporal_extent`. Things carry ``inception_year`` /
    ``dissolved_year``, people carry ``birth_year`` / ``death_year``; an item never carries both.
    """

    qid: str
    label: str
    description: str = ""
    instance_of: tuple[str, ...] = ()
    inception_year: int | None = None
    birth_year: int | None = None
    death_year: int | None = None
    dissolved_year: int | None = None


@runtime_checkable
class SparqlClient(Protocol):
    """Fetches curated neighbours of an item and descriptive facts for a set of items."""

    def neighbors(self, qid: str) -> tuple[NeighborEdge, ...]:
        """Return the curated outgoing statements of ``qid`` (empty if it has none)."""
        ...

    def entities(self, qids: Sequence[str]) -> dict[str, EntityFacts]:
        """Return descriptive facts for each requested QID that resolves."""
        ...


def _iri_tail(iri: str) -> str:
    """Return the entity id at the tail of a Wikidata IRI (``…/entity/Q42`` → ``Q42``)."""
    return iri.rsplit("/", 1)[-1]


class WikidataClient:
    """A :class:`SparqlClient` backed by the live Wikidata Query Service."""

    def __init__(
        self,
        *,
        endpoint: str = _ENDPOINT,
        user_agent: str = _USER_AGENT,
        timeout: int = _TIMEOUT_SECONDS,
    ) -> None:
        """Configure the endpoint, ``User-Agent`` (Wikidata requires one), and request timeout."""
        self._endpoint = endpoint
        self._user_agent = user_agent
        self._timeout = timeout

    def _run(self, query: str) -> list[dict[str, Any]]:
        """Execute a SPARQL query and return its result bindings."""
        url = f"{self._endpoint}?{urllib.parse.urlencode({'format': 'json', 'query': query})}"
        request = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload: dict[str, Any] = json.load(response)
        bindings: list[dict[str, Any]] = payload["results"]["bindings"]
        return bindings

    def neighbors(self, qid: str) -> tuple[NeighborEdge, ...]:
        """Query the reified statements of ``qid`` over the curated properties."""
        values = " ".join(f"wd:{pid}" for pid in HARVEST_PROPERTIES)
        query = f"""
        SELECT ?prop ?target ?rank (COUNT(DISTINCT ?ref) AS ?refCount) WHERE {{
          VALUES ?propEntity {{ {values} }}
          ?propEntity wikibase:claim ?claim ; wikibase:statementProperty ?ps .
          BIND(STRAFTER(STR(?propEntity), "entity/") AS ?prop)
          wd:{qid} ?claim ?statement .
          ?statement ?ps ?target .
          ?statement wikibase:rank ?rankNode .
          BIND(STRAFTER(STR(?rankNode), "#") AS ?rank)
          OPTIONAL {{ ?statement prov:wasDerivedFrom ?ref . }}
          FILTER(isIRI(?target))
        }}
        GROUP BY ?prop ?target ?rank
        """
        edges: list[NeighborEdge] = []
        for row in self._run(query):
            target = row.get("target", {}).get("value")
            if target is None:
                continue
            edges.append(
                NeighborEdge(
                    property_pid=row["prop"]["value"],
                    target_qid=_iri_tail(target),
                    rank=row.get("rank", {}).get("value", "normal"),
                    reference_count=int(row.get("refCount", {}).get("value", "0")),
                )
            )
        edges.sort(key=lambda e: (e.property_pid, e.target_qid))
        return tuple(edges)

    def entities(self, qids: Sequence[str]) -> dict[str, EntityFacts]:
        """Fetch labels, descriptions, ``P31`` classes and the date properties for ``qids``.

        Dates: inception (P571) and dissolution (P576) for things, birth (P569) and death (P570) for
        people. Each is optional and independently multi-valued; the ``(item x p31 x dates)`` row
        product is collapsed by :func:`_fold_entities` (earliest start, latest end; order-free).
        """
        if not qids:
            return {}
        values = " ".join(f"wd:{qid}" for qid in dict.fromkeys(qids))
        query = f"""
        SELECT ?item ?label ?description ?p31 ?inception ?birth ?death ?dissolved WHERE {{
          VALUES ?item {{ {values} }}
          OPTIONAL {{ ?item rdfs:label ?label . FILTER(LANG(?label) = "en") }}
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
          OPTIONAL {{ ?item wdt:P31 ?p31Node . BIND(STRAFTER(STR(?p31Node), "entity/") AS ?p31) }}
          OPTIONAL {{ ?item wdt:P571 ?inc . BIND(YEAR(?inc) AS ?inception) }}
          OPTIONAL {{ ?item wdt:P569 ?dob . BIND(YEAR(?dob) AS ?birth) }}
          OPTIONAL {{ ?item wdt:P570 ?dod . BIND(YEAR(?dod) AS ?death) }}
          OPTIONAL {{ ?item wdt:P576 ?dis . BIND(YEAR(?dis) AS ?dissolved) }}
        }}
        """
        return _fold_entities(self._run(query))


def _keep_year(store: dict[str, int], qid: str, value: int, *, latest: bool) -> None:
    """Fold one year into ``store`` deterministically: keep the latest if ``latest`` else earliest.

    A single item can expose several values for a date property (disputed births, staged
    dissolutions); picking min for starts and max for ends makes the harvest independent of SPARQL
    row order.
    """
    current = store.get(qid)
    if current is None:
        store[qid] = value
    else:
        store[qid] = max(current, value) if latest else min(current, value)


def _fold_entities(rows: list[dict[str, Any]]) -> dict[str, EntityFacts]:
    """Collapse the (item x P31 x dates) row product from the entities query into one record."""
    labels: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    inceptions: dict[str, int] = {}
    births: dict[str, int] = {}
    deaths: dict[str, int] = {}
    dissolutions: dict[str, int] = {}
    classes: dict[str, list[str]] = {}
    for row in rows:
        qid = _iri_tail(row["item"]["value"])
        if "label" in row:
            labels[qid] = row["label"]["value"]
        if "description" in row:
            descriptions[qid] = row["description"]["value"]
        if "inception" in row:
            _keep_year(inceptions, qid, int(row["inception"]["value"]), latest=False)
        if "birth" in row:
            _keep_year(births, qid, int(row["birth"]["value"]), latest=False)
        if "death" in row:
            _keep_year(deaths, qid, int(row["death"]["value"]), latest=True)
        if "dissolved" in row:
            _keep_year(dissolutions, qid, int(row["dissolved"]["value"]), latest=True)
        if "p31" in row:
            bucket = classes.setdefault(qid, [])
            if row["p31"]["value"] not in bucket:
                bucket.append(row["p31"]["value"])
    seen = (
        set(labels)
        | set(descriptions)
        | set(classes)
        | set(inceptions)
        | set(births)
        | set(deaths)
        | set(dissolutions)
    )
    return {
        qid: EntityFacts(
            qid=qid,
            label=labels.get(qid, qid),
            description=descriptions.get(qid, ""),
            instance_of=tuple(classes.get(qid, ())),
            inception_year=inceptions.get(qid),
            birth_year=births.get(qid),
            death_year=deaths.get(qid),
            dissolved_year=dissolutions.get(qid),
        )
        for qid in seen
    }


@dataclass
class FakeSparqlClient:
    """An offline :class:`SparqlClient` serving canned data — for tests and snapshot replay."""

    edges: dict[str, tuple[NeighborEdge, ...]] = field(default_factory=dict)
    facts: dict[str, EntityFacts] = field(default_factory=dict)

    def neighbors(self, qid: str) -> tuple[NeighborEdge, ...]:
        """Return the canned neighbours for ``qid`` (empty tuple if none were registered)."""
        return self.edges.get(qid, ())

    def entities(self, qids: Sequence[str]) -> dict[str, EntityFacts]:
        """Return canned facts for each requested QID that is known."""
        return {qid: self.facts[qid] for qid in qids if qid in self.facts}
