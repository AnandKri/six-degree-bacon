# ADR 0034 — Weight each domain jump by its unexpectedness given the predicate

- **Status:** accepted
- **Phase:** 2

## Context

`surprise` counted domain jumps flat: `W_DOMAIN (2.0) × (number of hops whose endpoints' domains
differ)`. That double-counts predicate semantics. Measured over the seed:

| predicate | edges | jumps | rate |
| --- | --- | --- | --- |
| `located_in` | 34 | 32 | **94%** (27 into `geography`) |
| `connected_via_trade` | 7 | 7 | **100%** |
| `on_trade_route` | 4 | 4 | **100%** |
| `part_of` | 30 | 14 | 47% |
| `influenced_by` | 34 | 20 | 59% |
| `follows` | 5 | 0 | **0%** |

Saying *where* a thing is essentially always crosses into `geography` — so a `located_in` jump
carries no information, yet was paid the same 2.0 as a `follows` jump, which almost never happens
and would be genuinely informative. `located_in` is also the single most common predicate in the
seed, so the term was quietly rewarding any route through a city.

It was **farmable**, and it hijacked a flagship. ADR 0033 added a true edge,
`copernicus part_of renaissance`. Copernicus's top journey became
`→ Renaissance → Florence → House of Medici` — one city, one era, one milieu — which banked **3**
jumps, beating `→ al-Tusi → Euclid → Jagannatha Samrat`, a Polish→Persian→Greek→Indian lineage
spanning 2000 years that banks **0**, because all four are tagged `science`. Both endpoints were
*equally* unexpected (endpoint term 7.01 vs 6.97); the entire gap was fake domain jumps.

At the time the edge was deleted to restore the flagship. **That was the wrong fix** — data is
truth, and the engine was faithfully implementing a rubric that was itself wrong. This ADR fixes the
rubric; the edge is restored.

## Decision

Weight each domain-crossing hop by how *unexpected* that crossing is given its predicate, under a
Laplace-smoothed base rate learned from the graph:

```
P(jump | predicate) = (jumps + α) / (edges + 2α)        α = DOMAIN_JUMP_ALPHA = 0.5
weight              = 1 − P(jump | predicate)
domain_jumps        = Σ over domain-crossing hops of weight(predicate)
```

Learned weights on the current seed: `located_in` **0.071**, `connected_via_trade` 0.062,
`on_trade_route` 0.100, `influenced_by` 0.414, `part_of` 0.516, `claimed_descent_from` 0.688,
`follows` **0.917**.

This mirrors `rarity`, which already derives self-information from predicate counts — the base rate
comes from the data, not a hand-written list of "predicates that don't count" (which would be the
same hardcoding this project exists to avoid, and would rot as the seed grows).

Bounded `[0, 1]`, so **`W_DOMAIN = 2.0` keeps its exact meaning** — a *fully* unexpected jump is
still worth 2.0 — and needed no re-tuning. An unseen predicate smooths to `P = 0.5` (weight 0.5): an
honest "no evidence either way" rather than a free full jump. `guided_paths`'s promise heuristic is
updated to match, so the walk is still guided by the score it will be ranked on.

## Consequences

- **This fix alone did not restore the flagship, and was not adjusted until it did.** With the edge
  restored, Florence still won: surprise 40.20 vs al-Tusi's 39.72 (jumps fell 3.0 → 0.66). The
  remaining margin was a *temporal* artifact, fixed independently in ADR 0035, after which al-Tusi
  returns to #1 (32.75 vs 32.16) — with the true edge in place and nothing deleted.
- The rubric's worked example changes: `domain_jumps` 2 → **0.5**, `surprise` 8.6 → **5.6**
  (`docs/confidence-rubric.md`, reproduced by `tests/test_surprise.py`). Still hand-reproducible:
  count, divide, subtract.
- `eval/golden.json` re-characterised from the engine (predicate-level surprise shifted).
- `SurpriseScore.domain_jumps` is now a `float`.
- **Known limitation, unaddressed here:** the term still cannot see that Polish → Persian → Greek →
  Indian is a vast cultural leap — it scores **0**, because `domain` models *discipline*, not
  culture or geography. The fix is a separate cultural/regional axis on `Node`, which is a data
  change across all 98 nodes; deferred until earned. This ADR only stops the term rewarding
  crossings that convey nothing.
- Deterministic, zero-LLM, hand-reproducible. All green (126 tests).
