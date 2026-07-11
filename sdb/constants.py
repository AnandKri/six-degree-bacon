"""The deterministic scoring rubric — the single source of truth for every weight and threshold.

A human can reproduce any trust or surprise score by hand using exactly these numbers; they are
documented, with worked examples, in ``docs/confidence-rubric.md``. Nothing here depends on an LLM.
"""

from __future__ import annotations

from sdb.schema.enums import SourceType, WikidataRank

# ---------------------------------------------------------------------------
# Trust — source reliability rubric (0..1)
# ---------------------------------------------------------------------------
SOURCE_RELIABILITY: dict[SourceType, float] = {
    SourceType.WIKIDATA_WITH_REF: 0.90,
    SourceType.SECONDARY_BOOK: 0.75,
    SourceType.WIKIPEDIA: 0.75,
    SourceType.WIKIDATA_NO_REF: 0.60,
    SourceType.DBPEDIA_INFERRED: 0.50,
    SourceType.OPEN_TEXT: 0.40,
    SourceType.MYTH_LEGEND: 0.30,
}

# Wikidata statement rank refines a source's reliability multiplicatively.
WIKIDATA_RANK_MULTIPLIER: dict[WikidataRank, float] = {
    WikidataRank.PREFERRED: 1.00,
    WikidataRank.NORMAL: 0.85,
    WikidataRank.DEPRECATED: 0.30,
}

# Validation penalties. Each failed rule multiplies confidence by ``(1 - penalty)``.
PENALTY_DATE_DISORDER = 0.50  # a node has start_year > end_year
PENALTY_TEMPORAL_IMPLAUSIBLE = 0.40  # e.g. "A follows B" but A predates B

# ---------------------------------------------------------------------------
# Ranking — the "wow" score
#   wow = surprise * trust
# Results rank by this composite, so a genuinely-surprising *and* well-evidenced connection beats a
# long, flimsy one. Because trust decays multiplicatively along a chain, the product naturally
# favours tight, trustworthy paths without hard-capping hops ("longest *meaningful* path" = longest
# path that stays trustworthy).
# ---------------------------------------------------------------------------
# Default evidence gate: only paths with trust >= POSSIBLY_THRESHOLD are surfaced (a genuine "wow
# with evidence" bar). `--include-possibly` lowers the gate to TRUST_FLOOR and flags sub-threshold
# paths "Possibly:". Below TRUST_FLOOR a path is never shown.
POSSIBLY_THRESHOLD = 0.50
TRUST_FLOOR = 0.15

# ---------------------------------------------------------------------------
# Surprise — documented weights
#   surprise = W_RARITY * sum_rarity
#            + W_DOMAIN * domain_jumps
#            + W_TEMPORAL * normalized_temporal_gap
#            + W_ENDPOINT * endpoint_unexpectedness
#            - W_HUB * hub_penalty
# Length is deliberately *not* rewarded: trust (in the wow score) already prefers shorter chains.
# ---------------------------------------------------------------------------
W_RARITY = 1.0
W_DOMAIN = 2.0
W_TEMPORAL = 1.5
W_ENDPOINT = 4.0
W_HUB = 0.75

# Total temporal gap (in years) is divided by this before weighting.
TEMPORAL_NORM_YEARS = 1000.0

# Nodes with degree above this are "hubs": penalized in surprise when used as intermediates.
HUB_DEGREE_THRESHOLD = 6

# ---------------------------------------------------------------------------
# Endpoint surprise — rewards *unexpected destinations*
#   endpoint_unexpectedness = -log2 P(endpoint | start)
# P(endpoint | start) is estimated from real Wikipedia-link co-occurrence (data/cooccurrence.json):
# an endpoint whose article is linked from the start's article is an expected destination (low
# surprise); an unlinked one is surprising. COOCCURRENCE_ALPHA is Laplace smoothing on the
# conditional, and also sets the term's dynamic range — smaller alpha widens the obvious/surprising
# gap. Without co-occurrence data the term is 0 (the engine still runs on seed.json alone).
COOCCURRENCE_ALPHA = 0.5

# ---------------------------------------------------------------------------
# Traversal defaults
# ---------------------------------------------------------------------------
MIN_HOPS_DEFAULT = 3
MAX_HOPS_DEFAULT = 6  # up to six degrees
TOP_DEFAULT = 1

# The "improbable adjacency" archetype (ADR 0007) looks at *short* paths only — its wow is a
# destination that feels worlds apart yet connects directly, not distance travelled.
MIN_HOPS_UNLIKELY = 1
MAX_HOPS_UNLIKELY = 3

# ---------------------------------------------------------------------------
# Search budgets — exact-when-tractable, guided-when-explosive (ADR 0010)
# ---------------------------------------------------------------------------
# Exhaustive simple-path enumeration is exact but exponential in degree x depth. The pipeline
# enumerates exhaustively while that stays cheap and switches to a guided best-first walk only when
# a search would exceed EXACT_PATH_BUDGET candidate paths. The seed's worst case is ~189 paths, so
# the seed is always enumerated exhaustively (identical results); only large harvests go guided.
EXACT_PATH_BUDGET = 5000

# The guided walk's own bounds: how many candidate paths it may emit, and a hard cap on frontier
# expansions so even a pathological graph terminates. Guidance orders *which* paths are found under
# budget; it never changes how a found path is scored (that stays surprise x trust, reproducible).
GUIDED_CANDIDATE_BUDGET = 2000
GUIDED_EXPANSION_BUDGET = 50_000
