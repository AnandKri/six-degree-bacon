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
topic ─▶ graph (networkx) ─▶ traverse ─▶ score surprise ─▶ rank / filter by trust ─▶ template TIL
```

- **Traverse** — enumerate candidate multi-hop paths from the topic node exactly while that's cheap,
  falling back to a bounded best-first **guided walk** only when a search would explode (ADR 0010).
- **Surprise** (information-theoretic, deterministic) — rewards rare edges, cross-domain jumps,
  temporal leaps, and **unexpected destinations** (`−log2 P(endpoint | start)` from real
  Wikipedia-link co-occurrence); penalizes routing through hubs. Length is *not* rewarded.
- **Trust** (deterministic) — per-source reliability rubric → multi-source corroboration (noisy-OR) →
  entity-link quality → validation penalties → weakest-link path trust.
- **Rank** — two **archetypes**, surfaced together (ADR 0007):
  - a **journey** — a fixed-length 3-hop cross-domain chain, ranked by the wow score
    `surprise × trust`;
  - an **improbable pair** — a short 1–2 hop link between entities that feel worlds apart, ranked by
    `endpoint_unexpectedness × trust` (so the *destination's* improbability decides it, not distance).

  Both gate at `trust ≥ 0.50` by default, so tight, well-evidenced connections win — or an honest
  "nothing confident" when none qualify (`--include-possibly` lowers the gate and flags `Possibly:`).
- **Narrate** — a template composes the TIL, citing sources. (A free/local LLM narrator is an
  optional later upgrade behind the same seam; the template stays the deterministic fallback.)

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

[`data/seed.json`](data/seed.json) is a curated **88-node / 123-statement** graph across 9 domains,
each statement fully provenanced. It spans a Roman–Silk Road–China web plus a Hellenistic–India–
Buddhism bridge and clusters for Ancient Greece, Ancient Egypt, the Islamic Golden Age, the
Scientific Revolution, East Asia, Norse/Celtic myth, Chinese technology, West Africa, and royal
divine descent — so it yields connections like Newton → Euclid → al-Tusi → Copernicus, Mansa Musa →
Islam → Zoroastrianism → Mithra, or **Elizabeth II → Alfred the Great → House of Wessex → Odin**.
[`data/cooccurrence.json`](data/cooccurrence.json) holds the committed Wikipedia-link co-occurrence
backing the endpoint-surprise term.

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
  graph/      build a networkx graph + cache derived features (degree, rarity, co-occurrence)
  engine/     traversal · surprise · confidence · narrate · pipeline    (pure, deterministic)
  harvest/    ingestion: Wikidata SPARQL client · rank/ref mapping · k-hop harvester · Wikipedia-link
              co-occurrence · merge-into-curated + corroboration · pinned snapshots · QID validator
  constants.py  the scoring rubric — the single source of truth for every weight and threshold
  web.py / static/  a zero-dependency stdlib web UI (sdb serve); site.py pre-renders it (build-site)
  cli.py      discover · harvest · build-cooccurrence · validate-qids · serve · build-site
data/seed.json          the curated graph (verified QIDs, full provenance)
data/cooccurrence.json  committed Wikipedia-link co-occurrence for the endpoint-surprise term
docs/         ADRs and the confidence rubric (with worked examples the tests reproduce)
eval/         golden expectations (ranker regression / characterization)
tests/        98 tests: human-vs-code confidence, surprise & endpoint checks, harvester, both
              archetypes, the clusters, the web round-trip, and a guided-walk scaling/perf test
```

## Design decisions

See [`docs/adr/`](docs/adr/). In short: local Python + in-memory `networkx` (the traversal we want is
non-standard and easier to control in Python than in Cypher); zero LLM (determinism + reproducibility
+ $0); a statement-reified, Wikidata-aligned data model (so multiple sources can corroborate a fact).
Heavier options — Neo4j for storage/query scale, an optional free/local LLM narrator — are documented
graduations for later, entered only when they earn their keep.

## License

MIT.
