# ADR 0048 — LLM boundary policy: draft / narrate / route / suggest, never score / rank / gate / attest

- **Status:** accepted (a governing policy; the engine stays zero-LLM — no code change)
- **Phase:** 3

## Context

"When do we add an LLM to the project?" recurs, and it is easy to answer badly, because the honest
answer is not "never" — it is "never *in the path that decides a result*, and only at the edges when a
specific need appears that curation genuinely can't serve." The north star (`CLAUDE.md`) is explicit:
**correctness never depends on an LLM**; every score is deterministic and reproducible by hand from
`docs/confidence-rubric.md`. The moment trust, surprise, ranking, the trust gate, or provenance
depends on a model call, the project's entire "AI-assisted coding done correctly" thesis is dead.

This ADR draws the exact line and orders the legitimate entry points, so a future session neither
smuggles an LLM into scoring nor treats "zero-LLM" as a ban on *all* model use where it would be
harmless. It records a **policy**, not a build; nothing here is implemented.

## Decision

**The line: an LLM may _draft_, _narrate_, _route_, or _suggest_ — it may never _score_, _rank_,
_gate_, or _attest_.** Anything a result's trust/surprise/order/provenance depends on stays
deterministic and hand-reproducible. Anything an LLM touches must be either (a) offline and
human-ratified before it enters the repo, or (b) runtime, optional, and clearly labelled as
generated/non-authoritative so it cannot be mistaken for a sourced fact.

Legitimate entry points, **cheapest and safest first** — adopt each only on a concrete pull:

1. **Build-time curation copilot (offline, human-ratified) — the first one, and arguably already
   justified.** As breadth grows, the bottleneck is hand-writing `evidence` / `headline` and choosing
   escape-edge clusters (ADR 0047). An LLM may **draft** those sentences and **propose** candidate
   bridges — but every committed artifact is still human-verified, QIDs still pass `validate-qids`,
   and the scores remain hand-reproducible. It is a tool, not a product dependency; the north star is
   untouched because nothing an LLM emitted reaches a score without a human ratifying it. Adopt when
   drafting speed is what gates a cluster.
2. **Optional, labelled narrator for the journey *arc* (runtime, flagged, non-authoritative).** The
   seam ADR 0042 explicitly recorded and declined: a per-*path* arc sentence, behind the existing
   template seam, visibly marked as generated so it can't be confused with the curated
   `Statement.headline` / per-hop `evidence`. Build only on real user pull; it stays optional forever
   and never affects scoring. Low priority — ADR 0042 already resolved narration with curated
   headlines.
3. **Natural-language input routing.** If the product ever grows a free-text front door ("connect
   jazz and the space race") instead of a topic that must match a node, an LLM mapping phrase → graph
   node is a clean non-correctness use: the *connection itself* is still deterministic. Worth it only
   if that front door is wanted.
4. **Offline LLM-as-judge to unblock weight tuning — most dangerous, do last.** HANDOVER §5 notes
   weight tuning is blocked by the absence of a human-labelled "wow" set. An LLM judge *could* produce
   candidate labels, but this is where model taste can launder into "reproducible" scores. Acceptable
   only if the labels are treated as a **noisy human-proxy that a human ratifies**, used purely
   offline to set constants that stay in the hand-reproducible rubric — and even then, for ~8
   continuous knobs a plain grid/random sweep beats a fancy optimiser (HANDOVER §5), so the LLM's only
   job is label *generation*, never tuning and never runtime.

## Consequences

- No code change; the engine, pipeline, scoring, and traversal stay **zero-LLM and deterministic**.
  This ADR is the standing answer to "should we add an LLM here?" — check the verb: draft/narrate/
  route/suggest is in bounds, score/rank/gate/attest is out.
- Entry point 1 (curation copilot) is pre-authorised *in principle* under the stated guardrails
  (human ratification + `validate-qids` + tests); it needs no new ADR to start, only the guardrails
  honoured. Entry points 2–4 each need their own ADR when built, recording the concrete pull and the
  labelling/ratification mechanism.
- Keeps the README's "zero LLM … documented graduations for later" claim honest and specific: this
  ADR *is* the specification of what those graduations may and may not do.
- Complements [ADR 0047](0047-brain-growth-stopping-rule.md): together they say the graph grows by
  human-verified tissue (0047) and an LLM may accelerate that verification but never replace it or
  reach a score (0048).

## Alternatives considered

- **Absolute ban — no LLM anywhere, ever.** Rejected as over-broad: it would forbid an offline,
  human-ratified drafting tool that touches no score, discarding real leverage for no gain in
  correctness. The north star constrains the *decision path*, not the authoring tools.
- **Allow an LLM narrator to synthesise the TIL per path.** Rejected as the default (ADR 0042):
  per-path synthesis goes stale on every scoring/seed shift and would break "zero AI / every link
  provenanced". Permitted only as the *optional, labelled* entry point 2 above, never as the
  authoritative TIL.
- **LLM in the loop for scoring/ranking (e.g. an LLM surprise judge at runtime).** Rejected
  outright — this is the exact thing the north star forbids; it trades a hand-verifiable exact result
  for a non-reproducible one, which is the project's whole differentiator (see also the GA rejection,
  HANDOVER §5).
