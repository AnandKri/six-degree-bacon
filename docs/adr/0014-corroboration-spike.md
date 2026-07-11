# ADR 0014 — Cross-source corroboration: spike, and the decision to defer

- **Status:** accepted (spike; feature deferred)
- **Phase:** 2

## Context

HANDOVER §5 item 4 proposes a second independent source (DBpedia / Wikipedia-text) plus a
deterministic predicate-alignment table, to corroborate curated facts and raise trust via the
existing noisy-OR machinery (ADR 0005). The standing note calls it "low-yield, only if earned." This
is the **time-boxed spike** to decide build-vs-defer with numbers, not intuition — run fully offline
and deterministically by simulating corroboration rather than building an ingestion pipeline.

## What the spike measured

Adding one independent DBpedia-grade source (reliability 0.50) to statements and re-running discovery
over the whole seed (41 nodes / 54 statements):

- **Trust is already high.** Mean edge trust is **0.811**; **49 of 54** edges already clear the
  `trust ≥ 0.50` gate. Corroboration lifts the mean only to ~0.90.
- **The only sub-gate edges are unattestable.** All **5** edges below the gate are sourced
  `open_text` / `myth_legend` — "Romulus *claimed descent from* Aeneas", "Hadrian's Wall *inspired by*
  the Great Wall" (whose own evidence reads "a speculative popular claim"), "Mithraism *related to*
  Christianity", etc. These are speculative or mythic; a structured KB **cannot** legitimately attest
  them as facts. Corroborating them (the "ceiling": 711 → 998 confident results, Rome's winner
  India → Rigveda) is therefore **not achievable**, only simulated.
- **The achievable part inflates trust rather than corroborating it.** Corroborating only the 49
  *factual* edges still moves things (711 → 855 results; two flagship winners shift) — **but** the
  candidate independent sources (DBpedia, Wikipedia-text extraction) are *derived from Wikipedia*,
  which most factual edges already cite. Feeding a Wikipedia-derived source into noisy-OR (which
  assumes **independence**) double-counts the same underlying claim and inflates trust *dishonestly*
  — the exact failure the ADR 0005 Wikidata guard exists to prevent. Where genuinely independent
  evidence matters, the seed already carries it as `secondary_book` citations.

## Decision

**Defer.** The value splits into a part that is unachievable (corroborating speculative/mythic edges),
a part that is dishonest (Wikipedia-derived "second" sources violating noisy-OR independence), and a
residue (truly independent secondary sources) that the seed **already** encodes where it counts. The
prior DBpedia spike (HANDOVER §4) further showed that without a predicate-alignment layer
(`located_in` ↔ `capital`/`birthPlace`) the real match rate is ≈ 0.

Build it only when **both** prerequisites are genuinely met: (1) a source **independent of Wikipedia**
(a scholarly dataset, not DBpedia), and (2) a deterministic, verified predicate-alignment table. Until
then, corroboration stays correct-but-dormant, and breadth (more curated/harvested facts) is the
higher-leverage investment.

## Consequences

- No product code changes; the spike is recorded here so the question isn't re-litigated from scratch.
- The current behaviour is *correct*: the 5 speculative edges **should** read low-trust, and the
  engine already surfaces them only under `--include-possibly`.
- Reproduce with the offline simulation described above (add a 0.50 source per statement, re-rank).
