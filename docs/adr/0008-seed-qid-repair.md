# ADR 0008 — Repair the hallucinated seed Wikidata QIDs

- **Status:** accepted
- **Phase:** 2

## Context

Prototyping the improbable-adjacency archetype (ADR 0007) surfaced a foundational bug: **16 of the
31 `wikidata_qid`s in `data/seed.json` pointed at the wrong entity.** `hadrian` → Q1409 (Caligula),
`silk_road` → Q34266 (Russian Empire), `proto_indo_european` → Q170460 (Secure Shell, the SSH
protocol), `trojan_war` → Q42285 (garlic chives), `mithraism` → Q131183 (cabaret), and so on. The
pattern — often off by a few digits, or a plausible neighbour — is the signature of **QIDs
hallucinated when the seed was authored**, an acute irony for a project whose premise is that
correctness never depends on an LLM.

The damage was not cosmetic:

- **Provenance was fake.** The "source" for Hadrian's Wall resolved to a Wikidata item literally
  labelled "building" — trust scores mean nothing if the citations are wrong.
- **The engine was silently corrupted.** Co-occurrence resolves each node through its QID, so wrong
  QIDs fetched the wrong Wikipedia article and produced garbage endpoint-surprise. In particular the
  broken `mithra`/`mithraism` QIDs gave those nodes *empty* co-occurrence → artificial *maximum*
  surprise, which is why "Mithra" spuriously topped many rankings.

## Decision

Repair every QID **deterministically and verifiably**, not by blind search (searching "Silk Road"
returns the darknet market, Q58027, ahead of the trade route):

1. Resolve each node's label to its English Wikipedia article, then read the article's
   `pageprops.wikibase_item` — the article "Silk Road" is unambiguously the trade route (Q36288).
2. **Verify** each resulting QID against its Wikidata label + description before applying (must read
   "Roman emperor" / "trade route" / "deity", etc.).
3. Apply node-scoped edits (the `qin`/`han` QIDs shuffle, so a global replace would collide), also
   filling in the two nodes that had no QID (`persia` → Q794, `china` → Q148).
4. Rebuild `data/cooccurrence.json` from the corrected QIDs (`sdb build-cooccurrence`).

## Consequences

- All 33 nodes now carry a correct, verified QID; co-occurrence covers 33/33 nodes (was 23).
- **Results de-artifact and improve.** With honest co-occurrence, Mithraism is correctly *expected*
  from Rome (not a false surprise), and **Roman Empire now tops out at Qin Shi Huang** (3 hops,
  trust 0.86 — Rome to the First Emperor of China), the tight, well-sourced "wow" that the buggy data
  had been burying. `eval/golden.json` re-characterized accordingly.
- Provenance is trustworthy again — the project's central promise.
- **Process gap, now guarded:** nothing had validated the curated QIDs. Added `sdb validate-qids`
  (`sdb/harvest/validate.py`) — it resolves each node's label → Wikipedia article → `wikibase_item`
  and asserts it equals the stored QID, exiting non-zero on any mismatch. Offline structural
  invariants (QID format/uniqueness, co-occurrence integrity) are covered by `tests/test_validate.py`;
  wiring the live command into a network-enabled CI job (still open) would fully close the gap.
