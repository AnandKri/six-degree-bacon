"""The seed/co-occurrence loaders — the single path from on-disk JSON to a queryable graph.

`load_graph` and `graph_from_seed` moved here from `sdb.web` (ADR 0037's refactor), so the CLI no
longer imports a graph loader from the web module and `discover` no longer re-implements it inline.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdb.graph.loader import (
    graph_from_seed,
    load_cooccurrence,
    load_graph,
    load_seed,
    load_similarity,
)

_DATA = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = _DATA / "seed.json"
COOCCURRENCE_PATH = _DATA / "cooccurrence.json"


def test_load_graph_matches_a_hand_assembled_graph() -> None:
    """The one-call loader is exactly load_seed + both sidecar tables, wired together."""
    graph = load_graph(SEED_PATH, COOCCURRENCE_PATH)
    seed = load_seed(SEED_PATH)

    assert {n.id for n in graph.nodes()} == {n.id for n in seed.nodes}
    # The endpoint term is live, so the co-occurrence sidecar was actually attached.
    assert graph.endpoint_unexpectedness("roman_empire", "buddhism") > 0.0


def test_graph_from_seed_tolerates_a_missing_sidecar(tmp_path: Path) -> None:
    """A missing co-occurrence file is not an error — the endpoint term simply scores 0."""
    seed = load_seed(SEED_PATH)
    graph = graph_from_seed(seed, tmp_path / "does-not-exist.json")

    assert {n.id for n in graph.nodes()} == {n.id for n in seed.nodes}
    assert graph.endpoint_unexpectedness("roman_empire", "buddhism") == 0.0


def test_graph_from_seed_reads_the_sidecar_once(tmp_path: Path, monkeypatch) -> None:
    """The two tables share a single parse — the read-twice the refactor removed stays removed."""
    sidecar = tmp_path / "cooc.json"
    sidecar.write_text(
        json.dumps({"links": {"roman_empire": ["silk_road"]}, "similarity": {}}),
        encoding="utf-8",
    )
    reads = 0
    real_read_text = Path.read_text

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        nonlocal reads
        if self == sidecar:
            reads += 1
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    graph_from_seed(load_seed(SEED_PATH), sidecar)
    assert reads == 1


def test_load_cooccurrence_and_similarity_read_their_own_tables() -> None:
    """The two public readers each project out their table from the shared file shape."""
    links = load_cooccurrence(COOCCURRENCE_PATH)
    similarity = load_similarity(COOCCURRENCE_PATH)

    assert links and all(isinstance(v, tuple) for v in links.values())
    assert similarity and all(isinstance(v, dict) for v in similarity.values())
