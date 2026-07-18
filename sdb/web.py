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
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import cast
from urllib.parse import parse_qs, urlparse

from sdb.brains import BrainSpec
from sdb.constants import TOP_DEFAULT
from sdb.engine.pipeline import TopicNotFoundError, discover_all, trust_gate
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_graph
from sdb.layout import compute_layout
from sdb.schema.models import DiscoveryResult
from sdb.serialize import hop_dicts, result_core, source_dicts

# The single self-contained page, loaded once from package data (works from a source tree or wheel).
_PAGE = resources.files("sdb").joinpath("static", "index.html").read_text(encoding="utf-8")


def _result_payload(graph: KnowledgeGraph, result: DiscoveryResult) -> dict[str, object]:
    """A single result as a JSON-friendly dict — richer than the CLI's, with per-hop phrasing.

    Display-facing, so the shared fields round to 2-3 dp; ``chain`` carries the sourced evidence
    the card renders under each step (the CLI emits a flat ``path`` of labels alongside its own
    copy of the same chain).
    """
    return {
        **result_core(graph, result, score_dp=2, trust_dp=3, metric_dp=2),
        "chain": hop_dicts(graph, result),
        "sources": source_dicts(result),
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
    try:
        by_archetype = discover_all(
            graph,
            topic,
            archetype=archetype,
            top=top,
            min_trust=trust_gate(include_possibly),
            min_hops=min_hops,
            max_hops=max_hops,
        )
    except TopicNotFoundError as error:
        return {"topic": topic, "error": "not_found", "suggestions": error.suggestions}
    return {
        "topic": topic,
        "results": {
            each.value: [_result_payload(graph, result) for result in results]
            for each, results in by_archetype.items()
        },
    }


def graph_payload(
    graph: KnowledgeGraph, layout: Mapping[str, tuple[float, float]] | None = None
) -> dict[str, object]:
    """The whole graph as a JSON-friendly dict for the bird's-eye map — laid-out nodes + edges.

    Nodes carry their deterministic ``(x, y)`` (see :func:`~sdb.layout.compute_layout`), ``domain``
    for the realm tint, and ``degree`` for sizing. Edges are the undirected statement pairs,
    de-duplicated (parallel statements collapse) and self-loop-free, mirroring the layout's own edge
    set. Deterministic; ``layout`` is accepted so a caller can compute it once and reuse it here.
    """
    positions = compute_layout(graph) if layout is None else layout
    nodes: list[dict[str, object]] = []
    for node in graph.nodes():
        x, y = positions[node.id]
        nodes.append(
            {
                "id": node.id,
                "label": node.label,
                "domain": node.domain.value,
                "type": node.type,
                "x": x,
                "y": y,
                "degree": graph.degree(node.id),
                "summary": node.summary,
                "year": node.start_year,
                "aliases": list(node.aliases),
            }
        )
    seen: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []
    for statement in graph.statements:
        a, b = statement.subject, statement.object
        if a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        edges.append({"source": key[0], "target": key[1]})
    return {"nodes": nodes, "edges": edges}


class _AppServer(ThreadingHTTPServer):
    """A threaded HTTP server carrying one or more (immutable, shared) brains.

    A "brain" is a named :class:`~sdb.graph.build.KnowledgeGraph` (ADR 0044). ``graphs`` maps each
    brain's name to its graph; ``order`` is the display order (first = default); ``labels`` the
    display names. A request selects a brain with ``?brain=<name>``, defaulting to
    ``default_brain``; an unknown name falls back to the default rather than erroring.
    """

    def __init__(
        self,
        address: tuple[str, int],
        graphs: Mapping[str, KnowledgeGraph],
        labels: Mapping[str, str],
        order: Sequence[str],
        default_brain: str,
    ) -> None:
        self.graphs = dict(graphs)
        self.brain_labels = dict(labels)
        self.brain_order = list(order)
        self.default_brain = default_brain
        # Each brain's map payload is computed once, lazily, on first request (the layout costs
        # ~1s), then shared read-only across request threads.
        self.graph_payload_cache: dict[str, dict[str, object]] = {}
        super().__init__(address, _Handler)

    def resolve(self, name: str | None) -> str:
        """The requested brain if it exists, else the default (never raises on a bad ?brain=)."""
        return name if name in self.graphs else self.default_brain


class _Handler(BaseHTTPRequestHandler):
    """Serves the page at ``/`` and JSON at ``/api/brains``, ``/api/discover``, ``/api/graph``."""

    server_version = "SixDegreeBacon/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _PAGE.encode("utf-8"))
        elif parsed.path == "/api/brains":
            self._send_json(self._brains())
        elif parsed.path == "/api/discover":
            self._send_json(self._discover(parse_qs(parsed.query)))
        elif parsed.path == "/api/graph":
            self._send_json(self._graph(parse_qs(parsed.query)))
        else:
            self._send_json({"error": "not_found"}, status=404)

    def _brain(self, params: dict[str, list[str]]) -> str:
        server = cast(_AppServer, self.server)
        return server.resolve(params.get("brain", [server.default_brain])[0])

    def _brains(self) -> dict[str, object]:
        server = cast(_AppServer, self.server)
        return {
            "brains": [
                {"name": name, "label": server.brain_labels[name]} for name in server.brain_order
            ]
        }

    def _graph(self, params: dict[str, list[str]]) -> dict[str, object]:
        server = cast(_AppServer, self.server)
        name = self._brain(params)
        if name not in server.graph_payload_cache:
            server.graph_payload_cache[name] = graph_payload(server.graphs[name])
        return server.graph_payload_cache[name]

    def _discover(self, params: dict[str, list[str]]) -> dict[str, object]:
        server = cast(_AppServer, self.server)
        graph = server.graphs[self._brain(params)]

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
    """Build (but do not start) a **single-brain** server. ``port=0`` binds an ephemeral port.

    The single graph is registered as the ``main`` brain, so a request with no ``?brain=`` (or an
    unknown one) resolves to it — which is exactly the pre-multi-brain behaviour this preserves.
    """
    return _AppServer((host, port), {"main": graph}, {"main": "Main"}, ["main"], "main")


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    brains: Sequence[BrainSpec],
) -> None:
    """Load every brain and serve the UI until interrupted (``PORT`` env overrides ``port``).

    The first brain is the default (served when no ``?brain=`` is given); the page's switcher offers
    the rest. All brains are loaded up front so switching is instant.
    """
    graphs = {b.name: load_graph(b.seed_path, b.cooccurrence_path) for b in brains}
    labels = {b.name: b.label for b in brains}
    order = [b.name for b in brains]
    port = int(os.environ.get("PORT", str(port)))
    server = _AppServer((host, port), graphs, labels, order, order[0])
    bound_host, bound_port = cast("tuple[str, int]", server.server_address)
    print(f"Six Degree Bacon UI -> http://{bound_host}:{bound_port}  (Ctrl+C to stop)")
    print(f"  brains: {', '.join(f'{b.label} [{b.name}]' for b in brains)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
