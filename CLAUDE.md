# CLAUDE.md — project guide for AI assistants

## What this is

**Six Degree Bacon** inverts "Six Degrees of Kevin Bacon": instead of the *shortest* path between two
things, it finds the *longest **meaningful*** one — a chain of real, sourced connections that hops
across domains (myth → religion → trade → history) until it lands somewhere surprising, presented as
a "TIL" card.

Two north stars:
1. **Product:** type a topic → get a genuinely surprising, true, well-sourced multi-hop connection,
   each result carrying a **reproducible trust score and surprise score**.
2. **Craft:** a reference for *AI-assisted coding done correctly* — deterministic, typed, tested,
   evaluated, fully provenanced. **Correctness never depends on an LLM.** Every score is reproducible
   by hand from `docs/confidence-rubric.md`.

## Status: Phase 1 complete

A local-first, **zero-LLM**, fully deterministic engine over a curated graph, now with (1) a
**Wikidata SPARQL harvester** that ingests a k-hop neighbourhood into the `Statement` model with
deterministic rank/reference→reliability mapping and pinned local snapshots, and (2) an
**endpoint-surprise term** — `−log P(endpoint | start)` from real Wikipedia-link co-occurrence — so
*unexpected destinations* win (Rome no longer tops out at the obvious "Latin"). Still zero-LLM,
deterministic, reproducible by hand. All checks green (ruff, format, mypy, 45 tests).

## How to run

```sh
uv sync --extra dev                     # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"      # a sourced TIL card (now: Chang'an, not Latin)
uv run sdb discover "Silk Road" --top 3 --json
uv run sdb harvest Q2277 --hops 2       # pin a Wikidata neighbourhood -> data/harvest/ (git-ignored)
uv run sdb build-cooccurrence           # refresh data/cooccurrence.json from Wikipedia links
uv run ruff check . && uv run ruff format --check . && uv run mypy sdb && uv run pytest
```

`make check` / `make discover` also work on Unix/CI. On Windows there is no `make`; run the `uv`
commands directly. The CLI degrades to ASCII glyphs automatically on a legacy console.

## Architecture (all pure Python, deterministic)

```
topic -> graph (networkx MultiGraph) -> traverse -> score surprise -> rank/filter by trust -> template TIL
```

- `sdb/schema/` — `enums.py` (Domain, Predicate→Wikidata props, SourceType…) + `models.py`
  (Pydantic: `Source`, `Node`, `Statement`, `Path`, `DiscoveryResult`). **Statement-reified**: every
  claim is a `Statement{subject, predicate, object, sources[], evidence, link_quality}` so multiple
  sources corroborate a fact.
- `sdb/constants.py` — **the scoring rubric**: the single source of truth for every weight/threshold.
- `sdb/graph/` — `build.py` (`KnowledgeGraph`: networkx graph + cached degree/rarity/counts + topic
  lookup) and `loader.py`.
- `sdb/engine/` — `traversal.py` (exhaustive simple-path enumeration), `surprise.py`
  (information-theoretic + **endpoint-unexpectedness** from co-occurrence), `confidence.py` (source
  rubric → noisy-OR corroboration → link quality → validators → weakest-link path trust),
  `narrate.py` (template TIL + `Possibly:` flag), `pipeline.py` (`discover()`).
- `sdb/harvest/` — Phase-1 ingestion (all deterministic given a snapshot): `client.py`
  (`SparqlClient` protocol + live `WikidataClient` + offline `FakeSparqlClient`), `mapping.py`
  (Wikidata rank/reference → `Source`, `P31` → `Domain`, PID → `Predicate`), `harvester.py` (k-hop
  BFS → `SeedData`), `cooccurrence.py` (Wikipedia-link co-occurrence harvest), `snapshot.py` (pin to
  `data/harvest/`, git-ignored).
- `sdb/cli.py` — the CLI (`discover`, `harvest`, `build-cooccurrence`). `sdb/viz.py` — optional
  matplotlib path drawing (`viz` extra).
- `data/seed.json` — curated 33-node / 40-statement graph across 8 domains, full provenance.
  `data/cooccurrence.json` — committed Wikipedia-link co-occurrence for the endpoint-surprise term.
- `docs/adr/` — decisions (0003 endpoint surprise, 0004 harvester). `docs/confidence-rubric.md` — the
  rubric, with worked examples the tests reproduce. `docs/reference/` — the original idea sketch
  (git-ignored, local only).
- `tests/` — 45 tests incl. human-vs-code confidence (0.75), surprise (8.6), and endpoint (0.49 vs
  2.81) golden cases, plus harvester/mapping/co-occurrence; `eval/golden.json` — ranker regression
  (characterization values).

## Scoring in one paragraph

**Trust** (is it true?): per-source reliability rubric → `1 − ∏(1 − rᵢ)` corroboration → × link
quality → × validator penalties; path trust = product of edge confidences. **Surprise** (is it
interesting?): `Σ −log2(count/total)` edge rarity + domain jumps + normalized temporal gap + length +
**endpoint unexpectedness** (`−log2 P(endpoint | start)` from Wikipedia-link co-occurrence) − hub
penalty. Results rank by **surprise**, with **trust** as tie-break + a hard floor. Below 0.5 trust →
`Possibly:`.

## Conventions (strict — see git history)

`main` branch, local only (no push unless asked). Conventional Commits. Identity: AnandKri
<anand.krishna0802@gmail.com>. `snake_case` modules, `PascalCase` classes, `UPPER_SNAKE_CASE`
constants, `test_<module>.py`, ADRs `NNNN-kebab.md`. Type hints + docstrings on public APIs. Ruff +
mypy + pytest must stay green (CI enforces it).

## Phase 1 — done (see ADR 0003, 0004)

1. ✅ **Wikidata SPARQL harvester** (`sdb/harvest/`): k-hop neighbourhood → `Statement` model,
   deterministic rank/reference→reliability mapping, pinned `data/harvest/` snapshots, stdlib-only
   client behind a protocol (offline `FakeSparqlClient` for tests).
2. ✅ **Endpoint-surprise fix**: `−log2 P(endpoint | start)` from real Wikipedia-link co-occurrence
   (`data/cooccurrence.json`), `W_ENDPOINT = 4.0` tuned against `eval/`. Rome now tops out at
   Chang'an, not Latin; regression-locked in `eval/golden.json` + `tests/test_eval_golden.py`.
3. ✅ Stayed **zero-LLM and deterministic**; every score still reproducible by hand.

## Next: Phase 2 candidates (only when earned)

- A **guided/seeded walk** to replace exhaustive enumeration once harvested graphs outgrow it
  (ADR 0001), and richer node enrichment (dates, better `P31`→`Domain`) on the harvest path.
- Higher-fidelity endpoint co-occurrence (backlink corpora) behind the existing `WikipediaClient`
  seam. Neo4j (scale / NL→Cypher), a web UI, an optional free/local LLM narrator remain documented
  graduations behind an interface — adopt only when earned.
