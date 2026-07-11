# ADR 0017 — Breadth: the Ancient Egypt cluster

- **Status:** accepted
- **Phase:** 2

## Context

Second breadth increment (after Ancient Greece, ADR 0016). Egypt is a natural addition: it hangs off
the existing Alexandria node (the Ptolemaic capital), gives the Roman thread a southern anchor
(Egypt was annexed as a province), and adds instantly-recognisable topics (Cleopatra, the pyramids,
the Nile, hieroglyphs).

## Decision

Add five verified nodes — Ancient Egypt (Q11768), Cleopatra (Q635), Nile (Q3392), Great Pyramid of
Giza (Q37200), Egyptian hieroglyphs (Q132659) — across four domains (history ×3, geography, language)
with seven sourced statements, stitched in at two seams: `cleopatra located_in alexandria` (into the
Hellenistic/Greek web) and `ancient_egypt part_of roman_empire` (the province of Aegyptus). The Nile,
the Great Pyramid, hieroglyphs, and Cleopatra all attach to Ancient Egypt.

Four of the five QIDs I first guessed were wrong (Q42237 = a fish family, etc.); all were re-resolved
via label → Wikipedia article → `wikibase_item` and confirmed before use (ADR 0008 discipline).
`validate-qids` (52/52) → `build-cooccurrence` (52 nodes).

**Tooling bug fixed en route.** Crossing 50 nodes exposed a latent bug in the co-occurrence harvester:
`outbound_links` sent every candidate title in one `pltitles`, but MediaWiki caps `pltitles` at 50 —
so at 52 nodes the API silently returned *no* links and `build-cooccurrence` wrote an empty matrix
(disabling the endpoint-surprise term). Fixed to chunk candidates by 50 and union the results
(`sdb/harvest/cooccurrence.py`).

## Consequences

- **Five new well-connected topics.** e.g. `Cleopatra → Alexandria → Alexander → India → Buddhism`
  (trust 0.77) and `Ancient Egypt → Roman Empire → Silk Road → Buddhism → India`; improbable pairs
  Cleopatra ↔ Aristotle/India, Ancient Egypt ↔ Mithraism. A test locks that Egyptian topics aren't an
  island.
- **Golden winners unchanged** at the cap-4 gate (Roman Empire → India, Christianity → Alexander,
  Euclid → Buddhism); no `eval/golden.json` change.
- The co-occurrence fix unblocks all future seed growth past 50 nodes — necessary for the remaining
  breadth work. Still zero-LLM, deterministic, hand-reproducible.
