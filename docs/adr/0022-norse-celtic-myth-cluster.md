# ADR 0022 — Breadth: the Norse/Celtic myth cluster

- **Status:** accepted
- **Phase:** 2

## Context

The seed's myth domain was Mediterranean-and-Vedic (Greek myth, Aeneas, Romulus, Mithra, the
Rigveda). The obvious next myth cluster is the northern Indo-European branch — Norse and Celtic —
which connects to the existing graph through **Proto-Indo-European**, exactly the hub that already
anchors Mithra and Latin, so it is not an island. It also lets the graph make one of comparative
mythology's textbook true-but-surprising links: the Norse thunder-god Thor and the Vedic Indra of
the Rigveda are cognates of a single Proto-Indo-European storm deity.

## Decision

Add five verified nodes — Norse mythology (Q128285), Odin (Q43610), Thor (Q42952), Loki (Q133147),
Celtic mythology (Q1106575), all `myth` — with seven sourced statements:

- `odin part_of norse_mythology`, `thor part_of norse_mythology`, `loki part_of norse_mythology`,
  `thor claimed_descent_from odin` (Thor is Odin's son) — the internal Norse pantheon.
- `norse_mythology derived_from proto_indo_european`, `celtic_mythology derived_from
  proto_indo_european` — both descend from the reconstructed PIE mythology (comparative
  Indo-European studies), tying the cluster to the PIE hub.
- `thor mythologically_related_to rigveda` — Thor is cognate with the Rigveda's Indra, a second
  bridge that reaches the Vedic/Indian world directly (not only through PIE).

QIDs verified against Wikidata (label → Wikipedia article → `wikibase_item`); `validate-qids`
(71/71) → `build-cooccurrence` (71).

## Consequences

- **Five new myth topics** with genuine cross-domain reach — e.g. `Thor → Rigveda → India →
  Buddhism` (a journey from a Norse god to an Indian religion), `Odin → Norse mythology → Proto-
  Indo-European → Celtic mythology`, `Celtic mythology → Proto-Indo-European → Latin → Romance
  languages`. Thor's improbable pairs are the eastern Indo-European world (Rigveda at 1 hop, India
  at 2), not other Norse gods. A property-based test locks that the pantheon reaches beyond itself
  through PIE and the Thor↔Rigveda cognate.
- **Golden winners unchanged** at the 3-hop gate (Roman Empire → India, Christianity → Great Wall
  of China, Euclid → India); no `eval/golden.json` change.
- Seed now **71 nodes / 100 statements** across 9 domains. Still zero-LLM, deterministic, and
  hand-reproducible; all checks green (89 tests).
