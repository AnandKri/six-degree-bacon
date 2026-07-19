# Six Degree Bacon

> The "Six Degrees of Kevin Bacon" game, **inverted**: instead of the *shortest* path between two
> things, find the *longest **meaningful*** one — a chain of real, sourced connections that hops
> across domains (myth → religion → trade → history) until it lands somewhere genuinely surprising,
> and present it as a "TIL" card.

**Live demo:** <https://anandkri.github.io/six-degree-bacon/>

A local-first, **zero-LLM**, fully deterministic engine over a curated knowledge graph. Every number
it shows — a **trust** score (is it true?) and a **surprise** score (is it interesting?) — is a
deterministic function of measurable evidence that a human can reproduce by hand from
[`docs/confidence-rubric.md`](docs/confidence-rubric.md). **Correctness never depends on an LLM.**

Two extras beyond the core engine: a **Wikidata SPARQL harvester** (ingest a k-hop neighbourhood into
the same statement model, with deterministic rank/reference→reliability mapping and pinned local
snapshots), and an **endpoint-surprise term** that rewards *unexpected destinations* using real
Wikipedia-link co-occurrence — so Rome tops out at Chang'an, not the obvious "Latin".

## What it does

```
topic ─▶ graph (networkx) ─▶ traverse ─▶ score surprise ─▶ rank / filter by trust ─▶ curated TIL
```

- **Traverse** — enumerate candidate multi-hop paths from the topic node exactly while that's cheap,
  falling back to a bounded best-first **guided walk** only when a search would explode (ADR 0010).
- **Surprise** (information-theoretic, deterministic) — rewards rare edges, cross-**discipline** jumps
  (domain) and cross-**culture** jumps (region — ADR 0039, so a same-field lineage that spans four
  civilisations still scores), **temporal leaps** (measured between nodes' *active periods* / floruits,
  not their bare existence extents — ADR 0041, so a still-living civilisation reads its classical era,
  not a midpoint stretched to the present), and **unexpected destinations** (`−log2 P(endpoint |
  start)` from real Wikipedia-link co-occurrence); penalizes routing through hubs. Length is *not*
  rewarded.
- **Trust** (deterministic) — per-source reliability rubric → multi-source corroboration (noisy-OR) →
  entity-link quality → validation penalties → weakest-link path trust.
- **Rank** — two **archetypes**, surfaced together (ADR 0007), the improbable pair first / default
  (ADR 0042):
  - an **improbable pair** — a short 1–2 hop link between entities that feel worlds apart, ranked by
    `endpoint_unexpectedness × trust` (so the *destination's* improbability decides it, not distance);
  - a **journey** — a fixed-length 3-hop cross-domain chain, ranked by the wow score `surprise × trust`.

  Both gate at `trust ≥ 0.50` by default, so tight, well-evidenced connections win — or an honest
  "nothing confident" when none qualify (`--include-possibly` lowers the gate and flags `Possibly:`).
- **TIL** — each card leads with **one quantized fact**: the curated `headline` of the path's payoff
  (last) hop — a sourced one-liner, one per statement — not a mechanically chained sentence (ADR 0042).
- **Narrate** — a template composes the TIL, and each hop of the chain carries its curated
  one-sentence **evidence**, citing sources (ADR 0037). (A free/local LLM narrator is an optional
  later upgrade behind the same seam; the template stays the deterministic fallback.)

Example — `sdb discover "Japan"` surfaces the journey **Japan → Zen → Buddhism → India → Alexander
the Great** and the improbable pair **Japan ⇢ Silk Road** (2 hops, via the Tang dynasty).

## Quick start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```sh
uv sync --extra dev                      # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"       # two archetypes: a journey + an improbable pair
uv run sdb discover "Silk Road" --top 3 --json
uv run sdb serve                         # interactive zero-dependency web UI at http://127.0.0.1:8000
uv run sdb build-site                    # pre-render a static site/ for free GitHub Pages hosting
uv run sdb validate-qids                 # check every node's wikidata_qid resolves (guard, ADR 0008)
uv run sdb harvest Q2277 --hops 2        # pin a Wikidata neighbourhood -> data/harvest/ (git-ignored)
uv run sdb discover "Roman Empire" --harvest data/harvest/q2277.json   # overlay a harvest, merged
uv run sdb build-cooccurrence            # refresh data/cooccurrence.json from Wikipedia links
uv run pytest                            # run the test suite
```

On Unix / CI you can use the `Makefile` instead: `make install`, `make check`, `make discover`. On
Windows there is no `make`; run the `uv` commands directly (the CLI degrades to ASCII glyphs on a
legacy console).

## The seed graph

[`data/seed.json`](data/seed.json) is a curated **116-node / 175-statement** graph spanning all 10
domains, each statement fully provenanced. It spans a Roman–Silk Road–China web plus a Hellenistic–
India–Buddhism bridge and clusters for Ancient Greece, Ancient Egypt, the Islamic Golden Age, the
Scientific Revolution, East Asia, Norse/Celtic myth, Chinese technology, West Africa, royal divine
descent, the Renaissance, South/Southeast Asia, and the Judaism/Abrahamic web — so it yields
connections like Newton → Euclid →
al-Tusi → Copernicus, Mansa Musa → Islam → Zoroastrianism → Mithra, **Elizabeth II → Alfred the Great
→ House of Wessex → Odin**, **Gutenberg → Printing press → Paper → Silk Road** (Europe's printing
revolution ran on a Chinese invention), or **Sanskrit → Proto-Indo-European → Norse mythology → Loki**
(India's classical language and the Norse pantheon share one prehistoric root).
[`data/cooccurrence.json`](data/cooccurrence.json) holds the committed Wikipedia-link co-occurrence
backing the endpoint-surprise term.

### Multiple brains

A **brain** is a self-contained `(seed, cooccurrence)` pair (ADR 0044). The engine and every CLI
command were already parameterised by both, so serving several graphs the user switches between needs
no engine change — the main graph stays at `data/seed.json`, and extra brains live under
[`data/brains/<name>/`](data/brains/). The first is a **detached 20th-century brain**
([`data/brains/twentieth_century/`](data/brains/twentieth_century/), **100 nodes / 109 statements** —
film, music, politics, technology, architecture, science) whose surprise comes from cross-domain and
cross-culture jumps *within* the century. The region axis grew modern spheres for exactly this —
`SOVIET`, `LATIN_AMERICAN`, `SUB_SAHARAN`, `CARIBBEAN` (ADR 0045/0046) — so it yields
**Mao → Chinese Revolution → Russian Revolution → Cuban Revolution** (a three-region arc),
**Nelson Mandela → Gandhi → MLK → civil rights**, **World Wide Web → the Internet → the computer →
Tetris**, **Fela Kuti → funk → soul → gospel**, or **anime → Osamu Tezuka → Walt Disney → Hollywood**.
`sdb serve` shows a switcher; `sdb build-site` bundles every brain behind one page.

## Deployment

- **GitHub Pages** (free, live) — a workflow builds `sdb build-site` and deploys on every push to
  `main`; the page probes a static `data.json` and needs no server.
- **Live server** — `sdb serve --host 0.0.0.0` reads `$PORT`, so Render / Fly / Cloud Run / a Docker
  Space can run it as-is. The page is dual-mode: it falls back from the static bundle to the live
  `/api/discover` endpoint.

## Repository layout

```
sdb/
  schema/     enums (Domain, Predicate, SourceType, Archetype, …) + Pydantic models (Node, Statement …)
  graph/      build a networkx graph + cache derived features (degree, rarity, co-occurrence); loader
  engine/     traversal · surprise · confidence · narrate · pipeline    (pure, deterministic)
  harvest/    ingestion: Wikidata SPARQL client · rank/ref mapping · k-hop harvester · Wikipedia-link
              co-occurrence · merge-into-curated + corroboration · pinned snapshots · QID validator
  constants.py  the scoring rubric — the single source of truth for every weight and threshold
  brains.py     the brain registry: a "brain" is a (seed, cooccurrence) pair (ADR 0044)
  layout.py     deterministic pure-Python force layout for the map; territories spread apart to
                reduce overlap (ADR 0030, 0040)
  serialize.py  the shared CLI/web result serializer, incl. per-hop sourced evidence (ADR 0037)
  web.py / static/  a zero-dependency stdlib web UI (sdb serve); site.py pre-renders it (build-site).
                Both are multi-brain: serve selects with ?brain=, build-site emits a brain per bundle
  cli.py      discover · harvest · build-cooccurrence · validate-qids · serve · build-site
data/seed.json          the curated main graph (verified QIDs, full provenance)
data/cooccurrence.json  committed Wikipedia-link co-occurrence for the endpoint-surprise term
data/brains/<name>/     additional detached brains (e.g. twentieth_century/) — each its own graph
docs/         ADRs and the confidence rubric (with worked examples the tests reproduce)
eval/         golden expectations (ranker regression / characterization)
tests/        171 tests: the multi-brain platform (registry, a real 2-brain HTTP round-trip, the
              per-brain integrity guards), human-vs-code confidence, surprise & endpoint checks (incl.
              region jumps), harvester, both archetypes, the clusters, the web round-trip, the seed
              loaders, the per-hop evidence contract, and a guided-walk scaling/perf test
```

## Design decisions

See [`docs/adr/`](docs/adr/). In short: local Python + in-memory `networkx` (the traversal we want is
non-standard and easier to control in Python than in Cypher); zero LLM (determinism + reproducibility
+ $0); a statement-reified, Wikidata-aligned data model (so multiple sources can corroborate a fact).
Heavier options — Neo4j for storage/query scale, an optional free/local LLM narrator — are documented
graduations for later, entered only when they earn their keep.

## License

MIT.
