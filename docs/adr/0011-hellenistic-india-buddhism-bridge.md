# ADR 0011 — Hellenistic–India–Buddhism seed bridge (Type-B coverage)

- **Status:** accepted
- **Phase:** 2

## Context

The "improbable adjacency" archetype (ADR 0007) ranks a short link by the *unexpectedness of its
destination* (`endpoint_unexpectedness × trust`). Diagnosing it on the seed exposed two structural
limits (HANDOVER §5 item 1):

- **The science/India cluster was nearly isolated.** Euclid → al-Tusi → Jagannatha → Jai Singh II
  reached the rest of the graph through a *single* bridge (`al-Tusi → Persia`). Euclid reached only
  six endpoints; there was no way for the engine to connect Greek mathematics or Mughal astronomy to
  the Mediterranean/Chinese world except that one seam.
- **Co-occurrence is near-binary.** `−log₂P(endpoint|start)` is high for *every* endpoint whose
  Wikipedia article the start's article does not link, so all unlinked endpoints tie at the same
  ceiling and improbability cannot discriminate among them — the winner is just the highest-*trust*
  unlinked neighbour. On thin, obscure articles this even produces *false* improbable pairs (e.g. Jai
  Singh II → his own court astronomer Jagannatha, who obviously belong together).

The fix is not to change scoring but to give it better structure: genuine, well-sourced short links
between clusters that feel worlds apart, routed through **well-documented** nodes (whose real
Wikipedia co-occurrence keeps the signal honest).

## Decision

Add a compact, on-theme **Hellenistic ↔ India ↔ Buddhism** bridge — four nodes, eight statements,
every QID verified against Wikidata and every claim sourced (Wikipedia + a secondary book, so trust
stays high; no fabricated Wikidata references — Alexandria's real `P138 → Alexander` carries *zero*
references, so it is cited as Wikipedia/secondary, not `wikidata_with_ref`):

- **Nodes:** `alexander_the_great` (Q8409), `alexandria` (Q87), `india` (Q668), `buddhism` (Q748).
- **Links:** `euclid → alexandria → alexander_the_great` (un-isolates Euclid with a second route out);
  `alexander_the_great → persia` and `→ india` (the Greek world into both the Silk-Road web and
  India); `buddhism → india` and `buddhism → connected_via_trade → silk_road` (Buddhism as the
  cross-cultural connector that carried into China); `rigveda → india`, `jai_singh_ii → india`
  (populate the India cluster so ancient scripture and Mughal science share a hub).

Then the mandatory post-seed process: `validate-qids` (41/41 resolve) → `build-cooccurrence`
(regenerated for 41 nodes) → re-characterise `eval/golden.json`.

## Consequences

- **The longest *meaningful* journeys now span Eurasia.** `Roman Empire → Silk Road → Persia →
  Alexander the Great → India → Buddhism` (5 hops, trust 0.75) is the new flagship; Christianity now
  reaches the Rigveda, and a no-longer-isolated Euclid reaches Persia across Alexandria/Alexander.
  `eval/golden.json` re-characterised accordingly (winners lead runners-up by ≥ 1.3 wow, so stable).
- **Genuine Type-B pairs appear:** Buddhism ↔ the Roman world / the Great Wall / Persia, Alexander ↔
  Buddhism / the Rigveda — worlds apart, ≤ 2 hops, all sourced. Rome's top improbable pair is now a
  three-way tie (Great Wall / Buddhism / Zhang Qian); `test_improbable_pair_…` was rewritten to assert
  the *invariant* (short + worlds-apart, beating the obvious Latin) rather than one tie-sensitive
  label, and a new test locks Buddhism's connection to the Greco-Roman/Chinese world.
- Still zero-LLM, deterministic, reproducible by hand. The known thin-co-occurrence caveat remains for
  intrinsically obscure nodes; using famous, well-linked bridge nodes keeps this addition clean.
