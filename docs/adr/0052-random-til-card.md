# ADR 0052 — A "random TIL" card: selection-only randomness, seeded and shareable

- **Status:** accepted
- **Phase:** 3

## Context

The map answers "what connects *this* topic?" — it needs the user to already have a topic in mind.
The product's north star is a *surprising* fact, and the fastest route to one is not searching but
being *shown* one. A "random" affordance turns the knowledge base into something browsable.

The obvious objection is the project's hard rule: **correctness never depends on an LLM, and every
score is deterministic and reproducible by hand**. Randomness sounds like it violates that. It does
not, provided it is confined to the right layer — which this ADR pins down.

The feasibility was checked before building, and one finding made it cheap: the static bundle
**already precomputes every node's card**. [`site.py::_bundle`](../../sdb/site.py) loops over all
nodes and stores `results[node_id] = {strict, loose}` (journey + improbable pair). So on the deployed
static site a random card is a pure client-side lookup — no new precompute, no backend, no engine
change. The page also already has a single hook that renders any node's card (`select(node, kind)`).

## Decision

**Randomness is selection-only.** It chooses a *start node*; everything downstream — traversal,
surprise, trust, the gate, the narrated TIL, provenance — is the same deterministic pipeline the map
and CLI already use. The engine, `sdb/constants.py`, both seeds and `eval/golden.json` are untouched.
Conceptually this is the search box with a different input method, not a scoring change.

Shipped in the web UI (both `sdb serve` and the static bundle, one shared code path):

- **A `random` button** in the top bar. It draws a start node and renders the ordinary card, with the
  existing **improbable pair / journey** toggle and the strict/`+ speculative` toggle intact.
- **A scope control**, shown only when more than one brain exists: **this brain** (default) or
  **all brains**. "All brains" picks a brain **weighted by node count**, then a node within it, so
  every *card in the whole corpus* is equally likely — 116 vs 102 nodes means main is drawn ~53.2% of
  the time, not 50%. Because the map renders one brain at a time, a cross-brain draw switches the map
  to the drawn node's brain first (reusing `switchBrain`), so the card and the map always agree.
- **Seeded and shareable.** A tiny deterministic PRNG (`mulberry32`) drives the draw, and the seed is
  written to the URL as `?random=<seed>[&scope=all]` via `replaceState`. Re-opening that URL replays
  the identical draw, so **a surprising card can be shared as a link** and the randomness itself is
  reproducible given the same data — the same standard the rest of the project holds.
- **The pool is only nodes that have a gated result** in the current mode (free to compute from the
  bundle), so a random draw never lands on an empty "no route" card.

Two small backend additions support the weighting, and nothing else changed server-side: each entry
in `brains.json` ([`build_multi_site`](../../sdb/site.py)) and in `/api/brains`
([`web.py`](../../sdb/web.py)) now carries its **`count`** (node count), so the page can weight the
draw without eagerly downloading every brain's bundle.

## Verification

- **Determinism:** the same seed replays the identical draw (verified against the shipped functions —
  seed `12345`, all-scope, drew `[brain 1, node 31]` on repeat runs). Scope is part of the draw, which
  is why it is encoded in the URL alongside the seed.
- **Weighting:** over 200k draws the main brain is chosen **0.5320** of the time vs the expected
  `116/218 = 0.5321`.
- **Uniformity:** node index over a 100-slot pool spreads evenly (min 1814 / max 2122 against a mean
  of 2000) — no positional bias.
- The whole page script passes a syntax check, the built static bundle contains the control, and the
  per-brain `count` contract is locked by tests in `test_brains.py` (the manifest and the live
  `/api/brains` round-trip). **176 tests**, ruff/format/mypy green.

## Consequences

- **No scoring, data, engine or golden-value change.** Purely an input affordance plus two additive
  JSON fields. The "zero AI / every link provenanced / reproducible by hand" claims are unaffected —
  a drawn card is byte-identical to the one you get by searching that topic.
- **The static deploy gets the feature for free**, because the bundle already held every card. The
  live server path uses the same client code, so the two surfaces cannot drift.
- **JS is not unit-tested here**, consistent with the rest of the page (the project has no JS test
  runner); the Python-side `count` contract *is* locked by tests, and the draw's determinism rests on
  a seeded PRNG verified above.
- A single-brain deploy hides the scope control entirely, so the single-brain UI is unchanged.
- Deliberately **not** built: a CLI `sdb random` (recorded as a cheap follow-up if wanted), and any
  "greatest hits" weighting by surprise score — biasing the draw toward high-scoring cards would make
  the feature a curator of taste rather than an honest sample, and the scores already rank within a
  result set.
