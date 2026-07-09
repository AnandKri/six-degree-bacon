# ADR 0004 — Phase-1 Wikidata SPARQL harvester

- **Status:** accepted
- **Phase:** 1

## Context

Phase 0 ran on a hand-curated 33-node seed graph. To grow beyond it without abandoning the
"correctness never depends on an LLM" and "reproducible by hand" principles, Phase 1 needs to ingest
real data from Wikidata — but ingestion must stay deterministic, testable offline, and must map onto
the existing statement-reified trust model (ADR 0002) rather than a new one.

## Decision

Add a `sdb.harvest` package that harvests a **k-hop neighbourhood** from a topic QID over the
**curated predicate set** into the validated `SeedData` (`Node` + `Statement`) model:

- **Client seam.** The harvester depends only on a `SparqlClient` protocol. `WikidataClient` talks to
  the live Query Service using the standard library only (`urllib`, no new dependencies);
  `FakeSparqlClient` serves canned data so the harvester is unit-tested end-to-end with zero network.
- **Deterministic trust grounding.** A Wikidata statement's **rank** and whether it carries
  **references** map — by the fixed rule in `sdb.harvest.mapping` — onto a `Source`:
  referenced → `wikidata_with_ref` (0.90), unreferenced → `wikidata_no_ref` (0.60), each times the
  rank multiplier. Endpoints are canonical QIDs, so `link_quality = 1.0` (no fuzzy entity linking).
  `P31` (instance-of) maps to a `Domain` via a small explicit table, falling back to `culture`.
- **Reproducibility via pinned snapshots.** A harvest is frozen to a `SeedData` JSON snapshot under
  `data/harvest/` (git-ignored): the network is consulted once, and every later run — including
  tests — replays the frozen file through the same validated loader.
- **Hub control.** `max_neighbors` caps per-node fan-out deterministically, taking low-signal
  "described by source" (P1343) edges last so a capped harvest keeps its structural edges.

Exposed as `sdb harvest <QID>` and `sdb build-cooccurrence` (the latter harvests the Wikipedia-link
co-occurrence of ADR 0003).

## Consequences

- Ingestion reuses the exact trust math already documented in `docs/confidence-rubric.md`; a
  harvested statement is scored identically to a curated one.
- The curated `data/seed.json` remains the tracked, authoritative graph; harvested snapshots are
  local, reproducible scratch under `data/harvest/`.
- Exhaustive traversal (ADR 0001) still bounds graph size; a guided walk and Neo4j remain the
  documented graduations for large harvested graphs.
