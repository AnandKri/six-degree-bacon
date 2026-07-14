# Hand-over — Six Degree Bacon (for the next session)

A working note to continue the project. Pair it with [`CLAUDE.md`](../CLAUDE.md) (the canonical guide)
and the ADRs in [`docs/adr/`](adr/). As of this note: **Phase 2**, **pushed to `origin/main`**
(public repo `github.com/AnandKri/six-degree-bacon`), **CI green**, **GitHub Pages live**, all checks
green (**90 tests**). Seed: **76 nodes / 107 statements**, 9 domains.

## 1. What it is (one paragraph)

Inverts "Six Degrees of Kevin Bacon": from a topic, find a *surprising, true, well-sourced* multi-hop
connection, each result carrying a **reproducible trust score and surprise score**. Hard rule:
**correctness never depends on an LLM** — every score is deterministic and reproducible by hand from
[`docs/confidence-rubric.md`](confidence-rubric.md). Local-first, zero external services at runtime.

## 2. Run, verify & deploy

```sh
uv sync --extra dev
uv run sdb discover "Roman Empire"           # two archetypes: a journey + an improbable pair
uv run sdb discover "Trojan War" --include-possibly
uv run sdb serve                             # interactive web UI (zero-dep, ADR 0013) at :8000
uv run sdb build-site                        # static export -> site/ for free hosting (ADR 0015)
uv run sdb validate-qids                     # network: checks seed QIDs resolve (guard for ADR 0008)
uv run ruff check . && uv run ruff format --check . && uv run mypy sdb && uv run pytest
```

**Deployment (all live/ready):**
- **GitHub Pages** — auto-builds + deploys on every push to `main` (`.github/workflows/pages.yaml`);
  live at `https://anandkri.github.io/six-degree-bacon/`. Repo setting already on (Pages → Actions).
- **Live server** — `sdb serve --host 0.0.0.0` reads `$PORT`, so Render / HF Docker Space / Fly / Cloud
  Run run it as-is.
- **React embed** — the page is dual-mode; `build-site --theme <css>` injects a theme override. A
  themed bundle already lives in the user's separate repo at `<personal-site>/public/six-degrees/`
  (theme `six-degrees-theme.css`, notes `six-degrees-README.md`). **Regenerate after any seed change:**
  `sdb build-site --out <personal-site>/public/six-degrees --theme <personal-site>/six-degrees-theme.css`.
  See memory `sdb-deployment-react` (that repo has no CLAUDE.md/memory; point its Claude at the README).

Windows note: prefix ad-hoc `python -c` scripts with `PYTHONUTF8=1` or the cp1252 console chokes on
Unicode labels (the `sdb` CLI already degrades to ASCII safely).

## 3. Architecture map

- `sdb/schema/` — `enums.py` (Domain, Predicate→Wikidata props, SourceType, **Archetype**),
  `models.py` (Pydantic; `DiscoveryResult` has `archetype`, `score`, `endpoint_unexpectedness`).
- `sdb/constants.py` — **the rubric**: every weight/threshold. `wow = surprise × trust`; default gate
  `trust ≥ 0.50`; UNLIKELY hop range `[1,3]`; JOURNEY `[3,3]` — a fixed-length 3-hop chain (cap cut
  6→4 ADR 0012, then 4→3 ADR 0021; still `--max-hops`-overridable). No length reward.
- `sdb/graph/build.py` — `KnowledgeGraph`: networkx graph + cached rarity/degree + **co-occurrence**
  (`endpoint_unexpectedness`). `loader.py` — `load_seed`, `load_cooccurrence`.
- `sdb/engine/` — `traversal.py` (`find_paths`: exact `enumerate_paths` under budget, else bounded
  best-first `guided_paths` — ADR 0010), `surprise.py`, `confidence.py` (trust), `narrate.py`
  (template TIL), `pipeline.py` (`discover(..., archetype=...)`).
- `sdb/harvest/` — `client.py` (SPARQL, live + fake), `mapping.py` (rank/ref→Source, P31→Domain,
  temporal extent, PID→Predicate + aliases), `harvester.py` (k-hop BFS→SeedData), `cooccurrence.py`
  (Wikipedia-link matrix; **chunks `pltitles` by 50 — MediaWiki caps it, ADR 0017**), `merge.py`,
  `snapshot.py` (git-ignored `data/harvest/`), `validate.py` (QID guard).
- `sdb/cli.py` — `discover`, `harvest`, `build-cooccurrence`, `validate-qids`, `serve`, `build-site`
  (`--theme`). `sdb/web.py` + `sdb/static/index.html` — zero-dep dual-mode web UI (ADR 0013):
  `discover_payload()` (pure/testable) behind a stdlib `http.server`. `sdb/site.py` — `build_site()`
  pre-renders that page + a `data.json` bundle to `site/` (git-ignored) for free static hosting
  (ADR 0015).
- `.github/workflows/` — `ci.yaml` (offline lint/type/test on every push), `pages.yaml` (build+deploy
  Pages), `qid-validation.yaml` (network QID guard on `data/seed.json` changes + weekly + manual).
- `data/seed.json` (76 nodes / 107 statements, verified QIDs) + `data/cooccurrence.json` (committed).
  `eval/golden.json` — ranker regression (characterization values, not hand-picked).

## 4. Done so far (see the ADRs)

Phase 0 deterministic engine · Phase 1 (0003 endpoint-surprise from co-occurrence, 0004 Wikidata
harvester) · **Phase 2:** 0005 harvest→curated merge, **0006 wow = surprise × trust + evidence gate**,
**0007 two archetypes**, **0008 seed-QID repair** (+ the `validate-qids` guard), **0009 harvest node
enrichment** (P31→Domain incl. SCIENCE/ART; birth/death/dissolution dates), **0010 guided walk for
scale**, **0011 Hellenistic–India–Buddhism bridge**, **0012 default hop cap 6→4**, **0013 web UI**,
**0014 corroboration spike → deferred**, **0015 static-site export**, **0016 Ancient Greece**, **0017
Ancient Egypt** (+ the co-occurrence `pltitles` fix), **0018 Islamic Golden Age**, **0019 Scientific
Revolution**, **0020 East Asia** (Confucius/Confucianism, Tang dynasty, Japan, Zen), **0021 journey
hop cap 4→3** (fixed-length 3-hop journeys — punchier, distinct from the improbable pair), **0022
Norse/Celtic myth** (Odin, Thor, Loki, Norse & Celtic mythology — via Proto-Indo-European + the
Thor↔Rigveda thunder-god cognate), **0023 Chinese tech** (paper, Cai Lun, woodblock printing,
gunpowder, compass — the Four Great Inventions, via Han/Tang/Silk Road/Buddhism). Plus: theme-able
embed (`build-site --theme`), CI for QID-validation + Pages, and the push to a public GitHub repo
with Pages live.

**Key finding (do not re-litigate):** cross-source *corroboration* is low-yield here (ADR 0014). Trust
is already high; the only sub-gate edges are speculative/mythic ones a structured KB can't attest; and
candidate second sources (DBpedia/Wikipedia-text) *derive from* Wikipedia, so noisy-OR would inflate
trust dishonestly. Build only with (1) a source genuinely independent of Wikipedia **and** (2) a
deterministic predicate-alignment table. **Breadth is the higher-leverage investment.**

## 5. What's next (forward-looking)

1. **Breadth — the main ongoing thread.** Add coherent, well-connected clusters, **one commit each**,
   following the process in §6. Done: **East Asia** (ADR 0020), **Norse/Celtic myth** (ADR 0022) and
   **Chinese tech** (ADR 0023: paper/printing/gunpowder/compass — via Han/Tang/Silk Road/Buddhism).
   Next candidate that connects via existing hubs: **West Africa** (Mali, Mansa Musa, Timbuktu,
   trans-Saharan trade — via a new Islam hub). **Avoid Mesoamerica** — pre-Columbian, it would be an
   island. Reusable recipe in memory `sdb-breadth-paused`.
2. **Deploy polish (small, optional).** (a) Add a `<personal-site>/CLAUDE.md` pointer so that repo's
   Claude auto-picks-up the `/six-degrees` embed, and wire its SPA-rewrite to exclude `/six-degrees/*`
   (else the CRA fallback serves the React app instead of the static files — the one real gotcha).
   (b) A custom domain / nav link for the Pages site. (c) **CORS headers on `sdb/web.py`'s `_Handler`**
   — only needed if someone builds a native React UI that calls a *live* `sdb serve` API cross-origin.
3. **Corroboration** — deferred (ADR 0014); only if both prerequisites in §4 are genuinely met.
4. **Documented graduations (adopt only when earned):** Neo4j (scale / NL→Cypher for ~10k+ nodes), an
   optional free/local LLM narrator behind the existing template seam. The guided walk (0010) already
   makes traversal scale; Neo4j is about *storage/query* scale, not needed at 76 nodes.

## 6. Conventions / gotchas

- **Commit only when asked; push only when asked.** Conventional Commits; identity `AnandKri
  <anand.krishna0802@gmail.com>`; end messages with the `Co-Authored-By: Claude …` trailer. `main`,
  now tracking `origin/main` (public).
- **After ANY `data/seed.json` edit:** `sdb validate-qids` → `sdb build-cooccurrence` → run tests →
  re-characterise `eval/golden.json` if a winner shifted (adding edges shifts predicate rarity). This
  pushing to `main` also triggers the `qid-validation` CI job. Regenerate the personal-site embed too.
- **Verify every new QID** — resolve label → Wikipedia article → `wikibase_item` (validate.py does
  this). My from-memory QID guesses are frequently wrong (a fish family, Jean-Claude Killy, a military
  school…); never trust memory for a QID.
- **Keep improbable-pair tests property-based**, not hardcoded-label: Rome's trans-Eurasian top tie
  keeps growing as the seed grows. Assert "short + more unexpected than the obvious Latin neighbour".
- **Tests are offline & deterministic.** Network clients sit behind protocols with fakes; never add a
  network-dependent unit test. (The web round-trip test uses a localhost socket, not external net.)
- **Scores stay hand-reproducible** — a new scoring term needs a rubric worked example + a new ADR.
- **Co-occurrence scales past 50 nodes now** (the `pltitles`-chunking fix, ADR 0017) — earlier it
  silently wrote an empty matrix and disabled the surprise term. If `build-cooccurrence` ever writes
  "0 nodes", suspect a network/API issue and retry (it hits Wikipedia live).
