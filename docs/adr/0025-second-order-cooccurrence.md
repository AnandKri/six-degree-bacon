# ADR 0025 — Second-order co-occurrence to de-saturate the endpoint term

- **Status:** accepted
- **Phase:** 2

## Context

The endpoint-surprise term (ADR 0003) scores a destination by `−log2 P(endpoint | start)`, where the
conditional comes from Wikipedia-link **strength** — the number of link directions between the two
articles, so a value in `{0, 1, 2}`. On the curated seed this is far too coarse: the overwhelming
majority of node pairs are unlinked (strength 0), so they all receive the *same* maximal
unexpectedness. A test-robustness audit measured the damage: **71 of 80 nodes tie at the maximum
unexpectedness from Confucius**, and within the improbable-pair candidate sets 6/10 (Confucius),
15/20 (Woodblock printing), 20/25 (Roman Empire) tie at the top.

Because the improbable-pair archetype ranks by `endpoint_unexpectedness × trust`, this saturation
means the ranking is decided almost entirely by **trust**, not by how genuinely worlds-apart the
destination is — undercutting the archetype the project most wants to lean into (a single, quantized,
surprising TIL). This is a scoring-quality bug, not merely test debt.

## Decision

Add a graded **second-order** signal, keeping the term a hand-reproducible `−log2 P`. Two nodes that
co-occur with the *same* other articles share context even if their own articles never link each
other, so define the **effective strength**

```
effective_strength(a, b) = strength(a, b) + γ · | shared co-occurrence neighbours(a, b) |
```

with `γ = COOCCURRENCE_NEIGHBOUR_WEIGHT = 0.25` (a direct link still outweighs shared context — four
shared neighbours ≈ one link direction). Neighbours are symmetric (every node an article co-occurs
with, either direction). The conditional and its per-start denominator use `effective_strength` in
place of `strength`; it remains a proper distribution, so `−log2 P` is still a valid self-information.
Symmetric neighbour sets and denominators are precomputed at graph-build time (an O(N²) pass, fine
for a curated seed; an inverted index would restore near-linearity if a future harvest is huge).
`γ` and the worked arithmetic are in `sdb/constants.py` and `docs/confidence-rubric.md`.

## Consequences

- **De-saturated, sharper rankings.** Distinct unexpectedness values within the candidate set jump
  (Roman Empire 3 → 15; Confucius 3 → 7), and ties at the max collapse (Roman Empire 20 → 1). The
  improbable pair now surfaces genuinely isolated destinations: **Mansa Musa ⇢ Zoroastrianism**,
  **Buddhism ⇢ Thor**, **Woodblock printing ⇢ Rigveda** — striking single-fact juxtapositions rather
  than a trust-broken tie.
- **Golden re-characterised (two winners shifted).** At the 3-hop gate: Roman Empire → **Qin Shi
  Huang** (the First Emperor is more isolated than India once shared context is discounted) and
  Christianity → **Great Wall of China**; Euclid → India is unchanged. Recorded in `eval/golden.json`.
- **Hand-reproducibility preserved.** The existing `a↔b` worked example (0.49 / 2.81) is unchanged
  (no shared neighbours there); a new worked example and test lock the shared-neighbour arithmetic
  (0.87 / 1.87 / 2.46). Two cluster tests were made property-based / structural where the sharper
  ranking moved a hardcoded endpoint.
- Still zero-LLM, deterministic, offline, and a pure function of `data/cooccurrence.json`. All checks
  green (94 tests). Open follow-on: `γ` is a first pass tuned against the seed; a larger corpus or a
  richer co-occurrence source (link counts / full-text) could refine it further.
