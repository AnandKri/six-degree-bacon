# ADR 0036 — Interval separation for temporal distance: measured, and *not* adopted

- **Status:** accepted (the decision is **keep midpoint distance**; ADR 0035's recorded successor is
  closed, not pending)
- **Phase:** 2

## Context

[ADR 0035](0035-close-open-temporal-extents.md) closed the 24 open-ended temporal extents and, in its
*Alternatives rejected*, recorded a successor:

> **Replace midpoint distance with interval separation** (overlapping extents → gap 0). Genuinely
> more principled — `Copernicus (1473-1543)` and the `Renaissance (1300-1600)` overlap, so their true
> temporal distance is 0, not 58 — but it is a *rubric* change needing its own ADR and worked
> example, and it is only worth it once the extents are honest. Recorded as the natural successor;
> this ADR is the prerequisite either way.

The prerequisite is now met, so this ADR was opened to build it. It was measured first. **The
measurement says do not build it**, for a reason that is structural rather than a data problem — so
this ADR closes the successor instead of implementing it.

## The measurement

`temporal_gap` is a **sum of per-hop distances** (`sdb/engine/surprise.py::_temporal_gap`). Swapping
midpoint distance for interval separation *per hop* was applied to the current seed:

| | midpoint (today) | interval separation |
| --- | --- | --- |
| dated node pairs with distance `> 0` | 4263 / 4278 (**99.6%**) | 2163 / 4278 (**50.6%**) |
| top journeys with a nonzero temporal term | 96 | **42** |
| top journeys whose term collapses to exactly `0` | — | **54 of 96 (56%)** |
| mean `temporal_gap` lost | — | **1.67** (`× W_TEMPORAL = 2.5` surprise points) |

### Why: separation does not compose along a chain

The flagship, hop by hop:

```
Roman Empire        (-27, 476)    -> Silk Road            (-130, 1450)   sep = 0
Silk Road           (-130, 1450)  -> Great Wall of China  (-220, 1644)   sep = 0
Great Wall of China (-220, 1644)  -> Qin Shi Huang        (-259, -210)   sep = 0
                                                     SUM of per-hop sep =  0 years
       END-TO-END separation, Roman Empire vs Qin Shi Huang =  183 years
```

**Consecutive entities in a path overlap — that is *why* they are linked.** Things that touch each
other in a knowledge graph generally coexisted. So every per-hop separation is `0`, and a sum of
zeroes is `0`, even though the chain's endpoints are genuinely 183 years apart.

Midpoint distance is a **metric** and accumulates along the chain. Interval separation is a
*closest-approach* measure: it is `0` for any overlapping pair, and overlap is the normal case
between linked nodes. Summing closest-approach along a path is not meaningful — the term stops
measuring "how much time does this chain traverse" and starts measuring "did any two adjacent things
fail to coexist", which is nearly always "no".

ADR 0035's intuition was **right pairwise** and does not survive being summed per-hop. Copernicus
(1473-1543) vs the Renaissance (1300-1600) *should* read as 0. The error is not in that judgement;
it is in assuming a pairwise-correct measure stays correct when composed.

### The motivating defect is already fixed

Interval separation was proposed to kill `Copernicus → Renaissance → Florence → House of Medici`.
ADR 0035 already killed it by closing the extents: `Copernicus → al-Tusi → Euclid → Jagannatha
Samrat` is #1 at wow **32.8**. And that flagship barely moves under separation (temporal 3.80 → 3.58)
because its four figures genuinely *don't* overlap. So adopting it now would fix nothing that is
still broken and zero the term on 56% of journeys.

## Decision

**Keep midpoint distance.** `_temporal_gap` is unchanged; no weight, constant, or rubric figure
moves. ADR 0035's successor is **closed with evidence**, not left pending — so it is not rediscovered
and built later on the assumption that it is a free improvement.

## Alternatives considered

- **End-to-end separation** (start vs endpoint, not summed per hop) — would give the flagship its
  real 183 years and sidesteps the composition problem entirely. **Not adopted:** it silently
  redefines the term from "time this chain traverses" to "how far apart the endpoints are", which is
  a different claim needing its own motivation — and the endpoint axis is already served by
  `endpoint_unexpectedness` (ADR 0003/0007). Recorded as an option, with no evidence yet that it
  beats midpoint.
- **Hybrid** (separation for short extents, midpoint for long) — two formulas selected by a
  hand-tuned span threshold, i.e. exactly the hardcoding ADR 0034 rejected in the domain-jump table.
- **Adopt it anyway on principle.** The north star is a score that tracks *real* surprise, not one
  that is elegant. A term dormant on 56% of results is worse at the job, and "more principled" is not
  a defence when measurement says it measures less.

## Consequences

- No code, data, weight or golden-value change. `eval/golden.json` untouched; **130 tests** unchanged
  and green.
- **The root cause is now named, and it is the `Node` schema, not the formula.** `[start, 2025]`
  answers *"does this still exist?"*; the temporal term wants *"when was this thing's active
  period?"*. Those differ, and both formulas inherit the confusion — midpoint too: after ADR 0035,
  India's midpoint is `(-3300 + 2025) / 2 = -638`, a number describing nothing. The honest fix is a
  **separate active-period/floruit axis** on `Node`, distinct from the existence extent. That is a
  data change across all 98 nodes and is **not** started here.
- This joins ADR 0034's closing limitation (`domain` models *discipline*, so Polish→Persian→Greek→
  Indian scores 0 jumps) as the same shape of problem: **the node schema is thinner than the surprise
  the rubric wants to express.** Two independent terms are now blocked on it, which is what would
  earn that data change — see `docs/HANDOVER.md` §5.
- Zero-LLM, deterministic, hand-reproducible.
