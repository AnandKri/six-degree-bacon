# ADR 0042 — A curated per-statement `headline` as the TIL, and the improbable pair as the default archetype

- **Status:** accepted
- **Phase:** 2

## Context

Since [ADR 0037](0037-surface-statement-evidence.md) surfaced the curated per-hop `evidence` prose, the
card's auto-generated **TIL** became its visibly weakest line. The narrator (ADR 0028) builds it by
mechanically chaining predicates into relative clauses — *"Renaissance contained Renaissance humanism,
which was influenced by Ancient Greece, which influenced House of Wisdom"* — while genuinely good,
sourced sentences sit right below it as the hop evidence. The owner's product steer (recorded in the
hand-over note) is that a TIL should read as **one quantized surprising fact**, the shape the improbable
pair already implies — not a narrated walking tour.

A *fully synthesized* one-liner ("the Renaissance ran on a Chinese invention") is a summarization task,
which the zero-LLM north star keeps out of the product — the UI itself advertises **"zero AI"** and
**"every link is provenanced"**. So a good single sentence must come from **curated prose**, not a
cleverer template (a template can only rearrange labels and predicates — the mechanical thing being
left).

## Decision

**1. Add a curated `headline` to `Statement`** — a tight, self-contained one-fact line, a *faithful
compression* of that edge's existing `evidence` (so it inherits the same provenance; no new claims).
Distinct from `evidence`: `evidence` is the fuller per-hop justification (rendered under its hop),
`headline` is the punchy TIL line. All **158** curated statements carry one, guarded by a completeness
test mirroring the `evidence` guard.

**2. The TIL is the payoff hop's headline.** `narrate` uses the curated `headline` of the path's
**payoff (last) hop** — the hop that lands on the destination endpoint — prefixed `TIL:` / `Possibly:`.
The mechanical relative-clause chain (`_chain_narrative`) remains the guaranteed **fallback** for any
payoff statement without a curated headline (harvested edges), honouring narrate.py's long-standing
"template remains the fallback" contract. No engine/scoring change: the narrator is presentation, so
trust/surprise and `eval/golden.json` are untouched.

Per-**edge** (not per-**path**) is deliberate. The winning path shifts whenever the seed or scoring
changes (11 winners moved in [ADR 0041](0041-active-period-temporal-axis.md) alone, and every breadth
cluster moves more), so a per-path TIL cache would go stale constantly; a per-edge headline is stable,
bounded (158), composes into any path, and — being a faithful compression of the edge's sourced
evidence — keeps "every link provenanced" and "zero AI" honest. The tradeoff is that a journey's TIL
states the *destination fact* rather than the whole start→end arc (the card header and the hop chain
supply the arc); the improbable pair, whose "fact" *is* the endpoint edge, maps to it perfectly.

**3. The improbable pair is the first / default archetype.** `ARCHETYPE_CHOICES["both"]` becomes
`(UNLIKELY, JOURNEY)` (CLI print order + payload order follow), and the web tab defaults to the
improbable pair. It already has the one-quantized-fact shape the product leans into.

## Worked example (from the seed, hand-verifiable)

`Renaissance → Printing press → Paper` (improbable pair; payoff hop `Printing press → Paper`):

- Payoff headline: *"Gutenberg's printing press ran on paper — a Chinese invention that reached Europe
  through the Islamic world."*
- TIL rendered: `TIL: Gutenberg's printing press ran on paper — a Chinese invention that reached
  Europe through the Islamic world.` (was: *"Renaissance was influenced by Printing press, which was
  influenced by Paper."*)
- The two hops still render their fuller `evidence` below, unchanged.

## Consequences

- **Every card leads with a real fact**, on both archetypes and every surface (the TIL comes from the
  shared `DiscoveryResult.til`). The mechanical chain survives only as the harvest fallback.
- **The still-open half of the product steer is resolved.** ADR 0037 shipped the evidence half; this
  ships the narrator half — the journey's generated line is no longer the weakest thing on the card.
- **`Statement.headline` stays internal to the narrator** — it is *not* added to
  `serialize.hop_dicts`/`result_core`, so it never bloats the payload.
- **Three test invariants updated** for the single-sentence TIL: narrative faithfulness now asserts the
  TIL *is* the curated payoff headline (not "every label appears"); the web card asserts a single
  curated fact; and the archetype-order assertions expect `[UNLIKELY, JOURNEY]`.
- **Zero-LLM and provenanced preserved:** headlines are hand-curated, evidence-faithful prose reviewed
  in the commit — not runtime generation. A free/local LLM *drafting aid* or narrator remains a
  documented later option behind the same seam, unused here.
- All green (ruff, format, mypy, **153 tests**), incl. the payoff-headline narrator test, the chain
  fallback, and a guard that every curated statement carries a headline. `eval/golden.json` winners
  unchanged (narration does not affect ranking).
