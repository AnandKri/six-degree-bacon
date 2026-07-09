# Six Degree Bacon

> The "Six Degrees of Kevin Bacon" game, **inverted**: instead of the *shortest* path between two
> things, find the *longest **meaningful*** one — a chain of real, sourced connections that hops
> across domains (myth → religion → trade → history) until it lands somewhere genuinely surprising,
> and present it as a "TIL".

This repository is **Phase 0**: a local-first, **zero-LLM**, fully deterministic engine over a small
curated knowledge graph. Every number it shows — a **trust** score and a **surprise** score — is a
deterministic function of measurable evidence that a human can reproduce by hand from
[`docs/confidence-rubric.md`](docs/confidence-rubric.md). Correctness never depends on an LLM.

## What it does

```
topic ─▶ graph (networkx) ─▶ traverse ─▶ score surprise ─▶ rank / filter by trust ─▶ template TIL
```

- **Traverse** — enumerate candidate multi-hop paths from the topic node.
- **Surprise** (information-theoretic, deterministic) — rewards rare edges, cross-domain jumps,
  temporal leaps, and length; penalizes routing through hubs.
- **Trust** (deterministic) — per-source reliability rubric → multi-source corroboration (noisy-OR) →
  entity-link quality → validation penalties → weakest-link path trust.
- **Narrate** — a template composes the TIL, citing sources and prefixing `Possibly:` when trust is
  low. (A free/local LLM narrator is an optional later upgrade; the template stays the fallback.)

## Quick start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```sh
uv sync --extra dev          # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"
uv run pytest                # run the test suite
```

On Unix / CI you can use the `Makefile` instead: `make install`, `make check`, `make discover`.

## Repository layout

```
sdb/
  schema/     enums (Domain, Predicate, SourceType, …) + Pydantic models (Node, Statement, …)
  graph/      build a networkx graph + cache derived features (degree, rarity, counts)
  engine/     traversal · surprise · confidence · narrate · pipeline   (pure, deterministic)
  constants.py  the scoring rubric — the single source of truth for every weight and threshold
  cli.py      `sdb discover "<topic>"`
data/seed.json  the curated Phase-0 graph, with a planted cross-domain surprising path + sources
docs/         ADRs and the confidence rubric (the original idea sketch is kept locally, untracked)
eval/         golden expectations (ranker regression)
tests/        unit tests, incl. the human-vs-code confidence & surprise checks
```

## Design decisions

See [`docs/adr/`](docs/adr/). In short: local Python + in-memory `networkx` (the traversal we want is
non-standard and easier to control in Python than in Cypher); zero LLM (determinism + reproducibility
+ $0); a statement-reified, Wikidata-aligned data model (so multiple sources can corroborate a fact).
Heavier options — Neo4j, an ingestion pipeline, a web UI, an optional free/local LLM narrator — are
documented graduations for later phases, entered only when they earn their keep.

## License

MIT.
