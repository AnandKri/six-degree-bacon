# The scoring rubric — deterministic, grounded, reproducible

Every number Six Degree Bacon shows is a deterministic function of measurable evidence. A human who
follows this document reaches the same result as the code (within floating-point rounding). No LLM is
involved. The exact constants live in [`sdb/constants.py`](../sdb/constants.py) — this file explains
them and works two examples end to end.

Two independent scores accompany every result:

- **Trust** — *is this chain true?*
- **Surprise** — *is this chain interesting?*

They are computed separately, then combined into the **wow score** that ranks results:

```
wow = surprise × trust
```

A connection wins only when it is *both* genuinely surprising *and* well-evidenced. Because trust
decays multiplicatively along a chain, the product naturally prefers tight, trustworthy paths — so
"longest *meaningful* path" becomes "longest path that stays trustworthy." By default only paths with
`trust ≥ POSSIBLY_THRESHOLD (0.50)` are surfaced (the "wow with evidence" gate); `--include-possibly`
lowers the gate to `TRUST_FLOOR (0.15)` and flags sub-threshold paths `Possibly:`.

### Two archetypes (ADR 0007)

Results come in two shapes, ranked on their own scales and surfaced together:

| Archetype | Hops | Ranking score |
|---|---|---|
| **Journey** — a fixed-length cross-domain chain | 3 | `surprise × trust` (the wow score above) |
| **Improbable pair** — a short link between entities that feel worlds apart | 1–2 | `endpoint_unexpectedness × trust` |

The improbable pair ranks by the *destination's* improbability (not the route's length or total
surprise), so an obvious one-hop neighbour never wins: e.g. "Roman Empire → Great Wall of China"
(2 hops, worlds apart) beats "Roman Empire → Latin" (directly co-occurring, low improbability).

---

## Trust

### 1. Per-source reliability

Each source has a fixed reliability from its type (`SOURCE_RELIABILITY`):

| Source type | Reliability |
|---|---|
| `wikidata_with_ref` | 0.90 |
| `secondary_book` | 0.75 |
| `wikipedia` | 0.75 |
| `wikidata_no_ref` | 0.60 |
| `dbpedia_inferred` | 0.50 |
| `open_text` | 0.40 |
| `myth_legend` | 0.30 |

For **Wikidata** sources only, reliability is multiplied by the statement-rank multiplier
(`WIKIDATA_RANK_MULTIPLIER`: preferred ×1.0, normal ×0.85, deprecated ×0.30). Non-Wikidata sources
ignore rank.

### 2. Corroboration (noisy-OR)

Independent sources combine so that more evidence never lowers confidence:

```
corroborated = 1 − ∏ (1 − reliabilityᵢ)
```

Two 0.75 sources → `1 − 0.25 × 0.25 = 0.9375`.

### 3. Entity-link quality

Multiply by `link_quality` ∈ [0, 1] — how confidently the endpoints resolved to canonical ids
(1.0 for hand-curated seed data; a fuzzy-match score for Phase-1 ingestion).

### 4. Validation penalties

Each failed deterministic validator multiplies confidence by `(1 − penalty)`:

| Validator | Penalty |
|---|---|
| A node has `start_year > end_year` | 0.50 (`PENALTY_DATE_DISORDER`) |
| `A follows B` but A predates B (by midpoint year) | 0.40 (`PENALTY_TEMPORAL_IMPLAUSIBLE`) |

### Statement confidence

```
statement_confidence = clamp01( corroborated × link_quality × ∏(1 − penaltyₖ) )
```

### Path trust (weakest-link)

```
path_trust = ∏ edge_confidence          # a chain is only as strong as its least-trusted edge
```

- `path_trust < POSSIBLY_THRESHOLD (0.50)` → dropped by default (the "wow with evidence" gate); with
  `--include-possibly` it is kept, its TIL prefixed `Possibly:` and flagged low-confidence.
- `path_trust < TRUST_FLOOR (0.15)` → never shown, even with `--include-possibly`.

### Worked example (matches `tests/test_confidence.py`)

A statement with two `0.75` sources and `link_quality = 0.8`, no validator failures:

```
corroborated = 1 − (1 − 0.75)(1 − 0.75) = 0.9375
confidence   = 0.9375 × 0.8            = 0.75
```

---

## Surprise

Computed from a path's features with documented weights:

```
surprise = W_RARITY·Σ rarity
         + W_DOMAIN·domain_jumps
         + W_REGION·region_jumps
         + W_TEMPORAL·normalized_temporal_gap
         + W_ENDPOINT·endpoint_unexpectedness
         − W_HUB·hub_penalty
```

| Term | Definition | Weight |
|---|---|---|
| `rarity` (per edge) | `−log2( count(predicate) / total_edges )` — self-information; rarer ⇒ more surprising | `W_RARITY = 1.0` |
| `domain_jumps` | Σ over **discipline**-crossing hops of `1 − P(jump \| predicate)`, the jump's unexpectedness given the predicate that made it — Laplace-smoothed with `DOMAIN_JUMP_ALPHA = 0.5` and learned from the graph (ADR 0034). Was a flat count, which paid full price for tautological crossings like `located_in → geography`. | `W_DOMAIN = 2.0` |
| `region_jumps` | Σ over **culture**-crossing hops of `1 − P(region_jump \| predicate)`, the same machinery on an independent axis (ADR 0039). `domain` is discipline, so a same-discipline chain across four civilisations (Copernicus → al-Tusi → Euclid → Jagannatha Samrat, all `science`) scores 0 domain jumps but banks its cultural surprise here. Only edges whose endpoints both carry a `Region` feed the rate; `REGION_JUMP_ALPHA = 0.5`. | `W_REGION = 2.0` |
| `normalized_temporal_gap` | `Σ |midpoint_yearₐ − midpoint_year_b| / 1000` | `W_TEMPORAL = 1.5` |
| `endpoint_unexpectedness` | `−log2 P(endpoint | start)` — an *unexpected destination* (see below) | `W_ENDPOINT = 4.0` |
| `hub_penalty` | for each **intermediate** node, `max(0, degree − 6) / 6` | `W_HUB = 0.75` |

Length is deliberately **not** rewarded: paying paths for extra hops just produced long, low-trust
rambles, and the wow score (`surprise × trust`) already prefers tight, trustworthy chains.

### Endpoint unexpectedness (rewarding unexpected *destinations*)

The other terms reward a wild *route*; this one rewards a wild *destination*, so a scenic path that
merely lands somewhere obvious (Rome → Latin) no longer wins over one that lands somewhere genuinely
far-flung. It is estimated from **real Wikipedia-link co-occurrence** — deterministic, offline, and
hand-checkable from a committed table ([`data/cooccurrence.json`](../data/cooccurrence.json)).

Define the **link strength** between two nodes as the number of link *directions* between their
English Wikipedia articles (0, 1, or 2 — one point each way an article links to the other). Direct
strength alone is coarse: on a sparse graph almost every pair sits at strength 0 and ties at the
maximum unexpectedness, which leaves the improbable-pair ranking to trust rather than to how
worlds-apart the destination really is. So we add a graded **second-order** term: two articles that
link the *same* other articles share context even if they never link each other. The **effective
strength** is

```
effective_strength(a, b) = strength(a, b) + γ · jaccard(a, b)
```

where `jaccard(a, b) = |Aₗᵢₙₖₛ ∩ Bₗᵢₙₖₛ| / |Aₗᵢₙₖₛ ∪ Bₗᵢₙₖₛ|` over the two articles' **full**
outbound link sets (committed as `similarity` in `data/cooccurrence.json`), and
`γ = COOCCURRENCE_SIMILARITY_WEIGHT = 2.0`. ADR 0025 first measured that overlap inside the
seed-sized keyhole, which starved peripheral nodes — `house_of_wessex` links only *one* seed node, so
94% of the graph tied at maximum; measuring over the whole encyclopaedia (ADR 0029) restores a graded
signal for them (every start is now fully distinct). Jaccard is bounded `[0, 1]`, so `γ = 2.0` makes a
*totally* overlapping article worth about one mutual link, while typical real overlaps (0.005–0.30)
contribute a fraction of a link direction: enough to order the unlinked pairs, not to drown the direct
signal.

Then, for a start node with `N` graph nodes and Laplace smoothing `α = COOCCURRENCE_ALPHA = 0.5`:

```
P(endpoint | start) = ( effective_strength(start, endpoint) + α ) / Σₑ ( effective_strength(start, e) + α )
endpoint_unexpectedness = −log2 P(endpoint | start)
```

A destination whose article co-occurs with the start (directly, or via shared context) is *expected*
→ low term; a genuinely isolated one is *surprising* → high term. Without co-occurrence data the term
is `0`, so the engine still runs on the seed graph alone.

#### Worked example — direct strength only (matches `tests/test_cooccurrence.py`)

A 4-node graph where only `a` and `b` are mutually linked (`strength(a,b) = 2`), and `a`, `c` share
no link *and no article overlap* (so the second-order term is 0 throughout). The denominator is
`0.5·3 + (1 out-link + 1 in-link) = 3.5`:

```
P(b | a) = (2 + 0.5) / 3.5 = 0.714  →  endpoint_unexpectedness(a→b) = −log2 0.714 = 0.49  (obvious)
P(c | a) = (0 + 0.5) / 3.5 = 0.143  →  endpoint_unexpectedness(a→c) = −log2 0.143 = 2.81  (surprising)
```

#### Worked example — second-order de-saturation (matches `tests/test_cooccurrence.py`)

A 4-node graph where `a` links `b` (`strength = 1`); `a` and `c` never link each other but their full
articles overlap (`jaccard = 0.25`); `d` shares nothing. With `γ = 2.0`:
`effective_strength(a,b) = 1`, `(a,c) = 2.0 × 0.25 = 0.5`, `(a,d) = 0`, so the denominator is
`1.5 + 1.0 + 0.5 = 3.0`:

```
P(b | a) = (1   + 0.5) / 3.0 = 0.500  →  endpoint_unexpectedness(a→b) = 1.00  (linked)
P(c | a) = (0.5 + 0.5) / 3.0 = 0.333  →  endpoint_unexpectedness(a→c) = 1.58  (shares context)
P(d | a) = (0   + 0.5) / 3.0 = 0.167  →  endpoint_unexpectedness(a→d) = 2.58  (truly isolated)
```

The shared-context node `c` now sits *between* the linked `b` and the isolated `d`, instead of
tying with `d` at the maximum — the de-saturation that lets the most worlds-apart destination win.

### Worked example (matches `tests/test_surprise.py`)

A 2-hop path whose two edges each use a predicate that occurs once in a 4-edge graph
(`rarity = −log2(1/4) = 2.0` each), crossing a domain at each step, with midpoint-year gaps
summing to 400 years, no hub intermediates, and **no co-occurrence data** (endpoint term `= 0`).

Each jump is weighted by how *unexpected* it is given its predicate (ADR 0034), not counted flat.
In this graph each of the four predicates crosses a domain on its single edge, so a jump is exactly
what that predicate always does — fully predictable, and worth little:

```
P(jump | predicate) = (jumps + α) / (edges + 2α) = (1 + 0.5) / (1 + 1) = 0.75
weight              = 1 − 0.75                                         = 0.25   (per jumping hop)

Σ rarity                = 2.0 + 2.0            = 4.0
domain_jumps            = 0.25 + 0.25          = 0.5    (a flat count would say 2)
region_jumps            = 0                    (these fixture nodes carry no region)
normalized_gap          = 400 / 1000           = 0.4
endpoint_unexpectedness = 0                    (no co-occurrence data)
hub_penalty             = 0

surprise = 1.0·4.0 + 2.0·0.5 + 2.0·0 + 1.5·0.4 + 4.0·0 − 0.75·0 = 5.6
```

Its wow score would be `surprise × trust`; e.g. at `trust = 0.75`, `wow = 5.6 × 0.75 = 4.2`.

### Region jumps — the cultural axis (worked example, ADR 0039)

`domain` is a node's *discipline*, so the `domain_jumps` term is blind to a chain that changes
*culture* without changing discipline. `region_jumps` supplies that, with the identical
`1 − P(region_jump | predicate)` machinery on a `Region` axis (macro-cultural spheres: `WESTERN`,
`NEAR_EASTERN`, `SOUTH_ASIAN`, `SINITIC`, …). The flagship case is
`Copernicus → al-Tusi → Euclid → Jagannatha Samrat` — three `influenced_by` hops, **all `science`**
(so `domain_jumps = 0`), crossing WESTERN → NEAR_EASTERN → WESTERN → SOUTH_ASIAN:

```
count the seed:  influenced_by has 39 edges with both endpoints regioned, 15 of which cross a region
P(region_jump | influenced_by) = (15 + 0.5) / (39 + 2·0.5) = 15.5 / 40 = 0.3875
region_jump_weight             = 1 − 0.3875                              = 0.6125

region_jumps = 0.6125 × 3 (all three hops cross a region) = 1.838
surprise gained = W_REGION · 1.838 = 2.0 · 1.838 = 3.68   (was 0 under domain alone)
```

The axes are near-orthogonal *per predicate*: `located_in` is a domain tautology (weight 0.06 — a
thing is nearly always located in `geography`) but region-informative (0.89 — usually its own
culture's place), so each term sees crossings the other cannot. The term is **additive** — an
unregioned graph scores exactly as before (region_jumps = 0), so nothing already scored is taxed.

On the real seed the weights separate sharply, which is the point: `located_in` crosses into
`geography` on 36 of its 38 edges, so `weight = 1 − (36+0.5)/(38+1) = 0.06` — saying *where* a thing
is always changes domain, so it is no surprise. `follows` crosses on 0 of 6, so a `follows` jump
would be genuinely informative: `weight = 1 − (0+0.5)/(6+1) = 0.93`.

---

## Why this is the design

Confidence from an LLM would not be reproducible: two runs, or two people, could not recompute it.
By deriving both scores from measurable evidence and a written rubric, anyone can audit — and
reproduce — exactly why a connection is trusted and why it is surprising. The optional Phase-3 upgrade
(fitting a *frozen* logistic/isotonic calibrator on 👍/👎 feedback) keeps this property: the mapping
stays deterministic, just better calibrated.
