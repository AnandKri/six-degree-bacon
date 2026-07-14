"""The local web UI: pure payload builder + a real (localhost, offline) HTTP round-trip."""

from __future__ import annotations

import json
import threading
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from sdb.graph.build import KnowledgeGraph
from sdb.web import _PAGE, _AppServer, discover_payload, make_server


def test_payload_has_journey_and_unlikely_with_sourced_chains(seed_graph: KnowledgeGraph) -> None:
    data = discover_payload(seed_graph, "Roman Empire", top=3)
    assert data["topic"] == "Roman Empire"
    results = data["results"]
    assert isinstance(results, dict)
    assert results["journey"] and results["unlikely"]  # both archetypes present

    card = results["journey"][0]
    assert card["topic"] == "Roman Empire"
    assert card["hops"] == len(card["chain"])  # one chain step per hop
    assert all({"from", "phrase", "to"} <= step.keys() for step in card["chain"])
    assert 0.0 <= card["trust"] <= 1.0
    assert card["sources"] and all("id" in s and "type" in s for s in card["sources"])
    assert card["endpoint"] in card["til"]  # narrative names the destination


def test_payload_reports_not_found_with_suggestions(seed_graph: KnowledgeGraph) -> None:
    data = discover_payload(seed_graph, "Rmoan Empire")
    assert data["error"] == "not_found"
    assert data["suggestions"]  # near-miss hints for the UI


def test_empty_topic_is_rejected_without_searching(seed_graph: KnowledgeGraph) -> None:
    assert discover_payload(seed_graph, "   ")["error"] == "empty"


def test_include_possibly_widens_results(seed_graph: KnowledgeGraph) -> None:
    # Same wide `top` for both, so this isolates the gate. Lowering it is strictly additive: the
    # loose journey endpoints are a proper superset of the strict ones (not merely "not fewer").
    strict = discover_payload(seed_graph, "Trojan War", top=99, include_possibly=False)
    loose = discover_payload(seed_graph, "Trojan War", top=99, include_possibly=True)
    strict_endpoints = {card["endpoint"] for card in strict["results"]["journey"]}
    loose_endpoints = {card["endpoint"] for card in loose["results"]["journey"]}
    assert strict_endpoints < loose_endpoints


def test_page_is_self_contained_no_external_assets() -> None:
    assert _PAGE.lstrip().startswith("<!doctype html>")
    assert "<title>Six Degree Bacon</title>" in _PAGE
    # A strict "self-contained" invariant: the shell pulls in no remote scripts/styles/fonts.
    for needle in ("src=", "cdn", "https://", "http://"):
        assert needle not in _PAGE.lower()


@contextmanager
def _running(graph: KnowledgeGraph) -> Iterator[_AppServer]:
    server = make_server(graph, port=0)  # ephemeral port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(server: _AppServer, path: str) -> tuple[int, str]:
    host, port = server.server_address[0], server.server_address[1]
    with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_http_round_trip_serves_page_and_json(seed_graph: KnowledgeGraph) -> None:
    # A genuine end-to-end check over a localhost socket (no external network).
    with _running(seed_graph) as server:
        status, body = _get(server, "/")
        assert status == 200
        assert "Six Degree Bacon" in body

        status, body = _get(server, "/api/discover?topic=Roman%20Empire&top=1")
        assert status == 200
        payload = json.loads(body)
        assert payload["topic"] == "Roman Empire"
        assert payload["results"]["journey"][0]["endpoint"]


def test_http_unknown_path_is_404(seed_graph: KnowledgeGraph) -> None:
    with _running(seed_graph) as server, pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(server, "/nope")
    assert excinfo.value.code == 404
