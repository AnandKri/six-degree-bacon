# ADR 0002 — Statement-reified, Wikidata-aligned data model

- **Status:** accepted
- **Phase:** 0

## Context

Confidence must be *deterministic and grounded*: reproducible by a human from a written rubric. That
requires modelling **evidence** explicitly — in particular, allowing several independent sources to
corroborate the same fact.

## Decision

Reify every claim as a **`Statement { subject, predicate, object, sources[], evidence, link_quality }`**
rather than attaching provenance to a flat edge.

- **Multiple sources per statement** enable deterministic corroboration (noisy-OR) — see
  `docs/confidence-rubric.md`.
- **Wikidata alignment:** node `type` maps to Wikidata classes and `predicate` to Wikidata properties
  (`PREDICATE_WIKIDATA` in `sdb/schema/enums.py`), so provenance can point at an exact statement and
  Phase-1 ingestion can adopt Wikidata's own rank/reference signals directly.
- **First-class `domain` enum** (myth, history, trade, …) so cross-domain jumps — the core surprise
  signal — are computed deterministically rather than inferred.
- **Cached derived features** (`degree`, predicate counts → edge rarity, temporal midpoints) are
  computed once at graph build and feed the deterministic scoring.

This supersedes the flat-edge sketch from the project's original notes (kept locally, untracked),
keeping their fields but reifying the edge.

## Consequences

- Trust is a pure function of the statement's sources, link quality, and validator penalties.
- A statement with no sources scores 0 trust and is filtered — provenance is mandatory, by design.
