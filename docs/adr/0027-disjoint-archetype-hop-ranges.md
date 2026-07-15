# ADR 0027 — Make the archetype hop ranges disjoint (improbable pair 1–3 → 1–2)

- **Status:** accepted
- **Phase:** 2

## Context

ADR 0007 surfaces two archetypes together on the premise that they are **two different kinds of
delight**: a *journey* (a cross-domain chain) and an *improbable pair* (a thin link between entities
that feel worlds apart). But their candidate ranges overlapped:

```
journey  = [MIN_HOPS_DEFAULT,  MAX_HOPS_DEFAULT]  = [3, 3]   (ADR 0021)
unlikely = [MIN_HOPS_UNLIKELY, MAX_HOPS_UNLIKELY] = [1, 3]   ← fully contains [3, 3]
```

Nothing de-duplicates across archetypes, so whenever a topic's most-improbable destination happened
to sit exactly 3 hops away, **both archetypes selected the identical path** and the user saw the same
TIL twice under two labels. An independent review caught this; on the current seed it reproduced for
**3 of 10 sampled topics — including Roman Empire and Christianity**, i.e. the flagship demo and two
golden cases. That defeats the entire premise of having two archetypes.

## Decision

Set `MAX_HOPS_UNLIKELY = 2`, making the ranges **disjoint by construction** — journey `[3, 3]`,
pair `[1, 2]`. A collision becomes structurally impossible, with no cross-archetype dedupe logic to
write or maintain. It also sharpens the archetype's meaning: an improbable *adjacency* should be a
short, thin link, so 1–2 hops is truer to ADR 0007's intent than 1–3.

The alternative — keeping `[1, 3]` and excluding the journey's chosen path from the pair's candidate
set — was rejected: more code, and it would leave the two archetypes competing for the same 3-hop
paths rather than owning distinct shapes.

## Consequences

- **Fixed:** duplicates drop from 3/10 to **0/10** across the sampled topics. Roman Empire now gives
  the journey `→ Qin Shi Huang` and the distinct pair `⇢ Zhang Qian` (2 hops); Christianity gives
  `→ Great Wall of China` and `⇢ Roman Republic`.
- **Golden winners unchanged** — the journey range is untouched, so `eval/golden.json` needed no
  re-characterisation (as the review predicted).
- Pair examples cited in earlier ADRs that were 3 hops (e.g. Buddhism ⇢ Aristotle) now resolve to a
  ≤2-hop destination (Buddhism ⇢ Woodblock printing). The flagship lineage pairs are unaffected
  (Naruhito ⇢ Amaterasu and Elizabeth II ⇢ House of Wessex are both 2 hops).
- A regression test locks the invariant (`MAX_HOPS_UNLIKELY < MIN_HOPS_DEFAULT`, plus no topic
  returning the same path twice), so widening the range back would fail loudly.
- The shared `_assert_worlds_apart` test helper was relaxed from "the most-obvious node never appears
  in the top-n" to "it never **wins**": with a 1–2 hop range some starts have only a handful of
  candidates, so an obvious node can legitimately appear far down a `top=5` list. Winning is the
  regression; appearing last is not.
- One constant, documented here and in `sdb/constants.py`. Zero-LLM, deterministic, hand-reproducible.
  All green (96 tests).
