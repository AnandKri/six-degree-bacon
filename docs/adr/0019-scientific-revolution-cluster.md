# ADR 0019 — Breadth: the Scientific Revolution cluster

- **Status:** accepted
- **Phase:** 2

## Context

The seed's science thread reached the Islamic Golden Age (ADR 0018) but stopped before the early
modern era. Extending it to Ptolemy → Copernicus → Galileo → Newton closes a striking **2000-year
lineage** — exactly the kind of true-but-surprising cross-time connection the project exists to
surface — and ties directly into existing nodes (Alexandria, al-Tusi, Euclid), so it is not an
island.

## Decision

Add four verified nodes — Ptolemy (Q34943), Nicolaus Copernicus (Q619), Galileo Galilei (Q307),
Isaac Newton (Q935), all `science` — with six sourced statements: `ptolemy located_in alexandria`
(into the Alexandria/Greek cluster), `copernicus influenced_by ptolemy`, `copernicus influenced_by
al_tusi` (the *Tusi couple* — a documented geometric device in Copernicus's models; the evidence
states the mathematical fact, not a claim of direct transmission), `galileo influenced_by
copernicus`, `isaac_newton influenced_by galileo`, and `isaac_newton influenced_by euclid` (the
Principia's Euclidean geometric style). QIDs verified against Wikidata; `validate-qids` (61/61) →
`build-cooccurrence` (61).

## Consequences

- **Four new topics** on a long lineage, e.g. `Isaac Newton → Euclid → Alexandria → Alexander →
  India` and `Nicolaus Copernicus → al-Tusi → Euclid → Alexandria → Alexander`; improbable pairs
  Newton ↔ al-Tusi, Copernicus ↔ al-Khwarizmi, Galileo ↔ Ptolemy. A test locks that Newton reaches
  Euclid and Copernicus reaches al-Tusi.
- **Golden winners unchanged** at the cap-4 gate (Roman Empire → Rigveda, Christianity → Alexander,
  Euclid → Buddhism); no `eval/golden.json` change.
- Seed now 61 nodes / 85 statements across 9 domains. Still zero-LLM, deterministic, hand-reproducible.
