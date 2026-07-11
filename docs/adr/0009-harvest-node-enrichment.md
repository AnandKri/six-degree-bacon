# ADR 0009 — Node enrichment on the harvest path

- **Status:** accepted
- **Phase:** 2

## Context

Harvested nodes were thinner than curated ones in two ways that quietly weakened the surprise score:

- **Domain under-coverage.** `INSTANCE_OF_DOMAIN` (the P31→`Domain` table) mapped ~36 classes and had
  **no entries at all for the `SCIENCE` and `ART` domains** — even though the seed carries a science
  subgraph (Euclid → al-Tusi → Jagannatha Samrat → Jai Singh II). Anything unmapped falls to the
  `culture` fallback, and ~30% of a typical harvest did. Domain *changes* are what earn the
  `W_DOMAIN` surprise term, so mis-domaining a third of the graph as one blob suppresses genuine
  cross-domain jumps.
- **People were undated.** `entities()` fetched only inception (`P571`), which humans never carry, so
  every harvested person had `start_year = end_year = None`. The temporal-gap surprise term
  (`W_TEMPORAL`) and the date validators (`PENALTY_DATE_DISORDER`, `PENALTY_TEMPORAL_IMPLAUSIBLE`)
  then had nothing to work with on exactly the nodes — scholars, rulers — that anchor a good journey.

Both are bounded, deterministic gaps (HANDOVER §5 item 2). No new scoring term is introduced; this
only feeds the existing rubric better inputs.

## Decision

1. **Grow `INSTANCE_OF_DOMAIN`** with ~44 more P31 classes, adding first-class coverage for `SCIENCE`
   (academic discipline, branch of science, mathematics, astronomy, theorem, theory, scientific
   instrument, observatory, unit of measurement) and `ART` (art, art movement, work of art, painting,
   sculpture, musical work, film), plus common subtypes of the existing domains (settlement/admin and
   physical-feature classes for geography; state/kingdom/event/siege/rebellion/revolution/treaty for
   history; denomination/temple/church/monastery for religion; dialect/writing-system for language;
   mythology/mythical-creature for myth). **Every added QID was verified against Wikidata** (label
   confirmed, recorded in the inline comment); one candidate resolved to "Hurricane" (a US city) and
   was dropped — the ADR 0008 failure mode, refused at authoring time.
2. **Pull a full temporal extent.** `entities()` now also reads birth (`P569`), death (`P570`) and
   dissolution (`P576`). A documented combiner, `mapping.temporal_extent`, folds them by a rule
   reproducible by hand: `start = inception ?? birth`, `end = dissolution ?? death`. Because a
   person's item never carries `P571/P576` and a place's never carries `P569/P570`, at most one of
   each pair is set, so the rule is unambiguous. The `(item × P31 × dates)` SPARQL row product is
   collapsed deterministically (earliest start, latest end) independent of row order.
3. **`time_precision` stays unset.** It is consumed by *no* score (verified in `surprise.py` /
   `confidence.py`); reading it needs a heavier per-statement precision query. Deferred, not faked.

## Consequences

- A live 1-hop harvest of Euclid (Q8747), previously undated, now yields `start_year = -333`,
  `end_year = -284`, `domain = history` — the temporal-gap term and validators have real inputs.
- Fewer harvested nodes land in the `culture` bucket, so cross-domain surprise reflects real domain
  structure instead of a fallback monoculture; `SCIENCE`/`ART` nodes are no longer invisible.
- Still zero-LLM and hand-reproducible: the domain table is a verified lookup and `temporal_extent`
  is a two-line precedence rule. `data/seed.json` is untouched, so no `validate-qids` /
  `build-cooccurrence` / `eval/golden.json` churn. Live queries remain untested-by-design behind the
  `SparqlClient` protocol; the offline `FakeSparqlClient` exercises the mapping, the combiner, and
  the order-independent fold.
