# ADR 0045 — A modern region refinement: the `SOVIET` (Cold War) sphere

- **Status:** accepted
- **Phase:** 3

## Context

The `Region` axis (ADR 0039) was built for the premodern Old World; its granularity is deliberately
**civilisational and coarse** — the whole Greco-Roman-Byzantine-European continuum is one `WESTERN`
sphere — because a finer split let a Western-canon walking tour *farm* "cultural" crossings. The
detached 20th-century brain (ADR 0044) reused that vocabulary as-is, which was correct for a first cut
but flattened one distinction the 20th century is *defined* by: the **Cold War** split between the
Western bloc and the Soviet / Eastern bloc. With every 20th-century node tagged `WESTERN`, a
Sputnik → Apollo hop — the archetypal cross-cultural moment of the century — scored **zero** region
surprise. The handover flagged this as the "modern region refinement", to be done the ADR 0039 way:
only split off a sphere when the split reflects **real cultural distance**, not a farmable crossing.

## Decision

Add exactly one region member, `SOVIET` (the USSR / Eastern bloc), and **keep the US / UK /
Western-European pop continuum as `WESTERN`** — applying ADR 0039's own test to the modern era:

- **`SOVIET` is a genuine fault line, not farming.** The Cold War *is* two opposed worlds; a hop
  between them is a real cultural crossing (Sputnik ↔ Apollo, Tetris ↔ the Western computer industry).
- **US ↔ UK ↔ Western Europe is *not* split.** The transatlantic exchange is one intertwined
  liberal-capitalist tradition — the British Invasion was Britons playing American music — so an
  `AMERICAN → BRITISH` hop would be exactly the ADR 0039 walking-tour trap in modern clothes. It stays
  `WESTERN`. (`LATIN_AMERICAN`, a modern `SUB_SAHARAN` sphere distinct from the medieval `WEST_AFRICAN`
  cluster, etc. are deferred until a brain actually populates them — a region with no nodes is
  untestable.)

The change is a shared-enum addition (`Region.SOVIET`; the enum feeds no layout, so order is free) but
its **scoring effect is per-brain**: the region-jump base rates are learned from each graph's own
statements, and the main brain has no `SOVIET` node, so **the main brain's scoring is untouched**.

To exercise and measure the new sphere, the 20th-century brain grew by **5 nodes / 6 statements**
(seed 27 → 32 / 27 → 33, all QIDs verified): `sputnik` (Q80811), `yuri_gagarin` (Q7327), `tetris`
(Q71910) — all `SOVIET` — plus `apollo_11` (Q43653) and `elvis_presley` (Q303). The Cold War arc
(`yuri_gagarin follows sputnik`, `apollo_11 inspired_by sputnik`, `apollo_11 influenced_by computer`,
`tetris influenced_by computer`) gives the brain **two** Western↔Soviet crossings and plugs into the
existing tech thread; `elvis_presley part_of rock_and_roll` + `the_beatles influenced_by elvis_presley`
deepen the music thread.

## Measurement (per the truth hierarchy — structural, not a pinned winner)

- **The term fires and reads as merit.** Cold War journeys score **higher** than the pre-refinement
  ones (surprise ~30–33 vs ~25) *because* of the new Western↔Soviet jump: `Tetris → computer →
  Apollo 11 → Sputnik` ("America raced to the Moon because the Soviet Sputnik got there first"),
  `Star Wars → computer → Apollo 11 → Sputnik` (a sci-fi franchise reaching the real Soviet space
  programme).
- **No farming.** Within-Western music journeys (`jazz → blues → rock and roll → transistor`) still
  score **0** region jumps — the split only adds surprise where a real culture boundary is crossed.
- **No brain broken.** Existing 20th-century winners held or shifted toward *more* trans-sphere
  destinations (`star_wars` and `computer` now reach the Soviet space arc); the main brain is
  unchanged (its statements never mention `SOVIET`). Guarded by a structural test that a
  Western↔Soviet edge exists (`test_brains.py`).

## Consequences

- `Region` gains `SOVIET`; the 20th-century brain is **32 nodes / 33 statements** with its
  co-occurrence rebuilt. Main brain untouched (116 / 175).
- Per-brain integrity guards (ADR 0044) already cover the new nodes (region + active period + evidence
  + headline). All green: ruff, format, mypy, **170 tests**.
- The modern region vocabulary is now *started*, not finished: the next brain-growth that reaches
  Latin America / decolonising Africa / the Middle East should add its sphere the same way — measured,
  one ADR, only when real cultural distance (not a farmable crossing) justifies it.
