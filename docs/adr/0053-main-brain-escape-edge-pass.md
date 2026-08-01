# ADR 0053 — Main brain: an escape-edge tissue pass, and the stop signal for its starved starts

- **Status:** accepted
- **Phase:** 3

## Context

[ADR 0047](0047-brain-growth-stopping-rule.md) replaced "add more nodes" with a measured
grow-vs-stop rule, and [ADR 0051](0051-connectivity-sweep-tool.md) made its instrument a committed
command (`sdb sweep`). The full cycle has since run twice — but only on the **20th-century** brain
([0049](0049-twentieth-century-pendant-bridging.md) edges, [0050](0050-twentieth-century-node-pass-parity.md)
nodes), which it took to parity and then stopped.

The **main** brain has never had the cycle run against it. Its starved starts have been tracked in
`docs/HANDOVER.md` §5 as prose since ADR 0033 (the trend line `16/88 → 15/98 → 12/116`), with the
diagnosis already written down and never acted on: *"the fix is breadth — specifically edges that
**escape** a cluster, not nodes beside it."* Running the committed sweep confirms it:

| Metric | Main brain (before) |
| --- | --- |
| Good non-obvious top pair | **100/116 (86.2%)** |
| Truly starved (no non-obvious pair exists) | **12/116** |
| Median journey `domain_jumps` | 0.537 |
| Median journey `region_jumps` | 0.622 |
| **Median journey (domain+region)** | **1.165** |

The 12: `julius_caesar`, `augustus`, `china`, `aeneas`, `trojan_war`, `troy`, `romance_languages`,
`nile`, `mali_empire`, `jimmu`, `mona_lisa`, `hebrew_bible`. Seven are degree-1/2 pendants
(`troy`, `nile`, `romance_languages`, `mona_lisa` each hang off a **single** edge into their own
cluster), which is ADR 0049's finding in the older graph: *no islands ≠ no pendants*.

## Decision

**Six sourced escape edges between *existing* nodes — no new nodes, no new QIDs — each giving a
flagged start a route out of its own cluster, biased to cross a discipline or a culture.**

| edge | crossing |
| --- | --- |
| `nile mentioned_in hebrew_bible` | geography ↔ religion, EGYPTIAN ↔ NEAR_EASTERN |
| `romance_languages influenced_by christianity` | language ↔ religion, WESTERN ↔ NEAR_EASTERN |
| `florence connected_via_trade trans_saharan_trade` | geography ↔ trade, WESTERN ↔ WEST_AFRICAN |
| `julio_claudian_dynasty claimed_descent_from aeneas` | genealogy ↔ myth (WESTERN) |
| `aeneas located_in troy` | myth ↔ geography (WESTERN) |
| `mona_lisa part_of renaissance` | art ↔ culture (WESTERN) |

Three cross **both** axes; the other three buy reach for a pendant that had none. Each carries a
one-sentence `evidence`, a curated `headline` and ≥ 2 sources, exactly like every curated statement
since ADR 0037/0042.

**Co-occurrence was *not* rebuilt** — the endpoint-surprise matrix keys on *nodes* (each article's
outbound Wikipedia links), and no node changed. Same reasoning as ADR 0049, re-confirmed here.

### Sources were verified against the *claim*, not just the article

Two of the six were drafted with a plausible-looking citation that does not actually carry the
claim, and checking each source against its sentence caught both:

- `julio_claudian_dynasty → aeneas` cited the **Julio-Claudian dynasty** article, which never
  mentions the descent claim. The **Aeneas** article states it outright ("The Julian family of Rome,
  most notably Julius Cæsar and Augustus, traced their lineage to Ascanius and Aeneas, thus to the
  goddess Venus"). Re-sourced.
- `florence → trans_saharan_trade` cited the **Trans-Saharan trade** article for West African gold
  reaching Europe; that article stops at the Mediterranean ports and mentions no European buyer. The
  claim is carried by **Mansa Musa** ("two thirds of the gold circulating in the Medieval
  Mediterranean came from West Africa") and **Florin (Italian coin)** ("most of the gold used in
  Europe came from Africa"). Re-sourced and the evidence reworded to those two clauses.

This is the [ADR 0008](0008-seed-qid-repair.md) hazard one level up: a *verified node* can still
carry an *unverified claim*. The QID guard cannot see it — only reading the source can.

## Measurement (after)

| Metric | before → after |
| --- | --- |
| **Good non-obvious top pair** | **100/116 (86.2%) → 107/116 (92.2%)** |
| **Truly starved** | **12 → 5** |
| Median journey `domain_jumps` | 0.537 → 0.524 |
| Median journey `region_jumps` | 0.622 → 0.607 |
| Median journey (domain+region) | 1.165 → 1.115 |

Seven starts left the starved set: `nile`, `hebrew_bible`, `romance_languages`, `mali_empire`,
`troy`, `aeneas`, `mona_lisa`. Leave-one-out confirms **every** edge pays for itself on metric 1 —
dropping any one costs 1–2 good pairs, and `aeneas → troy` only pays *in combination* with
`julio_claudian_dynasty → aeneas` (together they are Troy's whole escape route):

| dropped edge | good pairs | starved |
| --- | --- | --- |
| — (all six) | 107 | 5 |
| `nile → hebrew_bible` | 105 | 7 |
| `julio_claudian_dynasty → aeneas` | 105 | 7 |
| `romance_languages → christianity` | 106 | 6 |
| `florence → trans_saharan_trade` | 106 | 6 |
| `aeneas → troy` | 106 | 6 |
| `mona_lisa → renaissance` | 106 | 6 |

**Metric 2 dips ~4%, and that is the rubric working, not a loss.** ADR 0034 prices a domain jump at
`1 − P(jump | predicate)`, so *every* edge that crosses a domain makes each future crossing by that
predicate worth slightly less. Adding six crossings therefore lowers the per-jump price graph-wide;
the median over top journeys reads lower while the graph's actual reach improved. This is the same
"global rarity re-weighting" ADR 0038 recorded when its cluster flipped two winners hair's-breadth
apart. Metric 2 is a *dilution-sensitive* measure, and it is worth having that written down before a
future session reads a dip as damage.

New winners the pass produced (re-characterised from the engine, never pinned): `Florence →
Trans-Saharan trade → Timbuktu → Mansa Musa` (37.54) displaces ADR 0041's Florence walking-tour, and
`Copernicus → Renaissance → Florence → Trans-Saharan trade` enters Copernicus's top 3 without
disturbing the al-Tusi flagship at #1.

### One golden case re-characterised

`Christianity`'s top journey shifts **Roman Republic → Proto-Indo-European** (`christianity →
romance_languages → latin → proto_indo_european`, 44.83 vs the Roman Republic route's 39.01),
reached through the new Church-Latin hop: the route crosses NEAR_EASTERN → WESTERN → CENTRAL_ASIAN
and lands on a Bronze-Age proto-language, so it is the ADR 0039 region term firing on real
crossings, not a farmed walking tour. `Roman Empire → Zen` and `Euclid → Maurya Empire` are
unchanged; `Copernicus → Jagannatha Samrat`, `Elizabeth II → Odin` and `Naruhito → Shinto` hold.

### A site test that asserted more than the rubric promises

`test_strict_is_confident_and_loose_is_a_superset` asserted that lowering the trust gate never
displaces a confident result. Nothing in the rubric promises that: both lists are the **top-N of the
same ranking key** over a widening candidate set, so a higher-scoring speculative path can take a
slot. The pass falsified it exactly where the test's own docstring said it had been fragile before —
`troy`, which gained its *first* confident journeys here (`troy → aeneas → julio_claudian_dynasty →
roman_empire`, trust 0.510) while its speculative `troy → trojan_war → aeneas →
julio_claudian_dynasty` (19.76, trust 0.464) outscores them.

Renamed to `test_strict_is_confident_and_loose_only_ever_outranks` and rewritten to assert the
invariant that *is* claimed: a confident card leaves the top-N only when every card that replaced it
scores at least as high. That is a **stronger** check than the old subset one — it would still catch
a gate that dropped results outright.

## Consequences

- `data/seed.json`: **116 nodes / 175 → 181 statements**. No new nodes, no new QIDs; `validate-qids`
  re-run clean (116/116). The 20th-century brain is untouched (per-brain scoring).
- **177 tests**, ruff/format/mypy green. A structural value-lock
  (`test_main_brain_escape_edges_relieve_the_starved_pendants`) asserts the six edges exist, that
  each crosses a domain or a region, and that the seven relieved starts now surface a genuinely
  non-obvious improbable pair — property-based, never a pinned endpoint.
- **The honest boundary: 5 starved starts remain, and edges cannot fix them.** They split in two,
  and neither half is a defect:
  - **Hub articles** — `china` co-occurs with **28.7%** of the graph, `augustus` 20.9%,
    `julius_caesar` 20.0%, against a graph-wide median of **13.0%**. Their Wikipedia articles link so
    much that *every* destination within 1–2 hops is one they already mention. No edge changes that;
    only a distant new cluster could, and their articles would likely link that too.
  - **Tight mythic pendants** — `trojan_war` and `jimmu` sit inside closed lineages
    (Homer/Aeneas/Greek myth; Amaterasu/Naruhito) where every honest edge out lands on something
    they already co-occur with. Forcing one would be the ADR 0034 mistake in miniature.
- **Per ADR 0047, this is the main brain's stop signal for connectivity work.** The edge lever is
  now exhausted: the starts it can fix are fixed, and the remainder are structural. Future main-brain
  growth is a *product* choice (a cluster someone wants to see), not a connectivity need — and the
  0047 soft ceiling (~150–200 nodes) and walking-tour caution still govern it. Both brains have now
  run the full cycle and both say stop; the next graph is a **new brain**, not a bigger one.
- Zero-LLM, deterministic, hand-reproducible. No weight, constant, or threshold changed — only the
  graph grew tissue, and one golden value was re-characterised from the engine with the reason
  recorded in `eval/golden.json`.

## Alternatives considered

- **Add a cluster (Byzantine–Ottoman) instead.** Rejected for *this* purpose: it adds mass beside
  the existing Western/Near-Eastern clusters and would not touch a single one of the 12 starved
  starts, which is precisely the failure mode ADR 0047 exists to prevent. It remains available as a
  product choice.
- **Fix the pair archetype instead of the graph** (exclude directly-co-occurring destinations, or
  floor the pair's endpoint-unexpectedness). Rejected, as measured in HANDOVER §5: on the starved
  starts it returns *nothing at all*, trading a mediocre TIL for an empty result. The root cause was
  never scoring — it was reach, and reach is what this pass bought.
- **Drop `aeneas → troy`, whose solo contribution is zero.** Rejected: it is true, sourced, and the
  leave-one-out shows it is half of Troy's escape route. Selecting edges by their solo number rather
  than their truth is how a graph starts serving its metrics.
