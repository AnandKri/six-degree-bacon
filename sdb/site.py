"""Static-site export: pre-render every topic's results for free, zero-ops hosting.

Because the engine is deterministic and the seed is small, the whole UI is precomputable:
:func:`build_site` writes a ``data.json`` (per-topic *strict* and *speculative* results plus a
resolution index) and copies the very same ``static/index.html`` that ``sdb serve`` uses. That page
probes for ``./data.json`` on load and, finding it, runs entirely client-side — so a plain static
host (GitHub Pages, Netlify) serves the app with no backend, and there is no separate template to
drift from the live one.
"""

from __future__ import annotations

import datetime as dt
import json
from importlib import resources
from pathlib import Path

from sdb.graph.build import KnowledgeGraph
from sdb.web import discover_payload

_EMPTY: dict[str, object] = {"journey": [], "unlikely": []}


def build_site(graph: KnowledgeGraph, out_dir: Path, *, top: int = 3) -> Path:
    """Pre-render the whole graph into a static bundle under ``out_dir``; return the ``index.html``.

    For every node it precomputes both toggle states the UI offers — ``strict`` (the default
    ``trust ≥ 0.50`` gate) and ``loose`` (speculative, down to the trust floor) — so the static page
    reproduces the live experience exactly. Deterministic, offline, no network.
    """
    index: list[dict[str, object]] = []
    results: dict[str, dict[str, object]] = {}
    for node in graph.nodes():
        strict = discover_payload(graph, node.id, top=top, include_possibly=False)
        loose = discover_payload(graph, node.id, top=top, include_possibly=True)
        index.append(
            {
                "id": node.id,
                "label": node.label,
                "qid": node.wikidata_qid,
                "aliases": list(node.aliases),
            }
        )
        results[node.id] = {
            "strict": strict.get("results", _EMPTY),
            "loose": loose.get("results", _EMPTY),
        }

    payload = {
        "generated": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "index": sorted(index, key=lambda entry: str(entry["label"])),
        "results": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    page = resources.files("sdb").joinpath("static", "index.html").read_text(encoding="utf-8")
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve files verbatim
    return index_path
