# ADR 0001 — Local Python, in-memory graph, zero-LLM engine

- **Status:** accepted
- **Phase:** 0

## Context

Six Degree Bacon must (1) discover *surprising* multi-hop paths between ideas and (2) be a reference
for AI-assisted coding done correctly, under a hard constraint of minimal cost. The original sketch
proposed Neo4j + an LLM extraction/ranking/narration pipeline.

## Decision

For Phase 0 we build a **local-first, pure-Python** engine with **no LLM** and **no external
services**:

- **Graph:** an in-memory `networkx.MultiGraph`. The traversal we need is non-standard — the
  *longest surprising* path, avoiding hubs and preferring rare edges — which is easier to express and
  control in Python than in Cypher, and needs no database for a small graph.
- **No LLM.** Traversal, surprise, and trust are deterministic functions of measurable features; the
  narrative is template-composed. This is free, reproducible, and means correctness never depends on
  a model. A free/local LLM narrator is an optional later upgrade *behind an interface*; the template
  stays the guaranteed fallback.
- **Reproducibility:** `uv`-locked dependencies, deterministic traversal ordering and scoring, a
  tracked curated seed graph, `ruff` + `mypy` + `pytest` in CI.

Hub-avoidance and rare-edge preference are realized in the **surprise ranking**, not by pruning the
traversal — cleaner, and exactly equivalent while the graph is small enough to enumerate exhaustively.

## Consequences

- Anyone can reproduce any score by hand from `docs/confidence-rubric.md`.
- Exhaustive path enumeration is fine for the Phase-0 seed but will not scale; Phase 1 replaces it
  with a guided/seeded walk, and Neo4j + NL→Cypher remain a documented graduation for ~10k+ nodes.

## Graduations (later phases, only when earned)

Neo4j (scale / NL→Cypher) · a web UI (Gradio on a free HF Space) · an automated Wikidata ingestion
pipeline · an optional free/local LLM narrator. Each sits behind an interface so adoption is a swap.
