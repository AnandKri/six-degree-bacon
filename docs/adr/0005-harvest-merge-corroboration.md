# ADR 0005 — Merging a harvest into the curated graph, with corroboration

- **Status:** accepted
- **Phase:** 2 (first increment)

## Context

Phase 1 gave us a harvester (ADR 0004) but the curated `data/seed.json` stayed separate. Two Phase-2
opportunities followed from running it: (1) the harvester saw only 7 predicates, and (2) discovery
over a *raw* harvest is low-trust because each harvested fact is single-source. The natural next step
is to overlay a harvest onto the curated graph so the two reinforce each other.

## Decision

**Widen the harvest vocabulary** (`sdb.harvest.mapping`):
- Reconnect `inspired_by` to its real Wikidata property **P941** (it had been treated as
  project-specific).
- Add **alias properties** that map many Wikidata properties onto one predicate (`P17` country and
  `P131` located-in-admin → `located_in`; `P463` member-of → `part_of`), each a faithful
  subject→object match. Aliases widen recall without adding narration vocabulary.
- Expand the `P31 → Domain` table so fewer harvested nodes fall to the `culture` fallback.

**Merge overlay onto base** (`sdb.harvest.merge`, exposed as `sdb discover --harvest <snapshot>`):
- **Node unification by QID** — an overlay node sharing a curated node's `wikidata_qid` is identified
  with it (the curated node wins); otherwise it is added. Base is never mutated.
- **Corroboration** — an overlay statement with the same `(subject, predicate, object)` contributes
  its source, raising the noisy-OR trust. An **independence guard** adds a source only if its
  *origin* is new: a curated fact already citing Wikidata is **not** double-counted by a harvested
  Wikidata source (all Wikidata sources share one origin), but a fact sourced only from
  Wikipedia/books *does* gain Wikidata as a genuine corroborator.

## Consequences

- **Breadth is the immediate, measured win.** Merging one 2-hop Roman-Empire harvest grew the graph
  33→73 nodes / 41→93 statements and lifted reachable endpoints from Roman Empire from 25 to 44.
- **Corroboration is correct but near-dormant on *this* seed** — a deliberate, honest finding. The
  curated graph was already sourced from Wikidata wherever Wikidata asserts the fact; the statements
  it sources only from Wikipedia/books are exactly the ones Wikidata models differently or lacks
  (e.g. Rome is Wikidata's *capital* `P36` of the Empire, not its *location* `P276`). So a Wikidata
  harvest can corroborate almost none of them. Corroboration's value is realized when a **genuinely
  independent** second source is harvested (e.g. DBpedia, or Wikipedia-text extraction) — a
  documented graduation, not built until earned. The mechanism is kept because it is correct, is
  load-bearing for idempotent re-merges, and needs no rework when that source arrives.
- Strict `(subject, predicate, object)` matching is retained over looser subject/object matching:
  corroborating a fact under a *different* relation would be semantically wrong and is not
  deterministic-by-evidence. Recall is grown by the alias table above, not by loosening the match.
- The merge is a **non-destructive, runtime overlay**; the tracked seed stays authoritative and
  snapshots stay git-ignored under `data/harvest/`.
