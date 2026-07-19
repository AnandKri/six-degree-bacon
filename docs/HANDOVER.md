# Hand-over — Six Degree Bacon (for the next session)

A working note to continue the project. Pair it with [`CLAUDE.md`](../CLAUDE.md) (the canonical guide)
and the ADRs in [`docs/adr/`](adr/). As of this note: **Phase 2 done, Phase 3 (the multi-brain
platform) kicked off**, **pushed to `origin/main`** (public repo
`github.com/AnandKri/six-degree-bacon`), **CI green**, **GitHub Pages live**, all checks green
(**176 tests**). Main seed: **116 nodes / 175 statements**, 10 curated domains — **all now
populated**: the harvest fallback moved out of `culture` into a dedicated `other` bucket (ADR 0032),
then a Renaissance cluster filled `culture` (0→2) and `art` (1→4) (ADR 0033). `Node` now carries
**both** the axes the surprise rubric was missing: a **`Region`** cultural axis (ADR 0039) and an
**active-period (floruit)** temporal axis (ADR 0041) — so **both schema-blocker terms are now CLOSED**.
Most recent change (ADR 0041): `Node.active_start`/`active_end` carry the era of peak influence, and
`midpoint_year` (hence the `temporal_gap` term) keys off it, falling back to the existence extent — so
India reads its classical `300` not a meaningless `−638`, Rome-the-city its `−138`, Florence its
Renaissance `1450`. Measured: 11/107 journey winners shifted toward more trans-regional destinations
(Florence → Renaissance → printing press → Paper), every flagship intact, no new weight. Before that
(ADR 0040): a presentation-only map-layout tidy — domain territories spread apart (centroid-separation
force + cohesion bump), hull overlap ~33%→~16%, no score touched.

**Newest work (Phase 3 kickoff, ADR 0044): the multi-brain platform + a detached 20th-century brain.**
Phase 2 is **done** (both schema-blocker terms + the narrator closed; a coverage sweep found 104/116
starts return a good improbable pair, the 12 starved all degree ≤ 4 — the plateau). A **probe** first
added 20th-century nodes to the *shared* brain and measured two things: the material is excellent
(`Alan Turing ⇢ al-Khwarizmi`, `Gandhi → Hinduism → Rigveda → Thor`), **but** modern nodes contaminate
the ancient results — being maximally distant from everything ancient, they win as surprise
destinations and displace flagships (`Roman Empire` journey Zen → Joseph Campbell; `Algebra` re-routed
through the new `algorithm` node). That decided **separation**. A "brain" is a `(seed, cooccurrence)`
pair; the engine and every CLI command were **already** parameterised by both, so multi-brain needed
**no engine change** — only `sdb/brains.py` (the registry: main + `data/brains/*`), a `?brain=`
selector on `sdb serve` (`/api/brains`) and the map UI's switcher, and `build_multi_site` (a
`brains.json` manifest + one `data.json`/`data-<name>.json` per brain). First extra brain:
`data/brains/twentieth_century/` (now **102 nodes / 123 statements**, film/music/politics/tech/
architecture/science), journey-led because its one-century span mutes the temporal-gap term, its
surprise carried by cross-domain + cross-region jumps (`Gandhi → MLK → civil rights → jazz`,
`Turing → computer → Star Wars → Hidden Fortress`). Per-brain integrity guards (`test_validate.py`)
now run over **every** brain, so a new brain inherits the whole curation contract for free. Main brain
untouched. **Then (ADR 0045) the first modern region refinement:** `Region` gained `SOVIET` (the Cold
War Eastern bloc — the US/UK/W-European pop continuum stays `WESTERN`, applying ADR 0039's anti-farming
test), exercised by a Cold War space-race arc (Sputnik/Gagarin/Tetris ↔ Apollo 11): the term fires on
merit (`Tetris → computer → Apollo 11 → Sputnik`, `Star Wars → … → Sputnik`; Cold War journeys score
~30–33 vs ~25) with no farming (within-Western music still scores 0 region jumps) and per-brain scoring
leaves the main brain untouched. **Newest (ADR 0046): the 20th-century brain was built out to 100
nodes** (32 → 100 / 33 → 109) across the whole growth backlog — architecture, global cinema, deeper
music/science, Cold War politics — earning three more populated regions (`LATIN_AMERICAN`,
`SUB_SAHARAN` — modern, distinct from the medieval `WEST_AFRICAN` — and `CARIBBEAN`). One connected
component, no islands; new journeys like `Mao → Chinese Revolution → Russian Revolution → Cuban
Revolution` (a `SINITIC → SOVIET → LATIN_AMERICAN` arc) and `Nelson Mandela → Gandhi → MLK → civil
rights`. The `validate-qids` guard caught the ADR 0043 hazard again (label "Constructivism" resolves
to a different QID than the art movement → relabelled "Constructivism (art)").

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

Newest work (ADR 0039): **a cultural-region surprise term — the schema-blocker fix the note below
long called "the highest-value non-breadth work".** `domain` models a node's *discipline*, so a
Polish→Persian→Greek→Indian science lineage (Copernicus → al-Tusi → Euclid → Jagannatha Samrat)
crossed **zero** domains and banked 0 domain-jump surprise despite spanning four civilisations. A new
`Region` macro-cultural axis on `Node` (10 spheres; all 107 nodes curated) + an **additive**
`region_jumps` term (identical `1 − P(jump|predicate)` machinery as ADR 0034, `W_REGION = 2.0`)
scores exactly that. Two decisions, both **measured before building** (per the truth hierarchy):
(1) *additive, not a replacement* — 47% of jump-edges cross a domain but not a region and 6% cross a
region but not a domain, so each axis sees crossings the other can't; (2) *macro granularity* — the
Greco-Roman-European continuum is one `WESTERN` sphere, because a finer split let a Western-canon
walking tour (`Rome → Greece → Renaissance → Plato`) farm three "cultural" crossings while the
trans-Eurasian route banked fewer. Result: the science lineage is restored to Copernicus's #1 **on
merit** (the term reinforces it, no test pins it), Western walking tours leave the top results, and
within-culture origin stories (Naruhito → Amaterasu, Elizabeth II → Odin) correctly score 0 region
jumps. `eval/golden.json` re-characterised from the engine (Roman Empire → Zen, Christianity → Zhang
Qian; Euclid → Maurya unchanged). This **closes one of the two schema-blocker terms** in §"The real
blocker" below; the temporal/floruit axis remains.

Before that (ADR 0038): **a South/SE Asia cluster** — 9 nodes / 17 statements (Hinduism, Sanskrit,
Maurya, Ashoka, Chola, Srivijaya, Khmer, Angkor Wat, Borobudur), seed **98 → 107 nodes / 141 → 158
statements**. Four independent bridges keep it connected: the **Indo-European language** link
(`sanskrit → proto_indo_european`, the best structural addition — **Sanskrit → Proto-Indo-European →
Norse mythology → Loki**, and the ADR 0022 Thor↔Rigveda cognate now reaches SE Asia: **Angkor Wat →
Hinduism → Rigveda → Thor**), the **Hellenistic** link (`maurya_empire follows alexander_the_great` —
**Maurya Empire → Alexander → Alexandria → Euclid**), the **maritime Silk Road** (Chola/Srivijaya/
Borobudur `connected_via_trade`), and **religion** (into the Buddhism/Rigveda hubs). Domains follow
precedent: empires/dynasties and monuments → `history`, Sanskrit → `language`, Hinduism → `religion`.
No flagship hijack (Copernicus→al-Tusi, Gutenberg→paper, Newton intact). Two golden winners
re-characterised from the engine, not tuned: **Euclid**'s terminus improved to the new Maurya Empire,
and **Roman Empire** flipped Qin Shi Huang → Plato by a hair (38.02 vs 37.65, pure global
rarity re-weighting — noted in ADR 0038 as a possible future rubric question about weighting endpoint
unexpectedness, *not* acted on). 4 of 8 from-memory QIDs were wrong again (the ADR 0008 hazard).

Before that (ADR 0037): **the curated `Statement.evidence` prose now ships on every hop.** All 141
statements had a hand-written, sourced one-line justification since ADR 0002, read by *nothing* — the
narrator, CLI, web and static bundle all ignored it, and the shipped TIL chained predicates
mechanically while a better sentence sat unused beside each hop. It went dark on a terminology
collision: ADR 0028 reasoned about "the evidence" meaning the *hop chain* and walked past a field of
that exact name. Now a shared `serialize.hop_dicts` renders the `chain` with per-hop `evidence` on
both surfaces (so it can't reach one and miss the other), guarded by a seed-integrity test that every
curated statement carries it. Bundled refactor in the same change: `load_graph` moved from `web.py`
into `graph/loader.py` (the sole JSON→graph path; also stops a double-parse of the co-occurrence
sidecar), and the archetype dispatch + trust gate moved into `pipeline.discover_all`/`trust_gate`,
shared by the CLI and web. Before that: **all ten curated realms are populated.** ADR 0032 split the
harvest fallback out of `culture` (which was ~100% unmapped fallout and 0% culture) into a dedicated
`other` bucket; ADR 0033 then filled `culture` and `art` with a **Renaissance cluster**, which also
relieved two of the "starved" starts measured in §5 — breadth, not a scoring change, was the fix.
Best TIL: **Gutenberg → Printing press → Paper → Silk Road** (Europe's printing revolution ran on a
Chinese invention). Before that: a **map-first UI** — the whole knowledge base as domain territories, laid out
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
- **Personal site** — the user's personal site simply **redirects** to the GitHub Pages URL above; it
  no longer embeds a themed static bundle. So a pushed seed change is all that's needed for the live
  embed (Pages auto-rebuilds), and there is **nothing to regenerate**. The `build-site --theme`
  embed-override path that fed the old bundle was removed as redundant. See memory
  `sdb-deployment-react`.

Windows note: prefix ad-hoc `python -c` scripts with `PYTHONUTF8=1` or the cp1252 console chokes on
Unicode labels (the `sdb` CLI already degrades to ASCII safely).

## 3. Architecture map

- `sdb/schema/` — `enums.py` (Domain=discipline, **Region**=macro-culture (ADR 0039),
  Predicate→Wikidata props, SourceType, **Archetype**),
  `models.py` (Pydantic; `Node.region`; `Node.active_start`/`active_end` — the floruit axis
  `midpoint_year` prefers over the existence extent, ADR 0041; `Statement.headline` — the one-fact TIL
  line, ADR 0042; `DiscoveryResult` has `archetype`, `score`, `endpoint_unexpectedness`).
- `sdb/constants.py` — **the rubric**: every weight/threshold. `wow = surprise × trust`; default gate
  `trust ≥ 0.50`; UNLIKELY hop range `[1,2]`; JOURNEY `[3,3]` — a fixed-length 3-hop chain (cap cut
  6→4 ADR 0012, then 4→3 ADR 0021; still `--max-hops`-overridable). No length reward.
- `sdb/graph/build.py` — `KnowledgeGraph`: networkx graph + cached rarity/degree + **co-occurrence**
  (`endpoint_unexpectedness`). `loader.py` — `load_seed`, `load_cooccurrence`, `load_similarity`, and
  the JSON→graph helpers `graph_from_seed` / `load_graph` (moved here from `web.py`, ADR 0037; the
  latter is the one loader the CLI and `serve` share).
- `sdb/engine/` — `traversal.py` (`find_paths`: exact `enumerate_paths` under budget, else bounded
  best-first `guided_paths` — ADR 0010), `surprise.py`, `confidence.py` (trust), `narrate.py`
  (TIL = the payoff hop's curated `Statement.headline`, chain as fallback — ADR 0042), `pipeline.py`
  (`discover(..., archetype=...)`, plus `discover_all` + `trust_gate`, the shared dispatch the CLI and
  web both go through — ADR 0037; `ARCHETYPE_CHOICES["both"]` leads with the improbable pair, ADR 0042).
- `sdb/harvest/` — `client.py` (SPARQL, live + fake), `mapping.py` (rank/ref→Source, P31→Domain,
  temporal extent, PID→Predicate + aliases), `harvester.py` (k-hop BFS→SeedData), `cooccurrence.py`
  (Wikipedia-link matrix; **chunks `pltitles` by 50 — MediaWiki caps it, ADR 0017**), `merge.py`,
  `snapshot.py` (git-ignored `data/harvest/`), `validate.py` (QID guard).
- `sdb/serialize.py` — the shared CLI/web result serializer: `result_core` + `source_dicts` +
  `hop_dicts` (the per-hop `chain`, carrying each statement's curated `evidence`, ADR 0037), so a new
  result field can't reach one surface and miss the other.
- `sdb/cli.py` — `discover`, `harvest`, `build-cooccurrence`, `validate-qids`, `serve`, `build-site`.
  `sdb/web.py` + `sdb/static/index.html` — zero-dep dual-mode web UI (ADR 0013):
  `discover_payload()` (pure/testable) behind a stdlib `http.server`. `sdb/site.py` — `build_site()`
  pre-renders that page + a `data.json` bundle to `site/` (git-ignored) for free static hosting
  (ADR 0015).
- `.github/workflows/` — `ci.yaml` (offline lint/type/test on every push), `pages.yaml` (build+deploy
  Pages), `qid-validation.yaml` (network QID guard on `data/seed.json` changes + weekly + manual).
- `data/seed.json` (116 nodes / 175 statements, verified QIDs) + `data/cooccurrence.json` (committed).
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
max tie-fraction 94%→1.1%, every start now fully distinct), **0030/0031 map-first terminal UI**
(deterministic pure-Python layout + the bird's-eye map), **0032 `other` domain / harvest-fallback
split**, **0033 Renaissance cluster** (filled the last two empty realms), **0034 domain-jump
information weighting** (+ **0035 closed temporal extents** — the scoring fix behind the al-Tusi
reversal; see the rule at the top), **0036 interval separation measured & rejected**, **0037 surface
the curated `Statement.evidence` on every hop** (+ the `load_graph`/`discover_all` refactor), **0038
South/SE Asia cluster** (Indo-European/Sanskrit + Hellenistic/Maurya + maritime Silk Road bridges),
**0039 cultural-region surprise term** (the `Node.region` axis + additive `region_jumps`; closes one
of the two schema-blocker terms), **0040 spread domain territories** (map-layout tidy, presentation
only), **0041 active-period (floruit) temporal axis** (the `Node.active_start`/`active_end` axis;
`midpoint_year` prefers it over the existence extent — closes the *second and last* schema-blocker
term), **0042 curated `Statement.headline` as the TIL** (each card leads with one quantized fact — the
payoff hop's headline; the mechanical chain is now the fallback; improbable pair is the default
archetype — resolves the narrator half of the product steer), **0043 Judaism/Abrahamic-web cluster**
(9 nodes / 17 statements — the third Abrahamic religion; Abraham the shared patriarch of Judaism +
Islam, Christianity ← Judaism, Jerusalem under Rome; Christianity's flagship re-characterised Zhang Qian
→ Roman Republic), **0044 multi-brain platform + a detached 20th-century brain** (Phase 3 kickoff — a
brain is a `(seed, cooccurrence)` pair; `sdb/brains.py` registry, `?brain=` on serve, `build_multi_site`
manifest, UI switcher; first extra brain `data/brains/twentieth_century/`), **0045 modern region
refinement** (the `SOVIET` Cold War sphere + a space-race arc in the 20th-century brain), **0046
20th-century brain to 100 nodes** (32 → 100 / 33 → 109 across the whole backlog + three modern regions
`LATIN_AMERICAN`/`SUB_SAHARAN`/`CARIBBEAN`), and two **governing-policy ADRs** (records, no code/data
change): **0047 brain-growth stopping rule** (node count is the wrong axis — grow connective *tissue*
per the starved-start evidence, soft-cap main ~150–200 / auditable-by-hand ceiling ~300, drive by the
two connectivity metrics and stop when they plateau; outgrow → a new brain, not a bigger one) and
**0048 LLM boundary policy** (an LLM may **draft / narrate / route / suggest**, never **score / rank /
gate / attest** — first legitimate use is an offline, human-ratified curation copilot; the engine
stays zero-LLM). Then **0049 20th-century pendant-bridging** — the *first ADR 0047 measurement in
action*: the connectivity sweep found the 20c brain under-tissued (median journey `domain_jumps`
**0.000**, 21% starved), so 7 sourced escape edges between existing nodes (no new QIDs, four of them
art↔history bridges) lifted median `domain_jumps` to **0.469** and cut starved to 16 — brain
**109 → 116 statements**, main brain untouched, co-occurrence not rebuilt (it keys on nodes). Then
**0050 20th-century node pass** — the ADR 0049 node-pass increment: two new nodes (`cuban_missile_crisis`
Q128160, a three-region Cold War hub bridging LATIN_AMERICAN↔WESTERN↔SOVIET and history↔science via
`nuclear_weapon`; `jean_renoir` Q50713, a SOUTH_ASIAN↔WESTERN cinema bridge fixing Satyajit Ray) + 7
statements. **The brain reached main-brain parity** (median domain+region **1.151** vs 1.165, median
`domain_jumps` **0.625** > main's 0.537), so per ADR 0047 the recommendation is **stop growing it**.
Brain **100 → 102 nodes / 116 → 123 statements**; co-occurrence *was* rebuilt (node set changed);
whole brain re-validated (0 QID mismatches); main brain untouched. Then **0051 connectivity sweep as a
committed tool** — the ADR 0047 instrument that drove 0049/0050 lived only in a scratchpad script; it
is now `sdb/sweep.py` + the **`sdb sweep`** CLI diagnostic (defaults to all brains), with the two
metric definitions pinned in the ADR and a property-based invariant test (`test_sweep.py`). Pure
diagnostic — no scoring/data/behaviour change; reproduces the scratchpad numbers byte-for-byte.
Plus: CI for QID-validation
+ Pages, and the push to a public GitHub repo with Pages live.

**Key finding (do not re-litigate):** cross-source *corroboration* is low-yield here (ADR 0014). Trust
is already high; the only sub-gate edges are speculative/mythic ones a structured KB can't attest; and
candidate second sources (DBpedia/Wikipedia-text) *derive from* Wikipedia, so noisy-OR would inflate
trust dishonestly. Build only with (1) a source genuinely independent of Wikipedia **and** (2) a
deterministic predicate-alignment table. **Breadth is the higher-leverage investment.**

## 5. What's next (forward-looking)

### ✅ DONE (ADR 0041) — the temporal active-period (floruit) axis on `Node`

**The last schema-blocker term is now closed.** `Node` gained nullable `active_start`/`active_end` (the
floruit / era of peak influence), and `midpoint_year` — hence the `temporal_gap` surprise term and the
`FOLLOWS` plausibility check — keys off it, falling back to the existence extent. All **102 dated**
curated nodes were curated per the **peak-influence floruit** rule (the owner's steer); the 5 genuinely
undated nodes stay undated; guards enforce "every dated curated node has an active period" +
`active_start ≤ active_end`. No engine change (the property redefinition flowed through both consumers,
exactly like ADR 0039's `region`), no new weight. Measured before shipping: **11/107 journey winners
shifted**, all toward more trans-regional destinations (e.g. `Florence → Renaissance → printing press →
Paper`, replacing a Western walking tour — Florence now reads its 1450 Renaissance floruit, not a
midpoint dragged to 2025); every flagship intact (Copernicus→al-Tusi, Roman Empire→Zen, the
divine-descent lineages) and all three `eval/golden.json` cases unchanged. Interval separation was
**not** rebuilt (ADR 0036 killed it; this task changed what the *midpoint means*, a different lever).

### ✅ DONE (ADR 0042) — the journey narrator decision (the owner's product-steer half)

**Resolved by curated prose, not an LLM.** Each card's TIL is now a **single quantized fact** — the
curated `Statement.headline` of the discovered path's **payoff (last) hop** — replacing the mechanical
predicate chain (which survives only as the harvest fallback). All **158** statements carry a
`headline` (a tight, *evidence-faithful* one-liner, so it inherits the edge's provenance — "zero AI" +
"every link provenanced" stay honest), guarded like `evidence`. The **improbable pair** is now the
first / default archetype. Chosen **per-edge, not per-path** (per-path caching goes stale on every
scoring/seed shift — 11 winners moved in ADR 0041 alone — and would break "zero AI"); the tradeoff is
that a journey's TIL states the *destination fact* rather than the whole arc (the header + hop chain
carry the arc), while the improbable pair — whose fact *is* the endpoint edge — maps to it perfectly.
Narration only: scoring and `eval/golden.json` unchanged. If a true start→end *arc* sentence is ever
wanted, that is the per-path / optional-local-LLM route (recorded, not built).

### ▶ NEXT TASK IN LINE — grow / polish the multi-brain platform (Phase 3)

Phase 2 is done, the multi-brain platform is kicked off (ADR 0044), and the first modern region
refinement (`SOVIET`, ADR 0045) has landed. **This whole thread is now governed by two policy ADRs:**
**[0047](adr/0047-brain-growth-stopping-rule.md)** — don't chase a node count; every addition must be
connective tissue (an escape edge for a starved/low-degree start or a real cross-region bridge), soft
ceilings ~150–200 (main) / auditable-by-hand ~300, and *stop* when the two connectivity metrics (% of
starts with a good gated pair; median region+domain jumps of top journeys) plateau — and
**[0048](adr/0048-llm-boundary-policy.md)** — an LLM may draft/narrate/route/suggest but never
score/rank/gate/attest (first sanctioned use: an offline, human-ratified curation copilot). The open
Phase-3 increments, one commit each:

0. **✅ DONE (ADR 0049 then 0050) — the 20c brain reached main-brain parity; STOP growing it.** The
   full 0047 cycle ran end to end: sweep → ADR 0049 edges-only pass (`domain_jumps` 0.000 → 0.469,
   starved 21 → 16) → ADR 0050 node pass (two new nodes — `cuban_missile_crisis`, a three-region Cold
   War hub; `jean_renoir`, a South-Asian↔Western cinema bridge for Satyajit Ray — + 7 statements) →
   re-sweep. **Result: parity** — median (domain+region) **1.151 vs main 1.165**, median `domain_jumps`
   **0.625 > main 0.537**; good pairs 82.4% vs 86%, starved 15 vs 12. Per ADR 0047 that is the plateau
   signal: **do not keep adding nodes to this brain.** The residual degree-1 nodes are either not
   reach-starved (Berners-Lee via `www→internet→computer`, Gagarin via the space cluster, Jobim via
   `bossa_nova→jazz`) or need a bespoke new cluster for marginal gain (Joseph Campbell, Mies, anime —
   whose neighbours would co-occur and not fix its pair). Forcing a same-region neighbour edge to drop
   the count is the ADR 0034 mistake. **Next lever is NOT more 20c nodes** — see the modern-Middle-East
   region (only when a cluster populates it) and the ADR 0048 curation copilot below.

1. **The 20th-century-brain backlog is now largely BUILT (ADR 0046 — 100 nodes).** The five backlog
   threads — architecture (Art Deco / Bauhaus↔Constructivism / Le Corbusier→Chandigarh / Brutalism /
   the International Style), global cinema (Hollywood hub, Disney→Tezuka→anime, neorealism→Ray,
   Bollywood, the New Wave, Leone←Kurosawa), deeper music (Armstrong/Miles/Gershwin, James Brown→MJ,
   punk/disco, reggae/bossa/salsa/Fela), deeper science (Einstein→relativity/quantum→transistor/bomb,
   von Braun's V-2→Apollo, von Neumann→computer, IC→Silicon-Valley→PC→WWW), and Cold War politics
   (Lenin→Stalin→Khrushchev, Mao's China, the Cuban Revolution, Mandela/Nkrumah←Gandhi) — are all in.
   **Deeper fill is still open** (more artists/films/genres inside each thread; the still-unbuilt
   **Gothic Revival** node — e.g. the Woolworth Building, the only in-era way "Gothic" enters — never
   medieval Gothic here). Same recipe as a main-brain cluster (§6): batch-verify QIDs with
   `LiveTitleResolver`, source `evidence` + `headline`, rebuild **this brain's** co-occurrence
   (`sdb build-cooccurrence --seed data/brains/twentieth_century/seed.json --out
   data/brains/twentieth_century/cooccurrence.json`), re-check its own results, connect every node to a
   hub (no islands). Journey-led: grow *cross-domain* and *cross-region* tissue, not time depth.
2. **Modern `Region`s: `SOVIET`+`LATIN_AMERICAN`+`SUB_SAHARAN`+`CARIBBEAN` are in (ADR 0045/0046).**
   The next real fault line is a **modern Middle East** (distinct from the medieval `NEAR_EASTERN`) —
   add it the ADR 0039/0045/0046 way: **only when a cluster populates it**, only where the crossing is
   real, never pre-adding an empty region. The deliberate non-split stands: the US/UK/W-European pop
   continuum stays `WESTERN` (an `AMERICAN → BRITISH` hop would be the walking-tour trap).
3. **Stay at two brains for now (owner's steer).** A third brain is cheap when wanted (a directory
   under `data/brains/` + its co-occurrence; registry/serve/build-site/guards pick it up
   automatically — Mesoamerica would be a clean island-as-a-feature candidate) — but **parked**; the
   effort goes into the 20th-century brain.

**Main-brain breadth** is still available but lower-value (§5.1; the graph already spans most Old-World
civilisations, the starved count is plateauing). Candidates if wanted: **Byzantine–Ottoman** (via
Constantinople + the Fall of Constantinople); the **Enlightenment** is almost entirely `WESTERN`, so
low cross-cultural surprise (the ADR 0039 walking-tour lesson). Avoid pre-Columbian Mesoamerica (an
island) — **or** make it a *new brain*, where islanding is a feature, not a bug.

---

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
reach genuinely unlinked destinations) without touching a single scoring weight. Reproduce with
**`sdb sweep`** (ADR 0051; `sdb/sweep.py`'s `connectivity_sweep` — for each node it runs
`discover(archetype=UNLIKELY, top=25)` and compares the winner against `load_cooccurrence()` link
sets). Most starts are unaffected (Naruhito ⇢ Amaterasu, Roman Empire ⇢ Paper). If a fix is ever built, it needs an honest "no worlds-apart pair exists here" path for the
starved 11, not a silent empty.

**Watch for cluster hijack (found in ADR 0033; the fix corrected in 0034/0035).** A dense new
sub-cluster can out-compete an existing flagship on domain jumps: `copernicus part_of renaissance` —
one true edge — pushed al-Tusi out of Copernicus's top 4 entirely, replacing ADR 0019's flagship with
a bland `→ Renaissance → Florence → House of Medici` walking tour. **ADR 0033 dropped the edge; that
was the wrong fix and ADR 0034 reversed it** — the edge is true and is now restored. The defect was
the rubric (flat `domain_jumps` paid full price for tautological `located_in → geography` crossings),
and 0034 fixed it there; al-Tusi is #1 again on merit, edge intact. So: after adding any cluster,
re-check the *existing* flagships, not just the new nodes — but when one is hijacked, **fix the
rubric, never the data**. See the rule at the top of this note.

**Interval separation — measured and CLOSED, do not rebuild (ADR 0036).** ADR 0035 recorded
"replace midpoint distance with interval separation" as its natural successor. It was measured before
being built, and the measurement killed it: `temporal_gap` is a **sum of per-hop distances**, and
consecutive entities in a path overlap — *that is why they are linked* — so every per-hop separation
is 0. The flagship sums to **0 years** hop-by-hop (`Roman Empire (-27,476) → Silk Road (-130,1450) →
Great Wall (-220,1644) → Qin Shi Huang (-259,-210)`, each pair overlapping) while its endpoints are
genuinely **183 years** apart. **54 of 96** top journeys (56%) collapse to exactly 0. Midpoint
distance is a metric and accumulates; separation is *closest approach* and does not compose. 0035's
pairwise intuition was right and simply doesn't survive being summed. Its motivating case (the bogus
Florence route) was already fixed by 0035 itself. `end-to-end` separation is recorded in 0036 as an
untested option, not a plan.

**The schema blocker — BOTH of its two terms are now CLOSED (ADR 0039 + ADR 0041).** The `Node`
schema was thinner than the surprise the rubric wanted to express, along two independent axes, each
fixed by a nullable second axis on `Node` + a curation pass (data, not engine):
(1) ✅ **CLOSED (ADR 0039) — `domain` models *discipline*, not culture** (ADR 0034's closing
limitation). Polish→Persian→Greek→Indian scored **0** domain jumps. ADR 0039 added the `Region`
cultural axis + an additive `region_jumps` term (all 107 nodes curated) — the science lineage now
scores its cross-cultural surprise and is Copernicus's #1 on merit. (2) ✅ **CLOSED (ADR 0041) — the
temporal extent modelled *existence* (`[start, 2025]`), not the active period** (ADR 0036), so India's
midpoint was `(-3300+2025)/2 = -638`, a number describing nothing. ADR 0041 added the
`active_start`/`active_end` floruit axis and pointed `midpoint_year` (hence `temporal_gap`) at it,
falling back to the existence extent; India now reads its classical `300`. 11/107 journey winners
shifted toward more honest trans-regional destinations, all flagships intact, no new weight —
re-characterised from the engine, not tuned. **With both terms closed, the schema is no longer the
constraint; the narrator decision (ADR 0042) is likewise closed, so breadth is the top thread (see
§"NEXT TASK IN LINE" above).**

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

**Product direction (owner's steer) — now fully shipped.** A TIL should read as **one quantized
surprising fact** (e.g. "Japan's imperial line traces to the sun goddess", "Elizabeth II descends from
Odin"), not a narrated walking tour, and the **improbable pair** (now the default archetype) has that
shape. **Half shipped in ADR 0037** (the path rendered as curated per-hop *evidence*); **the other half
shipped in ADR 0042** — the TIL itself is now the curated `Statement.headline` of the payoff hop (a
single sourced fact), replacing the mechanical chain (kept only as the harvest fallback). Chosen
per-edge (stable, provenanced, zero-LLM) over per-path synthesis. A natural breadth target that suits
the one-fact TIL is genealogy/derivation chains (royal descent, `claimed_descent_from` /
`derived_from`).

1. **Breadth — the main ongoing thread.** Add coherent, well-connected clusters, **one commit each**,
   following the process in §6. Done this round: **East Asia** (ADR 0020), **Norse/Celtic myth**
   (0022), **Chinese tech** (0023) and **West Africa/Islam** (0024); then the **Renaissance** (0033 —
   which filled the last two empty realms, `culture` and `art`, and relieved `plato`/`constantinople`);
   then **South/Southeast Asia** (0038 — Hinduism/Sanskrit/Maurya/Chola/Srivijaya/Khmer/Angkor,
   adding the Indo-European language bridge and the maritime Silk Road). The graph now spans most major
   Old-World civilisations. Possible future clusters that still connect via existing hubs:
   **Byzantine–Ottoman** (via Constantinople/Byzantine Empire/Fall of Constantinople — now doubly
   hooked), the **Enlightenment** proper (via Newton/Galileo/the printing press), or **Judaism/the
   Abrahamic web** (via the Islam node + Christianity). **Avoid Mesoamerica** — pre-Columbian, it would
   be an island. Reusable recipe in memory `sdb-breadth-paused`.
2. **Deploy polish (small, optional).** (a) A custom domain / nav link for the Pages site.
   (b) **CORS headers on `sdb/web.py`'s `_Handler`** — only needed if someone builds a native React UI
   that calls a *live* `sdb serve` API cross-origin. (The old personal-site static embed is gone — it
   now redirects to Pages — so the SPA-rewrite / `<personal-site>/CLAUDE.md` pointer items are dropped.)
3. **Corroboration** — deferred (ADR 0014); only if both prerequisites in §4 are genuinely met.
4. **Documented graduations (adopt only when earned):** Neo4j (scale / NL→Cypher for ~10k+ nodes), an
   optional free/local LLM narrator behind the existing template seam. The guided walk (0010) already
   makes traversal scale; Neo4j is about *storage/query* scale, not needed at 116 nodes.

## 6. Conventions / gotchas

- **Commit only when asked; push only when asked.** Conventional Commits; identity `AnandKri
  <anand.krishna0802@gmail.com>`; end messages with the `Co-Authored-By: Claude …` trailer. `main`,
  now tracking `origin/main` (public).
- **Update the docs in the same commit as the change — `README.md` included.** The live-truth docs
  are `README.md`, `CLAUDE.md` and this note. If a commit moves a user-visible fact, fix it in all
  three: **seed size** (116 nodes / 175 statements), **test count**, the **rubric's worked-example
  figures**, the module list, the ADR list, domain counts. **Grep the old number** — prose lies, and
  a figure can be quoted in a file you didn't touch. **ADRs are records: never back-edit them.** Mark
  a superseded one with a status line + a pointer to its successor (see ADR 0033's header) and leave
  the body intact — historical figures inside an ADR (0006's `8.6`, 0033's `123 → 140`) were true
  when written and must stay. **README is the one that rots**: it is the public face of a public repo
  and nobody reads it locally, so it sat at 88 nodes / 123 statements / **99 tests** (off by 23)
  while CLAUDE.md was current — because the recipe used to say "CLAUDE.md + HANDOVER" and stopped
  there. A stale doc is a defect in *this* project, not a cosmetic issue: the whole claim is that the
  record is trustworthy.
- **The drift sweep, when in doubt:** `len(seed['nodes'])` / `len(seed['statements'])` / the `pytest`
  count, then grep every `.md` for the old figures. And **verify before flagging a contradiction** —
  two "conflicts" found in review dissolved on measurement (README's "9 domains" vs CLAUDE's "10"
  were populated-vs-declared, both right at the time; "11 starved" vs "12" were post- vs pre-cluster).
- **After ANY `data/seed.json` edit:** `sdb validate-qids` → `sdb build-cooccurrence` → run tests →
  re-characterise `eval/golden.json` if a winner shifted (adding edges shifts predicate rarity).
  Pushing to `main` also triggers the `qid-validation` CI job and the Pages rebuild — no personal-site
  regeneration needed (it redirects to Pages).
- **Every new curated statement needs a one-sentence `evidence` (ADR 0037).** It now renders under
  its hop on every surface, so a blank is a visible hole in the card — `test_validate.py` fails if any
  curated statement omits it. It is a plain sourced sentence justifying that specific claim; don't
  restate the predicate mechanically (that is what the generated TIL already does).
- **`data/harvest/` snapshots go stale silently after a `mapping.py` change — regenerate them.**
  Regenerated 2026-07-17 (`sdb harvest Q2277 --hops 2 --out data/harvest/roman_2hop.json`;
  `Q34266 --hops 1`), so they are currently clean: **0 `"domain": "culture"`, 13 `"other"`**, and a
  `--harvest` merge now yields `culture: 2` (the real curated Renaissance nodes) + `other: 12`
  (fallout), correctly separated. They had been pre-ADR-0032 with **32** nodes tagged `"culture"`.
  Why it matters: `merge.py` adds an unmatched overlay node *with the domain the snapshot recorded*,
  so a stale snapshot re-injects the confusion 0032 removed — worse now than at 0032, since `culture`
  was empty then but ADR 0033 filled it, so fallout would land indistinguishably on real culture
  nodes, and `domain` is a scoring input. They are **git-ignored and local, so CI cannot catch this**;
  it stays invisible until a `--harvest` result looks wrong. Snapshots record no provenance (no QID,
  hops or date), so the regen command is written down here on purpose.
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
