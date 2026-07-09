# ADR 0003 — Endpoint surprise from Wikipedia-link co-occurrence

- **Status:** accepted
- **Phase:** 1

## Context

Phase 0 scored surprise purely from *path-internal* features (edge rarity, domain jumps, temporal
gaps, length). This rewards a wild-looking *route* even when it ends somewhere obvious: for "Roman
Empire" the top result was **Latin** — the language of Rome — reached by a scenic six-hop chain. An
obvious destination should not win no matter how ornate the path to it. We wanted a deterministic,
LLM-free term that rewards *unexpected destinations*, and specifically `−log P(endpoint | start)` (a
known Phase-0 gap, noted in `eval/golden.json`).

The hard part is estimating `P(endpoint | start)`. A purely graph-structural proxy (geodesic
distance, degree, common neighbours) is dependency-free but fails here: the seed deliberately plants
a rich Rome↔Great-Wall subgraph, so structure rates that pairing as *close*, and geodesic distance
over the small graph collapses to the range 1–4 — far too compressed to separate an obvious endpoint
from a surprising one.

## Decision

Estimate `P(endpoint | start)` from **real Wikipedia inter-article links** — genuine human
co-occurrence with wide dynamic range — harvested once and committed to
[`data/cooccurrence.json`](../../data/cooccurrence.json):

- **Signal.** `links[X]` lists the seed nodes whose English Wikipedia article X's article links to
  (namespace-0 links, redirects followed), harvested deterministically by
  `sdb.harvest.cooccurrence` (`sdb build-cooccurrence`). If Rome's article links to Latin, that pair
  is *expected*; the absence of a link to the Rigveda marks it *surprising*.
- **Score.** With symmetric **link strength** ∈ {0, 1, 2} (link directions between the two articles)
  and Laplace smoothing `α = 0.5`:
  `P(endpoint | start) = (strength + α) / Σₑ (strength + α)`, and
  `endpoint_unexpectedness = −log2 P(endpoint | start)`, weighted `W_ENDPOINT = 4.0`. Fully
  reproducible by hand from the committed table (see `docs/confidence-rubric.md`).
- **Graceful default.** With no co-occurrence data the term is `0`, so the engine still runs on
  `data/seed.json` alone and the existing surprise worked example is unchanged.
- **Weight tuning.** `W_ENDPOINT = 4.0` is the smallest weight (tuned against `eval/`) that demotes
  the obvious Latin endpoint below genuinely surprising ones while keeping path-internal surprise
  meaningful and leaving Latin visible in the ranking.

The co-occurrence source sits behind a small client seam (`WikipediaClient`), so a higher-fidelity
signal (e.g. full backlink corpora) can replace it later without touching the scorer.

## Consequences

- "Roman Empire" now tops out at **Chang'an** (the Silk Road's eastern terminus) rather than Latin;
  surprising destinations (Chang'an, Zhang Qian, Rigveda, Great Wall of China) outrank obvious ones.
  `eval/golden.json` is re-characterised accordingly and a regression test locks the demotion.
- `data/cooccurrence.json` is a committed, human-auditable, externally-derived dataset. It is
  regenerated deliberately (and the change recorded in an ADR) whenever the seed graph changes.
- The "reproducible by hand" north star holds: every number is a table lookup plus a `−log2`.
