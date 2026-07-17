# ADR 0038 — South / Southeast Asia cluster (an Indo-European language bridge, a Hellenistic bridge, and a maritime-trade bridge)

- **Status:** accepted
- **Phase:** 2

## Context

Breadth is the project's highest-leverage lever (ADR 0014, re-confirmed by ADR 0033): a curated
cluster that *escapes* an existing cluster relieves "starved" low-degree starts and adds genuinely
worlds-apart TILs, with **zero scoring changes**. The graph already reached India (`india`,
`buddhism`, `rigveda`) and the Hellenistic east (`alexander_the_great`, `alexandria`), and the
Norse/Celtic cluster (ADR 0022) hangs off `proto_indo_european` with a Thor↔Rigveda thunder-god
cognate — but South Asia proper was thin (no Hinduism, no Sanskrit) and **Southeast Asia was absent
entirely**. Two structural gaps stood out:

- **No `sanskrit` node.** The single most valuable missing edge in the graph: Sanskrit is the
  best-attested Indo-Aryan descendant of Proto-Indo-European, so a Sanskrit node ties the whole
  Indian religious cluster to the Norse/Greek/Latin language family already anchored on
  `proto_indo_european`.
- **No maritime Asia.** The Cholas, Srivijaya and the Khmer/Angkor world are a coherent,
  richly-sourced region that connects to the graph through the *sea* route of the Silk Road and
  through Hinduism/Buddhism — a different escape edge from the overland Silk Road the graph already
  had.

## Decision

Add **9 nodes / 17 statements**, seed **98 → 107 nodes / 141 → 158 statements**.

Nodes — `religion`: Hinduism · `language`: Sanskrit · `history`: Maurya Empire, Ashoka, Chola
dynasty, Srivijaya, Khmer Empire, Angkor Wat, Borobudur.

Domains follow established seed convention rather than intuition: empires and dynasties are `history`
(matching Roman/Mali Empire and the Han/Tang dynasties), and **temples are `history`** — the mirror
of `great_pyramid_of_giza`/`great_wall_of_china`, monumental structures already in `history`, not
`art` (which the seed reserves for created artworks like the Mona Lisa).

The cluster re-enters the graph through four **independent bridges** (it stays connected even if any
one is removed):

1. **Indo-European language** — `sanskrit --derived_from--> proto_indo_european`. The cluster's best
   structural link and its best TIL family: **Sanskrit → Proto-Indo-European → Norse mythology →
   Loki**, and (via the existing thunder-god cognate) **Khmer Empire / Angkor Wat → Hinduism →
   Rigveda → Thor**. The Norse↔India bridge of ADR 0022 now reaches Southeast Asia.
2. **Hellenistic** — `maurya_empire --follows--> alexander_the_great` (Chandragupta founded the
   Maurya Empire in the wake of Alexander's withdrawal from the Indus), so **Maurya Empire →
   Alexander the Great → Alexandria → Euclid**.
3. **Maritime trade** — `chola_dynasty` / `srivijaya` / `borobudur --connected_via_trade-->
   silk_road` (the sea route through the Bay of Bengal and the Strait of Malacca), the same
   `X connected_via_trade silk_road` pattern the graph uses for `paper`, `buddhism` and
   `tang_dynasty`.
4. **Religion** — `ashoka` / `srivijaya` / `borobudur --influenced_by--> buddhism` and
   `hinduism --derived_from--> rigveda`, `khmer_empire`/`angkor_wat --influenced_by--> hinduism`, so
   the cluster ties into the existing Buddhism hub and the Vedic/Rigveda thread.

### What was deliberately *not* claimed

- **No dynastic attribution for Borobudur.** The popular Sailendra/Srivijaya attribution of the
  monument is genuinely nuanced; the graph asserts only the textbook part — Borobudur is a Mahayana
  Buddhist monument (`influenced_by buddhism`) that sat on the maritime trade routes carrying
  Buddhism to Java (`connected_via_trade silk_road`). Correctness is the north star; a tidier TIL is
  not worth a disputed edge (the same discipline as ADR 0033's declined movable-type claim).
- **No Chola raid on Srivijaya.** The 1025 naval campaign is a real, documented link between two of
  the new nodes, but the vocabulary has no conflict predicate; forcing it into `influenced_by` or
  `connected_via_trade` would misstate the relationship, so it is left out rather than mislabelled.

## Consequences

- **`history` 29 → 36, `language` 4 → 5, `religion` 9 → 10.** No curated node uses `other` (locked by
  test). All 10 curated domains remain populated.
- **No flagship hijack** (the ADR 0033 → 0034 watch). Re-checked the existing flagships after the
  cluster: **Copernicus** still tops out at `→ Nasir al-Din al-Tusi → Euclid → Jagannatha Samrat`
  (the ADR 0034 result, intact), **Gutenberg** still at `→ Printing press → Paper → Silk Road`, and
  **Newton** still reaches back across the ~2000-year lineage. The new nodes competed on merit rather
  than displacing protected lineages.
- **Two golden winners re-characterised, both legitimate — data was *not* touched to steer them.**
  Adding 17 statements shifted predicate-level rarity globally (more `connected_via_trade`,
  `influenced_by`, `located_in` edges each lower their own rarity), which re-ordered two winners:
  - **Euclid**'s terminus moved `Persia → Maurya Empire` (`Euclid → Alexandria → Alexander the Great
    → Maurya Empire`) — a genuine *improvement*: the new node is a more unexpected endpoint for Greek
    geometry than a node Euclid already reached.
  - **Roman Empire**'s top journey flipped `Qin Shi Huang → Plato` by a **hair** (38.02 vs 37.65) —
    `Roman Empire → Ancient Greece → Renaissance humanism → Plato` now edges out `→ Silk Road → Great
    Wall of China → Qin Shi Huang`. Neither path uses a new node; the flip is pure global
    re-weighting. Both are high-trust and defensible, so per the truth hierarchy `eval/golden.json`
    (a change *detector*, not a favourite-pin) is re-characterised to the engine's output, not tuned
    back. **Observation for a possible future rubric ADR, not acted on here:** Qin Shi Huang is the
    *more unexpected* endpoint (`eu` 8.09 vs Plato 7.99) yet loses on total surprise; if the endpoint
    term should weigh more heavily against a longer in-canon walk, that is a rubric change with its
    own worked example — never a data edit.
  - Christianity → Paper is unchanged.
- **The cluster's payoff is in journeys, not (yet) improbable pairs.** The new low-degree nodes'
  top *journeys* are the standout (the Indo-European and Hellenistic bridges above); their improbable
  *pairs* are more modest and several land in-cluster — the known fresh-node pattern (ADR 0033):
  a brand-new node's 1–2 hop reach is largely its own cluster until later breadth escapes it.
- All 107 QIDs verified live (`validate-qids`); **4 of 8 from-memory QID guesses were wrong** (Maurya
  Empire is Q62943, Chola dynasty Q151148, Khmer Empire Q201705, Borobudur Q42798) — the ADR 0008
  failure mode, caught by the recipe before any hallucinated QID reached the seed.
- Co-occurrence + similarity rebuilt for 107 nodes. Zero-LLM, deterministic, hand-reproducible. All
  green (ruff, format, mypy, **142 tests**).
