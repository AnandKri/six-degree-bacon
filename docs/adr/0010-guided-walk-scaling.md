# ADR 0010 — Guided walk for scale (exact when tractable, guided when explosive)

- **Status:** accepted
- **Phase:** 2

## Context

Traversal enumerated **every** simple path from the source with a hop count in `[min_hops, max_hops]`
(`enumerate_paths`, ADR 0001). That is exact and, on the 37-node seed, cheap — the worst case over
all topics is ~189 candidate paths in ~1.5 ms. But it is exponential in *degree × depth*: on a
harvested neighbourhood (thousands of nodes, average degree in the tens) a depth-6 enumeration is
millions of paths and does not return. ADR 0001 flagged a guided/seeded walk as the Phase-1+
replacement; this is it.

The hard requirement: **do not change the seed's results.** The golden ranker regression
(`eval/golden.json`), the planted low-trust 6-hop Rome → Great Wall chain, and the archetype tests
all pin exact winners, hop counts and `Possibly:` flags. Scoring must stay reproducible by hand.

## Decision

Keep exhaustive enumeration where it is tractable and switch to a **bounded, guided best-first walk**
only when a search would explode. One entry point, `find_paths`, chooses:

- **`enumerate_paths(..., budget=EXACT_PATH_BUDGET)`** first. It gains an optional `budget` and raises
  `SearchBudgetExceededError` as soon as it would emit more than `budget` paths — a cheap explosion
  detector. `EXACT_PATH_BUDGET = 5000` sits ~26× above the seed's worst case, so **every seed search
  enumerates exhaustively and is byte-identical to before.**
- **`guided_paths(...)`** on overflow. A deterministic priority frontier expands partial walks in
  descending order of a prefix *promise* — an incremental mirror of the surprise score (rare edges +
  domain jumps + `−log₂P(endpoint|start)` of the current node, less a hub penalty), reusing the
  `constants` weights. It emits a candidate whenever a popped prefix is within the hop range and
  stops at `GUIDED_CANDIDATE_BUDGET = 2000` emitted paths or `GUIDED_EXPANSION_BUDGET = 50 000`
  frontier pops, so even a pathological graph terminates. Heap ties break on a monotonic counter, so
  the frontier never compares `Path`s and the walk is fully deterministic.

**Guidance orders discovery; it never scores.** The promise heuristic only decides *which* paths are
found under budget. Every found path is still ranked by the same `surprise × trust` (or
`endpoint_unexpectedness × trust`) in the pipeline — no LLM, reproducible by hand. Because the guided
walk enumerates the *same set* of paths as `enumerate_paths` when its budgets do not bind, it is a
strict generalization: on the seed it would return the identical set, so the fallback can never
silently change a small-graph answer.

## Consequences

- **Seed unchanged.** All 71 tests green; `sdb discover "Roman Empire"` still returns the Mithra
  journey (4 hops); golden + planted-path + archetype expectations hold verbatim.
- **Large graphs bounded.** On a synthetic dense graph (1500 nodes, ~30 k edges) exhaustive `[3,6]`
  overflows the budget, while `find_paths` returns 2000 candidates in ~67 ms, deterministically. A
  scale/perf test (`test_guided_walk_bounds_an_explosive_search`) locks this: exact enumeration
  raises `SearchBudgetExceededError`, the guided fallback stays ≤ budget, valid (simple paths in
  range), and order-stable — a guarantee that does not depend on wall-clock timing.
- **Verified equivalence.** `guided_paths` with non-binding budgets emits the same path *set* as
  `enumerate_paths` across five seed topics × both hop ranges (`test_guided_walk_equals_exhaustive…`).
- Still open (documented graduations): neighbourhood pre-pruning and Neo4j/NL→Cypher for ~10 k+ nodes;
  a higher-fidelity promise heuristic if guided-only recall needs tuning on real harvests.
