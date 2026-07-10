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
*unexpected destinations* win (Rome no longer tops out at the obvious "Latin"). Phase-2 increments add
**harvest→curated merge** (`discover --harvest`, QID unification + corroboration), harvest
noise-filtering, and a **wow-score rebalance** — results now rank by `surprise × trust` and are gated
on evidence, so tight, well-sourced connections win (Rome → Mithra in 4 sourced hops) over long
low-trust rambles. Still zero-LLM, deterministic, reproducible by hand. All checks green (ruff,
format, mypy, 54 tests).

## How to run

```sh
uv sync --extra dev                     # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"      # a confident, sourced TIL card (now: Rome -> Mithra, 4 hops)
uv run sdb discover "Trojan War" --include-possibly   # speculative paths when none clear the gate
uv run sdb discover "Silk Road" --top 3 --json
uv run sdb harvest Q2277 --hops 2       # pin a Wikidata neighbourhood -> data/harvest/ (git-ignored)
uv run sdb discover "Roman Empire" --harvest data/harvest/q2277.json   # overlay a harvest, merged
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
- `sdb/harvest/` — ingestion (all deterministic given a snapshot): `client.py`
  (`SparqlClient` protocol + live `WikidataClient` + offline `FakeSparqlClient`), `mapping.py`
  (Wikidata rank/reference → `Source`, `P31` → `Domain`, PID → `Predicate` incl. alias PIDs),
  `harvester.py` (k-hop BFS → `SeedData`), `cooccurrence.py` (Wikipedia-link co-occurrence harvest),
  `merge.py` (overlay a harvest onto the curated graph: QID node-unification + independent-source
  corroboration), `snapshot.py` (pin to `data/harvest/`, git-ignored).
- `sdb/cli.py` — the CLI (`discover` [+ `--harvest` overlay], `harvest`, `build-cooccurrence`).
  `sdb/viz.py` — optional matplotlib path drawing (`viz` extra).
- `data/seed.json` — curated 33-node / 40-statement graph across 8 domains, full provenance.
  `data/cooccurrence.json` — committed Wikipedia-link co-occurrence for the endpoint-surprise term.
- `docs/adr/` — decisions (0003 endpoint surprise, 0004 harvester, 0005 harvest merge/corroboration,
  0006 wow-score ranking; 0007 improbable-adjacency archetype *proposed*). `docs/confidence-rubric.md`
  — the rubric, with worked examples the tests reproduce. `docs/reference/` — the original idea
  sketch (git-ignored, local only).
- `tests/` — 54 tests incl. human-vs-code confidence (0.75), surprise (8.6), and endpoint (0.49 vs
  2.81) golden cases, plus harvester/mapping/co-occurrence/merge and wow-score ranking;
  `eval/golden.json` — ranker regression (characterization values).

## Scoring in one paragraph

**Trust** (is it true?): per-source reliability rubric → `1 − ∏(1 − rᵢ)` corroboration → × link
quality → × validator penalties; path trust = product of edge confidences. **Surprise** (is it
interesting?): `Σ −log2(count/total)` edge rarity + domain jumps + normalized temporal gap +
**endpoint unexpectedness** (`−log2 P(endpoint | start)` from Wikipedia-link co-occurrence) − hub
penalty (length is *not* rewarded). Results rank by the **wow score `surprise × trust`** and are
gated at `trust ≥ 0.50` by default (`--include-possibly` lowers the gate and flags `Possibly:`).

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

## Phase 2 — in progress

- ✅ **Wow-score rebalance** (ADR 0006): rank by `surprise × trust`, gate at `trust ≥ 0.50` by default
  (`--include-possibly` to see speculative), and drop the length reward. Tight, well-evidenced
  connections now win (Rome → Mithra, 4 hops, trust 0.84; Zoroastrianism → Qin Shi Huang) over long
  low-trust rambles; topics with no confident connection honestly return nothing.
- ✅ **Harvest→curated merge** (ADR 0005): `discover --harvest <snapshot>` overlays a harvest onto
  the tracked seed — QID node-unification + independent-source corroboration (noisy-OR, with a guard
  so a Wikidata harvest never double-counts a fact already citing Wikidata). Measured win is
  **breadth** (one 2-hop harvest: 33→73 nodes, 25→44 reachable endpoints). Also widened the harvest
  vocabulary: `inspired_by`→P941, alias PIDs (P17/P131→located_in, P463→part_of), bigger `P31`→Domain.
- ✅ **Harvest noise-filtering**: `P1343` ("described by source") is Wikidata's *bibliographic*
  citation relation, bulk-linked to old public-domain encyclopedias (Brockhaus, Meyers, Nuttall…).
  It stays in the vocabulary for curated `MENTIONED_IN` but is never harvested
  (`HARVEST_EXCLUDED_PROPERTIES`), so a 2-hop Roman-Empire harvest drops 40→26 nodes with the
  encyclopedia clutter gone and new endpoints that are real entities (Constantinople, Papal States…).
- **Known finding (ADR 0005):** corroboration is correct but near-dormant on this seed, which is
  already Wikidata-sourced wherever Wikidata agrees. Its value needs a **genuinely independent second
  source** (DBpedia / Wikipedia-text extraction) — a documented graduation, built only when earned.
- **Proposed — "improbable adjacency" archetype (ADR 0007):** surface *short* (1–3 hop) improbable
  links (e.g. "Jai Singh had Euclid translated into Sanskrit") as a first-class "wow", by lowering
  `MIN_HOPS_DEFAULT` and rewarding surprise *density* (per-hop) alongside the "journey" archetype.
- Still open: a **guided/seeded walk** to replace exhaustive enumeration at scale (ADR 0001);
  richer node enrichment (fewer `culture`-fallback domains); higher-fidelity endpoint co-occurrence.
  Neo4j, a web UI, an optional free/local LLM narrator remain graduations — adopt only when earned.
