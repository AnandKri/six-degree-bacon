# The scoring rubric — deterministic, grounded, reproducible

Every number Six Degree Bacon shows is a deterministic function of measurable evidence. A human who
follows this document reaches the same result as the code (within floating-point rounding). No LLM is
involved. The exact constants live in [`sdb/constants.py`](../sdb/constants.py) — this file explains
them and works two examples end to end.

Two independent scores accompany every result:

- **Trust** — *is this chain true?*
- **Surprise** — *is this chain interesting?*

They are deliberately separate: results are ranked by **surprise**, with **trust** as a tie-break and
a hard floor.

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

- `path_trust < TRUST_FLOOR (0.15)` → the path is dropped.
- `path_trust < POSSIBLY_THRESHOLD (0.50)` → the TIL is prefixed `Possibly:` and flagged low-confidence.

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
         + W_TEMPORAL·normalized_temporal_gap
         + W_LENGTH·length_bonus
         − W_HUB·hub_penalty
```

| Term | Definition | Weight |
|---|---|---|
| `rarity` (per edge) | `−log2( count(predicate) / total_edges )` — self-information; rarer ⇒ more surprising | `W_RARITY = 1.0` |
| `domain_jumps` | number of consecutive nodes whose `domain` differs | `W_DOMAIN = 2.0` |
| `normalized_temporal_gap` | `Σ |midpoint_yearₐ − midpoint_year_b| / 1000` | `W_TEMPORAL = 1.5` |
| `length_bonus` | `max(0, hops − 2)` | `W_LENGTH = 0.5` |
| `hub_penalty` | for each **intermediate** node, `max(0, degree − 6) / 6` | `W_HUB = 0.75` |

### Worked example (matches `tests/test_surprise.py`)

A 2-hop path whose two edges each use a predicate that occurs once in a 4-edge graph
(`rarity = −log2(1/4) = 2.0` each), crossing a domain at each step (2 jumps), with midpoint-year gaps
summing to 400 years, no hub intermediates:

```
Σ rarity            = 2.0 + 2.0            = 4.0
domain_jumps        = 2
normalized_gap      = 400 / 1000          = 0.4
length_bonus        = max(0, 2 − 2)       = 0
hub_penalty         = 0

surprise = 1.0·4.0 + 2.0·2 + 1.5·0.4 + 0.5·0 − 0.75·0 = 8.6
```

---

## Why this is the design

Confidence from an LLM would not be reproducible: two runs, or two people, could not recompute it.
By deriving both scores from measurable evidence and a written rubric, anyone can audit — and
reproduce — exactly why a connection is trusted and why it is surprising. The optional Phase-3 upgrade
(fitting a *frozen* logistic/isotonic calibrator on 👍/👎 feedback) keeps this property: the mapping
stays deterministic, just better calibrated.
