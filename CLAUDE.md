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

## Status: Phase 2 in progress — see [`docs/HANDOVER.md`](docs/HANDOVER.md) for the pick-up guide

A local-first, **zero-LLM**, fully deterministic engine over a curated graph, now with (1) a
**Wikidata SPARQL harvester** that ingests a k-hop neighbourhood into the `Statement` model with
deterministic rank/reference→reliability mapping and pinned local snapshots, and (2) an
**endpoint-surprise term** — `−log P(endpoint | start)` from real Wikipedia-link co-occurrence — so
*unexpected destinations* win (Rome no longer tops out at the obvious "Latin"). Phase-2 increments add
**harvest→curated merge** (`discover --harvest`, QID unification + corroboration), harvest
noise-filtering, a **wow-score rebalance** (rank by `surprise × trust`, gated on evidence), a
**seed-QID repair** (16 hallucinated QIDs fixed), **two archetypes** (a *journey* + an *improbable
pair*), **harvest node enrichment** (P31→Domain coverage incl. `SCIENCE`/`ART`, and a full temporal
extent so harvested people are dated), and a **Hellenistic–India–Buddhism seed bridge** that connects
the science/India cluster into the Rome–Silk Road–China web. Tight, well-sourced cross-culture
connections win — e.g. Roman Empire → Silk Road → Persia → Alexander → India → Buddhism. Still
zero-LLM, deterministic, reproducible by hand, and now with a zero-dependency web UI (`sdb serve`)
plus a static export (`sdb build-site`, theme-able for embedding) for free hosting. All checks green
(ruff, format, mypy, 93 tests).

## How to run

```sh
uv sync --extra dev                     # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"      # two archetypes: a journey + an improbable pair
uv run sdb serve                        # interactive web UI at http://127.0.0.1:8000 (zero-dep)
uv run sdb build-site                    # pre-render a static site/ for free GitHub Pages hosting
uv run sdb validate-qids                # check every node's wikidata_qid resolves (guard, ADR 0008)
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
- `sdb/engine/` — `traversal.py` (`find_paths`: exact enumeration under a budget, else a bounded
  best-first **guided walk** — ADR 0010), `surprise.py` (information-theoretic +
  **endpoint-unexpectedness** from co-occurrence), `confidence.py` (source rubric → noisy-OR
  corroboration → link quality → validators → weakest-link path trust), `narrate.py` (template TIL +
  `Possibly:` flag), `pipeline.py` (`discover()`).
- `sdb/harvest/` — ingestion (all deterministic given a snapshot): `client.py`
  (`SparqlClient` protocol + live `WikidataClient` + offline `FakeSparqlClient`), `mapping.py`
  (Wikidata rank/reference → `Source`, `P31` → `Domain`, PID → `Predicate` incl. alias PIDs),
  `harvester.py` (k-hop BFS → `SeedData`), `cooccurrence.py` (Wikipedia-link co-occurrence harvest),
  `merge.py` (overlay a harvest onto the curated graph: QID node-unification + independent-source
  corroboration), `snapshot.py` (pin to `data/harvest/`, git-ignored).
- `sdb/cli.py` — the CLI (`discover` [+ `--archetype`, `--harvest`], `harvest`, `build-cooccurrence`,
  `validate-qids`, `serve`, `build-site`). `sdb/web.py` + `sdb/static/index.html` — a zero-dependency
  stdlib web UI (`sdb serve`; ADR 0013) that wraps `discover()` with no engine change; the page is
  dual-mode, so `sdb/site.py` (`build-site`; ADR 0015) pre-renders a static bundle of the *same* page
  for free GitHub Pages hosting. `sdb/viz.py` — optional matplotlib path drawing (`viz` extra).
- `data/seed.json` — curated 81-node / 116-statement graph across 9 domains, full provenance (incl. a
  Hellenistic–India–Buddhism bridge and Ancient Greece / Ancient Egypt / Islamic Golden Age /
  Scientific Revolution / East Asia / Norse–Celtic myth / Chinese-tech / West-Africa clusters — e.g.
  Newton → Euclid → al-Tusi → Copernicus, Zen → Buddhism → India → Alexander, Thor → Rigveda → India,
  Paper → Silk Road → Buddhism → India, and Mansa Musa → Islam → Zoroastrianism → Mithra).
  `data/cooccurrence.json` — committed Wikipedia-link co-occurrence for the endpoint-surprise term.
- `docs/adr/` — decisions (0003 endpoint surprise, 0004 harvester, 0005 harvest merge/corroboration,
  0006 wow-score ranking, 0007 improbable-adjacency archetype, 0008 seed-QID repair, 0009 harvest
  node enrichment, 0010 guided-walk scaling, 0011 Hellenistic–India–Buddhism bridge, 0012 default
  hop cap 6→4, 0013 web UI, 0014 corroboration spike/defer, 0015 static-site export, 0016 Ancient
  Greece cluster, 0017 Ancient Egypt cluster, 0018 Islamic Golden Age cluster, 0019 Scientific
  Revolution cluster, 0020 East Asia cluster, 0021 journey hop cap 4→3, 0022 Norse/Celtic myth
  cluster, 0023 Chinese-tech cluster, 0024 West-Africa/Islam cluster). `docs/confidence-rubric.md` —
  the rubric, with worked examples the tests reproduce.
  `docs/reference/`
  — the original idea sketch (git-ignored, local only).
- `tests/` — 93 tests incl. human-vs-code confidence (0.75), surprise (8.6), and endpoint (0.49 vs
  2.81) golden cases, plus harvester/mapping/co-occurrence/merge, wow-score ranking, both archetypes,
  the Hellenistic–India–Buddhism bridge, the web UI (payload + a real localhost HTTP round-trip), the
  static-site export, and a guided-walk scaling/perf test; `eval/golden.json` —
  ranker regression (characterization values).

## Scoring in one paragraph

**Trust** (is it true?): per-source reliability rubric → `1 − ∏(1 − rᵢ)` corroboration → × link
quality → × validator penalties; path trust = product of edge confidences. **Surprise** (is it
interesting?): `Σ −log2(count/total)` edge rarity + domain jumps + normalized temporal gap +
**endpoint unexpectedness** (`−log2 P(endpoint | start)` from Wikipedia-link co-occurrence) − hub
penalty (length is *not* rewarded). Results come in two **archetypes** (ADR 0007), surfaced together:
a **journey** (a fixed 3-hop chain, ranked `surprise × trust`) and an **improbable pair** (1–3 hops,
ranked `endpoint_unexpectedness × trust`). Both gate at `trust ≥ 0.50` by default
(`--include-possibly` lowers the gate and flags `Possibly:`).

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

- ✅ **Harvest node enrichment** (ADR 0009): grew `INSTANCE_OF_DOMAIN` (P31→Domain) by ~44 verified
  classes — first-class `SCIENCE`/`ART` coverage (both previously had *zero* mappings) plus common
  geography/history/religion/language/myth subtypes — so fewer harvested nodes fall to the `culture`
  fallback and cross-domain surprise reflects real structure. Pulled a full temporal extent:
  `entities()` now also reads birth/death (P569/P570) and dissolution (P576), folded by
  `mapping.temporal_extent` (`start = inception ?? birth`, `end = dissolution ?? death`), so
  **harvested people are dated** (were `None` — P571 doesn't apply to humans; live Euclid harvest now
  gives (-333, -284)). Every added QID verified against Wikidata (one "Hurricane"/city mismatch
  dropped, the ADR 0008 failure mode). `time_precision` left unset (no score consumes it).
- ✅ **Seed-QID repair** (ADR 0008): 16 of 31 curated `wikidata_qid`s were hallucinated (silk_road →
  "Russian Empire", proto_indo_european → "Secure Shell"), faking provenance and poisoning
  co-occurrence. Repaired deterministically (label → Wikipedia article → `wikibase_item`, verified),
  co-occurrence rebuilt. De-artifacted results (Mithraism correctly reads as expected-from-Rome, not
  a false surprise). A `validate-qids` guard + `tests/test_validate.py` prevent recurrence.
- ✅ **Type-B seed coverage** (ADR 0011): added a science subgraph (Euclid → al-Tusi → Jagannatha
  Samrat → Jai Singh II) and then a **Hellenistic–India–Buddhism bridge** (India, Buddhism, Alexander
  the Great, Alexandria + 8 sourced links) that connects the formerly-isolated science/India cluster
  into the Rome–Silk Road–China web. New flagship journey **Roman Empire → … → Buddhism** (5 hops) and
  genuinely worlds-apart improbable pairs (Buddhism ↔ Rome/Great Wall, Alexander ↔ Rigveda). Nuance
  found earlier: Jai Singh ↔ Euclid *is* documented together on Wikipedia, so the improbable-pair
  archetype correctly does **not** flag it — it isn't fooled by a famous-but-documented link.
- ✅ **Wow-score rebalance** (ADR 0006): rank by `surprise × trust`, gate at `trust ≥ 0.50` by default
  (`--include-possibly` to see speculative), and drop the length reward. Tight, well-evidenced
  connections now win over long low-trust rambles; topics with no confident connection honestly
  return nothing.
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
- ✅ **"Improbable adjacency" archetype (ADR 0007):** `sdb discover` now surfaces two archetypes —
  a **journey** and an **improbable pair** (short 1–3 hop link between entities that feel worlds
  apart, ranked `endpoint_unexpectedness × trust`). Rome → Great Wall of China (2 hops) is a genuine
  Type-B wow; obvious neighbours (Rome → Latin) correctly rank low. Richer Type-B destinations await
  broader seed coverage.
- ✅ **Guided walk for scale (ADR 0010):** `find_paths` enumerates exhaustively while cheap and
  switches to a bounded best-first **`guided_paths`** only when a search would exceed `EXACT_PATH_BUDGET`
  (5000; seed worst case ~189, so the seed stays exact — all golden/planted/archetype tests
  unchanged). The walk is guided by a prefix *promise* mirroring the surprise score (rarity + domain
  jumps + endpoint-unexpectedness − hub penalty, same weights), deterministic, and bounded by
  candidate/expansion budgets. Guidance orders discovery only; scoring is unchanged. A perf test
  proves it: a dense 1500-node graph overflows exhaustive `[3,6]` while `find_paths` stays ≤ budget.
- Still open: higher-fidelity endpoint co-occurrence; neighbourhood pre-pruning + a tuned promise
  heuristic if guided-only recall needs it on real harvests. Neo4j (NL→Cypher for ~10k+ nodes), a
  web UI, an optional free/local LLM narrator remain graduations — adopt only when earned.
