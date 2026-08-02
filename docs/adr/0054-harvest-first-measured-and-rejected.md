# ADR 0054 — Harvest-first discovery: measured and rejected (the material is not in Wikidata)

- **Status:** accepted (a negative result; no code or data change)
- **Phase:** 3

## Context

The owner raised the north-star gap directly: *"the TIL examples which I shared — which I came to
know about on my own by doing wiki rabbit-hole reading, before the inception of this project — were
the only ones which are actually worthy TILs."* A new example was offered as the target shape:
**The Lord of the Rings → oliphaunt → olifant → The Song of Roland** (Tolkien took *oliphaunt* from
Middle English ← Old French *olifaunt*, "elephant"; the **olifant** is an ivory hunting horn carved
from elephant tusk, and its first documented use as a horn is in *La Chanson de Roland*).

Measuring against that steer produced a finding that reframed the whole thread:

**Five of the six gold TILs are already the engine's top results.** `elizabeth_ii → alfred_the_great
→ house_of_wessex → odin`, `naruhito → jimmu → amaterasu → shinto`, `gutenberg → printing_press →
paper → silk_road`, `sanskrit → proto_indo_european → norse_mythology → loki`, `angkor_wat →
hinduism → rigveda → thor`. The scoring is *not* burying them. They are the TILs the owner already
knew, because the owner found them and we curated them in.

So the engine has never returned a fact nobody put there — and the architecture guarantees it. 116
nodes and 181 hand-written edges contain no latent structure, and
[ADR 0047](0047-brain-growth-stopping-rule.md) makes that a *design goal* ("a knowledgeable person
can audit the entire graph and reproduce every score"). **A graph one person can hold in their head
cannot surprise that person.** The north star ("genuinely surprising") and the craft star
("reproducible by hand") are in tension at this scale, and 53 ADRs optimised the craft star.

Two scoring fixes were prototyped first and **measured as ineffective** before this spike (recorded
here so they are not retried): an information-scaled hub-mediation penalty
(`Σ max(0, log2(degree) − 1)` over intermediates) and a per-predicate *transmission* weight
(origin-claim 1.0 / association 0.5 / containment 0.15) scaling each hop's rarity. Across
`W_HUB ∈ {0.75, 2, 4, 6}` the gold TILs kept was **5/6 → 5/6 → 4/6 → 4/6** and the hub tours still
won 2/3. Cause: the endpoint term is **57–80% of every score** (21.8–32.8 of a ~40-point total),
so both terms moved a rounding error. *Any* reweighting reorders the same 6,670 known pairs; it
cannot add one.

That left **harvest-first** — make the graph bigger than we can read — as the only option that could
surface an uncurated fact. This ADR records the spike that tested it.

## The spike (deterministic given the snapshots; QIDs resolved live)

Reference-filtered 2-hop Wikidata harvests around the owner's own example:

| seed | QID | harvest yield |
| --- | --- | --- |
| The Lord of the Rings | Q15228 | **7 nodes, 8 statements** |
| The Song of Roland | Q185427 | **7 nodes, 7 statements** |
| Olifant | Q297041 | **1 node, 0 statements** |

**No path connects LOTR to Song of Roland.** They share no node. Verified this was not a
`--max-neighbors` cap (none was passed; the default is `None`).

### Finding 1 — the harvester understands 10 properties; the items carry 56–86

| item | properties on Wikidata | understood by `WIKIDATA_PREDICATE` |
| --- | --- | --- |
| Lord of the Rings | **86** (26 with entity targets) | **2** — `P155` follows, `P941` inspired_by |
| Song of Roland | **56** | ~2 — `P361` part_of (and `P1343`, deliberately excluded) |

Ignored throughout: `P50` author, `P136` genre, `P527` has-part, **`P674` characters**, `P840`
narrative location, **`P921` main subject**, `P186` material used. For Roland, `P674 → Charlemagne`
and `P921 → Battle of Roncevaux Pass` are precisely the edges a good chain needs. The vocabulary was
tuned for geography/history material and starves on cultural material.

### Finding 2 — what *does* come back is taxonomy junk, worse than the curated graph

Five of Song of Roland's seven harvested edges are `part_of` a **category**: "Dutch literature",
"Canon of Dutch Literature (2008, DBNL)", "French literature", "medieval literature", "Matter of
France". Category membership is the classification itself, not a discovery — and it feeds
`domain_jumps` directly.

**Domain mapping fails on this material too:** **11 of the 14 harvested nodes fell to the `other`
bucket** (ADR 0032's unclassified fallback), and the only two that received a real domain received a
*wrong* one — "French literature" and "medieval literature" both mapped to `science`.

### Finding 3 — the trust gate blocks harvested journeys regardless of size

Measured on the committed `data/harvest/roman_2hop.json` snapshot (40 edges, 36 of them
`wikidata_no_ref`):

| edge source | median confidence | 1-hop | 2-hop | 3-hop |
| --- | --- | --- | --- | --- |
| curated (181 edges) | **0.938** | 0.938 ✅ | 0.879 ✅ | 0.824 ✅ |
| harvested | **0.510** | 0.510 ✅ | 0.260 ❌ | 0.133 ❌ |

The journey archetype is a fixed 3-hop chain (ADR 0021), so **every pure-harvest journey is blocked
by the `POSSIBLY_THRESHOLD = 0.50` gate.** The arithmetic on the way out, worth pinning because it
is counter-intuitive:

- one unreferenced source (0.60 × 0.85 normal rank = **0.51**) → 3-hop **0.133** ❌
- **two** corroborating unreferenced sources → 0.760 → 3-hop **0.439** ❌ *(still blocked)*
- three corroborating → 0.882 → 3-hop **0.687** ✅
- one **referenced** Wikidata statement (0.90) → 3-hop **0.729** ✅

Referenced statements were **4 of 40 = 10% yield**. A harvest-first graph needs ~10× the raw nodes
to reach a usable edge count.

### Finding 4 — the etymology itself is not in Wikidata

The oliphaunt↔olifant link is *linguistic*. `Q297041` ("Olifant") is a **Wikimedia disambiguation
page**; the instrument is `Q1335907` ("type of horn instrument made from ivory"). Wikidata models
etymology weakly, and no property chain in it expresses "Tolkien revived a Middle English word".
The fact lives in **Wikipedia prose**, which the harvester does not read.

### Scale ceilings, measured while we were there

Recorded so a future session does not re-derive them:

- **Map layout** (`compute_layout`, pure-Python O(n²), ADR 0030): 116 → 1.33s, 300 → 7.55s,
  **600 → 34.19s**. Past a usable build budget around ~600 nodes.
- **Co-occurrence sidecar** (O(n²) similarity matrix, ~17.8 bytes/pair): 116 → 0.24 MB, 1,000 →
  ~18 MB, 5,000 → ~446 MB, 10,000 → ~1.8 GB, plus one live Wikipedia full-link fetch per node.
- **Narration**: **0 of 40** harvested statements carry a `headline`, so every harvest-first card
  falls back to the mechanical predicate chain — the exact output ADR 0042 was written to replace.

## Decision

**Stop harvest-first work.** Wikidata is a structured-facts store; the TILs this product is judged by
are prose, etymology and literary-transmission facts. The spike measured a 7/7/1-node yield with no
connecting path, and the one connection the owner asked for is not modelled there at all.

Recorded as a **decision with a trigger**, in the lineage of [ADR 0014](0014-corroboration-spike.md)
(corroboration) and [ADR 0036](0036-interval-separation-measured-and-rejected.md) (interval
separation), so it is not re-litigated from scratch.

**Triggers to revisit — any one of these, not a vague "later":**

1. **A source that models derivation/etymology** — Wiktionary dumps (which encode `derived_from`
   between word forms) or Wikipedia link-plus-prose extraction. That is where this material lives.
2. **The harvest vocabulary is widened for some other reason** — then re-run these three seeds and
   re-measure before drawing any conclusion from the old numbers. The 10-property figure is the
   single biggest confound in this spike and it was *not* controlled for.
3. **A genuinely independent second source appears** (ADR 0014's standing prerequisite), which would
   lift unreferenced harvest edges over the 3-hop gate via corroboration.

## Consequences

- **No code, data, weight or golden value changed. 177 tests unchanged.** This is a record.
- **The honest cost, stated plainly:** this closes the only avenue that could surface a fact nobody
  curated. The owner chose it with that trade-off explicit. It follows that
  **the product claim needs revisiting** — README and `CLAUDE.md` currently promise "type a topic →
  get a genuinely surprising, true, well-sourced multi-hop connection", and what the system reliably
  delivers is a rigorous, fully-provenanced *presentation* of connections a human found. That
  rewrite is a separate decision and is **not** taken here.
- **The two rejected scoring terms are recorded above** with their measurements so they are not
  retried. The endpoint term's 57–80% dominance is a real design observation and remains available
  as its own (non-north-star) piece of work.
- **A new form of the ADR 0008 hazard, unfixed:** `validate-qids` accepts a QID that resolves from a
  correct label but points at a **Wikimedia disambiguation page** (`P31 = Q4167410`) — as "Olifant"
  → `Q297041` does. A curated node could silently carry a meaningless entity and every guard would
  pass. A one-line check closes it; recorded here, not built, because it is out of this ADR's scope.
- The `data/harvest/` snapshots from this spike are throwaway and were written to a scratch
  directory, not `data/harvest/`, so the committed snapshots stay the ADR 0005 ones.

## Alternatives considered

- **Widen the harvest vocabulary and re-measure (spike 2).** The strongest technical objection to
  this ADR, and deliberately left as trigger 2 rather than done: `P674`/`P921`/`P50` would certainly
  produce a bigger graph. It was declined because findings 2–4 are *independent* of vocabulary
  size — category junk, failed domain mapping, the 10% referenced yield, and the absence of
  etymology from Wikidata would all survive a wider vocabulary, and the specific TIL asked for
  still would not appear.
- **Lower the trust gate so harvested journeys surface.** Rejected outright: the gate is the "wow
  with evidence" bar and the entire trust thesis. Moving it to make weak results appear is the ADR
  0033 mistake at the rubric level.
- **Hand-build an etymology/derivation brain** (words, works, objects; edges almost all
  `derived_from`/`named_after`). Still live as a *product* option — it would deliver TILs of exactly
  the target shape — but it does not address discovery, since those TILs would also be curated.
