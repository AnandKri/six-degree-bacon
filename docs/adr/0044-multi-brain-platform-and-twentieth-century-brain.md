# ADR 0044 — Phase 3 kickoff: the multi-brain platform + a detached 20th-century brain

- **Status:** accepted (first increment built; web multi-brain UI pending — see Consequences)
- **Phase:** 3

## Context

Phase 2 is at its exit: both schema-blocker terms (ADR 0039 region, 0041 active-period) and the
narrator decision (ADR 0042) are closed, and a coverage sweep shows the single-brain scoring model
has plateaued (below). The remaining Phase-2 thread — breadth on the ancient graph — has thinning
marginal value (the graph already spans most major Old-World civilisations). The question was what a
*phase-worthy* next step is, not another cluster.

**Owner's steer:** a **"20th Century"** surface — rich cross-cultural influence across film, music,
politics and technology — as a **detached knowledge graph ("separate brain")**. This ADR records the
measurement that justified it and the first built increment.

### Phase-2 exit measurement (the plateau)

Starved-start sweep over all 116 curated nodes (for each, does the top improbable pair clear the gate
and land somewhere it does *not* directly co-occur?):

- **104 / 116 (89.7%)** return a good, non-obvious improbable pair; **0** return nothing gated.
- **12 / 116 (10.3%)** are "starved" — **every one has graph-degree 1–4** (structurally its own
  cluster; a scoring change can't help, only a breadth edge *into* that node).
- Journeys: only **2** (troy, aeneas — degree ≤ 2) return nothing gated.
- Trend across the project: **16/88 → 15/98 → 12/116** — ratio *and* absolute count both falling.

With no open scoring/schema/narrator defect and coverage plateaued, **Phase 2 is declared done.**

### The probe (measure before building — per the truth hierarchy)

A 13-node / 14-statement 20th-century cluster was added to the *shared* brain, bridging into existing
hubs (Kurosawa→Japan, Campbell→Buddhism, Ravi-Shankar→Hinduism, algorithm→al-Khwarizmi, MLK→Gandhi).
Two findings decided the architecture:

1. **The material is excellent.** Every new node produced a gated journey into antiquity and strong
   one-fact TILs (`Alan Turing ⇢ al-Khwarizmi` — "the word 'algorithm' comes from a 9th-century
   Baghdad mathematician"; `Gandhi → Hinduism → Rigveda → Thor`; `Beatles ⇢ Ravi Shankar`).
2. **In the shared brain it contaminates the ancient results.** A 20th-century node is *maximally
   distant* (time + region + endpoint) from everything ancient, so it wins as a surprise destination
   and displaces curated flagships: `Roman Empire` journey Zen → **Joseph Campbell**; `Japan` →
   **Joseph Campbell**; `Algebra`'s science lineage re-routed through the new `algorithm` node (the two
   test re-characterisations the probe caused — legitimate per the truth hierarchy, but symptomatic).
   At 13 nodes it is a nudge; **at scale it would drown every ancient-to-ancient connection.**

Finding 2 is the decisive argument for **separation**: the probe was reverted from the shared brain,
and the 20th century becomes its own brain.

## Decision

**A "brain" is a `(seed.json, cooccurrence.json)` pair.** The engine, pipeline and *every* CLI command
(`discover`, `build-cooccurrence`, `validate-qids`, `serve`, `build-site`) are **already parameterised
by `--seed`/`--cooccurrence`**, so multi-brain needs **no engine refactor** — only data, plus a web UI
that can hold more than one brain (deferred). New brains live under `data/brains/<name>/`; the main
brain stays at `data/seed.json` (no disruptive move).

**First brain built: `data/brains/twentieth_century/`** — **17 nodes / 16 statements**, self-contained,
all QIDs verified label→article→wikibase_item, every statement carrying `evidence` + `headline`:

- **film** (`akira_kurosawa`, `the_hidden_fortress`, `star_wars`, `george_lucas`, `joseph_campbell`),
  **music** (`blues`, `jazz`, `rock_and_roll`, `the_beatles`, `ravi_shankar`, `indian_classical_music`),
  **tech** (`transistor`, `computer`, `alan_turing`), **politics** (`civil_rights_movement`,
  `martin_luther_king`, `mahatma_gandhi`).
- **Internal cross-domain spine (not deep-time bridges):** film↔tech (`star_wars influenced_by
  computer` — motion-control/ILM), tech↔music (`rock_and_roll influenced_by transistor` — the
  transistor radio), music↔politics (`civil_rights_movement inspired_by jazz`). One connected
  component, no isolated nodes.
- **Three cross-region cultural bridges** carry the cross-cultural surprise: `star_wars ⇢ Hidden
  Fortress` (western↔japanese), `Beatles ⇢ Ravi Shankar` and `MLK ⇢ Gandhi` (western↔south_asian).

### Detached-brain design principles (learned from the probe + the eval)

- **Journey-led, not improbable-pair-led.** In a globalised, well-documented century the wow-facts
  *are* documented (Beatles↔Shankar, Lucas↔Kurosawa, MLK↔Gandhi all co-occur), so the co-occurrence
  "improbability" term flags them as directly-adjacent even though they are great TILs. The **journey**
  archetype (cross-domain chain) carried every node; the improbable pair still returns a solid one-fact
  TIL but as a documented adjacency. A 20th-c. brain should surface journeys first.
- **The temporal-gap term goes quiet** (one century) — confirmed. Surprise here is carried by the
  other four terms (rarity + domain jumps + region jumps + endpoint unexpectedness). This is *why* the
  brain must be internally cross-domain and cross-region rather than lean on time depth.
- **`Region` reused as-is for this increment** (American/British both `WESTERN`), which is coarse but
  correct: the jumps that matter (→japanese, →south_asian) fire, and the Anglo-American pop continuum
  is genuinely one sphere. A finer modern split (AMERICAN / SOVIET / …) is a deferred design decision
  under ADR 0039's walking-tour caution, not free.

## Measurement (the detached brain, standalone)

Every node returns a gated journey and improbable pair. Representative journeys, all driven by
domain+region jumps with the temporal term ~silent:

- `Gandhi → MLK → civil rights → jazz` (an Indian independence leader to American jazz),
- `Alan Turing → computer → Star Wars → Hidden Fortress` (a mathematician to a Kurosawa samurai film),
- `transistor → rock and roll → blues → jazz`, `blues → rock and roll → Beatles → Ravi Shankar`.

Scores run lower than the main brain (~13–22 vs ~26–42): no temporal contribution and a smaller,
denser graph depress rarity/endpoint magnitudes. Scores are only compared *within* a brain, so this is
immaterial. Trust 0.66–0.82, all clear the 0.50 gate.

## Consequences

- **Main brain untouched:** `data/seed.json` stays **116 nodes / 175 statements**, 154 tests green.
  The probe was reverted; no ancient flagship moved.
- **New artifact:** `data/brains/twentieth_century/{seed,cooccurrence}.json`, runnable *today* via
  `sdb discover "…" --seed data/brains/twentieth_century/seed.json --cooccurrence
  data/brains/twentieth_century/cooccurrence.json`.
- **Pending increments (not in this ADR):** (1) **web multi-brain** — `serve`/`build-site` load one
  graph today; a brain switcher / tab + one `data.json` per brain is the one real code change; (2) a
  thin **brain registry** so `--brain 20c` resolves the path pair; (3) **grow the brain** (more film /
  music / Cold War / decolonisation, with its own value-locking tests); (4) revisit a **modern Region**
  refinement if the coarse `WESTERN` proves limiting. Each is its own commit.
- Zero-LLM, deterministic, reproducible by hand. Phase 2 closes; Phase 3 = the multi-brain platform.
