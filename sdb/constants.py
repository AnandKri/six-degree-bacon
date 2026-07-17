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
#            + W_REGION * region_jumps
#            + W_TEMPORAL * normalized_temporal_gap
#            + W_ENDPOINT * endpoint_unexpectedness
#            - W_HUB * hub_penalty
# Length is deliberately *not* rewarded: trust (in the wow score) already prefers shorter chains.
# ---------------------------------------------------------------------------
W_RARITY = 1.0
W_DOMAIN = 2.0
W_REGION = 2.0  # cultural-sphere jumps, valued on par with disciplinary jumps (ADR 0039)
W_TEMPORAL = 1.5
W_ENDPOINT = 4.0
W_HUB = 0.75

# Each domain jump is weighted by how *unexpected* it is given the predicate that made it, rather
# than counted flat (ADR 0034). A flat count double-counts predicate semantics: `located_in` crosses
# into `geography` in 94% of the seed's 34 such edges — saying where a thing is *always* changes
# domain — so a flat +1 paid W_DOMAIN for a tautology. `connected_via_trade`/`on_trade_route` are
# 100%. Meanwhile `follows` jumps 0% of the time, so a jump there is genuinely informative and was
# paid exactly the same. The result was farmable: a chain through a tight local cluster
# (Renaissance -> Florence -> House of Medici — one city, one era) banked 3 jumps of "surprise",
# beating a Polish -> Persian -> Greek -> Indian lineage that banks 0 (all four are `science`).
#
# The weight is the jump's unexpectedness under a Laplace-smoothed base rate learned from the graph
# itself, mirroring how `rarity` already derives self-information from predicate counts:
#   P(jump | predicate) = (jumps + alpha) / (edges + 2*alpha)
#   weight              = 1 - P(jump | predicate)
# Bounded [0, 1], so W_DOMAIN keeps its meaning: a *fully* unexpected jump is still worth 2.0 and no
# re-tuning was needed. An unseen predicate smooths to P = 0.5 (weight 0.5) — an honest "no idea"
# rather than a free full jump. Deterministic and hand-reproducible: count, divide, subtract.
DOMAIN_JUMP_ALPHA = 0.5

# Each *region* jump — a hop between two mutually-foreign macro-cultures (:class:`sdb.schema.enums.
# Region`) — is weighted by the same machinery on an independent axis (ADR 0039). `domain` models a
# node's *discipline*, so a Polish -> Persian -> Greek -> Indian science lineage (Copernicus ->
# al-Tusi -> Euclid -> Jagannatha Samrat) crosses **zero** domains and banks 0 domain-jump surprise
# despite spanning four civilisations. The region term supplies exactly that missing signal, and it
# is *additive* rather than a replacement: measured over the seed, 47% of jump-edges cross a domain
# but not a region (a within-culture discipline change) and 6% cross a region but not a domain (a
# same-discipline culture change), so each axis carries surprise the other cannot see (ADR 0039).
# A hop that crosses both is doubly surprising and is credited on both — W_REGION calibrates the
# magnitude. Same Laplace-smoothed, self-learned base rate as the domain term:
#   P(region_jump | predicate) = (region_jumps + alpha) / (edges + 2*alpha)
#   weight                     = 1 - P(region_jump | predicate)
REGION_JUMP_ALPHA = 0.5

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

# Second-order co-occurrence (ADR 0025, reworked by ADR 0029). Direct link strength is only 0, 1 or
# 2, so on a sparse graph most pairs sit at strength 0 and tie at the maximum unexpectedness —
# leaving the improbable-pair ranking to be decided by trust rather than by how genuinely
# worlds-apart the destination is. The fix is a graded *shared context* signal: two articles that
# link the same other articles are related even if they never link each other. The effective
# strength is
#   strength(a, b) + COOCCURRENCE_SIMILARITY_WEIGHT * jaccard(a, b)
# where `jaccard` is the overlap of the two articles' **full** outbound link sets (committed in
# data/cooccurrence.json). ADR 0025 first measured that overlap inside the seed-sized keyhole, which
# starved peripheral nodes (house_of_wessex links just one seed node, so 94% of the graph tied at
# max); measuring over the whole encyclopaedia restores a graded signal for them.
#
# Jaccard is bounded [0, 1] — unlike the old unbounded neighbour count — so the weight sets what a
# *fully* overlapping article is worth relative to a direct link direction. 2.0 makes complete
# overlap comparable to a mutual link, and typical real overlaps (0.05-0.30) contribute a fraction
# of one link direction: enough to order the unlinked pairs, without drowning the direct signal.
COOCCURRENCE_SIMILARITY_WEIGHT = 2.0

# ---------------------------------------------------------------------------
# Traversal defaults
# ---------------------------------------------------------------------------
MIN_HOPS_DEFAULT = 3
# Default journey range. With MIN=MAX=3 the journey is a fixed-length 3-hop chain: long enough to
# cross a couple of domains and read as a genuine "journey", but tight enough to stay punchy and
# well-evidenced (trust decays multiplicatively, so 4-hop chains rambled for little extra surprise;
# ADR 0021). Users can still request deeper chains per query via `--max-hops` (the engine supports
# the full "six degrees").
MAX_HOPS_DEFAULT = 3
TOP_DEFAULT = 1

# The "improbable adjacency" archetype (ADR 0007) looks at *short* paths only — its wow is a
# destination that feels worlds apart yet connects directly, not distance travelled.
#
# The cap is 2, not 3, so the ranges are **disjoint by construction**: the journey is exactly [3, 3]
# and the pair is [1, 2], which makes it impossible for the two archetypes to select the same path.
# At 3 they overlapped and collided on real topics (Roman Empire and Christianity both surfaced the
# identical chain under both labels — the same TIL twice), defeating ADR 0007's premise that these
# are two different kinds of delight. 1-2 hops is also truer to "improbable *adjacency*": a thin,
# short link. See ADR 0027.
MIN_HOPS_UNLIKELY = 1
MAX_HOPS_UNLIKELY = 2

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
