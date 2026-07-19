# ADR 0050 — 20th-century brain: a node pass to main-brain parity (the ADR 0047 plateau reached)

- **Status:** accepted
- **Phase:** 3

## Context

[ADR 0049](0049-twentieth-century-pendant-bridging.md) bridged every 20c pendant reachable *between
existing nodes* and recorded the honest boundary: ten nodes stayed degree-1 because bridging them
truthfully needs a **new node in another cluster**. It named that a *node pass* as the next
increment. [ADR 0047](0047-brain-growth-stopping-rule.md) governs the decision — grow tissue while the
two connectivity metrics climb, **stop when they plateau at main-brain parity** — so this pass was run
targeted (the highest-leverage marquee pendants), not exhaustive, and re-measured to decide stop.

## Decision

**Add two nodes and seven statements**, each new node a bridge that opens a marquee pendant onto a
*distant* cluster (verified QIDs, `evidence` + `headline` on every edge, Wikipedia + an already-cited
secondary book):

- **`cuban_missile_crisis`** (Q128160; history, LATIN_AMERICAN, 1962) — the highest-leverage single
  add. A three-region hub: `→ nuclear_weapon` (history↔**science**, LATIN_AMERICAN↔WESTERN),
  `→ Khrushchev` (LATIN_AMERICAN↔SOVIET), `→ JFK` (LATIN_AMERICAN↔WESTERN), `follows cuban_revolution`
  (ties it to the Cuban cluster). Castro and Che stay degree-1 but gain deep new *reach* — their
  2-hop neighbourhood now opens onto the nuclear/Cold-War clusters through the crisis.
- **`jean_renoir`** (Q50713; art, WESTERN, fl. 1930–1969) — fixes **Satyajit Ray**: `Ray influenced_by
  Renoir` (Ray assisted Renoir on *The River*, shot in Bengal — SOUTH_ASIAN↔WESTERN), and
  `French New Wave influenced_by Renoir` opens the whole Western-cinema cluster to Ray. Ray moves
  degree-1 → degree-2.
- Plus one edge, no node: **`Mandela influenced_by Nkrumah`** (pan-Africanism) — opens Mandela onto
  the arts via ADR 0049's `Nkrumah → Fela` edge (a domain-jump journey).

QIDs resolved live (`LiveTitleResolver`) and the **whole 102-node brain re-validated with zero
mismatches** — including the label↔QID hazard (ADR 0043) that has bitten before. Co-occurrence **was**
rebuilt (a node pass changes the node set, unlike ADR 0049's edges-only pass); `tetris` remains the
one node with no seed co-occurrence, exactly as before this pass (its article links no seed-node
article) — pre-existing and benign, the endpoint term degrades gracefully.

## Measurement — parity reached

Connectivity sweep, 20c across the pass, vs the main-brain baseline the 0047 thresholds are calibrated
on:

| Metric | baseline | after 0049 | **after this pass** | main |
| --- | --- | --- | --- | --- |
| Median journey `domain_jumps` | 0.000 | 0.469 | **0.625** | 0.537 |
| Median journey `region_jumps` | 0.583 | 0.688 | **0.682** | 0.622 |
| Median journey (domain+region) | 0.841 | 0.824 | **1.151** | 1.165 |
| Good non-obvious top pair | 76% | 81% | **82.4%** | 86% |
| Truly starved | 21 | 16 | **15** | 12 |

**The journey metrics are now at main-brain parity** — median (domain+region) 1.151 ≈ 1.165, and
`domain_jumps` 0.625 *exceeds* the main brain's 0.537. The improbable-pair metrics (82.4% vs 86%, 15
vs 12 starved) sit just short and are flattening (the big move was ADR 0049; this pass added less on
the pair axis). Per ADR 0047 that is the **plateau signal: stop node-adding on this brain.**

## Consequences

- `data/brains/twentieth_century/`: **100 → 102 nodes / 116 → 123 statements**, co-occurrence rebuilt
  (101/102 nodes, `tetris` sparse as before). Main brain untouched (116 / 175); per-brain scoring, so
  its sweep is byte-identical and every flagship holds. A structural value-lock
  (`test_twentieth_century_node_pass_bridges`) asserts the crisis hub touches three regions and Renoir
  bridges SOUTH_ASIAN↔WESTERN — property-based, no pinned TIL. **173 tests**, ruff/format/mypy green.
- **Recommendation recorded: the 20c brain has reached parity — stop growing it.** The residual
  degree-1 nodes are either not reach-starved (Berners-Lee via `www→internet→computer`, Gagarin via
  the space cluster, Jobim via `bossa_nova→jazz`) or genuinely need a bespoke new cluster for marginal
  gain (Joseph Campbell — mythology; Mies van der Rohe; anime — whose neighbours would co-occur and
  not fix its pair). Chasing them past parity would be growth for its own sake, which 0047 forbids.
- **Next lever, per ADR 0047/0048 (not more nodes):** a *modern Middle East region* only when a
  cluster populates it; or the first sanctioned LLM use — an offline, human-ratified **curation
  copilot** (ADR 0048) — if the drafting/QID-verification labour this pass exercised is what now gates
  breadth. Both are their own commits; neither is started here.
- This closes the ADR 0049 node-pass increment and demonstrates a full 0047 cycle end to end:
  **sweep → read the metrics → act (bridge, then add) → re-sweep → parity → stop.**
- Zero-LLM, deterministic, hand-reproducible. No weight, constant, or golden value changed; narration
  and scoring untouched — only the graph grew tissue.
