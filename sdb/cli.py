"""Command-line interface: ``sdb discover "<topic>"``.

Renders each discovered path as a plain-text "TIL card" showing the chain, the templated narrative,
the deterministic trust and surprise scores, and the provenance behind every hop.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from sdb.constants import MAX_HOPS_DEFAULT, MIN_HOPS_DEFAULT, TOP_DEFAULT
from sdb.engine.pipeline import TopicNotFoundError, discover
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_seed
from sdb.schema.enums import PREDICATE_PHRASE, PREDICATE_PHRASE_REVERSED
from sdb.schema.models import DiscoveryResult, Source

_DEFAULT_SEED = Path("data/seed.json")
_WRAP_WIDTH = 66


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
    discover_parser.add_argument("--top", type=int, default=TOP_DEFAULT, help="Number of results.")
    discover_parser.add_argument("--min-hops", type=int, default=MIN_HOPS_DEFAULT)
    discover_parser.add_argument("--max-hops", type=int, default=MAX_HOPS_DEFAULT)
    discover_parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit JSON instead of a card."
    )

    args = parser.parse_args(argv)
    if args.command == "discover":
        return _run_discover(args)
    return 1


def _run_discover(args: argparse.Namespace) -> int:
    """Load the graph, run discovery, and print results (or a helpful error)."""
    topic = " ".join(args.topic)
    try:
        seed = load_seed(args.seed)
    except FileNotFoundError:
        print(f"seed file not found: {args.seed}", file=sys.stderr)
        return 2

    graph = KnowledgeGraph.from_seed(seed)
    try:
        results = discover(
            graph, topic, min_hops=args.min_hops, max_hops=args.max_hops, top=args.top
        )
    except TopicNotFoundError as error:
        print(f"Topic not found: {topic!r}", file=sys.stderr)
        if error.suggestions:
            print("Did you mean: " + ", ".join(error.suggestions) + "?", file=sys.stderr)
        return 2

    if not results:
        print(f"No sufficiently-trusted surprising path found for {topic!r}.", file=sys.stderr)
        return 1

    if args.as_json:
        payload = [_result_to_dict(graph, result, i) for i, result in enumerate(results, 1)]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"\nSix Degree Bacon — {topic}\n" + "=" * _WRAP_WIDTH)
    for index, result in enumerate(results, 1):
        print(_render_card(graph, result, index))
        print()
    return 0


def _render_card(graph: KnowledgeGraph, result: DiscoveryResult, index: int) -> str:
    """Render a single discovery result as a plain-text card."""
    start = graph.node(result.path.node_ids[0]).label
    end = graph.node(result.path.node_ids[-1]).label

    lines: list[str] = [f"#{index}  {start}  ⇢  {end}   ({result.path.length} hops)", ""]
    lines.append(f"   {start}")
    for hop in result.path.hops:
        phrases = PREDICATE_PHRASE_REVERSED if hop.is_reversed else PREDICATE_PHRASE
        lines.append(f"     → ({phrases[hop.statement.predicate]}) {graph.node(hop.to_id).label}")
    lines.append("")

    lines.extend(f"   {line}" for line in textwrap.wrap(result.til, width=_WRAP_WIDTH))
    lines.append("")

    possibly_tag = "   ⚠ low confidence" if result.possibly else ""
    lines.append(f"   trust    {_bar(result.trust)}  {result.trust:.2f}{possibly_tag}")
    lines.append(f"   surprise {result.surprise:.2f}")
    lines.append("")

    lines.append("   sources:")
    for source in _unique_sources(result):
        location = f"  {source.url}" if source.url else ""
        lines.append(f"     [{source.id}] {source.source_type.value}{location}")
    return "\n".join(lines)


def _bar(value: float, width: int = 10) -> str:
    """Render a 0..1 value as a small filled bar."""
    filled = round(max(0.0, min(1.0, value)) * width)
    return "█" * filled + "░" * (width - filled)


def _unique_sources(result: DiscoveryResult) -> list[Source]:
    """Collect the distinct sources (by id) used across all hops, in first-seen order."""
    seen: dict[str, Source] = {}
    for hop in result.path.hops:
        for source in hop.statement.sources:
            seen.setdefault(source.id, source)
    return list(seen.values())


def _result_to_dict(
    graph: KnowledgeGraph, result: DiscoveryResult, index: int
) -> dict[str, object]:
    """Convert a result to a JSON-friendly dict."""
    return {
        "rank": index,
        "topic": graph.node(result.path.node_ids[0]).label,
        "endpoint": graph.node(result.path.node_ids[-1]).label,
        "hops": result.path.length,
        "trust": round(result.trust, 4),
        "surprise": round(result.surprise, 4),
        "possibly": result.possibly,
        "til": result.til,
        "path": [graph.node(node_id).label for node_id in result.path.node_ids],
        "sources": [
            {"id": source.id, "type": source.source_type.value, "url": source.url}
            for source in _unique_sources(result)
        ],
    }
