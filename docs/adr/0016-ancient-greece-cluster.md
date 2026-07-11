# ADR 0016 — Breadth: the Ancient Greece cluster

- **Status:** accepted
- **Phase:** 2

## Context

The seed leaned Roman/Mediterranean + a China thread + a Persia/India/science thread. The single
highest-leverage gap was **Ancient Greece** — the natural hub between myth, Rome, Alexander, and
science (Aristotle tutored Alexander; Homer chronicled the Trojan War; Rome's culture derives from
Greece; Greek mathematics underlies Euclid). This is the first increment of the breadth programme:
add coherent, *well-connected* clusters (never isolated islands), one per commit, each fully
verified and sourced.

## Decision

Add six verified nodes — Ancient Greece (Q11772), Athens (Q1524), Aristotle (Q868), Plato (Q859),
Homer (Q6691), Greek mythology (Q34726) — spanning five domains (history, geography, science ×2, art,
myth), with ten sourced statements that stitch the cluster into the existing graph at three seams:

- **Greece ↔ Alexander/East:** `alexander_the_great influenced_by aristotle` (Aristotle tutored
  Alexander) — routes Greek philosophy into the Silk-Road/India/Buddhism web.
- **Greece ↔ Rome:** `roman_empire influenced_by ancient_greece`.
- **Greece ↔ myth:** `trojan_war part_of greek_mythology`, `trojan_war mentioned_in homer`,
  plus internal links (`aristotle influenced_by plato`, both `located_in athens`, `athens`/`homer`/
  `greek_mythology` into `ancient_greece`).

Every QID verified against Wikidata; every statement Wikipedia- (and, for the load-bearing ones,
secondary-book-) sourced. Ran `validate-qids` (47/47) → `build-cooccurrence` (47 nodes).

## Consequences

- **Six new well-connected topics.** Aristotle, Plato, Homer, Athens, Ancient Greece, and Greek
  mythology now return rich results, e.g. `Aristotle → Alexander → India → Buddhism → Silk Road`
  (trust 0.77) and `Homer → Ancient Greece → Roman Empire → Silk Road → Persia`. New worlds-apart
  improbable pairs: Aristotle ↔ Buddhism/India, Homer ↔ Roman Empire/China, Plato ↔ Silk Road.
- **Golden winners unchanged.** At the default cap-4 gate the flagship winners (Roman Empire → India,
  Christianity → Alexander, Euclid → Buddhism) are unaffected — the cluster adds reach without
  destabilising the tuned core, so `eval/golden.json` needs no change. The planted-path test now
  spans all reachable endpoints (seed growth pushed the deep Great Wall chain to rank 21; it's still
  discoverable at 6 hops). A new test locks Aristotle's philosophy-to-the-East reach.
- Still zero-LLM, deterministic, hand-reproducible. Next breadth increments (deferred): Ancient Egypt
  (Cleopatra ↔ Rome), the Islamic Golden Age (al-Khwarizmi ↔ Euclid/al-Tusi).
