# Hand-over — Six Degree Bacon (for the next session)

A working note to continue the project. Pair it with [`CLAUDE.md`](../CLAUDE.md) (the canonical guide)
and the ADRs in [`docs/adr/`](adr/). As of this note: **Phase 2 in progress**, `main` @ pushed,
all checks green (**72 tests**).

## 1. What it is (one paragraph)

Inverts "Six Degrees of Kevin Bacon": from a topic, find a *surprising, true, well-sourced* multi-hop
connection, each result carrying a **reproducible trust score and surprise score**. Hard rule:
**correctness never depends on an LLM** — every score is deterministic and reproducible by hand from
[`docs/confidence-rubric.md`](confidence-rubric.md). Local-first, zero external services at runtime.

## 2. Run & verify

```sh
uv sync --extra dev
uv run sdb discover "Roman Empire"           # two archetypes: a journey + an improbable pair
uv run sdb discover "Trojan War" --include-possibly
uv run sdb validate-qids                      # network: checks seed QIDs resolve (guard for ADR 0008)
uv run ruff check . && uv run ruff format --check . && uv run mypy sdb && uv run pytest
```
Windows note: prefix console-printing scripts with `PYTHONUTF8=1` or the cp1252 console chokes on
Unicode (the `sdb` CLI already degrades to ASCII safely; this only bites ad-hoc `python -c` scripts).

## 3. Architecture map

- `sdb/schema/` — `enums.py` (Domain, Predicate→Wikidata props, SourceType, **Archetype**),
  `models.py` (Pydantic; `DiscoveryResult` has `archetype`, `score`, `endpoint_unexpectedness`).
- `sdb/constants.py` — **the rubric**: every weight/threshold. `wow = surprise × trust`; default gate
  `trust ≥ 0.50`; UNLIKELY hop range `[1,3]`; JOURNEY `[3,4]` (default cap cut 6→4, ADR 0012, still
  `--max-hops`-overridable). No length reward.
- `sdb/graph/build.py` — `KnowledgeGraph`: networkx graph + cached rarity/degree + **co-occurrence**
  (`endpoint_unexpectedness`). `loader.py` — `load_seed`, `load_cooccurrence`.
- `sdb/engine/` — `traversal.py` (`find_paths`: exact `enumerate_paths` under budget, else bounded
  best-first `guided_paths` — ADR 0010), `surprise.py`, `confidence.py` (trust), `narrate.py`
  (template TIL), `pipeline.py` (`discover(..., archetype=...)`).
- `sdb/harvest/` — `client.py` (SPARQL, live + fake), `mapping.py` (rank/ref→Source, P31→Domain,
  PID→Predicate + aliases, `HARVEST_EXCLUDED_PROPERTIES`), `harvester.py` (k-hop BFS→SeedData),
  `cooccurrence.py` (Wikipedia-link matrix), `merge.py` (overlay harvest onto seed + corroboration),
  `snapshot.py` (pin to git-ignored `data/harvest/`), `validate.py` (QID guard).
- `sdb/cli.py` — `discover` (`--archetype`, `--include-possibly`, `--harvest`), `harvest`,
  `build-cooccurrence`, `validate-qids`.
- `data/seed.json` (41 nodes / 54 statements, verified QIDs) + `data/cooccurrence.json` (committed).
- `eval/golden.json` — ranker regression (characterization values, not hand-picked).

## 4. Done so far (see the ADRs)

Phase 0 deterministic engine · Phase 1 (ADR 0003 endpoint-surprise from co-occurrence, 0004 Wikidata
harvester) · Phase 2 so far: 0005 harvest→curated merge+corroboration, **0006 wow = surprise × trust
+ evidence gate**, **0007 two archetypes (journey + improbable pair)**, **0008 seed-QID repair**
(16 hallucinated QIDs fixed). Plus harvest noise-filtering (exclude bibliographic P1343) and the
QID-validation guard.

**Key finding (do not re-litigate):** cross-source *corroboration* is low-yield on this seed — the
curated relations are hand-modelled abstractions ("Rome *located_in* it") that structured KBs encode
differently (`capital`, `birthPlace`) or not at all. Proven via a DBpedia spike. It needs a genuinely
independent source **plus** a predicate-alignment layer to pay off. Merge's real win today is
**breadth**, not corroboration.

## 5. Remaining work (priority order)

1. ✅ **Seed coverage for genuine improbable pairs (Type B) (ADR 0011).** Added a Hellenistic–India–
   Buddhism bridge (India, Buddhism, Alexander the Great, Alexandria + 8 short cross-cultural links,
   all sourced, QIDs verified) that connects the formerly-isolated science/India cluster into the
   Rome–Silk Road–China web. New flagship journey: Roman Empire → Silk Road → Persia → Alexander →
   India → Buddhism (5 hops); new worlds-apart pairs Buddhism ↔ Rome/Great Wall/Persia, Alexander ↔
   Buddhism/Rigveda. Re-ran `validate-qids` (41/41) → `build-cooccurrence` (41 nodes) →
   re-characterised `eval/golden.json`. **Remaining caveat (unchanged):** intrinsically obscure nodes
   have thin Wikipedia co-occurrence → occasional false "improbable" (e.g. Jai Singh → his own court
   astronomer); mitigate by bridging through well-documented nodes. **Process after any
   `data/seed.json` edit:** `sdb validate-qids` → `sdb build-cooccurrence` → re-check `eval/golden.json`
   (adding edges shifts global predicate rarity, so journey winners can move).
2. ✅ **Node enrichment on the harvest path (ADR 0009).** Grew `INSTANCE_OF_DOMAIN` (P31→Domain) by
   ~44 verified classes — first-class `SCIENCE`/`ART` coverage (both had *zero* mappings) plus common
   geography/history/religion/language/myth subtypes — so fewer harvested nodes fall to the `culture`
   fallback. Pulled a full temporal extent: `entities()` now reads birth/death (P569/P570) and
   dissolution (P576) alongside inception (P571), folded by `mapping.temporal_extent`
   (`start = inception ?? birth`, `end = dissolution ?? death`). **Harvested people are now dated**
   (were `None` — P571 doesn't apply to humans): a live 1-hop Euclid harvest yields (-333, -284).
   Every added QID verified against Wikidata (one "Hurricane"/city mismatch dropped). `time_precision`
   left unset (no score consumes it). Seed untouched → no validate-qids/co-occurrence/golden churn.
3. ✅ **Guided/seeded walk (scale) (ADR 0010).** `find_paths` now enumerates exhaustively while that
   stays cheap and switches to a bounded **best-first `guided_paths`** only when a search would exceed
   `EXACT_PATH_BUDGET` (5000; seed worst case is ~189, so the seed is always exact — golden/planted/
   archetype tests unchanged). The walk is guided by a prefix *promise* mirroring the surprise score
   (rarity + domain jumps + endpoint-unexpectedness − hub penalty, same weights), bounded by
   `GUIDED_CANDIDATE_BUDGET`/`GUIDED_EXPANSION_BUDGET`, deterministic (monotonic-counter heap ties).
   Guidance orders discovery only; scoring is unchanged. Perf test locks it: on a dense 1500-node
   graph exhaustive `[3,6]` overflows while `find_paths` returns ≤ budget in ~67 ms, deterministically.
4. **Corroboration, only if earned:** a second *independent* source (DBpedia/Wikipedia-text) **with**
   a deterministic predicate-alignment table. See §4 — don't build without the alignment layer.
5. **Wire `validate-qids` into CI** (a network-enabled job) so hallucinated QIDs can't reappear.

Documented graduations (adopt only when earned): Neo4j (scale/NL→Cypher), a web UI, an optional
free/local LLM narrator behind the existing template seam.

## 6. Conventions / gotchas

- **Commit only when asked.** Conventional Commits; identity `AnandKri <anand.krishna0802@gmail.com>`;
  end messages with the `Co-Authored-By: Claude …` trailer. `main`, push only when asked.
- **Tests are offline & deterministic.** Network clients sit behind protocols with fakes
  (`FakeSparqlClient`, fake resolvers). Never add a network-dependent unit test.
- **Harvest snapshots** go to `data/harvest/` (git-ignored). `data/seed.json` +
  `data/cooccurrence.json` are the tracked, authoritative data.
- **Scores must stay hand-reproducible** — if you add a scoring term, document it in the rubric with a
  worked example the tests reproduce, and record the decision in a new ADR.
- After changing `data/seed.json`, always: `validate-qids` → `build-cooccurrence` → re-check golden.
