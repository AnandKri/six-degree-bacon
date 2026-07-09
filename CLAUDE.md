# CLAUDE.md — project guide for AI assistants

## What this is

**Six Degree Bacon** inverts "Six Degrees of Kevin Bacon": instead of the *shortest* path between two
things, it finds the *longest **meaningful*** one — a chain of real, sourced connections that hops
across domains (myth → religion → trade → history) until it lands somewhere surprising, presented as
a "TIL" card.

Two north stars:
1. **Product:** type a topic → get a genuinely surprising, true, well-sourced multi-hop connection,
   each result carrying a **reproducible trust score and surprise score**.
2. **Craft:** a reference for *AI-assisted coding done correctly* — deterministic, typed, tested,
   evaluated, fully provenanced. **Correctness never depends on an LLM.** Every score is reproducible
   by hand from `docs/confidence-rubric.md`.

## Status: Phase 0 complete

A local-first, **zero-LLM**, fully deterministic engine over a small curated graph. Committed and
pushed to `origin` (`https://github.com/AnandKri/six-degree-bacon`). All checks green.

## How to run

```sh
uv sync --extra dev                     # create .venv + install (writes uv.lock)
uv run sdb discover "Roman Empire"      # a sourced TIL card
uv run sdb discover "Silk Road" --top 3 --json
uv run ruff check . && uv run ruff format --check . && uv run mypy sdb && uv run pytest
```

`make check` / `make discover` also work on Unix/CI. On Windows there is no `make`; run the `uv`
commands directly. The CLI degrades to ASCII glyphs automatically on a legacy console.

## Architecture (all pure Python, deterministic)

```
topic -> graph (networkx MultiGraph) -> traverse -> score surprise -> rank/filter by trust -> template TIL
```

- `sdb/schema/` — `enums.py` (Domain, Predicate→Wikidata props, SourceType…) + `models.py`
  (Pydantic: `Source`, `Node`, `Statement`, `Path`, `DiscoveryResult`). **Statement-reified**: every
  claim is a `Statement{subject, predicate, object, sources[], evidence, link_quality}` so multiple
  sources corroborate a fact.
- `sdb/constants.py` — **the scoring rubric**: the single source of truth for every weight/threshold.
- `sdb/graph/` — `build.py` (`KnowledgeGraph`: networkx graph + cached degree/rarity/counts + topic
  lookup) and `loader.py`.
- `sdb/engine/` — `traversal.py` (exhaustive simple-path enumeration), `surprise.py`
  (information-theoretic), `confidence.py` (source rubric → noisy-OR corroboration → link quality →
  validators → weakest-link path trust), `narrate.py` (template TIL + `Possibly:` flag),
  `pipeline.py` (`discover()`).
- `sdb/cli.py` — the CLI. `sdb/viz.py` — optional matplotlib path drawing (`viz` extra).
- `data/seed.json` — curated 33-node / 40-statement graph across 8 domains, full provenance.
- `docs/adr/` — decisions. `docs/confidence-rubric.md` — the rubric, with worked examples the tests
  reproduce. `docs/reference/` — the original idea sketch (git-ignored, local only).
- `tests/` — 27 tests incl. human-vs-code confidence (0.75) and surprise (8.6) golden cases;
  `eval/golden.json` — ranker regression (characterization values).

## Scoring in one paragraph

**Trust** (is it true?): per-source reliability rubric → `1 − ∏(1 − rᵢ)` corroboration → × link
quality → × validator penalties; path trust = product of edge confidences. **Surprise** (is it
interesting?): `Σ −log2(count/total)` edge rarity + domain jumps + normalized temporal gap + length −
hub penalty. Results rank by **surprise**, with **trust** as tie-break + a hard floor. Below 0.5 trust
→ `Possibly:`.

## Conventions (strict — see git history)

`main` branch, local only (no push unless asked). Conventional Commits. Identity: AnandKri
<anand.krishna0802@gmail.com>. `snake_case` modules, `PascalCase` classes, `UPPER_SNAKE_CASE`
constants, `test_<module>.py`, ADRs `NNNN-kebab.md`. Type hints + docstrings on public APIs. Ruff +
mypy + pytest must stay green (CI enforces it).

## Next: Phase 1 (per the saved plan)

1. **Wikidata SPARQL harvester**: from a topic QID, pull a k-hop neighbourhood over the curated
   predicate set into the `Statement` model, mapping Wikidata rank/reference-count → source
   reliability deterministically. **Pin harvests to local JSON snapshots** (reproducible; goes under
   `data/harvest/`, git-ignored).
2. **Endpoint-surprise fix** (known Phase-0 gap): the current ranker rewards *path-internal* surprise,
   so an obvious destination like Rome→Latin can top the list despite a wild-looking chain. Add a
   deterministic `−log P(endpoint | start)` term estimated from **real co-occurrence** (Wikipedia
   links / Wikidata) so *unexpected destinations* win. Noted in `eval/golden.json`.
3. Keep it **zero-LLM and deterministic**; tune surprise weights against `eval/`.

Everything paid/heavy (Neo4j, a web UI, an optional free/local LLM narrator) stays a documented
graduation for later phases, behind an interface — adopt only when earned.
