# ADR 0021 — Cut the default journey cap from 4 to 3 hops (fixed-length journeys)

- **Status:** accepted
- **Phase:** 2

## Context

ADR 0012 cut the JOURNEY default from 6 to 4 hops for punchier cards. In use, the **improbable
pair** archetype (ADR 0007) reliably produces the bigger "wow" — a short link between two entities
that feel worlds apart — while the 4-hop journeys still occasionally read as a ramble and, because
trust decays multiplicatively, the 4th hop buys little extra surprise for a real trust cost. Product
feedback: keep the journey, but make it shorter. Reviewing the seed's journeys at a 3-hop cap, the
3-hop chains are consistently strong and often better than their 4-hop counterparts — e.g.
`Christianity → Roman Empire → Silk Road → Great Wall of China`, `Japan → Tang dynasty → Silk Road →
Roman Empire`, `Roman Empire → Silk Road → Buddhism → India`.

A 2-hop journey was considered and rejected: with `MIN_HOPS_DEFAULT = 3` a 2-hop cap returns nothing,
and lowering the minimum to 2 would make the journey indistinguishable from the improbable pair
(both short, differing only in ranking key). Keeping the journey at a fixed 3 hops preserves a clean
division of labour: the **pair** owns the 1–2 hop "worlds apart" wow; the **journey** is a genuine
3-hop cross-domain chain.

## Decision

Set `MAX_HOPS_DEFAULT = 3`. With `MIN_HOPS_DEFAULT` still 3, the JOURNEY archetype becomes a
**fixed-length 3-hop chain** (`[3, 3]`). This is a *default*, not a hard limit: the engine still
supports the full "six degrees" via `--max-hops` / `discover(..., max_hops=…)`. The UNLIKELY range
`[1, 3]` and every scoring weight are untouched; nothing is special-cased.

## Consequences

- **Punchier journeys, one clear shape per archetype.** At the 3-hop cap the golden winners become
  Roman Empire → India (via Silk Road → Buddhism), **Christianity → Great Wall of China** (via Roman
  Empire → Silk Road — a genuine wow), and Euclid → India (via Alexandria → Alexander the Great).
  `eval/golden.json` re-characterised (all three now `expected_hops: 3`).
- **One cluster test made more robust.** The Islamic-cluster test asserted Baghdad's 4-hop journey
  *endpoints*; at 3 hops those endpoints move one node closer, so it now asserts the stable property
  that every top Baghdad journey routes **through the Silk Road hub** — bridge, not island.
- **Deep chains remain reachable on demand** (`--max-hops 6`); the planted-path and guided-walk perf
  tests, which pass depth explicitly, are unaffected.
- Zero-LLM, deterministic, reproducible by hand — a single tuning constant, documented here and in
  `sdb/constants.py`. All checks green (88 tests).
