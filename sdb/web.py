"""Local web UI: ``sdb serve`` wraps :func:`~sdb.engine.pipeline.discover` behind a tiny server.

Zero new dependencies (Python's :mod:`http.server`), a single self-contained page (``static/
index.html``, inline CSS/JS, no external assets), and **no engine changes** — the browser calls
``/api/discover`` and renders the same journey / improbable-pair results the CLI prints. Deployable
on any host that runs Python (Render, a Hugging Face Docker Space, Fly.io, Cloud Run); ``PORT`` is
read from the environment so those platforms work out of the box.

The request handling is a thin wrapper over :func:`discover_payload`, a pure, offline-testable
function that turns a topic into a JSON-friendly dict.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlparse

from sdb.constants import POSSIBLY_THRESHOLD, TOP_DEFAULT, TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_cooccurrence, load_seed, load_similarity
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED, Archetype
from sdb.schema.models import DiscoveryResult, Hop

# The single self-contained page, loaded once from package data (works from a source tree or wheel).
_PAGE = resources.files("sdb").joinpath("static", "index.html").read_text(encoding="utf-8")

_ARCHETYPES: dict[str, list[Archetype]] = {
    "journey": [Archetype.JOURNEY],
    "unlikely": [Archetype.UNLIKELY],
    "both": [Archetype.JOURNEY, Archetype.UNLIKELY],
}


def _hop_payload(graph: KnowledgeGraph, hop: Hop) -> dict[str, str]:
    """One step of a path as ``{from, phrase, to}``, phrased in the direction traversed."""
    phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
    return {
        "from": graph.node(hop.from_id).label,
        "phrase": phrases[hop.statement.predicate],
        "to": graph.node(hop.to_id).label,
    }


def _result_payload(graph: KnowledgeGraph, result: DiscoveryResult) -> dict[str, object]:
    """A single result as a JSON-friendly dict — richer than the CLI's, with per-hop phrasing."""
    seen: dict[str, dict[str, str | None]] = {}
    for hop in result.path.hops:
        for source in hop.statement.sources:
            seen.setdefault(
                source.id,
                {"id": source.id, "type": source.source_type.value, "url": source.url},
            )
    return {
        "archetype": result.archetype.value,
        "topic": graph.node(result.path.node_ids[0]).label,
        "endpoint": graph.node(result.path.node_ids[-1]).label,
        "hops": result.path.length,
        "score": round(result.score, 2),
        "trust": round(result.trust, 3),
        "surprise": round(result.surprise, 2),
        "endpoint_unexpectedness": round(result.endpoint_unexpectedness, 2),
        "possibly": result.possibly,
        "til": result.til,
        "chain": [_hop_payload(graph, hop) for hop in result.path.hops],
        "sources": list(seen.values()),
    }


def discover_payload(
    graph: KnowledgeGraph,
    topic: str,
    *,
    archetype: str = "both",
    top: int = TOP_DEFAULT,
    include_possibly: bool = False,
    min_hops: int | None = None,
    max_hops: int | None = None,
) -> dict[str, object]:
    """Turn a topic into a JSON-friendly result dict (pure, deterministic, offline-testable).

    Returns ``{"topic", "results": {archetype: [...]}}`` on success, or
    ``{"topic", "error": "not_found", "suggestions": [...]}`` when the topic doesn't resolve.
    """
    if not topic.strip():
        return {"topic": topic, "error": "empty"}
    archetypes = _ARCHETYPES.get(archetype, _ARCHETYPES["both"])
    min_trust = TRUST_FLOOR if include_possibly else POSSIBLY_THRESHOLD
    try:
        by_archetype = {
            a: discover(
                graph,
                topic,
                archetype=a,
                top=top,
                min_trust=min_trust,
                min_hops=min_hops,
                max_hops=max_hops,
            )
            for a in archetypes
        }
    except TopicNotFoundError as error:
        return {"topic": topic, "error": "not_found", "suggestions": error.suggestions}
    return {
        "topic": topic,
        "results": {
            a.value: [_result_payload(graph, r) for r in by_archetype[a]] for a in archetypes
        },
    }


def load_graph(seed_path: Path, cooccurrence_path: Path) -> KnowledgeGraph:
    """Load the knowledge graph (with co-occurrence if the sidecar exists) for serving."""
    exists = cooccurrence_path.exists()
    cooccurrence = load_cooccurrence(cooccurrence_path) if exists else None
    similarity = load_similarity(cooccurrence_path) if exists else None
    return KnowledgeGraph.from_seed(load_seed(seed_path), cooccurrence, similarity)


class _AppServer(ThreadingHTTPServer):
    """A threaded HTTP server carrying the (immutable, shared) knowledge graph."""

    def __init__(self, address: tuple[str, int], graph: KnowledgeGraph) -> None:
        self.graph = graph
        super().__init__(address, _Handler)


class _Handler(BaseHTTPRequestHandler):
    """Serves the single page at ``/`` and JSON results at ``/api/discover``."""

    server_version = "SixDegreeBacon/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _PAGE.encode("utf-8"))
        elif parsed.path == "/api/discover":
            self._send_json(self._discover(parse_qs(parsed.query)))
        else:
            self._send_json({"error": "not_found"}, status=404)

    def _discover(self, params: dict[str, list[str]]) -> dict[str, object]:
        graph = cast(_AppServer, self.server).graph

        def first(key: str, default: str) -> str:
            return params.get(key, [default])[0]

        try:
            top = max(1, int(first("top", str(TOP_DEFAULT))))
        except ValueError:
            top = TOP_DEFAULT
        return discover_payload(
            graph,
            first("topic", ""),
            archetype=first("archetype", "both"),
            top=top,
            include_possibly=first("include_possibly", "false").lower() == "true",
        )

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        self._send(status, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request stderr logging."""


def make_server(graph: KnowledgeGraph, host: str = "127.0.0.1", port: int = 8000) -> _AppServer:
    """Build (but do not start) the HTTP server. ``port=0`` binds an ephemeral port (for tests)."""
    return _AppServer((host, port), graph)


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    seed_path: Path,
    cooccurrence_path: Path,
) -> None:
    """Load the graph and serve the UI until interrupted (``PORT`` env overrides ``port``)."""
    graph = load_graph(seed_path, cooccurrence_path)
    port = int(os.environ.get("PORT", str(port)))
    server = make_server(graph, host, port)
    bound_host, bound_port = cast("tuple[str, int]", server.server_address)
    print(f"Six Degree Bacon UI -> http://{bound_host}:{bound_port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
