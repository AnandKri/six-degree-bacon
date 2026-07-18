# ADR 0041 — An active-period (floruit) temporal axis on `Node` (giving the temporal term the "when" it actually wants)

- **Status:** accepted
- **Phase:** 2

## Context

`Node` carries a temporal *existence* extent (`start_year`/`end_year`). ADR 0036 named its defect and
closed the interval-separation successor with it: `[start, 2025]` answers *"does this still exist?"*,
not *"when was this thing's active period?"*, and the two differ for anything long-lived. After
ADR 0035 closed the open-ended extents by setting `end_year` to the present for still-living entities,
**30 curated nodes carry `end_year = 2025`**, so their midpoints describe nothing:

| node | existence extent | existence midpoint |
|---|---|---|
| `india` (region) | `[−3300, 2025]` | **−638** (Iron Age — an era India means nothing in) |
| `rome` (the city) | `[−753, 2025]` | **636** (medieval — not its classical peak) |
| `hinduism` | `[−1500, 2025]` | **262** |
| `florence` | `[−59, 2025]` | **983** (a Roman-founded date + the present — not the Renaissance) |
| `great_pyramid_of_giza` | `[−2560, 2025]` | **−268** (Iron Age — not the Old Kingdom that built it) |

`midpoint_year` feeds the `temporal_gap` surprise term (`Σ |midpointₐ − midpoint_b|`) and the `FOLLOWS`
plausibility check, so a hop into a long-lived node books a **fake or muted** temporal leap off a
number that belongs to no era the entity was actually influential in. This is the second (and last) of
the two "schema-blocker" surprise terms the hand-over note tracked; the first — the cultural axis —
closed in [ADR 0039](0039-region-jump-surprise-term.md), which is the exact template for this one.

## Decision

Add a second temporal axis to `Node` — the **active period** (floruit / era of peak historical
influence) — distinct from the existence extent, and point `midpoint_year` at it:

```
active_start / active_end : int | None    # signed years, nullable — the floruit
midpoint_year = active-period midpoint when curated, else existence-extent midpoint
```

Because `_temporal_gap` (`sdb/engine/surprise.py`) and the `FOLLOWS` check
(`sdb/engine/confidence.py`) already read `Node.midpoint_year`, **redefining that one property flows
the fix through both with no engine change** — exactly how ADR 0039's `region` flowed through. No new
weight, constant, or rubric figure: `W_TEMPORAL` and `TEMPORAL_NORM_YEARS` are untouched. This changes
what the *midpoint means*, not how it is weighted (contrast ADR 0039, which added a whole additive
term). The existence extent stays: the `PENALTY_DATE_DISORDER` validator and the map's node-year
metadata still read it.

### The curation rule — peak-influence floruit (owner's steer)

`active_[start, end]` is the sourced era of **formation + peak historical influence**, so a node's
midpoint lands where it actually drove the connections it participates in — not a midpoint stretched to
the present. Applied to all **102 dated** curated nodes:

- **People** (the largest group): floruit ≈ birth/death, so `active = existence` — a quick pass.
- **Long-lived polities / religions / languages / regions / cities / monuments** (the 30 sentinel
  nodes + fallen empires): the sourced classical/peak span — this is where the value is. Examples
  (full eras documented at the curation site): `india [−600, 1200]` (mid **300**), `rome [−753, 476]`
  (mid **−138**), `hinduism [−1500, 500]` (mid **−500**, Vedic → Gupta classical), `china [−1600,
  1912]` (Shang → end of imperial China), `latin [−200, 600]` (classical/late-antique living Latin),
  `florence [1300, 1600]` (mid **1450** — its decisive Renaissance era), `great_pyramid_of_giza
  [−2560, −2130]` (Old Kingdom), `paper [100, 1000]` (invention → spread across Asia & the Islamic
  world).

The **5 genuinely undated** nodes (`aeneas`, `greek_mythology`, `nile`, `algebra`, `amaterasu` — myth,
abstraction, an eternal river) legitimately have neither extent and stay undated; the temporal term
already skips them. A `test_validate.py` guard enforces the invariant *every **dated** curated node
carries an active period* (harvested nodes may lack one and fall back), plus an ordering guard
(`active_start ≤ active_end`) — mirroring the region/evidence completeness guards.

### Measured before shipping (per the truth hierarchy)

Keying `temporal_gap` off the active period vs the existence extent, over every start
(`data/seed.json` + `data/cooccurrence.json`, JOURNEY archetype):

- **11 of 107** journey winners' endpoints shift. The change is targeted — only paths touching a
  long-lived node move, and most flips are near-ties the honest midpoint tips.
- **The shifts are systematically *more* honest** — long-lived nodes now sit in their real era, so the
  winner leans trans-regional/trans-temporal rather than a within-culture neighbour:
  - `florence → renaissance → printing_press → **paper**` (Europe's Renaissance ran on a Chinese
    invention) **replaces** `florence → … → ancient_greece` (a Western walking tour) — because Florence
    now reads its 1450 floruit, not a midpoint dragged to 2025.
  - `china → tang_dynasty → silk_road → **roman_empire**` (a trans-Eurasian route) replaces the
    within-Sinitic `tang_dynasty`.
  - `alexander_the_great → india → rigveda → **thor**` — India's honest classical midpoint lets the
    worlds-apart Indo-European cognate destination win.
- **Every existing flagship holds**: `copernicus → al_tusi → euclid → jagannatha_samrat` (the ADR 0039
  cross-cultural science lineage, still #1), `roman_empire → silk_road → buddhism → zen`,
  `elizabeth_ii → alfred_the_great → house_of_wessex → odin`, `naruhito → jimmu → amaterasu → shinto`,
  and all three `eval/golden.json` cases (Roman Empire → Zen, Christianity → Zhang Qian, Euclid →
  Maurya Empire) are **unchanged**. No cluster hijack.

### Worked example (hand-reproducible)

A hop `Alexander the Great → India`, both `history`:

- `Alexander [−356, −323]` → midpoint **−339.5** (a person: active = existence).
- `India` exists to 2025 (existence midpoint a meaningless **−638**) but its floruit is `[−600, 1200]`
  → active midpoint **300.0**.
- `temporal_gap = |−339.5 − 300.0| / TEMPORAL_NORM_YEARS = 639.5 / 1000 = **0.6395**`; surprise gained
  `= W_TEMPORAL · 0.6395 = 1.5 · 0.6395 = **0.959**`.
- Off the **existence** extent it would have muted to `|−339.5 − (−638)| / 1000 = 0.298` — Alexander's
  Hellenistic era read as *closer* to India than to India's own classical age. The active period books
  the honest gap; count, subtract, divide, still zero-LLM.

## Consequences

- **The second schema-blocker term is CLOSED.** Both terms the hand-over note tracked — `domain` models
  discipline (ADR 0039) and the temporal extent models existence (this ADR) — are now resolved, each by
  a nullable second axis on `Node` + a curation pass, no engine rewrite.
- **Long-lived nodes read their real era everywhere `midpoint_year` is consumed** — the honesty fix
  applies to all 30 sentinel nodes' midpoints, not only the 11 starts whose winner flipped; even where
  the winner is unchanged, its temporal component is no longer computed off a fabricated year.
- **Additive and untaxing.** Undated/uncurated nodes (harvest fallout, the region-less unit fixtures)
  fall back to the existence extent and score exactly as before; the hand-calc golden surprise (5.6) is
  unchanged.
- **No new rubric figure.** `eval/golden.json` cases unchanged; the `_comment` history records the
  re-characterisation. All green (ruff, format, mypy, **152 tests**), incl. a temporal worked example,
  the active-vs-existence midpoint fallback, and the completeness + ordering guards.
- **A follow-on, not built here:** the existence extent and the active period now diverge, so a future
  term could reward a hop that lands *outside* a node's floruit (a genuinely anachronistic connection)
  — recorded as an option, with no evidence yet that it beats the midpoint gap.
