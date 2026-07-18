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
zero-LLM, deterministic, reproducible by hand, and now with a **map-first** zero-dependency web UI
(`sdb serve`) — a bird's-eye view of the whole knowledge base as domain territories, with the
discovered route lighting up in place — plus a static export (`sdb build-site`) for free
hosting. The map is laid out by a deterministic pure-Python force layout (`sdb/layout.py`, ADR 0030;
its domain territories are spread apart by a centroid-separation force so the crowded centre stops
overlapping — ADR 0040) and themed "minimal terminal" (dark slate, single teal accent; ADR 0031).
Each hop now renders its
curated one-line **evidence** — the `Statement.evidence` prose that shipped in the data model since
ADR 0002 but reached no surface until ADR 0037. A **South/SE Asia cluster** (ADR 0038 —
Hinduism, Sanskrit, Maurya, Ashoka, Chola, Srivijaya, Khmer, Angkor Wat, Borobudur) then extended the
eastern reach: `sanskrit → proto_indo_european` ties the Indian classical language to the Norse/Latin
family (Sanskrit → Proto-Indo-European → Norse mythology → Loki; Angkor Wat → Hinduism → Rigveda →
Thor), the Maurya Empire rose in the wake of Alexander, and the Chola/Srivijaya thalassocracies reach
the graph through the maritime Silk Road. Then a **cultural-region surprise term** (ADR 0039) gave
`Node` the axis it was missing: `domain` models *discipline*, so a Polish→Persian→Greek→Indian science
lineage (Copernicus → al-Tusi → Euclid → Jagannatha Samrat) crossed **zero** domains; a new `Region`
macro-sphere axis + an additive `region_jumps` term (mirroring ADR 0034's weighting) scores that
cross-cultural surprise, restoring the science lineage to #1 and pushing Western-canon walking tours
out of the top results — on merit, not by tuning. A **map-layout tidy** (ADR 0040) then spread the
domain territories apart — a new centroid-separation force plus a cohesion bump cut hull overlap
~33%→~16% while keeping the cross-domain bridges visible (presentation only; no score touched). Then
an **active-period (floruit) temporal axis** (ADR 0041) closed the *second* schema-blocker term: the
existence extent models "does this still exist?" (`end_year = 2025` for 30 still-living nodes), so
India's midpoint was a meaningless `−638`; new nullable `Node.active_start`/`active_end` carry the era
of peak influence and `midpoint_year` (hence the `temporal_gap` term) keys off it, so India reads its
classical `300`, Rome-the-city its `−138`, Florence its Renaissance `1450` — 11/107 journey winners
shifted toward more trans-regional destinations (Florence → Renaissance → printing press → Paper), all
flagships intact, no new weight. All checks green (ruff, format, mypy, 151 tests).

## How to run

```sh
uv sync --extra dev                     # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"      # two archetypes: a journey + an improbable pair
uv run sdb serve                        # map-first web UI at http://127.0.0.1:8000 (zero-dep)
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

- `sdb/schema/` — `enums.py` (Domain=discipline, **Region=macro-culture** (ADR 0039),
  Predicate→Wikidata props, SourceType…) + `models.py`
  (Pydantic: `Source`, `Node` (incl. `region` and the **active-period** `active_start`/`active_end`
  axis — ADR 0041, which `midpoint_year` prefers over the existence extent), `Statement`, `Path`,
  `DiscoveryResult`).
  **Statement-reified**: every claim is a
  `Statement{subject, predicate, object, sources[], evidence, link_quality}` so multiple
  sources corroborate a fact.
- `sdb/constants.py` — **the scoring rubric**: the single source of truth for every weight/threshold.
- `sdb/graph/` — `build.py` (`KnowledgeGraph`: networkx graph + cached degree/rarity/counts + topic
  lookup) and `loader.py` (`load_seed`/`load_cooccurrence`/`load_similarity`, plus `graph_from_seed`
  and the one-call `load_graph` that both the CLI and `sdb serve` use — the sole JSON→graph path,
  moved here from `web.py` in ADR 0037).
- `sdb/engine/` — `traversal.py` (`find_paths`: exact enumeration under a budget, else a bounded
  best-first **guided walk** — ADR 0010), `surprise.py` (information-theoretic: rarity + domain jumps +
  **region jumps** (ADR 0039) + temporal gap (between nodes' **active periods**, ADR 0041) +
  **endpoint-unexpectedness** from co-occurrence),
  `confidence.py` (source rubric → noisy-OR
  corroboration → link quality → validators → weakest-link path trust), `narrate.py` (template TIL — a
  single quantized claim, ADR 0028; + `Possibly:` flag), `pipeline.py` (`discover()`, and the shared
  `discover_all`/`trust_gate` the CLI and web both dispatch through — ADR 0037).
- `sdb/harvest/` — ingestion (all deterministic given a snapshot): `client.py`
  (`SparqlClient` protocol + live `WikidataClient` + offline `FakeSparqlClient`), `mapping.py`
  (Wikidata rank/reference → `Source`, `P31` → `Domain`, PID → `Predicate` incl. alias PIDs),
  `harvester.py` (k-hop BFS → `SeedData`), `cooccurrence.py` (Wikipedia-link co-occurrence harvest),
  `merge.py` (overlay a harvest onto the curated graph: QID node-unification + independent-source
  corroboration), `snapshot.py` (pin to `data/harvest/`, git-ignored).
- `sdb/layout.py` — a deterministic, pure-Python force-directed layout (`compute_layout`, ADR 0030)
  that groups same-domain nodes into territories for the map, then spreads those territories apart
  with a centroid-separation force so they stop overlapping (ADR 0040); byte-identical every run, no
  numpy.
- `sdb/serialize.py` — the `DiscoveryResult` → JSON fields the CLI (`--json`) and the web API share
  (`result_core` + `source_dicts` + `hop_dicts`), so a new result field can't reach one surface and
  miss the other. `hop_dicts` renders the per-hop `chain` incl. each statement's curated `evidence`
  (ADR 0037); each caller keeps its own extras (CLI `rank`/`path`), rounding, and appends `sources`
  last.
- `sdb/cli.py` — the CLI (`discover` [+ `--archetype`, `--harvest`], `harvest`, `build-cooccurrence`,
  `validate-qids`, `serve`, `build-site`). `sdb/web.py` + `sdb/static/index.html` — a zero-dependency
  stdlib web UI (`sdb serve`; ADR 0013) that wraps `discover()` with no engine change: a **map-first**
  page (ADR 0031) drawing the whole graph from `graph_payload()`/`/api/graph`, themed "minimal
  terminal" (dark slate + single teal accent). The page is dual-mode, so `sdb/site.py`
  (`build-site`; ADR 0015) pre-renders a static bundle of the *same* page (now incl. the laid-out
  `graph`) for free GitHub Pages hosting.
- `data/seed.json` — curated 107-node / 158-statement graph across 10 curated domains, all now
  populated (an 11th, `other`, is the harvest-only "unclassified" bucket and is never curated —
  ADR 0032), full provenance (incl. a Renaissance cluster — Florence/Medici/Leonardo/the printing
  press, ADR 0033 — reaching antiquity via Plato, Byzantium via the Fall of Constantinople, and China
  via paper; a South/SE Asia cluster — Hinduism/Sanskrit/Maurya/Chola/Srivijaya/Khmer/Angkor Wat,
  ADR 0038 — via the Indo-European language bridge, the wake of Alexander, and the maritime Silk Road;
  and a
  Hellenistic–India–Buddhism bridge and Ancient Greece / Ancient Egypt / Islamic Golden Age /
  Scientific Revolution / East Asia / Norse–Celtic myth / Chinese-tech / West-Africa / divine-descent
  clusters — e.g. Newton → Euclid → al-Tusi → Copernicus, Thor → Rigveda → India, Mansa Musa → Islam
  → Zoroastrianism → Mithra, Elizabeth II → Alfred the Great → House of Wessex → Odin, and Naruhito →
  Jimmu → Amaterasu → Shinto).
  `data/cooccurrence.json` — committed Wikipedia-link co-occurrence for the endpoint-surprise term.
- `docs/adr/` — decisions (0003 endpoint surprise, 0004 harvester, 0005 harvest merge/corroboration,
  0006 wow-score ranking, 0007 improbable-adjacency archetype, 0008 seed-QID repair, 0009 harvest
  node enrichment, 0010 guided-walk scaling, 0011 Hellenistic–India–Buddhism bridge, 0012 default
  hop cap 6→4, 0013 web UI, 0014 corroboration spike/defer, 0015 static-site export, 0016 Ancient
  Greece cluster, 0017 Ancient Egypt cluster, 0018 Islamic Golden Age cluster, 0019 Scientific
  Revolution cluster, 0020 East Asia cluster, 0021 journey hop cap 4→3, 0022 Norse/Celtic myth
  cluster, 0023 Chinese-tech cluster, 0024 West-Africa/Islam cluster, 0025 second-order co-occurrence,
  0026 divine-descent cluster, 0027 disjoint archetype hop ranges, 0028 single-claim TIL,
  0029 full-link Jaccard similarity, 0030 deterministic graph layout, 0031 map-first terminal UI,
  0032 `other` domain / harvest-fallback split, 0033 Renaissance cluster,
  0034 domain-jump information weighting, 0035 closed temporal extents, 0036 interval separation
  measured & rejected — keep midpoint distance, 0037 surface the curated `Statement.evidence` prose
  on every hop, 0038 South/SE Asia cluster, 0039 cultural-region surprise term, 0040 spread domain
  territories to reduce map overlap, 0041 active-period (floruit) temporal axis on `Node`).
  `docs/confidence-rubric.md` — the rubric, with worked examples the tests reproduce.
  `docs/reference/`
  — the original idea sketch (git-ignored, local only).
- `tests/` — 151 tests incl. human-vs-code confidence (0.75), surprise (5.6), and endpoint (0.49 vs
  2.81) golden cases, plus harvester/mapping/co-occurrence/merge, wow-score ranking, both archetypes,
  the Hellenistic–India–Buddhism bridge, the Renaissance cluster's three bridges + its starved-start
  relief (ADR 0033), the South/SE Asia cluster's bridges (ADR 0038 — Indo-European/Sanskrit,
  Hellenistic/Maurya, maritime Silk Road, worlds-apart Angkor Wat), the region-jump term (ADR 0039 —
  a worked example, the domain/region independence property, and a guard that every curated node has a
  region), the active-period axis (ADR 0041 — a temporal worked example, the active-vs-existence
  midpoint fallback, and completeness + ordering guards over every dated curated node), the web UI
  (payload + graph payload + real localhost HTTP
  round-trips), the static-site export, a deterministic-layout suite (`test_layout.py`: reproducibility
  + the domain-cohesion property + its negative control + a domain-separation negative control that
  fewer nodes intrude on a foreign territory (ADR 0040)), a guided-walk scaling/perf test, the seed
  loaders (`test_loader.py`: single-parse + missing-sidecar tolerance), and the per-hop evidence
  contract — shared across both surfaces + a guard that every curated statement carries it (ADR 0037);
  `eval/golden.json` — ranker regression (characterization values).

## Scoring in one paragraph

**Trust** (is it true?): per-source reliability rubric → `1 − ∏(1 − rᵢ)` corroboration → × link
quality → × validator penalties; path trust = product of edge confidences. **Surprise** (is it
interesting?): `Σ −log2(count/total)` edge rarity + domain (discipline) jumps + **region (culture)
jumps** (ADR 0039, same weighting on an independent axis) + normalized temporal gap (between nodes'
**active periods** / floruits, not their existence extents — ADR 0041) +
**endpoint unexpectedness** (`−log2 P(endpoint | start)` from Wikipedia-link co-occurrence) − hub
penalty (length is *not* rewarded). Results come in two **archetypes** (ADR 0007), surfaced together:
a **journey** (a fixed 3-hop chain, ranked `surprise × trust`) and an **improbable pair** (1–2 hops,
ranked `endpoint_unexpectedness × trust`). Both gate at `trust ≥ 0.50` by default
(`--include-possibly` lowers the gate and flags `Possibly:`).

## Conventions (strict — see git history)

`main` branch, local only (no push unless asked). Conventional Commits. Identity: AnandKri
<anand.krishna0802@gmail.com>. `snake_case` modules, `PascalCase` classes, `UPPER_SNAKE_CASE`
constants, `test_<module>.py`, ADRs `NNNN-kebab.md`. Type hints + docstrings on public APIs. Ruff +
mypy + pytest must stay green (CI enforces it).

**Docs move with the code, in the same commit — `README.md` included.** If a commit changes a
user-visible fact, update it everywhere in that commit: seed size (107 nodes / 158 statements), test
count, the rubric's worked-example figures, the module list, the ADR list, domain counts. **Grep the
old number; don't trust the prose.** The live-truth docs are `README.md`, this file, and
`docs/HANDOVER.md`. **ADRs are records — never back-edit them**; mark a superseded one with a status
line + a pointer (see ADR 0033) and leave the body, including figures that were true when written.
README is the one that rots — it is the public face of a public repo and nobody reads it locally, so
it silently sat at 88 nodes / 123 statements / 99 tests while this file was current. A stale doc is a
defect here, not a cosmetic issue: the project's claim is that its record is trustworthy.

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
  a **journey** and an **improbable pair** (short 1–2 hop link between entities that feel worlds
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
