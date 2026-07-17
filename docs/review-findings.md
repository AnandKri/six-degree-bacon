# Review findings — independent read-only review

> **HISTORICAL — all findings resolved. Nothing here is open; do not re-fix.**
> Kept because [ADR 0029](adr/0029-full-link-jaccard-similarity.md) cites Finding 2 by path as its
> motivation. This is a snapshot of `b11a679`, not live state — its code, constants and counts are
> all superseded.
>
> | # | Finding | Resolved by |
> |---|---|---|
> | 1 | Archetypes can return the identical path | [ADR 0027](adr/0027-disjoint-archetype-hop-ranges.md) — `MAX_HOPS_UNLIKELY` 3→2, exactly the fix proposed below |
> | 2 | Endpoint saturation for sparse starts | [ADR 0029](adr/0029-full-link-jaccard-similarity.md) — full-link Jaccard; max tie-fraction 94%→1.1%. Took option (2), the "richer signal" recommendation |
> | 3 | Cross-archetype scores not comparable | Open by choice — cosmetic; the raw numbers are still archetype-relative |
>
> Two of its assumptions have since been overtaken outright: the seed is now 98 nodes / 141
> statements (not 88/124), and `domain_jumps` is no longer a flat count ([ADR 0034](adr/0034-domain-jump-information.md)).

- **Reviewed at:** `b11a679` (ADR 0025) plus the uncommitted seed growth in the working tree
  (88 nodes / 124 statements at review time).
- **Scope:** read-only. **No files were changed**; nothing was committed. Findings only.
- **Method:** ran the gate, exercised the CLI across topics, and verified the scoring math
  numerically rather than by reading alone.

## Summary

| # | Finding | Severity | Fix cost |
|---|---|---|---|
| 1 | The two archetypes can return the **identical path** | Defect (user-visible, hits the flagship demo) | One constant |
| 2 | Endpoint saturation **persists for sparsely-linked starts** | Scoring quality | Medium |
| 3 | Cross-archetype `score` values are not comparable | Minor UX | Small |

## Verified correct — no action needed

Recorded so these are not re-litigated:

- **Gate green:** ruff, ruff-format, mypy, **94 tests pass**.
- **ADR 0025 (second-order co-occurrence) is mathematically sound.** The central claim — that the
  conditional remains a proper distribution after adding the shared-neighbour term — holds
  empirically: `Σₑ P(e | start) = 1.000000` for `roman_empire`, `confucius`, `buddhism`,
  `mansa_musa`. There are **zero** negative surprisals across all node pairs (so `P ≤ 1` always).
  `−log2 P` therefore remains a valid self-information, and the term is still hand-reproducible.
- **De-saturation is real** for well-connected starts: `roman_empire` now has 25 distinct
  unexpectedness values with only 5 tied at the maximum.
- **Product quality:** results are confident, not speculative (trust 0.82–0.94, no `Possibly:`) —
  e.g. `Roman Empire → Silk Road → Great Wall of China → Qin Shi Huang` (0.86),
  `Buddhism → India → Rigveda → Thor` (0.82), `Isaac Newton → Euclid → al-Tusi → al-Khwarizmi` (0.82).

---

## Finding 1 — the two archetypes can return the identical path (defect)

**Evidence.** Comparing the top *journey* and top *unlikely* result per topic (2 of 5 sampled
duplicate exactly):

| Topic | Result |
|---|---|
| Roman Empire | **DUPLICATE** — both return `Roman Empire → Silk Road → Great Wall of China → Qin Shi Huang` (3 hops) |
| Great Wall of China | **DUPLICATE** |
| Silk Road | distinct |
| Islam | distinct |
| Cleopatra | distinct |

**Root cause.** The candidate ranges overlap, and nothing de-duplicates across archetypes:

```python
MIN_HOPS_DEFAULT  = 3
MAX_HOPS_DEFAULT  = 3   # journey: fixed 3 hops (ADR 0021)
MIN_HOPS_UNLIKELY = 1
MAX_HOPS_UNLIKELY = 3   # fully CONTAINS the journey's [3, 3]
```

When a topic's most-improbable-endpoint pair happens to be 3 hops, both archetypes legitimately
select the same path. The user then sees **the same TIL twice under two labels**, which undermines
ADR 0007's premise that these are two different kinds of delight — and it lands on "Roman Empire",
the headline demo.

**Recommended fix (Occam).** Make the ranges disjoint by construction:

```python
MAX_HOPS_UNLIKELY = 2   # journey [3,3] and unlikely [1,2] can no longer collide
```

This needs no dedupe logic, and it *sharpens* the archetype's meaning — an "improbable **adjacency**"
should be short (ADR 0007 describes it as a 1–3 hop *thin* link; 1–2 is truer to the intent).

**Alternative** (if 3-hop pairs are worth keeping): exclude the journey's chosen path — or its
endpoint — from the unlikely candidate set. More code; keeps the wider range.

**Suggested regression test** (`tests/test_pipeline.py`):

```python
def test_archetypes_never_return_the_same_path(seed_graph: KnowledgeGraph) -> None:
    # The two archetypes are different delights (ADR 0007); surfacing one path twice is a bug.
    for topic in ["Roman Empire", "Great Wall of China", "Buddhism", "Silk Road"]:
        journey = discover(seed_graph, topic, archetype=Archetype.JOURNEY, top=1)
        unlikely = discover(seed_graph, topic, archetype=Archetype.UNLIKELY, top=1)
        if journey and unlikely:
            assert journey[0].path.node_ids != unlikely[0].path.node_ids, topic
```

**Blast radius.** The journey range is untouched, so `eval/golden.json` journey winners should not
move. The *unlikely* examples cited in ADR 0007 / 0025 consequences may shift — re-characterise and
note it.

---

## Finding 2 — endpoint saturation persists for sparsely-linked starts (scoring quality)

**Evidence.** Distinct `endpoint_unexpectedness` values over the other 87 nodes:

| Start | Distinct values | Tied at maximum |
|---|---|---|
| `roman_empire` | 25 | 5 |
| `confucius` | 11 | **30** |

ADR 0025 de-saturated **hub** starts, but the **periphery still ties**: from Confucius, roughly a
third of the graph is indistinguishable at maximum unexpectedness. For those topics the
improbable-pair ranking is decided largely by **trust** — precisely the failure ADR 0025 set out to
fix, now narrowed rather than removed.

**Root cause.** Co-occurrence **data sparsity**, not the formula. A node whose article co-occurs with
few seed nodes also shares few *neighbours* with anything, so `effective_strength ≈ 0` against most
of the graph and the smoothed conditional flattens. This gets **worse as breadth work adds more
peripheral nodes** — each new cluster starts life sparse.

**Options** (increasing cost):

1. **Tune `γ` / add a decayed third-order term.** Cheap, but stacking hand-tuned constants has
   diminishing returns and risks overfitting the seed.
2. **Richer co-occurrence signal behind the existing `WikipediaClient` seam** — ADR 0003 explicitly
   anticipated this. Use link *counts* (or backlink/full-text corpora) instead of a 0/1/2 direction
   count, giving a genuinely graded strength. **Highest durable value; the seam already exists.**
3. **Deterministic tiebreak when the term saturates** — when endpoints tie at max, fall back to
   domain/temporal distance. Cheap interim that stops *trust* silently deciding the ranking.

**Recommendation:** (2) as the real fix, with (3) as a cheap interim.

**Suggested canary** — a property test that the max-tie fraction stays bounded as the seed grows, so
this regression is caught rather than rediscovered:

```python
def test_endpoint_term_does_not_saturate(seed_graph: KnowledgeGraph) -> None:
    ids = [n.id for n in seed_graph.nodes()]
    for start in ["roman_empire", "confucius"]:
        vals = [round(seed_graph.endpoint_unexpectedness(start, e), 6) for e in ids if e != start]
        assert vals.count(max(vals)) <= 0.15 * len(vals), start  # tighten as the signal improves
```

---

## Finding 3 — cross-archetype scores are not comparable (minor UX)

For the same path, `journey.score ≈ 41.7` but `unlikely.score ≈ 6.9`, because they are different
quantities (`surprise × trust` vs `endpoint_unexpectedness × trust`). Presenting both raw in one view
invites a false comparison ("the journey is 6× better"). Consider labelling them distinctly (e.g.
*wow* vs *improbability*) or omitting the raw number in the combined view.

---

## Reproducing the evidence

```sh
# Gate
uv run ruff check . && uv run ruff format --check . && uv run mypy sdb && uv run pytest

# Finding 1 — duplicate archetypes
for t in "Roman Empire" "Great Wall of China" "Silk Road" "Islam" "Cleopatra"; do
  uv run sdb discover "$t" --top 1 --json
done   # compare the two archetypes' "path" arrays

# Findings 2 + the ADR 0025 verification
uv run python -c "
from sdb.graph.build import KnowledgeGraph
from sdb.graph.loader import load_seed, load_cooccurrence
kg = KnowledgeGraph.from_seed(load_seed('data/seed.json'), load_cooccurrence('data/cooccurrence.json'))
ids = [n.id for n in kg.nodes()]
for s in ['roman_empire', 'confucius']:
    print(s, 'sum P =', round(sum(2**(-kg.endpoint_unexpectedness(s, e)) for e in ids if e != s), 6))
    vals = [round(kg.endpoint_unexpectedness(s, e), 6) for e in ids if e != s]
    print('   distinct:', len(set(vals)), '| tied at max:', vals.count(max(vals)))
"
```

## Priority

Fix **1** first — one constant, immediately visible on the flagship demo. Then treat **2** as the
scoring frontier; it is the main thing standing between the improbable-pair archetype and the
"single, quantized, surprising TIL" the project wants to lean into. **3** is cosmetic.
