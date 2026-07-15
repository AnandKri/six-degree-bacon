# ADR 0026 — Breadth: the divine-descent (royal lineage) cluster

- **Status:** accepted
- **Phase:** 2

## Context

The project's sharpest TILs are **single quantized facts**, and one of the most striking flavours is
a *surprising lineage*: "Elizabeth II descends from Odin", "Japan's imperial family traces to the sun
goddess". The graph already had the `claimed_descent_from` predicate (Augustus ← Julius Caesar,
Romulus ← Aeneas, Thor ← Odin) but no modern-to-mythic descent chains, so that flavour of result
simply did not exist in the data. Both target chains anchor on nodes the graph already has — **Odin**
(from the Norse/Celtic cluster, ADR 0022) and **Japan** (from the East Asia cluster, ADR 0020) — so
the cluster is well-connected rather than an island.

## Decision

Add seven verified nodes and eight sourced statements, forming two descent chains that terminate in
existing nodes:

- **British:** Elizabeth II (Q9682) → `claimed_descent_from` → Alfred the Great (Q83476) →
  `part_of` → House of Wessex (Q511482) → `claimed_descent_from` → **odin**. The Anglo-Saxon royal
  genealogies traced Wessex's line to Woden, the Old English form of Odin.
- **Japanese:** Naruhito (Q217096) → `claimed_descent_from` → Jimmu (Q200188) →
  `claimed_descent_from` → Amaterasu (Q455602) → `part_of` → Shinto (Q812767) → `located_in` →
  **japan**.

Legendary descent claims cite the primary legendary source as `myth_legend` (the Anglo-Saxon
Chronicle; the Kojiki/Nihon Shoki) alongside Wikipedia, so the evidence states the *claim* honestly
rather than asserting literal descent from a god. QIDs verified against Wikidata; `validate-qids`
(88/88) → `build-cooccurrence` (88).

A trivial `naruhito located_in japan` edge was drafted and then **dropped**: it is low-information
(the Emperor of Japan is, of course, in Japan — the informative fact is the *role*, which
`located_in` does not capture) and it introduced a hub shortcut that routed journeys around the
lineage the cluster exists to express. The cluster still reaches Japan via `shinto located_in japan`,
so nothing islands.

## Consequences

- **The lineage TILs now exist and headline.** `Elizabeth II → Alfred the Great → House of Wessex →
  Odin` (trust 0.73) is Elizabeth II's top journey; `Naruhito → Jimmu → Amaterasu → Shinto` (0.64) is
  Naruhito's, with `Naruhito ⇢ Amaterasu` (2 hops) as his top improbable pair. A property-based test
  locks both chains and the Shinto→Japan anchor.
- **Golden winners unchanged** (Roman Empire → Qin Shi Huang, Christianity → Great Wall of China,
  Euclid → India); no `eval/golden.json` change.
- **Finding for the narration work (ADR 0027):** the lineage wow is a *distinct flavour* from the
  improbable pair. `Naruhito ↔ Amaterasu` is well documented on Wikipedia (unexpectedness 5.88 vs
  6.62 for an unrelated node), so the co-occurrence metric correctly rates it *less* improbable — yet
  it is a far better TIL than a merely-unlinked pair. This is the ADR 0011 nuance again (the engine
  is not fooled by famous-but-documented links) and it argues that "surprising origin/lineage" wants
  its own framing rather than competing on endpoint-unexpectedness.
- Seed now **88 nodes / 123 statements** across 9 domains. Still zero-LLM, deterministic, and
  hand-reproducible; all checks green (95 tests).
