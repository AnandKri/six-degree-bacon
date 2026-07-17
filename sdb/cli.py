"""Command-line interface: ``sdb discover "<topic>"``.

Renders each discovered path as a plain-text "TIL card" showing the chain, the templated narrative,
the deterministic trust and surprise scores, and the provenance behind every hop.

The card uses box/arrow glyphs when the terminal can encode them and falls back to ASCII otherwise,
so it never crashes on a legacy console (e.g. Windows cp1252).
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from sdb.constants import POSSIBLY_THRESHOLD, TOP_DEFAULT, TRUST_FLOOR
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_cooccurrence, load_seed, load_similarity
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED, Archetype
from sdb.schema.models import DiscoveryResult
from sdb.serialize import result_core, source_dicts, unique_sources

_DEFAULT_SEED = Path("data/seed.json")
_DEFAULT_COOCCURRENCE = Path("data/cooccurrence.json")
_WRAP_WIDTH = 66
_UNICODE_PROBE = "⇢→█░⚠"


@dataclass(frozen=True)
class _Glyphs:
    """The decorative characters used in a card (Unicode or ASCII variant)."""

    arrow: str
    step: str
    bar_full: str
    bar_empty: str
    warn: str


_UNICODE_GLYPHS = _Glyphs(arrow="⇢", step="→", bar_full="█", bar_empty="░", warn="⚠")
_ASCII_GLYPHS = _Glyphs(arrow="->", step="->", bar_full="#", bar_empty="-", warn="(!)")

# Nicer than "?" when degrading typographic punctuation to a pure-ASCII console.
# Keyed by Unicode code point (int) so the source stays pure-ASCII and unambiguous.
_ASCII_TRANSLITERATIONS: dict[int, str] = {
    0x2014: "-",  # em dash
    0x2013: "-",  # en dash
    0x2019: "'",  # right single quote
    0x2018: "'",  # left single quote
    0x201C: '"',  # left double quote
    0x201D: '"',  # right double quote
    0x2026: "...",  # ellipsis
}


def _stdout_encoding() -> str:
    """The encoding stdout will use (falling back to UTF-8 if it can't be determined)."""
    return getattr(sys.stdout, "encoding", None) or "utf-8"


def _supports_unicode() -> bool:
    """Whether the terminal can encode the card's Unicode decorations."""
    try:
        _UNICODE_PROBE.encode(_stdout_encoding())
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _glyphs() -> _Glyphs:
    """Pick the Unicode glyphs if the terminal supports them, else the ASCII fallback."""
    return _UNICODE_GLYPHS if _supports_unicode() else _ASCII_GLYPHS


def _emit(text: str) -> None:
    """Print ``text``, replacing any characters the terminal cannot encode (never crashes)."""
    encoding = _stdout_encoding()
    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        text = text.translate(_ASCII_TRANSLITERATIONS)
        text = text.encode(encoding, errors="replace").decode(encoding)
    print(text)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``sdb`` console script. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="sdb",
        description="Discover the longest *surprising* sourced path between ideas.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser(
        "discover", help="Discover a surprising, sourced path for a topic."
    )
    discover_parser.add_argument(
        "topic", nargs="+", help="Topic to start from (e.g. Roman Empire)."
    )
    discover_parser.add_argument(
        "--seed", type=Path, default=_DEFAULT_SEED, help="Path to the seed graph JSON."
    )
    discover_parser.add_argument(
        "--cooccurrence",
        type=Path,
        default=_DEFAULT_COOCCURRENCE,
        help="Path to the Wikipedia-link co-occurrence JSON (endpoint-surprise term).",
    )
    discover_parser.add_argument(
        "--harvest",
        type=Path,
        action="append",
        default=None,
        metavar="SNAPSHOT",
        help="Merge a harvest snapshot into the curated graph (repeatable).",
    )
    discover_parser.add_argument(
        "--archetype",
        choices=["journey", "unlikely", "both"],
        default="both",
        help="journey (long chain), unlikely (short improbable adjacency), or both (default).",
    )
    discover_parser.add_argument(
        "--top", type=int, default=TOP_DEFAULT, help="Number of results per archetype."
    )
    discover_parser.add_argument("--min-hops", type=int, default=None)
    discover_parser.add_argument("--max-hops", type=int, default=None)
    discover_parser.add_argument(
        "--include-possibly",
        action="store_true",
        help="Include speculative low-trust 'Possibly:' paths, not only confident ones.",
    )
    discover_parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit JSON instead of a card."
    )

    harvest_parser = subparsers.add_parser(
        "harvest", help="Harvest a k-hop Wikidata neighbourhood to a local snapshot."
    )
    harvest_parser.add_argument("qid", help="Wikidata QID to start from (e.g. Q2277).")
    harvest_parser.add_argument("--hops", type=int, default=2, help="Expansion rounds (default 2).")
    harvest_parser.add_argument(
        "--max-neighbors", type=int, default=None, help="Per-node cap on curated edges."
    )
    harvest_parser.add_argument(
        "--out", type=Path, default=None, help="Snapshot path (default data/harvest/<qid>.json)."
    )

    cooc_parser = subparsers.add_parser(
        "build-cooccurrence", help="Harvest Wikipedia-link co-occurrence for a seed graph."
    )
    cooc_parser.add_argument(
        "--seed", type=Path, default=_DEFAULT_SEED, help="Seed graph to build co-occurrence for."
    )
    cooc_parser.add_argument(
        "--out", type=Path, default=_DEFAULT_COOCCURRENCE, help="Output co-occurrence JSON path."
    )

    validate_parser = subparsers.add_parser(
        "validate-qids", help="Check that each node's wikidata_qid resolves back to that node."
    )
    validate_parser.add_argument(
        "--seed", type=Path, default=_DEFAULT_SEED, help="Seed graph to validate."
    )

    serve_parser = subparsers.add_parser("serve", help="Serve the interactive web UI locally.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (deploy: 0.0.0.0).")
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (or the PORT env var; default 8000)."
    )
    serve_parser.add_argument("--seed", type=Path, default=_DEFAULT_SEED, help="Seed graph JSON.")
    serve_parser.add_argument(
        "--cooccurrence", type=Path, default=_DEFAULT_COOCCURRENCE, help="Co-occurrence JSON."
    )

    site_parser = subparsers.add_parser(
        "build-site", help="Pre-render a static site for free hosting (e.g. GitHub Pages)."
    )
    site_parser.add_argument(
        "--out", type=Path, default=Path("site"), help="Output directory (default site/)."
    )
    site_parser.add_argument("--seed", type=Path, default=_DEFAULT_SEED, help="Seed graph JSON.")
    site_parser.add_argument(
        "--cooccurrence", type=Path, default=_DEFAULT_COOCCURRENCE, help="Co-occurrence JSON."
    )
    site_parser.add_argument(
        "--theme",
        type=Path,
        default=None,
        help="Optional CSS file injected as a theme override (for embedding in another site).",
    )

    args = parser.parse_args(argv)
    dispatch = {
        "discover": _run_discover,
        "harvest": _run_harvest,
        "build-cooccurrence": _run_build_cooccurrence,
        "validate-qids": _run_validate_qids,
        "serve": _run_serve,
        "build-site": _run_build_site,
    }
    return dispatch[args.command](args)


def _run_serve(args: argparse.Namespace) -> int:
    """Serve the local web UI (deferred import so the CLI's other commands stay lightweight)."""
    from sdb.web import serve

    if not args.seed.exists():
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2
    serve(args.host, args.port, seed_path=args.seed, cooccurrence_path=args.cooccurrence)
    return 0


def _run_build_site(args: argparse.Namespace) -> int:
    """Pre-render the static site (deterministic; deployable to any static host)."""
    from sdb.site import build_site
    from sdb.web import load_graph

    if not args.seed.exists():
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2
    theme_css: str | None = None
    if args.theme is not None:
        if not args.theme.exists():
            print(f"theme file not found: {args.theme}", file=sys.stderr)
            return 2
        theme_css = args.theme.read_text(encoding="utf-8")
    graph = load_graph(args.seed, args.cooccurrence)
    index_path = build_site(graph, args.out, theme_css=theme_css)
    print(
        f"Wrote static site for {len(graph.nodes())} topics to {index_path.parent}"
        f" — serve with any static host (e.g. GitHub Pages)."
    )
    return 0


def _run_discover(args: argparse.Namespace) -> int:
    """Load the graph, run discovery, and print results (or a helpful error)."""
    topic = " ".join(args.topic)
    try:
        seed = load_seed(args.seed)
    except FileNotFoundError:
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2

    if args.harvest:
        from sdb.harvest.merge import merge_seeds
        from sdb.harvest.snapshot import load_snapshot

        for snapshot_path in args.harvest:
            try:
                overlay = load_snapshot(snapshot_path)
            except FileNotFoundError:
                print(f"harvest snapshot not found: {snapshot_path}", file=sys.stderr)
                return 2
            merged = merge_seeds(seed, overlay)
            seed = merged.seed
            print(
                f"merged {snapshot_path}: +{merged.added_nodes} nodes, "
                f"+{merged.added_statements} statements, {merged.corroborated} facts corroborated",
                file=sys.stderr,
            )

    has_cooc = args.cooccurrence.exists()
    cooccurrence = load_cooccurrence(args.cooccurrence) if has_cooc else None
    similarity = load_similarity(args.cooccurrence) if has_cooc else None
    graph = KnowledgeGraph.from_seed(seed, cooccurrence, similarity)
    min_trust = TRUST_FLOOR if args.include_possibly else POSSIBLY_THRESHOLD
    archetypes = (
        [Archetype.JOURNEY, Archetype.UNLIKELY]
        if args.archetype == "both"
        else [Archetype(args.archetype)]
    )
    try:
        by_archetype = {
            archetype: discover(
                graph,
                topic,
                archetype=archetype,
                min_hops=args.min_hops,
                max_hops=args.max_hops,
                top=args.top,
                min_trust=min_trust,
            )
            for archetype in archetypes
        }
    except TopicNotFoundError as error:
        print(f"Topic not found: {topic!r}", file=sys.stderr)
        if error.suggestions:
            print("Did you mean: " + ", ".join(error.suggestions) + "?", file=sys.stderr)
        return 2

    if not any(by_archetype.values()):
        print(f"No confident connection found for {topic!r}.", file=sys.stderr)
        if not args.include_possibly:
            print("Try --include-possibly for speculative paths.", file=sys.stderr)
        return 1

    if args.as_json:
        payload = [
            _result_to_dict(graph, result, i)
            for archetype in archetypes
            for i, result in enumerate(by_archetype[archetype], 1)
        ]
        _emit(json.dumps(payload, indent=2))  # ensure_ascii=True -> always console-safe
        return 0

    glyphs = _glyphs()
    _emit(f"\nSix Degree Bacon - {topic}\n" + "=" * _WRAP_WIDTH)
    for archetype in archetypes:
        _emit(f"\n{_ARCHETYPE_HEADING[archetype]}")
        results = by_archetype[archetype]
        if not results:
            _emit(f"   (no confident {archetype.value} found)\n")
            continue
        for index, result in enumerate(results, 1):
            _emit(_render_card(graph, result, index, glyphs))
            _emit("")
    return 0


_ARCHETYPE_HEADING: dict[Archetype, str] = {
    Archetype.JOURNEY: "THE JOURNEY  (a surprising cross-domain chain)",
    Archetype.UNLIKELY: "THE IMPROBABLE PAIR  (worlds apart, yet a short hop away)",
}


def _run_harvest(args: argparse.Namespace) -> int:
    """Harvest a k-hop Wikidata neighbourhood and pin it to a local snapshot."""
    from sdb.harvest.client import WikidataClient
    from sdb.harvest.harvester import harvest
    from sdb.harvest.snapshot import DEFAULT_HARVEST_DIR, save_snapshot

    out = args.out or DEFAULT_HARVEST_DIR / f"{args.qid.lower()}.json"
    print(f"Harvesting {args.qid} ({args.hops} hops) from Wikidata ...", file=sys.stderr)
    seed = harvest(WikidataClient(), args.qid, args.hops, max_neighbors=args.max_neighbors)
    written = save_snapshot(seed, out)
    print(f"Wrote {len(seed.nodes)} nodes, {len(seed.statements)} statements to {written}")
    return 0


def _run_build_cooccurrence(args: argparse.Namespace) -> int:
    """Harvest Wikipedia-link co-occurrence for a seed graph and write the JSON matrix."""
    from sdb.harvest.cooccurrence import LiveWikipediaClient, build_cooccurrence

    try:
        seed = load_seed(args.seed)
    except FileNotFoundError:
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2

    print(f"Building co-occurrence for {len(seed.nodes)} nodes from Wikipedia ...", file=sys.stderr)
    matrix, similarity = build_cooccurrence(seed.nodes, LiveWikipediaClient())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": "Wikipedia-link co-occurrence for the endpoint-surprise term; see "
        "docs/confidence-rubric.md. `links` = direct seed-to-seed article links (first-order "
        "strength); `similarity` = Jaccard overlap of each pair's FULL outbound link sets "
        "(second-order shared context, ADR 0029). Regenerate with `sdb build-cooccurrence`.",
        "links": matrix,
        "similarity": similarity,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote co-occurrence for {len(matrix)} nodes to {args.out}")
    return 0


def _run_validate_qids(args: argparse.Namespace) -> int:
    """Check every node's ``wikidata_qid`` against Wikipedia; exit non-zero on any mismatch."""
    from sdb.harvest.validate import LiveTitleResolver, validate_qids

    try:
        seed = load_seed(args.seed)
    except FileNotFoundError:
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2

    checked = sum(1 for node in seed.nodes if node.wikidata_qid is not None)
    print(f"Validating {checked} node QIDs against Wikipedia ...", file=sys.stderr)
    mismatches = validate_qids(seed.nodes, LiveTitleResolver())
    if not mismatches:
        print(f"OK: all {checked} node QIDs resolve correctly.")
        return 0
    for mismatch in mismatches:
        print(
            f"  MISMATCH {mismatch.node_id}: stored {mismatch.stored_qid}, "
            f"{mismatch.label!r} resolves to {mismatch.resolved_qid}",
            file=sys.stderr,
        )
    print(f"{len(mismatches)} QID mismatch(es) — see ADR 0008.", file=sys.stderr)
    return 1


def _render_card(
    graph: KnowledgeGraph, result: DiscoveryResult, index: int, glyphs: _Glyphs
) -> str:
    """Render a single discovery result as a plain-text card."""
    start = graph.node(result.path.node_ids[0]).label
    end = graph.node(result.path.node_ids[-1]).label

    lines: list[str] = [
        f"#{index}  {start}  {glyphs.arrow}  {end}   ({result.path.length} hops)",
        "",
    ]
    lines.append(f"   {start}")
    for hop in result.path.hops:
        phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
        phrase = phrases[hop.statement.predicate]
        lines.append(f"     {glyphs.step} ({phrase}) {graph.node(hop.to_id).label}")
    lines.append("")

    lines.extend(f"   {line}" for line in textwrap.wrap(result.til, width=_WRAP_WIDTH))
    lines.append("")

    possibly_tag = f"   {glyphs.warn} low confidence" if result.possibly else ""
    if result.archetype is Archetype.UNLIKELY:
        score_line = (
            f"   improbable {result.score:.1f}   "
            f"(improbability {result.endpoint_unexpectedness:.1f} x trust)"
        )
    else:
        score_line = f"   wow      {result.score:.1f}   (surprise {result.surprise:.1f} x trust)"
    lines.append(score_line)
    lines.append(f"   trust    {_bar(result.trust, glyphs)}  {result.trust:.2f}{possibly_tag}")
    lines.append("")

    lines.append("   sources:")
    for source in unique_sources(result):
        location = f"  {source.url}" if source.url else ""
        lines.append(f"     [{source.id}] {source.source_type.value}{location}")
    return "\n".join(lines)


def _bar(value: float, glyphs: _Glyphs, width: int = 10) -> str:
    """Render a 0..1 value as a small filled bar."""
    filled = round(max(0.0, min(1.0, value)) * width)
    return glyphs.bar_full * filled + glyphs.bar_empty * (width - filled)


def _result_to_dict(
    graph: KnowledgeGraph, result: DiscoveryResult, index: int
) -> dict[str, object]:
    """Convert a result to a JSON-friendly dict.

    Machine-facing, so the shared fields keep 4 dp; ``rank`` and the flat ``path`` of labels are the
    CLI's own (the web card renders a phrased ``chain`` instead).
    """
    return {
        "rank": index,
        **result_core(graph, result, score_dp=4, trust_dp=4, metric_dp=4),
        "path": [graph.node(node_id).label for node_id in result.path.node_ids],
        "sources": source_dicts(result),
    }
