# ADR 0020 — Breadth: the East Asia (beyond China) cluster

- **Status:** accepted
- **Phase:** 2

## Context

The seed already reached China (Great Wall, Qin/Han, Chang'an, the Silk Road) but stopped at the
Chinese frontier: there was no Confucian thought, no post-Han dynasty, and nothing of Japan or the
East-Asian transmission of Buddhism. That left obvious surprising connections unreachable (Japan,
Confucius, Zen) and under-used three of the graph's strongest hubs — **China**, the **Silk Road**,
and **Buddhism**. The candidate was chosen over Norse/Celtic myth precisely because it ties into
*three* existing hubs rather than hanging off a single thin bridge (Proto-Indo-European), so it is
richly connected, not an island.

## Decision

Add five verified nodes — Confucius (Q4604, `science`), Confucianism (Q9581, `religion`), Tang
dynasty (Q9683, `history`), Japan (Q17, `geography`), Zen (Q7953, `religion`) — with eight sourced
statements:

- `confucius located_in china`, `confucianism derived_from confucius` — Chinese philosophy anchored
  to the China hub.
- `tang_dynasty located_in china`, `tang_dynasty connected_via_trade silk_road`,
  `tang_dynasty influenced_by confucianism` — the Tang golden age ties China, the Silk Road, and
  Confucian statecraft together.
- `japan influenced_by tang_dynasty` — Nara/Heian Japan modelled its script, capital, and
  bureaucracy on Tang China.
- `zen derived_from buddhism`, `zen located_in japan` — Zen descends from Chinese Chan Buddhism and
  became the pre-eminent Buddhist tradition of Japan.

Japan is therefore reachable by **two independent routes** — via Tang → China → Silk Road (history/
geography) and via Zen → Buddhism (religion) — so the cluster is robustly attached. QIDs verified
against Wikidata (label → Wikipedia article → `wikibase_item`); `validate-qids` (66/66) →
`build-cooccurrence` (66).

While verifying QIDs, a pre-existing stray reference was fixed: the `wd_han` source (on
`han_dynasty follows qin_dynasty`) cited `wikidata.org/wiki/Q9683`, which is **Tang dynasty**, not
Han (Q7209). The `validate-qids` guard only checks node QIDs, not reference URLs, so it never caught
it; corrected to Q7209.

## Consequences

- **Five new topics** producing genuinely cross-domain journeys and worlds-apart improbable pairs —
  e.g. `Zen → Buddhism → India → Alexander the Great → Alexandria`, `Japan → Tang dynasty → Silk
  Road → Persia`, and Christianity's new #3 journey now lands on **Japan**. Confucius's improbable
  partners (Silk Road, Japan) rank at or above his obvious neighbour, China.
- **Golden re-characterised (one flip):** at the cap-4 gate the Roman Empire winner moves from
  Rigveda to **India** — the long-standing near-tie the golden comment already flagged; the new
  edges shifted predicate rarity and nudged India ~0.23 wow ahead. Christianity → Alexander the
  Great and Euclid → Buddhism are unchanged. Recorded in `eval/golden.json`.
- Seed now **66 nodes / 93 statements** across 9 domains. Still zero-LLM, deterministic, and
  hand-reproducible; all checks green (88 tests).
