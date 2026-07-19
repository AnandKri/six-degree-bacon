# ADR 0047 — Brain-growth stopping rule: node count is the wrong axis

- **Status:** accepted (a governing policy for the breadth thread; no code or data change)
- **Phase:** 3

## Context

"Until what magnitude should we keep adding nodes — to the main brain and to the 20th-century
brain?" recurs every session that picks up breadth, and each session re-derives an answer. This ADR
settles it as a **decision** so the next session inherits a stopping rule instead of an open-ended
"add more".

The project has already, twice, measured that **node *count* is not the constraint** — connective
tissue is:

- The **starved-start** finding (ADR 0044, `docs/HANDOVER.md` §5): the starts that return weak
  results all have **graph-degree 1–4**. They are structurally their own cluster; more *mass*
  elsewhere does nothing for them. The trend line is `16/88 → 15/98 → 12/116` — starved *ratio and
  absolute count both fell* as the graph grew, because the additions were bridges, not filler.
- ADR 0033 (Renaissance) relieved `plato`/`constantinople` with a handful of **escape edges** and
  **zero** scoring change. The lever was edges that *leave* a cluster, not nodes beside one.
- Surprise is carried by **cross-domain + cross-region jumps** (ADR 0034/0039), not size. A dense
  within-`WESTERN` cluster (Enlightenment) would add nodes and *subtract* value — the walking-tour
  trap (ADR 0039).

So "how many nodes" is malformed. The right variable is *connectivity per addition*, and the ceiling
is set by three real limits, in the order they bite:

1. **The "reproducible by hand" north star** — the true cap. The whole claim is that a knowledgeable
   person can audit the *entire* graph and reproduce every score. That is credible at low hundreds of
   nodes and stops being credible somewhere around **~300 hand-curated nodes per brain**; past that
   the project is implicitly relying on nobody checking, which quietly violates the thesis the same
   way the README rotting to 88 nodes did.
2. **Curation labour** — every node is a verified QID, every edge a hand-sourced `evidence` +
   `headline`. This deterministic human work, not compute, is the actual bottleneck.
3. **Compute** — *not* a constraint yet. `EXACT_PATH_BUDGET = 5000`, seed worst case ~189; the guided
   walk (ADR 0010) already absorbs overflow. Neo4j is a `~10k+`-node graduation, far away.

## Decision

**Do not target a node count for either brain. Target connectivity, and stop when the connectivity
metrics plateau.**

- **Every added node must earn its place as connective tissue** — an escape edge for a low-degree /
  starved start, or a genuine cross-region bridge. A node that only deepens a cluster it is already
  inside is declined (it adds curation cost and dilutes rarity without moving surprise).
- **Soft ceilings, not targets:**
  - *Main brain* — **~150–200 nodes.** It already spans most major Old-World civilisations; new
    candidates are increasingly mono-region (Byzantine–Ottoman, Enlightenment) and low-surprise.
  - *20th-century brain* — more node headroom (a globalised century supplies real cross-domain /
    cross-region material, and its temporal-gap term is quiet so density is the *only* surprise
    source — ADR 0044), but the **same rule**: grow tissue (Cold War ↔ decolonisation ↔ pop-culture
    bridges), not time depth or within-cluster fill.
- **Drive growth by measured metrics, not by count.** The instruments already exist; a cluster is
  worth adding only if it moves one of them, and growth *stops* when they flatten:
  1. **% of starts returning a good, gated improbable pair** (main brain **104/116 ≈ 90%** at ADR
     0044) — via the starved-start sweep in HANDOVER §5.
  2. **Median region-jumps + domain-jumps of the top journeys** — the cross-cultural surprise the
     product is actually selling.
- **When a brain outgrows its hand-auditable ceiling, the honest next move is another brain, not a
  bigger one** (islanding-as-a-feature, ADR 0044) — so each graph stays reproducible by hand.

## Consequences

- No code, data, weight, or golden-value change. This is a policy record; **171 tests** unchanged.
- The breadth thread in `docs/HANDOVER.md` §5 is now governed by this rule: candidate clusters are
  judged against the two connectivity metrics and the mono-region caution, and "add more nodes" is
  no longer a standing instruction.
- Makes the eventual "stop" a *decision with a trigger* (metrics plateaued) rather than an
  open-ended backlog — the same discipline ADR 0014 and ADR 0036 applied to corroboration and
  interval separation.
- Zero-LLM, deterministic, hand-reproducible — and this rule is *why* it stays that way at the node
  level.

## Alternatives considered

- **Pick a fixed node target (e.g. "grow to 300").** Rejected: it optimises the wrong variable. The
  measured evidence is that value tracks escape edges and cross-region jumps, so a count target would
  reward filler and the walking-tour trap while leaving starved starts unfixed.
- **No ceiling — keep adding while material exists.** Rejected: it silently breaks the
  reproducible-by-hand north star. There is always more Old-World history; the constraint is
  auditability, not supply.
- **Raise the ceiling with tooling (Neo4j / an LLM curator) instead of stopping.** Deferred, not
  chosen here: Neo4j is a storage/query-scale graduation not needed at these sizes (ADR 0044), and an
  LLM curator is bounded by [ADR 0048](0048-llm-boundary-policy.md) — it may *draft*, never enlarge
  the graph past what a human still verifies.
