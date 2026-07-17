# ADR 0039 — A cultural-region surprise term (giving `Node` the axis `domain` could not express)

- **Status:** accepted
- **Phase:** 2

## Context

`Domain` models a node's **discipline** (science, history, religion…). ADR 0034's closing limitation,
restated by the hand-over note as "the real blocker", is that discipline is not culture: a
Polish → Persian → Greek → Indian science lineage — **Copernicus → Nasir al-Din al-Tusi → Euclid →
Jagannatha Samrat** — crosses **zero** domains (all four are `science`) and so banks **0** domain-jump
surprise, even though it spans four civilisations across two millennia. The surprise the rubric wants
to express is thinner than the `Node` schema can carry. The fix named across the docs is *a new axis
on `Node`* — a cultural/regional one — and it is data, not just code.

## Decision

Add a `Region` cultural-sphere axis to `Node` and an **additive** region-jump surprise term that
mirrors ADR 0034's domain-jump machinery exactly, on the new axis:

```
surprise += W_REGION · Σ_hops  region_jump_weight(predicate)      # summed over culture-crossing hops
region_jump_weight(pred) = 1 − P(region_jump | pred)
P(region_jump | pred)    = (region_jumps + α) / (regioned_edges + 2α)   # α = REGION_JUMP_ALPHA = 0.5
```

Only edges whose **both** endpoints carry a region feed the base rate or score (mirroring how the
temporal term skips undated nodes), so an unregioned harvest node never fabricates or suppresses a
jump. `W_REGION = 2.0`, on par with `W_DOMAIN` — cultural surprise is valued equally to disciplinary
surprise.

### Two decisions, each measured before building (per the truth hierarchy)

**1. Additive, not a replacement for `domain`.** Measured over the seed's 158 edges, classifying each
as a domain jump and/or a region jump:

| | count | share |
|---|---|---|
| crosses **both** axes | 28 | 19% |
| **domain only** (within-culture discipline change) | 71 | 47% |
| **region only** (same-discipline culture change) | 9 | 6% |
| neither | 43 | 28% |

47% of jump-edges cross a domain but **not** a region, and 6% cross a region but **not** a domain, so
each axis carries surprise the other is blind to — replacing `domain` with `region` would discard the
47%. The two are near-orthogonal *per predicate*, too: `located_in` is a domain tautology
(domain-weight 0.06 — a thing is nearly always located in `geography`) yet region-informative
(region-weight 0.89 — a thing is usually located in its *own* culture's place); `part_of` is
region-weight 0.93; `connected_via_trade` crosses both (domain 0.05, region 0.23). A hop that crosses
both is genuinely doubly surprising and is credited on both; `W_REGION` sets the magnitude.

**2. Macro-cultural granularity — the Greco-Roman-European continuum is one `WESTERN` sphere.** A
first pass split it into Hellenic / Italic / European / Byzantine. Measured, that let a Western-canon
walking tour farm "cultural" crossings: `Roman Empire → Ancient Greece → Renaissance humanism →
Plato` banked **three** region jumps (Italic→Hellenic→European→Hellenic) while the genuinely
trans-Eurasian `Roman Empire → Silk Road → Great Wall → Qin Shi Huang` banked fewer. That is the
opposite of honest — the Renaissance *revived* antiquity, so Rome → Greece stays inside one ancestral
tradition rather than entering a foreign culture. Collapsing the continuum to a single `WESTERN`
sphere makes that walking tour score **0** region jumps while the science lineage still scores 3
(it leaves and re-enters the West via Persia). The ten spheres: `WESTERN`, `NORSE_GERMANIC`,
`NEAR_EASTERN`, `EGYPTIAN`, `SOUTH_ASIAN`, `SOUTHEAST_ASIAN`, `SINITIC`, `JAPANESE`, `WEST_AFRICAN`,
`CENTRAL_ASIAN`. A node takes the culture it is *rooted in* (a religion's birthplace, a person's
home), not everywhere it spread; a trans-cultural route takes its heartland (the Silk Road is
`CENTRAL_ASIAN`). All 107 curated nodes carry one, guarded by a test.

### Worked example (hand-reproducible — the whole motivating case)

`Copernicus → al-Tusi → Euclid → Jagannatha Samrat`, three `influenced_by` hops, all `science`
(WESTERN → NEAR_EASTERN → WESTERN → SOUTH_ASIAN):

- Count the seed: `influenced_by` has **39** edges with both endpoints regioned, **15** of which
  cross a region. So `P(region_jump | influenced_by) = (15 + 0.5) / (39 + 2·0.5) = 15.5 / 40 =
  0.3875`, and `region_jump_weight = 1 − 0.3875 = **0.6125**`.
- All three hops cross a region: `region_jumps = 3 × 0.6125 = **1.838**`; `domain_jumps = 0` (all
  `science`).
- Surprise gained: `W_REGION · 1.838 = 2.0 · 1.838 = **3.68**`, which under ADR 0034 alone was
  **0.00**. The lineage the schema could not see is now scored.

## Consequences

- **The cross-cultural science lineage is restored to Copernicus's #1** on merit —
  `Copernicus → al-Tusi → Euclid → Jagannatha Samrat` now clearly leads the Renaissance walking tour
  it previously edged, and the term *reinforces* it rather than a test pinning it (the ADR 0033/0034
  hazard is not repeated).
- **Western-canon walking tours leave the top results.** `Roman Empire`'s top journeys are now all
  genuinely trans-Eurasian (`… → Silk Road → Buddhism → Zen`, `… → Great Wall → Qin Shi Huang`,
  `… → Buddhism → Borobudur`); the `→ Ancient Greece → Renaissance humanism → Plato` route that
  briefly won in ADR 0038 is gone. This is the "possible future rubric question" ADR 0038 recorded —
  now answered by an honest cultural model, not by tuning.
- **Within-culture origin stories are untouched** — `Naruhito → Jimmu → Amaterasu → Shinto` and
  `Elizabeth II → Alfred → House of Wessex → Odin` score **0** region jumps (each stays inside one
  culture); their surprise remains mythic/temporal, exactly as it should.
- **`eval/golden.json` re-characterised from the engine** (never hand-picked): Roman Empire → Zen,
  Christianity → Zhang Qian (Christianity is `near_eastern`, so its spread into the Roman world now
  scores); Euclid → Maurya Empire unchanged.
- **Additive, so nothing is taxed:** an unregioned graph (or the region-less unit fixtures) scores
  exactly as before — the hand-calc golden surprise (5.6) is unchanged. Deterministic, zero-LLM,
  hand-reproducible: count, divide, subtract.
- **Two limitations named by the hand-over note; this closes one.** The other — the temporal extent
  models *existence*, not the active period (ADR 0035/0036), so a long-lived node's midpoint
  describes nothing — remains open and is the natural successor curation pass.
- All green (ruff, format, mypy, **146 tests**), incl. a region worked-example, the domain/region
  independence property, and a guard that every curated node carries a region.
