"""Harvest Wikipedia-link co-occurrence: which seed nodes each node's article links to.

This is the *real co-occurrence* signal behind the endpoint-surprise term (see
:mod:`sdb.engine.surprise`). If Wikipedia's article for *A* links to *B*, the two are an expected
pairing; the absence of a link marks *B* as a surprising destination from *A*. The harvested matrix
is committed to ``data/cooccurrence.json`` and read deterministically offline thereafter.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from typing import Any, Protocol, runtime_checkable

from sdb.schema.models import Node

_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_USER_AGENT = "six-degree-bacon/0.1 (https://github.com/AnandKri/six-degree-bacon)"
_TIMEOUT_SECONDS = 60
_MAX_CONTINUATIONS = 10
# A busy article can list well over a thousand namespace-0 links; 500 arrive per request, so allow
# a deeper (but still bounded) walk when fetching the *unfiltered* set for the similarity matrix.
_MAX_LINK_CONTINUATIONS = 12


@runtime_checkable
class WikipediaClient(Protocol):
    """Resolves entities to article titles and reports links between articles."""

    def titles_for(self, qids: Sequence[str]) -> dict[str, str]:
        """Return the English Wikipedia title for each QID that has one."""
        ...

    def outbound_links(self, title: str, candidates: Sequence[str]) -> frozenset[str]:
        """Return which of ``candidates`` the article ``title`` links to (namespace-0 links)."""
        ...

    def all_outbound_links(self, title: str) -> frozenset[str]:
        """Return *every* namespace-0 article ``title`` links to (not just the seed nodes)."""
        ...


def build_cooccurrence(
    nodes: Iterable[Node], client: WikipediaClient
) -> tuple[dict[str, list[str]], dict[str, dict[str, float]]]:
    """Build the co-occurrence link matrix **and** the full-link similarity matrix.

    Two signals, both restricted to seed *pairs* but measured over different universes:

    - ``links`` — ``{node_id: [linked node ids]}``, the direct seed→seed Wikipedia links. This
      is the first-order strength (0, 1 or 2 link directions).
    - ``similarity`` — ``{node_id: {node_id: jaccard}}``, the Jaccard overlap of the two articles'
      **full** outbound link sets. Measuring shared context over the whole encyclopaedia rather than
      the seed-sized keyhole is what keeps the second-order term informative for peripheral nodes
      (ADR 0029): a node may link only one *seed* node yet still share hundreds of articles with
      another. Only non-zero, rounded values are emitted, and each pair is stored once (a < b).

    A node's Wikipedia title comes from its Wikidata sitelink when a ``wikidata_qid`` is present,
    otherwise from its label. Nodes whose article cannot be resolved are simply absent (and thus
    treated as maximally surprising destinations by the scorer). Output is sorted for a stable,
    diff-friendly committed file.
    """
    node_list = list(nodes)
    title_of = _resolve_titles(node_list, client)
    id_of_title = {title.casefold(): node_id for node_id, title in title_of.items()}
    candidate_titles = sorted(set(title_of.values()))

    matrix: dict[str, list[str]] = {}
    full_links: dict[str, frozenset[str]] = {}
    for node in node_list:
        title = title_of.get(node.id)
        if title is None:
            continue
        linked_ids = {
            id_of_title[link.casefold()]
            for link in client.outbound_links(title, candidate_titles)
            if link.casefold() in id_of_title
        }
        linked_ids.discard(node.id)
        if linked_ids:
            matrix[node.id] = sorted(linked_ids)
        full_links[node.id] = frozenset(
            link.casefold() for link in client.all_outbound_links(title)
        )

    return matrix, _similarity_matrix(full_links)


def _similarity_matrix(
    full_links: dict[str, frozenset[str]],
) -> dict[str, dict[str, float]]:
    """Pairwise Jaccard overlap of full outbound link sets, stored once per pair (a < b)."""
    similarity: dict[str, dict[str, float]] = {}
    ids = sorted(full_links)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            left, right = full_links[a], full_links[b]
            union = len(left | right)
            if not union:
                continue
            score = round(len(left & right) / union, 6)
            if score:
                similarity.setdefault(a, {})[b] = score
    return similarity


def _resolve_titles(nodes: Sequence[Node], client: WikipediaClient) -> dict[str, str]:
    """Resolve each node id to an article title (Wikidata sitelink first, else the label)."""
    qid_to_node = {node.wikidata_qid: node.id for node in nodes if node.wikidata_qid is not None}
    title_by_qid = client.titles_for(sorted(qid_to_node)) if qid_to_node else {}

    title_of: dict[str, str] = {}
    for node in nodes:
        if node.wikidata_qid is not None and node.wikidata_qid in title_by_qid:
            title_of[node.id] = title_by_qid[node.wikidata_qid]
        else:
            title_of[node.id] = node.label
    return title_of


class LiveWikipediaClient:
    """A :class:`WikipediaClient` backed by the live Wikipedia and Wikidata APIs."""

    def __init__(self, *, user_agent: str = _USER_AGENT, timeout: int = _TIMEOUT_SECONDS) -> None:
        """Configure the ``User-Agent`` sent to both APIs and the per-request timeout."""
        self._headers = {"User-Agent": user_agent}
        self._timeout = timeout

    def _get(self, base: str, params: dict[str, str]) -> dict[str, Any]:
        """Issue a GET to a MediaWiki API and return the parsed JSON."""
        url = f"{base}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload: dict[str, Any] = json.load(response)
        return payload

    def titles_for(self, qids: Sequence[str]) -> dict[str, str]:
        """Fetch the ``enwiki`` sitelink title for each QID via ``wbgetentities``."""
        titles: dict[str, str] = {}
        batch = list(dict.fromkeys(qids))
        for start in range(0, len(batch), 50):  # wbgetentities accepts up to 50 ids per call
            chunk = batch[start : start + 50]
            payload = self._get(
                _WIKIDATA_API,
                {
                    "action": "wbgetentities",
                    "format": "json",
                    "props": "sitelinks",
                    "sitefilter": "enwiki",
                    "ids": "|".join(chunk),
                },
            )
            for qid, entity in payload.get("entities", {}).items():
                sitelink = entity.get("sitelinks", {}).get("enwiki")
                if sitelink is not None:
                    titles[qid] = sitelink["title"]
        return titles

    def all_outbound_links(self, title: str) -> frozenset[str]:
        """Return every namespace-0 article ``title`` links to, following ``plcontinue`` pagination.

        Unlike :meth:`outbound_links` this is *not* filtered to the seed, so a busy article yields
        hundreds of titles — the wide universe the Jaccard similarity needs (ADR 0029). The
        continuation budget bounds a pathological page; a truncated set only makes the similarity
        conservative (smaller overlap), never wrong in a way that invents surprise.
        """
        found: set[str] = set()
        plcontinue: str | None = None
        for _ in range(_MAX_LINK_CONTINUATIONS):
            params = {
                "action": "query",
                "format": "json",
                "prop": "links",
                "titles": title,
                "plnamespace": "0",
                "pllimit": "max",
                "redirects": "1",
            }
            if plcontinue is not None:
                params["plcontinue"] = plcontinue
            payload = self._get(_WIKIPEDIA_API, params)
            for page in payload.get("query", {}).get("pages", {}).values():
                for link in page.get("links", []):
                    found.add(link["title"])
            cont = payload.get("continue")
            if cont is None:
                break
            plcontinue = cont.get("plcontinue")
        return frozenset(found)

    def outbound_links(self, title: str, candidates: Sequence[str]) -> frozenset[str]:
        """Return the subset of ``candidates`` that ``title`` links to (following redirects).

        ``pltitles`` accepts at most 50 values per query, so candidates are chunked by 50 (otherwise
        an over-long list is silently rejected and no links come back — which breaks once the seed
        grows past 50 nodes); the per-chunk results are unioned.
        """
        if not candidates:
            return frozenset()
        found: set[str] = set()
        unique = list(dict.fromkeys(candidates))
        for start in range(0, len(unique), 50):
            chunk = unique[start : start + 50]
            plcontinue: str | None = None
            for _ in range(_MAX_CONTINUATIONS):
                params = {
                    "action": "query",
                    "format": "json",
                    "prop": "links",
                    "titles": title,
                    "plnamespace": "0",
                    "pltitles": "|".join(chunk),
                    "pllimit": "max",
                    "redirects": "1",
                }
                if plcontinue is not None:
                    params["plcontinue"] = plcontinue
                payload = self._get(_WIKIPEDIA_API, params)
                for page in payload.get("query", {}).get("pages", {}).values():
                    for link in page.get("links", []):
                        found.add(link["title"])
                cont = payload.get("continue")
                if cont is None:
                    break
                plcontinue = cont.get("plcontinue")
        return frozenset(found)
