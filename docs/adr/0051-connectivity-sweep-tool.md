# ADR 0051 — The connectivity sweep as a committed, tested tool (`sdb sweep`)

- **Status:** accepted
- **Phase:** 3

## Context

[ADR 0047](0047-brain-growth-stopping-rule.md) made a brain's grow-vs-stop decision turn on two
measured connectivity metrics, and [ADR 0049](0049-twentieth-century-pendant-bridging.md) and
[0050](0050-twentieth-century-node-pass-parity.md) were each *driven* by running that measurement —
but from a throwaway script in a scratchpad. That left the load-bearing instrument of three ADRs
uncommitted, unversioned and untested, in a project whose whole claim is a **trustworthy, reproducible
record**. The metric definitions were also scattered across ADR 0044/0047/0049/0050 with no single
authority. This ADR promotes the sweep to a first-class, tested tool and pins the definitions here.

## Decision

**Add `sdb/sweep.py` (a pure, deterministic module) and an `sdb sweep` CLI diagnostic**, alongside
`validate-qids` as a guard/diagnostic rather than a product command. `sdb sweep` defaults to every
brain (like `serve`/`build-site`); an explicit `--seed`/`--cooccurrence` sweeps one.

`connectivity_sweep(graph, cooccurrence) -> SweepReport` runs the ordinary
`discover` over committed co-occurrence — no network, reproducible by hand — and for every start node
records:

- **Metric 1 — the improbable pair.** Classify the start by its **top gated `UNLIKELY` result**:
  - *good* — lands somewhere the start does **not** directly co-occur (a genuine worlds-apart pair);
  - *obvious* — lands on a directly-linked neighbour (`link_strength ≥ 1`);
  - *nothing gated* — no pair clears the trust gate at all.
  These three **partition every node**. A start is additionally **starved** when *no* gated pair
  anywhere in its 1–2 hop neighbourhood is non-obvious (so `nothing_gated ⊆ starved`, and starved is
  never a *good* start) — the degree-limited "its 2-hop reach is its own cluster" case (ADR 0044).
  The headline is `good_fraction` (good / nodes).
- **Metric 2 — the journey.** The **median of `domain_jumps + region_jumps`** of each start's top
  gated `JOURNEY`. In a journey-led brain (temporal term quiet, ADR 0044) this is *the* health
  signal; `domain_jumps` and `region_jumps` medians are reported separately too.

`SweepReport` carries **node ids, not just counts**, so a caller (or a future ADR) can name the
pendants — exactly what ADR 0049/0050 needed. `format_report` renders the plain-text block.

## Consequences

- New module `sdb/sweep.py`, CLI command `sdb sweep`, and `tests/test_sweep.py` (**176 tests**): the
  derived `good_fraction` + `format_report`, and a real-brain **invariant** test — the three buckets
  partition every node, `starved` sits within `obvious ∪ nothing_gated` and contains `nothing_gated`,
  medians are non-negative. Property-based, **no pinned brain numbers** (which shift with the seed, per
  the truth hierarchy). `sdb sweep` reproduces the scratchpad script byte-for-byte (main 100/116 good,
  1.165; 20c 84/102 good, 1.151).
- **The grow-vs-stop decision is now one reproducible command**, not a re-derivation. A future session
  facing "should I grow this brain?" runs `sdb sweep` and reads the two metrics against the main-brain
  baseline — the ADR 0047 loop, executable.
- **No product behaviour, scoring, data, weight or golden value changed.** `discover`, the engine and
  both seeds are untouched; this is pure diagnostic infrastructure (the shape of `validate-qids`).
- Closes the one real gap the ADR 0049/0050 commits opened (the informal instrument). The scratchpad
  script is superseded; docs now point at `sdb sweep`.
- Zero-LLM, deterministic, hand-reproducible.

## Alternatives considered

- **A standalone `scripts/connectivity_sweep.py`.** Rejected: the project has no `scripts/` convention,
  and a diagnostic belongs with the other stdlib CLI diagnostics (`validate-qids`) where it is
  discoverable and shares the brain-registry plumbing (`_selected_brains`).
- **Leave it in the scratchpad.** Rejected — that is the defect this ADR fixes; a load-bearing
  measurement three ADRs cite must be versioned and tested like any other guard.
- **Pin the current metric values in a golden file.** Rejected: the metrics are meant to *move* as a
  brain grows; pinning them would enshrine a snapshot and re-create the `eval/golden.json` change-detector
  role, not add one. The invariant test guards the *logic*; the numbers are read, not asserted.
