# ADR 0012 — Cut the default journey cap from 6 to 4 hops

- **Status:** accepted
- **Phase:** 2

## Context

The JOURNEY archetype enumerated chains of `[MIN_HOPS_DEFAULT, MAX_HOPS_DEFAULT] = [3, 6]` hops.
"Six" honours the "Six Degrees of Kevin Bacon" premise, but in practice a 6-hop result *reads* as a
ramble, and — because trust decays multiplicatively along a chain (a path is only as strong as its
weakest link) — the deepest winners are also the least trustworthy. After the Hellenistic–India–
Buddhism bridge (ADR 0011) the top journeys illustrated this: Christianity → Rigveda ran a full
6 hops at trust 0.56, and Euclid → Persia 6 hops at 0.71. Product feedback: the cards are more
compelling short.

## Decision

Set `MAX_HOPS_DEFAULT = 4` (JOURNEY default range `[3, 4]`). This is a *default*, not a hard limit:
the engine still supports the full "six degrees" — any user can request deeper chains per query with
`--max-hops`, and `discover(..., max_hops=…)` is unchanged. `MIN_HOPS_DEFAULT` (3), the UNLIKELY
range `[1, 3]`, and all scoring weights are untouched; nothing is special-cased.

## Consequences

- **Punchier, higher-trust journeys.** At cap 4 the golden winners become Roman Empire → India
  (trust 0.80), Christianity → Alexander the Great (0.64), and a now-un-isolated Euclid → Buddhism
  (0.77) — all shorter and better-evidenced than their 6-hop predecessors. `eval/golden.json`
  re-characterised; note Roman Empire's runner-up (Rigveda) trails by only ~0.35 wow, a deterministic
  near-tie recorded in the golden comment (characterisation locks whatever the engine produces).
- **Deep chains remain reachable on demand.** The planted 6-hop Rome → Great Wall chain is still
  discoverable with `--max-hops 6` (its regression test now passes the depth explicitly), and the
  guided-walk perf test still exercises `[3, 6]`.
- Zero-LLM, deterministic, reproducible by hand — this is a single tuning constant, documented here
  and in `sdb/constants.py`.
