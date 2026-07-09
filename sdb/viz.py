"""Optional path visualization (requires the ``viz`` extra: ``uv sync --extra viz``).

Kept out of the core import path so the engine has zero heavyweight dependencies. ``matplotlib`` is
imported lazily inside the function.
"""

from __future__ import annotations

from pathlib import Path

from sdb.graph.build import KnowledgeGraph
from sdb.schema.models import DiscoveryResult


def draw_path(graph: KnowledgeGraph, result: DiscoveryResult, out_path: str | Path) -> Path:
    """Render a discovered path as a simple left-to-right node/edge diagram (PNG).

    Args:
        graph: The knowledge graph the result came from.
        result: The discovery result to draw.
        out_path: Where to write the PNG.

    Returns:
        The path the image was written to.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    node_ids = result.path.node_ids
    xs = list(range(len(node_ids)))
    labels = [graph.node(node_id).label for node_id in node_ids]

    fig, ax = plt.subplots(figsize=(2.2 * len(node_ids), 3))
    ax.plot(xs, [0] * len(xs), "-o", color="#b45309", markersize=10, zorder=1)
    for x, label in zip(xs, labels, strict=True):
        ax.annotate(label, (x, 0), textcoords="offset points", xytext=(0, 12), ha="center")
    for x, hop in zip(xs[1:], result.path.hops, strict=True):
        ax.annotate(
            hop.statement.predicate.value,
            (x - 0.5, 0),
            textcoords="offset points",
            xytext=(0, -16),
            ha="center",
            fontsize=8,
            color="#6b7280",
        )
    ax.set_title(result.til, fontsize=9, wrap=True)
    ax.axis("off")

    out = Path(out_path)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out
