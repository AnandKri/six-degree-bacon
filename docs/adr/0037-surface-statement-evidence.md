# ADR 0037 — Surface the curated `Statement.evidence` prose in every result

- **Status:** accepted
- **Phase:** 2

## Context

Every one of the seed's 141 statements carries a hand-written, one-sentence justification in
`Statement.evidence` — curated, sourced, display-quality prose (median ~70 characters, all
well-formed sentences). The harvester writes it too (`Wikidata: {subject} {pid} {target}.`). It has
been in the data model since [ADR 0002](0002-statement-reified-data-model.md).

**Nothing read it.** Not the narrator, not the CLI card, not the web card, not the static-site
bundle. The only reference in the whole engine was the *write* in `sdb/harvest/harvester.py`. A
grep for `.evidence` outside the schema returned exactly one production line, and it was an
assignment.

This is worse than dead weight, because the unread prose is *better than the line we do ship*. For
the flagship journey the generated TIL chains predicates mechanically —

> TIL: Roman Empire was connected via trade to Silk Road, which was connected via trade to Great
> Wall of China, which was influenced by Qin Shi Huang.

— while the curated evidence sitting beside each hop reads as an actual fact:

> Rome imported Chinese silk along the Silk Road, calling the distant land Serica.
> · The Great Wall protected merchants and garrisons along the northern Silk Road.
> · Qin Shi Huang unified earlier border walls into a single Great Wall.

### Why it went dark: a terminology collision, named here so it can't recur

The field is called `evidence`. The **hop chain** rendered above the TIL is also, informally, "the
evidence". [ADR 0028](0028-single-claim-til.md) reasoned entirely in the second sense — "the hop
chain stays where it belongs, as the **evidence** rendered above the claim" — and in doing so
walked right past a schema field of that exact name without noticing it existed. The narrator was
redesigned around "evidence" while the thing literally named `evidence` stayed unread. One word,
two referents, and the concrete one lost.

## Decision

**Render `Statement.evidence` as a per-hop line under each step of the chain, on every surface.**
The chain stops being a list of predicates and becomes what ADR 0028 already called it — the
sourced evidence for the claim.

- A new shared renderer, `sdb.serialize.hop_dicts`, returns one
  `{from, from_id, phrase, to, to_id, evidence}` dict per hop. This *is* the mechanism against
  recurrence: `evidence` now travels in the same shared payload as every other cross-surface field,
  so it structurally cannot reach one front-end and miss another — the reason `sdb.serialize`
  exists ([the CLI/web serializer](../../sdb/serialize.py)). It replaces the web's private
  `_hop_payload`, and the CLI's JSON now emits the same `chain`.
- The CLI card prints the evidence indented under its hop; the web/static card renders it as a
  muted `.ev` line inside each route-list item.
- `evidence` may be `""` (the schema default), and every renderer treats a blank as "render
  nothing" rather than an empty line — so a future uncurated or harvested statement degrades
  cleanly.

## Consequences

- **The chain now reads as sourced fact on every surface**, which is the point. The generated TIL
  is retained unchanged as the one-line summary above it.
- **No scoring, ranking, traversal, or data change.** This is presentation only; `eval/golden.json`
  is untouched. The curated prose was already there — this ADR only connects it to the output.
- **The curation completeness is now load-bearing and guarded.** Because a blank renders as nothing,
  a statement with no `evidence` is now a visible hole in a card. `Statement.evidence` defaults to
  `""` and the schema can't require it, so `tests/test_validate.py` gains an offline guard that
  every *curated* statement carries non-empty evidence — the same class of seed-integrity check as
  the QID guard ([ADR 0008](0008-seed-qid-repair.md)). It asserts non-emptiness only, not prose
  style: legitimate evidence starts lower-case ("al-Khwarizmi …").
- **Observation, deliberately not acted on:** with the evidence surfaced, the generated TIL is
  visibly the weakest line on the card. This is consistent with the product direction in
  `docs/HANDOVER.md` §5 (a TIL should read as one quantized fact). Whether the journey's TIL should
  become curated prose, or be dropped in favour of the evidence chain, is a **narrator** question
  for a later ADR — it is not decided here, and no measurement backs a change yet.
- **Refactor bundled in the same change** (both touch the CLI/web result seam): `load_graph` moved
  from `sdb/web.py` to `sdb/graph/loader.py` (the CLI no longer imports a loader from the *web*
  module; `graph_from_seed` also stops the co-occurrence sidecar being parsed twice per load), and
  the journey/unlikely/both dispatch + trust-gate resolution moved into
  `sdb.engine.pipeline.discover_all` / `trust_gate`, which the CLI and web now share instead of
  each keeping its own copy. Also fixed a stale docstring that still claimed the pre-ADR-0021/0027
  hop ranges (`[3,4]`/`[1,3]`); it now points at the constants instead of restating them.
- Zero-LLM, deterministic, hand-reproducible.
