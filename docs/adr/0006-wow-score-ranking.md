# ADR 0006 — Rank by wow = surprise × trust, gate on evidence, drop the length reward

- **Status:** accepted
- **Phase:** 2

## Context

Ranking purely by *surprise* (with trust only a tie-break and a low 0.15 floor) had a structural
flaw: surprise **accumulates per hop** (rarity and temporal-gap are sums), so the ranker was
effectively *paid to ramble* to the maximum 6 hops — and 6-hop paths have the **lowest** trust
(weakest-link product). Every default result was therefore a long, `Possibly:`-flagged chain of
~0.25 trust, while genuinely striking, well-sourced short connections were buried. Concretely, "Roman
Empire → … → Chang'an" (6 hops, trust 0.25) outranked "Roman Empire → Silk Road → Great Wall →
Qin Shi Huang" (3 hops, **trust 0.86** — Rome to the First Emperor of China).

Two product principles drove the change: results should be **wow *with evidence***, and we should
prefer **one genuinely surprising, well-sourced** result over many mediocre ones.

## Decision

- **Rank by a composite wow score, `wow = surprise × trust`.** A path wins only when it is both
  surprising and believable. Since trust decays multiplicatively along a chain, the product naturally
  favours tight, trustworthy paths — reframing "longest *meaningful* path" as "longest path that
  stays trustworthy" — with no hard hop cap.
- **Gate on evidence.** By default only paths with `trust ≥ POSSIBLY_THRESHOLD (0.50)` are surfaced;
  if none qualify the CLI says so honestly (quality over quantity). `--include-possibly` lowers the
  gate to `TRUST_FLOOR (0.15)` and flags sub-threshold paths `Possibly:`.
- **Stop rewarding length.** The `length_bonus` term (`W_LENGTH`) is removed entirely — it only
  amplified the rambling bias; trust in the wow score already prefers shorter chains.

`DiscoveryResult` gains a `score` field; the CLI shows it as the headline "wow" number.

## Consequences

- Default results are now tight and confident (all `possibly = false`): Roman Empire → Mithra
  (4 hops, trust 0.84), Zoroastrianism → Qin Shi Huang (4 hops, trust 0.84), Silk Road → Mithra
  (3 hops, trust 0.89). Topics with no confident connection (e.g. Trojan War) return nothing by
  default rather than a flimsy path.
- Long, low-trust "showcase" chains (the planted 6-hop Rome → Great Wall) remain discoverable via
  `--include-possibly`; the regression test now asserts that under the lowered gate.
- `eval/golden.json` re-characterized; the surprise worked example (8.6) is unchanged because that
  path never earned a length bonus. Scores stay **reproducible by hand** — multiply the two numbers.
- Trust is now first-class in ranking, a deliberate departure from ADR-era "rank by surprise, trust
  as tie-break." The two scores are still computed independently and shown separately.
