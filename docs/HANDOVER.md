# Hand-over — Six Degree Bacon (for the next session)

A working note to continue the project. Pair it with [`CLAUDE.md`](../CLAUDE.md) (the canonical guide)
and the ADRs in [`docs/adr/`](adr/). As of this note: **Phase 2**, **pushed to `origin/main`**
(public repo `github.com/AnandKri/six-degree-bacon`), **CI green**, **GitHub Pages live**, all checks
green (**126 tests**). Seed: **98 nodes / 140 statements**, 10 curated domains — **all now
populated**: the harvest fallback moved out of `culture` into a dedicated `other` bucket (ADR 0032),
then a Renaissance cluster filled `culture` (0→2) and `art` (1→4) (ADR 0033).

**Read this first — the rule the project nearly broke (ADR 0034/0035).** Data and the rubric are the
truth; **a test may only verify what the rubric claims, never that a favourite wins**. This was
violated in the same session it was written: ADR 0033 added a *true* edge, a test asserting
`"Nasir al-Din al-Tusi" in copernicus[0]` failed, and the edge was **deleted to make it pass**. The
real defect was in the rubric — `domain_jumps` paid full price for tautological crossings
(`located_in` lands in `geography` on 94% of its edges), so a chain through one city in one era
(`Renaissance → Florence → House of Medici`) out-scored a Polish→Persian→Greek→Indian lineage that
scores **0** because all four are tagged `science`. Fixed properly in 0034/0035; the edge is
restored and al-Tusi is #1 again *on merit*. When a result looks wrong, ask: **did the engine
violate the rubric (a bug), or does the rubric mis-specify surprise (a design flaw)?** Fix the
rubric via ADR + worked example. Never the data — data changes only when a *fact* is wrong.
`eval/golden.json` is a change-*detector*, not a correctness oracle; re-characterising it would have
enshrined the bug.

Newest work: **all ten curated realms are populated.** ADR 0032 split the harvest fallback out of
`culture` (which was ~100% unmapped fallout and 0% culture) into a dedicated `other` bucket; ADR 0033
then filled `culture` and `art` with a **Renaissance cluster**, which also relieved two of the
"starved" starts measured in §5 — breadth, not a scoring change, was the fix. Best new TIL:
**Gutenberg → Printing press → Paper → Silk Road** (Europe's printing revolution ran on a Chinese
invention). Before that: a **map-first UI** — the whole knowledge base as domain territories, laid out
by a deterministic pure-Python force layout (`sdb/layout.py`, ADR 0030) and themed "minimal terminal"
(dark slate + single teal accent, ADR 0031). Click a node → its discovered route lights up in place.
The engine is untouched; the map is a pure consumer of `discover()` via a new `graph_payload()` /
`/api/graph` (baked into the static bundle's `graph` key).

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
  `trust ≥ 0.50`; UNLIKELY hop range `[1,2]`; JOURNEY `[3,3]` — a fixed-length 3-hop chain (cap cut
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
- `data/seed.json` (98 nodes / 140 statements, verified QIDs) + `data/cooccurrence.json` (committed).
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
gunpowder, compass — the Four Great Inventions, via Han/Tang/Silk Road/Buddhism), **0024
West-Africa/Islam** (Mali, Mansa Musa, Timbuktu, trans-Saharan trade + a new Islam hub — via Islam →
Zoroastrianism/Persia and the Abbasid caliphate), **0025 second-order co-occurrence** (a graded
shared-neighbour term de-saturates the endpoint surprise so the improbable pair surfaces genuinely
worlds-apart destinations — e.g. Mansa Musa ⇢ Zoroastrianism), **0026 divine descent** (Elizabeth II
→ Alfred → House of Wessex → Odin; Naruhito → Jimmu → Amaterasu → Shinto — the lineage TILs), **0027
disjoint archetype hop ranges** (pair cap 3→2 so journey `[3,3]` and pair `[1,2]` can never return the
same path — they collided on Roman Empire/Christianity), **0028 single-claim TIL** (the narrator now
emits one sentence stating the connection; the hop chain is the *evidence* the callers already render,
not prose to restate), **0029 full-link Jaccard similarity** (measure shared context over each
article's *whole* outbound link set, not the seed keyhole — kills the peripheral-node saturation:
max tie-fraction 94%→1.1%, every start now fully distinct). Plus: theme-able embed (`build-site
--theme`), CI for QID-validation + Pages, and the push to a public GitHub repo with Pages live.

**Key finding (do not re-litigate):** cross-source *corroboration* is low-yield here (ADR 0014). Trust
is already high; the only sub-gate edges are speculative/mythic ones a structured KB can't attest; and
candidate second sources (DBpedia/Wikipedia-text) *derive from* Wikipedia, so noisy-OR would inflate
trust dishonestly. Build only with (1) a source genuinely independent of Wikipedia **and** (2) a
deterministic predicate-alignment table. **Breadth is the higher-leverage investment.**

## 5. What's next (forward-looking)

**Endpoint saturation — fixed (ADR 0025 → 0029).** 0025's second-order term only *narrowed* the
saturation; the review (Finding 2) showed the periphery still tied (`house_of_wessex` tied 94% of the
graph), because 0025 measured shared context inside the seed keyhole. **0029 measures Jaccard overlap
of each article's full outbound link set instead** (committed as a `similarity` block; `γ =
COOCCURRENCE_SIMILARITY_WEIGHT = 2.0`). Result: max tie-fraction 94%→1.1%, **every start now fully
distinct**, and `test_endpoint_term_does_not_saturate` is a canary that bounds the tie fraction so a
future sparse cluster can't silently reintroduce it. Re-run `sdb build-cooccurrence` after any seed
change (it now also fetches each article's full link set — slower, ~a minute for the seed).

**Open follow-up (a *different* issue, not saturation) — MEASURED, and the obvious fix is wrong.**
With the pair capped at 1–2 hops (ADR 0027), some starts surface a directly co-occurring neighbour as
their *top* improbable pair (Confucius ⇢ China), because a high-trust 1-hop beats a more-unexpected
lower-trust 2-hop on `eu × trust`. An earlier draft of this note proposed: *exclude destinations the
start directly links (link_strength ≥ 1) from the pair set, or floor the pair's endpoint-unexpectedness*.
**Do not build that without reading this.** Measured across every start (2026-07-17; re-measured
after ADR 0033 — the shape held, the count improved **16/88 → 15/98**):

- **15 starts** surface a directly-co-occurring winner.
- Only **4** have a non-obvious alternative that merely loses on score (`confucius` → Chang'an 4.80 vs
  China 4.98; also `cleopatra`, `ptolemy`, `great_pyramid_of_giza`). These are the only ones the
  exclusion would fix — and it swaps for a barely-better endpoint.
- The other **11 are starved**: *every* candidate within 1–2 hops directly co-occurs (`julius_caesar`
  → Augustus, `troy` → Trojan War, `romance_languages` → Latin, `nile`, `jimmu`, `mali_empire`,
  `china`, `aeneas`, `trojan_war`, `augustus`, `mona_lisa`). Excluding direct links there returns
  **nothing at all** — trading a mediocre TIL for an empty result on 11 of 98 starts.

Root cause is **not scoring**: every starved start has graph-degree 1–4, so its 2-hop reach is its own
cluster and no distant destination exists to rank. `troy` (degree 1) can only reach Trojan War's
neighbours. The fix is **breadth — specifically edges that *escape* a cluster**, not nodes beside it
(e.g. `troy → Heinrich Schliemann → 19th-c. archaeology` jumps domain and two millennia in one hop).
This independently re-confirms ADR 0014's "breadth is the higher-leverage investment", and **ADR 0033
demonstrated it**: adding the Renaissance cluster relieved `plato` and `constantinople` (both now
reach genuinely unlinked destinations) without touching a single scoring weight. Reproduce with the
sweep: for each node, `discover(archetype=UNLIKELY, top=25)` and compare the winner against
`load_cooccurrence()` link sets. Most starts are unaffected (Naruhito ⇢ Amaterasu, Roman Empire ⇢
Paper). If a fix is ever built, it needs an honest "no worlds-apart pair exists here" path for the
starved 11, not a silent empty.

**Watch for cluster hijack (found in ADR 0033).** A dense new sub-cluster can out-compete an existing
flagship on domain jumps: `copernicus part_of renaissance` — one true edge — pushed al-Tusi out of
Copernicus's top 4 entirely, replacing ADR 0019's flagship with a bland `→ Renaissance → Florence →
House of Medici` walking tour. The edge was dropped. After adding any cluster, re-check the *existing*
flagships, not just the new nodes.

**A further rung if the endpoint term ever needs one: deterministic diffusion, not a GA.** Saturation
is already solved (0029), so this is no longer motivated by it — but **personalized PageRank /
random-walk-with-restart** over the co-occurrence graph remains the principled "all-order" successor
to the current first+second-order strength, and would also give a better "obviousness" measure than
the raw-degree hub penalty. Deterministic (fixed damping + power iteration) and rubric-specifiable;
adopt only if a concrete need appears. **Genetic algorithms
were considered and rejected:** at runtime they trade a hand-verifiable exact result for a
non-reproducible heuristic (killing the north star) with no benefit at this scale; offline weight
tuning is legitimate in principle but is blocked by the absence of a human-labelled "wow" set, and
for ~8 continuous knobs a plain grid/random sweep would beat a GA anyway. Stochastic epidemic
simulation (SIR) is likewise out for scoring (nondeterministic) — fine only as a visualisation.

**Product direction (owner's steer):** a TIL should read as **one quantized surprising fact**
(e.g. "Japan's imperial line traces to the sun goddess", "Elizabeth II descends from Odin"), not a
narrated walking tour. The **improbable pair** already has that shape and is the archetype to lean
into. Likely evolution: narrate the (start → endpoint) claim as a single sentence with the connecting
path demoted to collapsible *evidence*; then the **journey** either becomes "a surprising
lineage/origin stated as one fact" or is dropped. A natural breadth target for that flavour is
genealogy/derivation chains (royal descent, `claimed_descent_from` / `derived_from`).

1. **Breadth — the main ongoing thread.** Add coherent, well-connected clusters, **one commit each**,
   following the process in §6. Done this round: **East Asia** (ADR 0020), **Norse/Celtic myth**
   (0022), **Chinese tech** (0023) and **West Africa/Islam** (0024); then the **Renaissance** (0033 —
   which filled the last two empty realms, `culture` and `art`, and relieved `plato`/`constantinople`).
   The graph now spans most major Old-World civilisations. Possible future clusters that still connect
   via existing hubs: **Byzantine–Ottoman** (via Constantinople/Byzantine Empire/Fall of
   Constantinople — now doubly hooked), the **Enlightenment** proper (via Newton/Galileo/the printing
   press), **South/Southeast Asia** (via Buddhism/India), or **Judaism/the Abrahamic web** (via the
   Islam node + Christianity). **Avoid Mesoamerica** — pre-Columbian, it would be an island.
   Reusable recipe in memory `sdb-breadth-paused`.
2. **Deploy polish (small, optional).** (a) Add a `<personal-site>/CLAUDE.md` pointer so that repo's
   Claude auto-picks-up the `/six-degrees` embed, and wire its SPA-rewrite to exclude `/six-degrees/*`
   (else the CRA fallback serves the React app instead of the static files — the one real gotcha).
   (b) A custom domain / nav link for the Pages site. (c) **CORS headers on `sdb/web.py`'s `_Handler`**
   — only needed if someone builds a native React UI that calls a *live* `sdb serve` API cross-origin.
3. **Corroboration** — deferred (ADR 0014); only if both prerequisites in §4 are genuinely met.
4. **Documented graduations (adopt only when earned):** Neo4j (scale / NL→Cypher for ~10k+ nodes), an
   optional free/local LLM narrator behind the existing template seam. The guided walk (0010) already
   makes traversal scale; Neo4j is about *storage/query* scale, not needed at 81 nodes.

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
