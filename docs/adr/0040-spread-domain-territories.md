# ADR 0040 — Spread domain territories apart so the map's realms stop overlapping

- **Status:** accepted
- **Phase:** 2

## Context

The map-first UI (ADR 0031) draws each domain as a convex-hull "territory" over its nodes, laid out
by the deterministic force layout (ADR 0030). ADR 0030 set `DOMAIN_COHESION = 1.0` ("a domain pulls
exactly as hard as one edge") after a sweep on the **88-node** seed, and explicitly warned that
cohesion **above ~2 blobs the map at topology's expense**. Since then the seed grew to **107 nodes**
and the most cross-connected domains densified. The result, reported from the live map: the central
cluster — **geography, history, religion, genealogy, trade** — piles up into one mush of overlapping
hulls, because those domains share the most cross-domain edges (Roman Empire, the Silk Road, …) and so
their nodes intermingle.

Measured on the 107-node seed, drawing each domain's hull exactly as the page does:

- **Total pairwise hull overlap = 32.8% of total hull area.** Worst offenders, all in the flagged
  centre: geography↔history **55.8k**, history↔religion **36.0k**, geography↔religion **28.6k**,
  history↔trade 17.8k, genealogy↔religion 17.7k.
- Two contributors, measured separately: **node interleaving** (the layout) and the **58px territory
  stroke** in the CSS, whose round join inflates every hull by ~29px per side — heavy apparent overlap
  on its own, before a single node moves.

This is a **presentation-only** problem: territories are pixels. Per ADR 0030 the layout is chaotic
(perturbing one coordinate by 1 ulp moves the final layout by tens of units), and it never touches a
trust or surprise score. So the fix lives in `sdb/layout.py` (constants, never `sdb/constants.py`)
and the page CSS, and is judged by *measured overlap*, not by a favoured picture.

## Decision

Spread the territories apart with two layout levers plus a CSS trim — no engine change, no score
touched:

1. **A new domain-centroid *separation* force** (`DOMAIN_SEPARATION = 8.0`) — the honest counterpart
   to ADR 0030's centroid *cohesion*. Each iteration, every domain centroid repels every other with
   the node-repulsion law at territory scale (`k²/d`, inverse-distance), and the resulting vector is
   applied to **all** members of the domain as one rigid push. So a territory translates as a whole —
   its internal shape and its cohesion are untouched — and, being inverse-distance, only the cramped
   centre is pried open while already-distant realms barely feel it. Iterates the sorted-domain order
   already fixed for cohesion, so determinism (ADR 0030's whole point) is preserved.
2. **Cohesion raised 1.0 → 2.4.** Separation alone is weak: the final normalisation refits the cloud
   to the frame, so a uniform outward push is largely rescaled away — cohesion is the reliable lever
   (overlap falls monotonically as it rises). ADR 0030's ">2 blobs" was measured for cohesion
   **alone**; with the separation force now sharing the work the operating point moved, and 2.4
   tightens territories *without* collapsing them (evidence below).
3. **Territory stroke 58 → 34, fill-opacity .11 → .12** in `sdb/static/index.html`. Now that the
   layout separates territories structurally, the big soft halo is no longer needed to imply regions,
   and trimming it lets the new separation actually read.

The exact numbers (2.4, 8.0) are one point in a **robustly-good band** — a neighbourhood sweep
(cohesion 2.0–2.5 × separation 6–10) lands overlap in a **15–18%** window throughout, all with
topology preserved. Because the layout is chaotic, no decimal is "optimal"; the region is what's
earned, and the band is wide enough to survive seed growth (revisit, like ADR 0030's sweep, when the
seed jumps again).

## Consequences

- **Overlap roughly halved: 32.8% → 15.6% of hull area.** The worst central pairs drop hard —
  geography↔history 55.8k → 16.6k, history↔religion 36.0k → 5.8k, geography↔religion 28.6k → 20.1k —
  and foreign-node intrusions (a node sitting inside a *different* domain's hull) fall **52 → 23**.
  The centre reads as distinct territories, matching the ask.
- **Bridges are *not* blobbed — the ADR 0030 failure mode is avoided, and measured to be.** The
  blob signature is the mean-edge / mean-all-pairs length ratio *dropping* (edges collapsing inward);
  here it **rose** 0.34 → 0.40, i.e. cross-domain edges are relatively *longer* — bridge nodes still
  sit *between* their realms (Roman Empire, the Silk Road), which is the product. Every per-domain
  cohesion test still passes, and the cohesion ratio improved 0.50 → 0.37.
- **Deterministic and reproducible, unchanged.** All arithmetic stays `+ − × ÷ √` over the sorted
  domain/id order; the layout is byte-identical run to run; cost stays O(N²·iterations) (the
  centroid pass is O(domains²), negligible). No new dependency, no score altered — the page is still
  a pure consumer of `discover()`.
- **One new test** (`tests/test_layout.py`): a separation negative-control — with the force on, fewer
  nodes intrude on a foreign territory's hull than with it off (measured on foreign-node intrusions, a
  chaos-robust proxy for hull overlap, in this suite's property style rather than a pinned coordinate).
  All green (ruff, format, mypy, **147 tests**).
- **Honest limit.** 15.6% is a representative point in a chaotic band, not a guaranteed minimum for
  every future seed; "a reasonable amount of overlap is fine" and some remains by design (the graph is
  63% cross-domain, so touching territories are the truth). If a later cluster re-crowds the centre,
  the fix is another measured sweep here, not a per-cluster nudge.
