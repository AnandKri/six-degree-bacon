"""Validate that each node's ``wikidata_qid`` resolves back to that node.

This is the guard against the hallucinated-QID class of bug (ADR 0008): resolve each node's label
through its English Wikipedia article to the article's ``wikibase_item`` and confirm it equals the
stored QID. Since the seed was repaired by exactly this resolution, a mismatch means a wrong or
invented QID. The logic is a pure function of a :class:`TitleResolver`, so it is unit-tested offline
with a fake; the live resolver hits the Wikipedia API.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from sdb.schema.models import Node

_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = "six-degree-bacon/0.1 (https://github.com/AnandKri/six-degree-bacon)"
_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class QidMismatch:
    """A node whose stored QID differs from the one its Wikipedia article resolves to."""

    node_id: str
    label: str
    stored_qid: str
    resolved_qid: str | None


@runtime_checkable
class TitleResolver(Protocol):
    """Resolves article titles to the Wikidata QID each Wikipedia article is about."""

    def qids_for(self, titles: Sequence[str]) -> dict[str, str | None]:
        """Return ``{title: wikibase_item}`` for each title (value ``None`` if unresolved)."""
        ...


def validate_qids(nodes: Iterable[Node], resolver: TitleResolver) -> tuple[QidMismatch, ...]:
    """Return a mismatch for every node whose stored QID isn't what its label resolves to.

    Nodes without a ``wikidata_qid`` are skipped. Comparison is against the *resolved* QID (via the
    article, following redirects), so legitimate redirects like Persia → Iran (Q794) do not flag as
    long as the stored QID matches the resolution.
    """
    with_qid = [node for node in nodes if node.wikidata_qid is not None]
    resolved = resolver.qids_for([node.label for node in with_qid])
    mismatches: list[QidMismatch] = []
    for node in with_qid:
        stored = node.wikidata_qid
        if stored is None:  # unreachable (filtered above); narrows the type for the checker
            continue
        got = resolved.get(node.label)
        if got != stored:
            mismatches.append(QidMismatch(node.id, node.label, stored, got))
    return tuple(mismatches)


class LiveTitleResolver:
    """A :class:`TitleResolver` backed by the live Wikipedia API (``pageprops.wikibase_item``)."""

    def __init__(self, *, user_agent: str = _USER_AGENT, timeout: int = _TIMEOUT_SECONDS) -> None:
        """Configure the ``User-Agent`` and per-request timeout."""
        self._headers = {"User-Agent": user_agent}
        self._timeout = timeout

    def qids_for(self, titles: Sequence[str]) -> dict[str, str | None]:
        """Resolve each title to its article's ``wikibase_item`` (redirects followed)."""
        result: dict[str, str | None] = {}
        unique = list(dict.fromkeys(titles))
        for start in range(0, len(unique), 40):  # titles= accepts up to 50 per call
            self._resolve_batch(unique[start : start + 40], result)
        return result

    def _resolve_batch(self, titles: list[str], result: dict[str, str | None]) -> None:
        """Resolve one batch of titles into ``result`` (in place)."""
        url = f"{_WIKIPEDIA_API}?" + urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "redirects": "1",
                "titles": "|".join(titles),
            }
        )
        request = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload: dict[str, Any] = json.load(response)
        query = payload.get("query", {})
        # Map any normalised / redirected title back to the label we were asked about.
        alias = {entry["to"]: entry["from"] for entry in query.get("normalized", [])}
        for entry in query.get("redirects", []):
            alias[entry["to"]] = alias.get(entry["from"], entry["from"])
        for page in query.get("pages", {}).values():
            label = alias.get(page["title"], page["title"])
            result[label] = page.get("pageprops", {}).get("wikibase_item")
