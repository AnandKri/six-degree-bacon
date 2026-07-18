# ADR 0043 — Breadth: the Judaism / Abrahamic-web cluster

- **Status:** accepted
- **Phase:** 2

## Context

Breadth is the top thread now that both schema-blocker terms (ADR 0039, 0041) and the narrator decision
(ADR 0042) are closed. The most obvious gap in the seed: **Judaism** — the third Abrahamic religion —
was absent while Christianity and Islam were already hubs. Adding it (owner's pick from the candidate
list) fills the gap, ties the three Abrahamic faiths + Zoroastrian Persia + Roman Judaea into one web,
and adds Abraham/Moses genealogy-derivation chains that suit the one-fact TIL (ADR 0042). One coherent
cluster, one commit, following the recipe in memory `sdb-breadth-paused`.

## Decision

Add **9 nodes** (region `NEAR_EASTERN`, all QIDs verified label→article→wikibase_item) and **17
statements** (each with a sourced `evidence` and a `headline`):

`judaism` (Q9268), `hebrew_bible` (Q732870), `jerusalem` (Q1218), `abraham` (Q9181), `moses` (Q9077),
`second_temple` (Q728428), `king_david` (Q41370), `kingdom_of_israel` (label **United Monarchy**,
Q3185305), `talmud` (Q43290). Domains follow existing conventions (sacred text → `religion` like
Rigveda; city → `geography`; temple/kingdom/king → `history` like Angkor Wat/Maurya/Alfred; legendary
patriarch/prophet → `myth` like Romulus/Jimmu). Active periods use the peak-influence floruit rule
(ADR 0041); Abraham/Moses carry nominal legendary dates, matching the Romulus/Jimmu precedent.

**Bridges out to existing hubs (the value):** `christianity derived_from judaism`,
`christianity located_in jerusalem`, `islam claimed_descent_from abraham`,
`judaism claimed_descent_from abraham` (Abraham the shared-ancestor fan-in of two faiths),
`jerusalem part_of roman_empire` (a NEAR_EASTERN→WESTERN region jump), and the scholarly, carefully
hedged `judaism influenced_by zoroastrianism` (phrased "scholars have linked …", the Mithraism↔
Christianity precedent — never asserted as fact). The rest wire the cluster internally.

### Two details worth recording

- **`kingdom_of_israel` label = "United Monarchy" (the ADR 0008 hazard, caught by `validate-qids`).**
  The stored QID Q3185305 is correct (David's united monarchy), but the label "Kingdom of Israel"
  *resolves* to a different entity (Q6412608, the later northern kingdom). `validate-qids` flagged the
  mismatch; the fix was to relabel the node "United Monarchy" (which resolves to Q3185305) with
  "Kingdom of Israel" as an alias — not to change the QID. Verify the *label* resolves, not just that
  the QID is plausible.
- **Provenance density matched to the seed.** The cluster's factual, well-documented edges carry a
  second `secondary_book` source (Goodman *Rome and Jerusalem*; Sanders *Judaism: Practice and
  Belief*; Firestone on Abraham; Boyce *Zoroastrians*; Steinsaltz *The Essential Talmud*), lifting the
  cluster's mean statement confidence from 0.79 to **0.88** (the seed's is 0.86). Without it, an
  all-Wikipedia 3-hop journey scores `0.75³ = 0.42` and falls below the 0.50 trust gate — the cluster
  would be present but invisible in the journey archetype.

## Measurement (per the truth hierarchy — re-check flagships, re-characterise from the engine)

- **One golden winner shifted; the rest held.** `Christianity`'s top journey moved **Zhang Qian →
  Roman Republic** (`christianity → jerusalem → roman_empire → roman_republic`). This is **not** the
  ADR 0033-style hijack: it wins on rarity (9.1) and a genuinely-unexpected endpoint (`eu` 7.90 —
  Christianity's article links "Roman Empire", not the Republic), **not** on a farmed domain/region
  jump (dom 0.60, reg 0.91). The cluster in fact makes Christianity's results *more* coherent — it now
  reaches its own roots (Christianity → Judaism → Abraham → Islam is its #4; Christianity → Judaism →
  Zoroastrianism → Mithra its #2). Re-characterised in `eval/golden.json`, edges kept.
  (The Empire-vs-Republic endpoint granularity is the pre-existing "higher-fidelity endpoint
  co-occurrence" limitation the hand-over already records — not acted on here.)
- **`Roman Empire → Zen` and `Euclid → Maurya Empire` unchanged; the science lineage (Copernicus →
  al-Tusi → Euclid → Jagannatha) and the divine-descent lineages (Elizabeth II → Odin, Naruhito →
  Shinto) all held.** No true-edge deletion; no rubric change.
- **New cross-cultural TILs the cluster unlocks:** `Mansa Musa → Islam → Abraham → Judaism` (a West
  African emperor to Judaism via the shared patriarch), `Talmud ⇢ Christianity`, `Moses → Abraham →
  Islam`, `Judaism → … → Mithra`, `Jerusalem → … → Fall of Constantinople`.
- **The West-Africa bridge test (ADR 0024) was re-pointed**, not broken: Islam's *structural* tie to
  the Persia/Zoroastrian thread (the `islam → zoroastrianism` edge) is unchanged, but the Abrahamic web
  re-routed Islam's *top-N* journeys onto its newer Abraham/Judaism links, so the test now asserts the
  edge structurally rather than pinning a top-5 set (the recipe's known "pinned-property" failure mode).

## Consequences

- Seed **107 → 116 nodes / 158 → 175 statements**; all 10 curated domains still populated; every
  curated node still carries a region + active period, every statement an evidence + headline (guards
  green). `data/cooccurrence.json` rebuilt for 116 nodes.
- All green: ruff, format, mypy, **154 tests** (+1: the Abrahamic bridge test, property-style).
- Zero-LLM, deterministic, reproducible by hand. The graph now spans the full Abrahamic web; the next
  breadth candidates remain Byzantine–Ottoman and the Enlightenment.
