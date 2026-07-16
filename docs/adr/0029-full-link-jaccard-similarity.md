# ADR 0029 — Measure shared context over full article links (Jaccard), not the seed keyhole

- **Status:** accepted
- **Phase:** 2

## Context

ADR 0025 added a second-order term to the endpoint surprise: two nodes that co-occur with the *same*
other articles share context, so their pairing is less surprising. But it measured that overlap
**inside the seed** — the shared-neighbour count ran over the 88 seed nodes only. That keyhole starves
peripheral nodes. An independent review (Finding 2 of `docs/review-findings.md`) showed the term had
merely *narrowed* the saturation ADR 0025 set out to fix, not removed it; quantified across the whole
seed it was worse than the sample suggested:

| Node | co-occurrence degree | % of graph tied at max unexpectedness |
|---|---|---|
| `house_of_wessex` | 1 | **94.3%** |
| `mansa_musa` | 2 | 83.9% |
| `elizabeth_ii` | 3 | 77.0% |
| … | | median **23%** |

Five of the six worst offenders were nodes added in the immediately-preceding divine-descent cluster
(ADR 0026) — exactly the review's warning that "each new cluster starts life sparse, so this gets
worse with breadth." The root cause is **data**, not the formula: a node whose article links only one
*seed* node also shares almost nothing *within the seed*, so the seed-scoped signal is near-zero for
it — even though its real Wikipedia article links hundreds of pages and genuinely overlaps others.

## Decision

Measure shared context over each article's **full** outbound link set, not the seed keyhole. Add
`WikipediaClient.all_outbound_links(title)` (paginated, unfiltered) behind the existing client seam,
and in `build_cooccurrence` compute the pairwise **Jaccard** overlap of the full link sets:

```
jaccard(a, b) = |A_links ∩ B_links| / |A_links ∪ B_links|
effective_strength(a, b) = strength(a, b) + COOCCURRENCE_SIMILARITY_WEIGHT · jaccard(a, b)
```

The raw link sets are *not* shipped — only the ~3.8k non-zero pairwise Jaccard values, committed as a
`similarity` block in `data/cooccurrence.json` (the file grows to ~139 KB). Jaccard is bounded `[0, 1]`
(unlike the old unbounded count), so `COOCCURRENCE_SIMILARITY_WEIGHT = 2.0` makes a totally-overlapping
article worth ~one mutual link while typical real overlaps (0.005–0.30) contribute a fraction of a link
direction. Everything stays deterministic, offline after the harvest, and hand-reproducible (Jaccard of
two committed sets); the graph falls back to direct strength only when no `similarity` table is present.

## Consequences

- **Saturation is gone, not narrowed.** Max tie-fraction across the seed drops **94.3% → 1.15%**, and
  **every start now has a fully distinct ordering** (only the single maximum "ties"). `house_of_wessex`
  goes from 3 distinct unexpectedness values to 87. A canary test (`test_endpoint_term_does_not_saturate`)
  bounds the tie fraction so a future sparse cluster can't silently reintroduce this.
- **Golden re-characterised:** Roman Empire → **India** (via Silk Road → Buddhism) and Christianity →
  **Paper**; Euclid → India unchanged. (The 0025 winners Qin Shi Huang / Great Wall were themselves
  artefacts of the coarser keyhole signal.)
- **Data format extended, not broken:** `data/cooccurrence.json` gains a `similarity` key beside
  `links`; `load_similarity` reads it and an older file simply disables the term. `build.py`,
  `loader.py`, `cli.py`, `web.py`, and the test fixture were threaded through; the ADR 0025
  worked example / test are replaced by the Jaccard equivalents (`0.49/2.81` direct-strength example
  unchanged, new `1.00/1.58/2.58` de-saturation example).
- **Known follow-up (separate from saturation):** with the pair capped at 1–2 hops (ADR 0027), a few
  *sparse* starts (e.g. Confucius, degree 2) can still surface a directly co-occurring 1-hop neighbour
  as their top improbable pair, because a high-trust 1-hop beats a more-unexpected lower-trust 2-hop on
  `eu × trust`. That is a hop/trust interaction, not saturation, and wants its own decision (e.g. exclude
  destinations the start directly links, or floor the pair's unexpectedness). Recorded, not fixed here.
- All checks green (99 tests). Still zero-LLM, deterministic, hand-reproducible.
