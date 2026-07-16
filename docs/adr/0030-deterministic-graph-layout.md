# ADR 0030 — A deterministic, dependency-free graph layout for the map view

- **Status:** accepted
- **Phase:** 2

## Context

The engine knows 88 nodes and 123 sourced statements across 10 domains, but the UI (ADR 0013/0015)
only ever showed the three hops the ranker chose — the knowledge base itself, built cluster by cluster
across ADRs 0016–0026, was invisible. The map-first UI (ADR 0031) needs 2-D coordinates for every
node, grouped so same-domain nodes read as territories (à la musicmap.info).

Two constraints make this non-trivial and shape every decision:

1. **No numpy.** The project's runtime dependencies are `networkx`, `pydantic`, `rapidfuzz` only, so
   `networkx.spring_layout` (which requires numpy) is unusable. The layout must be pure Python.
2. **The project's whole thesis is reproducibility** — every score is byte-for-byte reproducible by
   hand. A map that jitters between runs, or differs across machines, would betray that. The layout
   must be **deterministic on every platform**, not merely seeded.

Measured facts that drove the design:

- **63% of edges (77/123) are cross-domain.** Unlike musicmap's near-hierarchical genres, this
  graph's bridges *are* the product. With edge attraction alone (cohesion off) the domains do **not**
  cluster — measured intra/inter distance ratio 0.90. So a domain-cohesion force is not a garnish; it
  is the only thing that forms territories, working against a cross-domain majority.
- **The system is chaotic.** Perturbing one initial coordinate by 1 ulp and running the cooled
  iterations moves the final layout by tens of units — cooling does not suppress it. So rounding the
  output is **cosmetic** (payload size, tidy SVG); it cannot be the determinism mechanism. Determinism
  has to come from bit-exact arithmetic. IEEE-754 mandates correct rounding for `+ - * / sqrt` but
  **not** for `sin`/`cos` (libm implementations legitimately differ by an ulp), so a circle
  initialisation would make cross-platform agreement a libm coincidence.

## Decision

Add `sdb/layout.py` — `compute_layout(graph) -> dict[str, tuple[float, float]]` — a pure-Python
Fruchterman-Reingold layout, deterministic by construction:

- **Square-perimeter initialisation, ordered by `(domain, id)`.** Nodes are seeded on the perimeter of
  a centred square (a closed loop, like a circle, but computed with only `+ - * /` — no `sin`/`cos`),
  so each domain starts as a contiguous arc *and* every operation is IEEE-correctly-rounded. A
  golden-ratio radial jitter (`φ⁻¹`, a low-discrepancy sequence — **no PRNG**) breaks symmetric
  equilibria. Rank-ordered init also means adding one node perturbs angles by O(1/N) rather than
  reshuffling the whole map, which matters because the seed grows a cluster per ADR.
- **Forces:** all-pairs repulsion `k²/d`, edge attraction `d²/k` over **unique** undirected pairs
  (parallel statements collapse — layout is topology, corroboration is the trust score's job), a
  **domain-centroid cohesion** `DOMAIN_COHESION · d²/k` toward each domain's mean position (a
  single-node domain's centroid is itself, so its force is exactly zero — no special case), and a weak
  `GRAVITY` toward the origin that keeps disconnected components and isolates in frame. Linear cooling.
- **Determinism guards:** iterate the sorted id order only (never dict/set iteration order, never
  `hash()`), a fixed `LAYOUT_ITERATIONS`, a uniform normalising scale (one scale for both axes, so
  clusters keep shape), and round to `COORDINATE_PRECISION` (adding `0.0` to fold a `-0.0` so the JSON
  is byte-stable). Constants live **in `layout.py`, not `sdb/constants.py`** — that module is "the
  single source of truth for every *scoring* weight and threshold," and these change pixels, never a
  score.

Cohesion strength is the one real tuning call. Swept 0 → 8: at 0 the domains don't cluster (ratio
0.90; `history` and `trade` fail outright); at 1.0 they cluster cleanly (ratio 0.47) while the
cross-domain edges the product is about stay expressed; above ~2 the map degrades into blobs at
topology's expense. `DOMAIN_COHESION = 1.0` — a domain pulls exactly as hard as one sourced link.

## Consequences

- **Territories form, measurably.** On the seed: mean intra-domain distance 202 vs inter-domain 427
  (**ratio 0.473**), minimum node separation 26.6 (no overlaps), every domain of ≥ 3 nodes clusters
  tighter than the global mean. A negative-control test pins the necessity: at `domain_cohesion = 0`
  the clustering property fails.
- **Reproducible and fast.** `compute_layout` is byte-identical run to run (asserted, including its
  JSON serialization); ~1.2 s for the seed's 88 nodes at 320 iterations, run once at `sdb serve`
  startup (cached) and once per `sdb build-site`.
- **Honest limits.** Cross-platform determinism is a proof only on mainstream CPython with IEEE-754
  doubles; and because 63% of edges cross domains, bridge nodes (e.g. Alexander the Great) sit
  *between* regions, so territories overlap — the graph being honest about itself, not a bug. The cost
  is O(N² · iterations): ~11 s projected at 300 nodes, at which point baking coordinates into the
  static bundle (or a Barnes-Hut pass) is the documented graduation — not needed at 88.
- 17 new tests in `tests/test_layout.py` (determinism, input-order independence, bounds, no-collapse,
  the cohesion property per multi-node domain, the negative control, and every edge case:
  empty/single/two-node graphs, single-node domains, isolates, disconnected components, parallel
  edges). Still zero-LLM, deterministic, reproducible by hand; all checks green (120 tests).
