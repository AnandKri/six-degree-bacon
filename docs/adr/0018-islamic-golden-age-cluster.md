# ADR 0018 — Breadth: the Islamic Golden Age cluster

- **Status:** accepted
- **Phase:** 2

## Context

Third and final breadth increment of the planned set (after Greece 0016 and Egypt 0017). The seed's
science thread ran Greek (Euclid) → Persian (al-Tusi) → Mughal India (Jagannatha, Jai Singh), but
skipped the pivotal middle: the **Islamic Golden Age** that transmitted and extended Greek
mathematics. Adding it closes the loop Greek ↔ Islamic ↔ Indian science and gives the graph a
Baghdad anchor on the Silk Road.

## Decision

Add five verified nodes — al-Khwarizmi (Q9038), House of Wisdom (Q33018), Baghdad (Q1530), Abbasid
Caliphate (Q12536), Algebra (Q3968) — across three domains (science ×3, geography, history) with
eight sourced statements. It stitches in at three seams: `house_of_wisdom influenced_by
ancient_greece` (translated Greek learning), `al_tusi influenced_by al_khwarizmi` (into the existing
Euclid subgraph), and `baghdad on_trade_route silk_road` (into the Silk-Road web). `algebra
derived_from al_khwarizmi` adds the discipline as an endpoint. QIDs were resolved via label →
Wikipedia → `wikibase_item` (four of the ten Egypt/Islamic QIDs I first guessed were wrong).
`validate-qids` (57/57) → `build-cooccurrence` (57).

## Consequences

- **Five new topics**, e.g. the math lineage `Algebra → al-Khwarizmi → al-Tusi → Euclid →
  Jagannatha Samrat`, `House of Wisdom → Ancient Greece → Roman Empire → Silk Road → Buddhism`, and
  `Baghdad → Silk Road → Buddhism → India → Rigveda`. New worlds-apart pairs: Rome ↔ the House of
  Wisdom / Baghdad. A test locks the Greek↔Islamic↔Indian science bridge.
- **Golden re-characterised (one flip).** Baghdad's Silk-Road edge shifts global predicate rarity
  enough that Roman Empire's cap-4 winner flips India → **Rigveda** by a razor-thin ~0.04 wow (a
  deterministic near-tie, noted in the golden comment). Christianity → Alexander and Euclid →
  Buddhism are unchanged. The improbable-pair test was made property-based (the trans-Eurasian top
  tie now includes Baghdad and the House of Wisdom; the invariant is "short + far more unexpected
  than the obvious Latin neighbour", not a fixed label set).
- Seed now 57 nodes / 79 statements across 9 domains; the three planned breadth clusters are done.
  Still zero-LLM, deterministic, hand-reproducible.
