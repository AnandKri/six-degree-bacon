# ADR 0023 — Breadth: the Chinese technology (Four Great Inventions) cluster

- **Status:** accepted
- **Phase:** 2

## Context

The seed's China/East-Asia coverage was political and religious (dynasties, the Silk Road,
Confucianism, Buddhism, Zen) but had no technology. China's **Four Great Inventions** — papermaking,
woodblock printing, gunpowder, and the compass — are among the most consequential and widely-known
in world history, and each attaches directly to hubs the graph already has (Han dynasty, Tang
dynasty, the Silk Road, Buddhism), so the cluster is well-connected rather than an island. It also
adds first-class technology topics that people actually search for.

## Decision

Add five verified nodes — Paper (Q11472, `science`), Cai Lun (Q229235, `history`), Woodblock
printing (Q1261053, `science`), Gunpowder (Q12861, `science`), Compass (Q34735, `science`) — with
seven sourced statements:

- `cai_lun part_of han_dynasty`, `paper influenced_by cai_lun`, `paper connected_via_trade
  silk_road` — papermaking from its Han-court origin out along the Silk Road.
- `woodblock_printing influenced_by tang_dynasty`, `woodblock_printing influenced_by buddhism` —
  printing developed in Tang China and driven by Buddhist demand for scriptures (the earliest dated
  printed book is the Buddhist Diamond Sutra, 868).
- `gunpowder influenced_by tang_dynasty`, `compass influenced_by han_dynasty` — the other two
  inventions anchored to their dynasties.

QIDs verified against Wikidata (label → Wikipedia article → `wikibase_item`); `validate-qids`
(76/76) → `build-cooccurrence` (76).

## Consequences

- **Five new technology topics** with cross-domain reach — e.g. `Paper → Silk Road → Buddhism →
  India`, `Woodblock printing → Buddhism → India → Alexander the Great`, `Gunpowder → Tang dynasty →
  Silk Road → Persia`. Woodblock printing's top improbable pair is the **Buddhism** hub it descends
  from (worlds apart from a printing technique, one hop away). A property-based test locks that the
  inventions reach beyond the China/tech neighbourhood via the Silk Road and Buddhism.
- **Golden re-characterised (one flip):** the Christianity winner moves from Great Wall of China to
  **Paper** (`Christianity → Roman Empire → Silk Road → Paper`) — the new `paper connected_via_trade
  silk_road` edge is a slightly more surprising Silk-Road terminus, ~0.5 wow ahead. Roman Empire →
  India and Euclid → India are unchanged. Recorded in `eval/golden.json`.
- Seed now **76 nodes / 107 statements** across 9 domains. Still zero-LLM, deterministic, and
  hand-reproducible; all checks green (90 tests).
