# ADR 0046 — The 20th-century brain to 100 nodes (+ three modern regions)

- **Status:** accepted
- **Phase:** 3

## Context

The 20th-century brain (ADR 0044, grown by ADR 0045) was a 32-node graph. The owner's steer: build it
out to **100 nodes**, working through the growth backlog recorded in `docs/HANDOVER.md`
(architecture, global cinema, deeper music, deeper science/tech, global politics), keeping the brain's
journey-led character — its one-century span mutes the temporal-gap term, so its surprise must come
from cross-**domain** and cross-**region** jumps, not time depth.

## Decision

Add **68 nodes / 76 statements** (seed 32 → **100 nodes / 33 → 109 statements**), all QIDs verified
label→article→wikibase_item, every statement carrying a sourced `evidence` + `headline`, in six
connected threads that each bridge into the existing graph (one connected component, **no islands**):

- **Architecture** (owner's lead pick, domain `art`): Art Deco → Hollywood; Bauhaus ← Soviet
  Constructivism `[WESTERN↔SOVIET]`; the International Style ← Wright / Mies; Le Corbusier → Brutalism
  and → Chandigarh `[WESTERN↔SOUTH_ASIAN]`; the Sydney Opera House.
- **Global cinema**: Hollywood the hub (← Kurosawa, → Star Wars); Disney → Osamu Tezuka → anime
  `[WESTERN↔JAPANESE]`; Italian neorealism → Satyajit Ray, Hollywood → Bollywood `[↔SOUTH_ASIAN]`;
  the French New Wave, Leone ← Kurosawa, Hitchcock, Chaplin, Welles, Spielberg, Kubrick.
- **Music**: the jazz/blues/funk hubs branch to Armstrong, Miles Davis, Gershwin, the Stones, James
  Brown → Michael Jackson, punk, disco — and cross-culture to **reggae/Marley `[CARIBBEAN]`**,
  **bossa nova/Jobim, salsa `[LATIN_AMERICAN]`**, **Fela Kuti `[SUB_SAHARAN]`**.
- **Science/tech**: Einstein → relativity/quantum → the transistor and the bomb (Manhattan Project);
  von Braun's V-2 → Apollo 11; von Neumann → the computer; the integrated circuit → Silicon Valley →
  the PC (Jobs) → the Web (Berners-Lee).
- **Global politics / Cold War**: the Soviet chain (Lenin → Stalin → Khrushchev → the Berlin Wall,
  and → Sputnik); Mao's China ← the Russian Revolution `[SINITIC↔SOVIET]`; the Cuban Revolution
  (Castro, Che) ← Marxism `[LATIN_AMERICAN↔SOVIET]`; Mandela and Nkrumah ← Gandhi
  `[SUB_SAHARAN↔SOUTH_ASIAN]`; Nehru ← Gandhi; JFK → Apollo 11.
- **Literature**: the Beat Generation ← jazz, → Bob Dylan.

**Three regions, each earned by a populated cluster** (ADR 0045's rule — add a sphere only when nodes
fill it and the crossing is real): `LATIN_AMERICAN` (6 nodes), `SUB_SAHARAN` (3 — the *modern* sphere,
distinct from the medieval `WEST_AFRICAN` trade cluster), `CARIBBEAN` (2). The US/UK/Western-European
continuum stays `WESTERN` (the ADR 0045 non-split). Scoring is per-brain, so the **main brain is
untouched**.

One QID-hygiene note (the ADR 0043 hazard, caught by `validate-qids`): the label "Constructivism"
resolves to a *different* entity than the art-movement QID Q207103, so the node is labelled
"Constructivism (art)" with "Constructivism" / "Soviet Constructivism" as aliases.

## Measurement (per the truth hierarchy — structural, not a pinned winner)

- **Cross-region surprise carries the brain, as designed.** A sweep of the new clusters returns a
  gated cross-region/cross-domain journey for every one, driven by domain + region jumps with the
  temporal term quiet. Standouts: **`Mao → Chinese Revolution → Russian Revolution → Cuban
  Revolution`** (a `SINITIC → SOVIET → LATIN_AMERICAN` three-region communist arc),
  **`Nelson Mandela → Gandhi → MLK → civil rights`** (`SUB_SAHARAN → SOUTH_ASIAN → WESTERN`),
  **`WWW → the Internet → the computer → Tetris`** (`WESTERN → SOVIET`), `Fela Kuti → funk → soul →
  gospel`, `anime → Tezuka → Disney → Hollywood` (`JAPANESE → WESTERN`), `Bauhaus → International
  Style → Art Deco → Hollywood` (architecture → cinema), `Chandigarh → Le Corbusier → …`
  (`SOUTH_ASIAN → WESTERN`). Trust 0.66–0.82, all clearing the gate.
- **No islands, no starved core.** The graph is one connected component; every new node reaches the
  existing hubs. New regions score cross-sphere jumps only where a real culture boundary is crossed
  (Fela Kuti ← Western funk; reggae ← Western soul), never within a continuum.
- **Structural guards** (`test_brains.py`): the new regions are populated and a cross-sphere edge
  exists for each; the per-brain integrity guards (ADR 0044) already cover all 100 nodes.

## Consequences

- 20th-century brain: **100 nodes / 109 statements**, co-occurrence rebuilt; three regions added to
  the shared `Region` enum (per-brain scoring — main brain **116 / 175** unchanged).
- Zero-LLM, deterministic, reproducible by hand; all green (ruff, format, mypy, tests). The backlog's
  architecture / cinema / music / science / politics threads are now largely built; remaining regions
  (a modern Middle East, etc.) stay deferred until a cluster populates them.
