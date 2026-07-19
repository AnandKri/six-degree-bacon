# ADR 0049 — 20th-century brain: an escape-edge tissue pass (the first ADR 0047 measurement in action)

- **Status:** accepted
- **Phase:** 3

## Context

[ADR 0047](0047-brain-growth-stopping-rule.md) says a brain grows by *connective tissue*, not node
count, and that the decision to grow (or stop) is driven by two measured metrics, not a target. This
ADR is the first application of that rule: the connectivity sweep it prescribes was run on the
20th-century brain, and it did **not** report a plateau — it reported the opposite, an
*under-tissued* graph where node count (100, ADR 0046) had outrun connective tissue.

### The sweep (deterministic; committed co-occurrence; no network)

Per-start improbable-pair + top-journey sweep over all 100 nodes, 20c vs the main-brain baseline the
0047 thresholds were calibrated on:

| Metric | 20c (before) | Main (baseline) |
| --- | --- | --- |
| Good non-obvious top pair | **76%** | 86% |
| Truly starved (no non-obvious pair exists) | **21%** | 10% |
| **Median journey `domain_jumps`** | **0.000** | 0.537 |
| Median journey `region_jumps` | 0.583 | 0.622 |

Two findings decided the action:

1. **`median domain_jumps = 0.000`.** The 20c brain is journey-led by design — its temporal-gap
   term is deliberately quiet (ADR 0044), so domain + region jumps *are* its surprise engine. Half
   its top journeys crossed **zero domains**: growth to 100 nodes had added within-domain depth
   faster than cross-domain bridges, and the entire politics/history cluster (revolutions, the Cold
   War, the independence leaders) connected to the arts/sciences almost nowhere — the only
   history↔art tissue was `civil_rights_movement ↔ jazz/gospel`.
2. **The starved starts were degree-1 pendants on *central* figures**, not irreducible leaf-concepts.
   Mandela, Nehru, Mao, Castro, Che, Gagarin, Berners-Lee, Michael Jackson and Satyajit Ray each hung
   off a single edge; Mandela and Nehru hung off the *same* one (`→ Gandhi`). "One connected
   component, no islands" (ADR 0046) was true and still missed this: no islands ≠ no pendants.

## Decision

**Add escape edges between *existing* nodes — no new nodes, no new QIDs — biased to cross a
discipline or culture, each giving a flagged pendant a second edge.** Seven sourced statements
(`evidence` + `headline` + a Wikipedia source corroborated by an already-cited secondary book), all
true and non-obvious:

| edge | crossing |
| --- | --- |
| `soviet_constructivism inspired_by russian_revolution` | art ↔ history (SOVIET) |
| `fela_kuti influenced_by kwame_nkrumah` | art ↔ history (SUB_SAHARAN) |
| `chandigarh influenced_by jawaharlal_nehru` | art ↔ history (SOUTH_ASIAN) |
| `bob_dylan inspired_by civil_rights_movement` | art ↔ history (WESTERN) |
| `mao_zedong influenced_by vladimir_lenin` | history, SINITIC ↔ SOVIET (region) |
| `bollywood influenced_by indian_classical_music` | within art/SOUTH_ASIAN (reach only) |
| `michael_jackson influenced_by soul_music` | within art/WESTERN (reach only) |

The four art↔history edges are the point: they wire the arts into the politics cluster, which is what
lifts the domain-jump term off zero for journeys that route through it.

**Co-occurrence was *not* rebuilt.** The endpoint-surprise matrix is keyed on **nodes** (each
article's outbound Wikipedia links); adding a curated edge between two existing nodes changes no
node's article, so the sidecar is unchanged. (Confirmed against the ADR 0017 build.)

## Measurement (after)

| Metric | before → after | main (unchanged) |
| --- | --- | --- |
| **Median journey `domain_jumps`** | **0.000 → 0.469** | 0.537 |
| Median journey `region_jumps` | 0.583 → 0.688 | 0.622 |
| Mean journey (domain+region) | 1.014 → 1.099 | 1.255 |
| Good non-obvious top pair | 76% → **81%** | 86% |
| Truly starved | 21 → **16** | 12 |

`soviet_constructivism` and `indian_classical_music` left the starved set entirely; `nehru` and `mao`
moved from degree-1 to degree-2. The **main brain is untouched** (per-brain scoring): its sweep is
byte-identical, all three `eval/golden.json` cases and every flagship hold.

## Consequences

- `data/brains/twentieth_century/seed.json`: **100 nodes / 109 → 116 statements**. Main brain stays
  116 nodes / 175 statements. A structural value-lock (`test_twentieth_century_pendant_bridging_tissue`)
  asserts the four bridged pendants now carry ≥ 2 edges and an art↔history escape edge exists —
  property-based, never a pinned TIL. **172 tests**, ruff/format/mypy green.
- **The honest boundary of an edges-only pass.** Ten nodes remain degree-1 pendants — Mandela, Ray,
  Castro, Che, Campbell, anime, Gagarin, Jobim, Berners-Lee, Mies van der Rohe. Each needs a *new
  node* in another cluster to bridge without overclaiming (e.g. an apartheid node for Mandela, a
  Bengali-cinema/Renoir hook for Ray). Forcing a weak edge to a same-region neighbour would trade a
  true graph for a better number — the ADR 0034 mistake. That is the next 0047-shaped increment, a
  *node* pass, recorded here and not done.
- This ADR is the template for a growth decision under 0047: **sweep → read the two metrics → act on
  what they say (here: bridge, not add) → re-sweep → stop when they plateau.** The 20c brain has not
  plateaued; a node pass for the remaining pendants is the next step, then re-measure.
- Zero-LLM, deterministic, hand-reproducible. No weight, constant, or golden value changed —
  narration and scoring are unchanged; only the graph grew tissue.
