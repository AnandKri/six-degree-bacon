"""Static-site export: pre-render every topic's results for free, zero-ops hosting.

Because the engine is deterministic and the seed is small, the whole UI is precomputable:
:func:`build_site` writes a ``data.json`` (per-topic *strict* and *speculative* results plus a
resolution index) and copies the very same ``static/index.html`` that ``sdb serve`` uses. That page
probes for ``./data.json`` on load and, finding it, runs entirely client-side — so a plain static
host (GitHub Pages, Netlify) serves the app with no backend, and there is no separate template to
drift from the live one.

For **multiple brains** (ADR 0044), :func:`build_multi_site` writes one bundle per brain — the first
to ``data.json`` (so a single-brain deploy and any bare ``./data.json`` consumer keep working) and
the rest to ``data-<name>.json`` — plus a ``brains.json`` manifest the page reads to build its
switcher. The page falls back to the lone ``data.json`` when no manifest is present.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence
from importlib import resources
from pathlib import Path

from sdb.brains import BrainSpec
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_graph
from sdb.web import discover_payload, graph_payload

_EMPTY: dict[str, object] = {"journey": [], "unlikely": []}


def _bundle(graph: KnowledgeGraph, *, top: int) -> dict[str, object]:
    """The full precomputed payload for one brain: index + per-topic results + laid-out graph."""
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
    return {
        "generated": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "index": sorted(index, key=lambda entry: str(entry["label"])),
        "results": results,
        "graph": graph_payload(graph),  # laid-out nodes + edges for the bird's-eye map
    }


def _write_page(out_dir: Path) -> Path:
    """Copy the packaged page + the GitHub-Pages ``.nojekyll`` marker into ``out_dir``."""
    page = resources.files("sdb").joinpath("static", "index.html").read_text(encoding="utf-8")
    index_path = out_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve files verbatim
    return index_path


def build_site(graph: KnowledgeGraph, out_dir: Path, *, top: int = 3) -> Path:
    """Pre-render one graph into a static bundle under ``out_dir``; return the ``index.html``.

    For every node it precomputes both toggle states the UI offers — ``strict`` (the default
    ``trust ≥ 0.50`` gate) and ``loose`` (speculative, down to the trust floor) — so the static page
    reproduces the live experience exactly. Deterministic, offline, no network.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "data.json").write_text(
        json.dumps(_bundle(graph, top=top), ensure_ascii=False), encoding="utf-8"
    )
    return _write_page(out_dir)


def build_multi_site(brains: Sequence[BrainSpec], out_dir: Path, *, top: int = 3) -> Path:
    """Pre-render several brains into one bundle with a ``brains.json`` manifest; return the page.

    The first brain is written to ``data.json`` (keeping a bare single-brain deploy working) and the
    rest to ``data-<name>.json``. ``brains.json`` lists ``{name, label, file}`` in switcher order.
    Falls back to :func:`build_site` for a single brain, so the output is byte-identical to the old
    single-brain bundle in that case.
    """
    if len(brains) == 1:
        return build_site(
            load_graph(brains[0].seed_path, brains[0].cooccurrence_path), out_dir, top=top
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str | int]] = []
    for position, brain in enumerate(brains):
        graph = load_graph(brain.seed_path, brain.cooccurrence_path)
        file = "data.json" if position == 0 else f"data-{brain.name}.json"
        (out_dir / file).write_text(
            json.dumps(_bundle(graph, top=top), ensure_ascii=False), encoding="utf-8"
        )
        # `count` (node count) lets the page weight an "all brains" random pick so every card is
        # equally likely, without eagerly loading every bundle (ADR 0052).
        manifest.append(
            {"name": brain.name, "label": brain.label, "file": file, "count": len(graph.nodes())}
        )
    (out_dir / "brains.json").write_text(
        json.dumps({"brains": manifest}, ensure_ascii=False), encoding="utf-8"
    )
    return _write_page(out_dir)
