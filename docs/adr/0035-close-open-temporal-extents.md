# ADR 0035 — Close the open-ended temporal extents (a living city is not an ancient node)

- **Status:** accepted
- **Phase:** 2

## Context

`Node.midpoint_year` falls back to `start_year` when `end_year` is `None`. **24 of 98 nodes** had a
start and no end, so a quarter of the graph collapsed to the date it *began*:

| node | modelled extent | midpoint | reality |
| --- | --- | --- | --- |
| Florence | `[-59, None]` | **-59** | founded 59 BC, still there |
| China | `[-1600, None]` | **-1600** | still there |
| India | `[-3300, None]` | **-3300** | still there |
| Rome | `[-753, None]` | **-753** | still there |
| Printing press | `[1440, None]` | 1440 | still in use |

`temporal_gap` sums midpoint distances, so **any hop into one of these booked a fake leap of up to
~3600 years**. Concretely: `Renaissance (1450) → Florence (-59)` scored a 1,509-year jump — to a
city the Renaissance *happened in*. That artifact was the last thing propping up the bogus
`Copernicus → Renaissance → Florence → House of Medici` journey after ADR 0034 (temporal 3.21 of its
surprise), which is how it was found.

The convention to fix it **already existed and was applied to 6 nodes** — all religions
(`christianity`, `buddhism`, `islam`, `shinto`, `zen`, `confucianism` are `[start, 2025]`,
`time_precision: century`). It had simply never been applied to cities, regions, languages or
technologies.

`end_year: None` was doing two incompatible jobs: "still going" (Florence) and "no recorded end"
(Homer, a person). Those need different answers, so neither a blanket "extend to present" nor the
existing "collapse to start" is right.

## Decision

Close all 24 extents explicitly, per node, using the existing convention.

**Still extant → `end_year: 2025`** (21): the cities and regions that still exist (Constantinople/
Istanbul, Chang'an/Xi'an, Rome, Alexandria, Athens, Baghdad, Timbuktu, Florence, Persia/Iran, China,
India, Japan), the monument still standing (Great Pyramid of Giza), the technologies still in use
(paper, woodblock printing, gunpowder, compass, printing press), a language family with living
descendants (Romance languages), Latin (still an official language of Vatican City), and a living
person (Naruhito, b. 1960).

**Genuinely ended → a real date** (3), because `2025` would simply be false:

- `troy` → **500** — Roman-era Ilion was abandoned by ~500 AD.
- `homer` → **-700** — a person with a traditional 8th-c. BC floruit, not an institution.
- `proto_indo_european` → **-2500** — reconstructed; dispersed by ~2500 BC.

This is a **data** correction, not a scoring change: the rubric already said "midpoint of the node's
temporal extent", and the extents were simply unrecorded. No weight moved.

## Alternatives rejected

- **Treat `None` as open-ended `[start, ∞)`.** Breaks people: Homer's interval would swallow every
  later era, making `Homer → Renaissance` a zero-year gap.
- **Treat `None` as "unknown" and skip the hop.** Discards real signal for a quarter of the graph,
  and silently — the failure mode would be invisible.
- **Replace midpoint distance with interval separation** (overlapping extents → gap 0). Genuinely
  more principled — `Copernicus (1473-1543)` and the `Renaissance (1300-1600)` overlap, so their
  true temporal distance is 0, not 58 — but it is a *rubric* change needing its own ADR and worked
  example, and it is only worth it once the extents are honest. Recorded as the natural successor;
  this ADR is the prerequisite either way.

## Consequences

- Florence's midpoint moves -59 → **983**, China's -1600 → **212**, and `Renaissance → Florence`
  stops reading as a 1,509-year leap.
- **Combined with ADR 0034, the flagship returns honestly**: `Copernicus → al-Tusi → Euclid →
  Jagannatha Samrat` is #1 again (32.75 vs 32.16) **with** the true `copernicus part_of renaissance`
  edge restored. It now wins on real temporal distance (3.80) and rarity, not farmed jumps. Neither
  fix was tuned toward that outcome: ADR 0034 alone left Florence ahead, and that was reported
  rather than adjusted around.
- `eval/golden.json` re-characterised from the engine: `Roman Empire → … → Qin Shi Huang` (was
  India) and `Euclid → … → Persia` (was India) — both better TILs, which is corroboration that the
  metric improved rather than merely moved.
- No QID or node-set change, so `validate-qids` and `build-cooccurrence` are unaffected
  (co-occurrence is keyed on the node set).
- Deterministic, zero-LLM, hand-reproducible. All green (126 tests).
