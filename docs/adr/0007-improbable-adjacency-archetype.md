# ADR 0007 — "Improbable adjacency" as a first-class surprise archetype

- **Status:** accepted (implemented)
- **Phase:** 2

## Context

The project's founding move was to invert "Six Degrees of Kevin Bacon" into the **longest meaningful
path** — surprise from the *journey* across domains. But there is a second, equally delightful shape
of "TIL" that the longest-path framing structurally excludes:

- **Type A — "the journey":** a long chain (myth → trade → history → …). Surprise from *distance
  travelled*. The current engine optimises for this.
- **Type B — "the improbable adjacency":** a **short** connection (1–3 hops) between two entities that
  feel worlds apart yet turn out to be *directly* linked. Surprise from the tension between how far
  apart they seem and how directly they connect.

Motivating example (Type B): *"Sawai Jai Singh II, an 18th-century Rajput astronomer-king, had
Euclid's Elements translated into Sanskrit."* A ~2,000-year gap and Hellenistic Greece ↔ Mughal-era
Rajasthan, carried by a single well-sourced fact. (Historically a short chain: Euclid → al-Tusi's
Arabic → Jagannatha Samrat's Sanskrit *Rekhaganita* → Jai Singh's court — so "thin" means *short and
improbable*, not necessarily one hop.)

Two observations make this tractable now:

1. **The signal already exists.** Type B is exactly "these endpoints are improbably connected," which
   the Phase-1 endpoint-surprise term `−log2 P(endpoint | start)` (ADR 0003) already measures.
   `P(Euclid | Jai Singh)` is tiny → high endpoint-surprise.
2. **Trust already carries the weight it must.** A thin link's entire TIL rests on one edge, so it
   lives or dies on trust. The recent `surprise × trust` ranking with a default `min_trust` gate
   (POSSIBLY_THRESHOLD) is precisely what Type B needs: a dubious single-edge claim is filtered; a
   well-sourced improbable fact rises.

What *blocks* Type B today is two length biases in scoring: **`MIN_HOPS_DEFAULT = 3`** (a short
improbable link is filtered before it is ever scored — the real blocker) and
**`W_LENGTH · (hops − 2)`** (length is rewarded as a goal rather than being incidental).

## Decision (proposed)

Recognise **improbable adjacency as a first-class archetype**, ranked by the *improbability of the
connection* rather than the *length of the path*. Concretely:

1. **Allow short paths.** Lower the effective `min_hops` to 1 for this archetype (keep a longer floor
   for the "journey" archetype if surfaced separately).
2. **Stop treating length as the goal.** Replace the raw `length_bonus` with **surprise density** —
   reward endpoint-improbability (and domain/temporal distance) *per hop*, so a 1-hop improbable link
   can outrank a padded 5-hop chain. Length becomes incidental, not an objective.
3. **Surface both archetypes** (recommended): return the best **"journey"** (long chain) *and* the
   best **"unlikely pair"** (short, high-endpoint-surprise, high-trust link). They are different
   delights and should not compete on one scale.
4. **Raise the trust bar for very short links.** A headline TIL resting on a single edge should
   require solidly-sourced evidence (at or above POSSIBLY_THRESHOLD), never `Possibly:`.

**Anti-flooding guardrail.** Allowing 1-hop paths is only safe *because* the endpoint-surprise term
exists: an obvious adjacency like "Roman Empire → Rome" scores near-zero endpoint-surprise (Rome is
heavily linked from the Roman Empire article) and is correctly *not* a wow. Type B = **short path +
high endpoint-surprise + adequate trust**.

### Alternatives considered

- **Do nothing / only lower `min_hops`.** Cheapest, but `length_bonus` still tilts the field toward
  long paths, so genuine thin links stay buried.
- **Single density scale for everything.** Elegant, but conflates two genuinely different reading
  experiences ("the journey" vs "the unlikely pair") into one ranking. Preferred fallback if two
  result streams add too much surface area.
- **Two explicit archetypes (recommended).** Most honest to the insight; small extra surface in the
  pipeline/CLI.

## Consequences

- Realising Type B needs edges the curated seed does not yet contain (there is no Jai Singh/Euclid
  fact in `data/seed.json`), so *seeing* it is a Phase-2 **ingestion/coverage** matter. This ADR
  fixes the **scoring philosophy** now, ahead of the data — the clean time to decide it.
- Scoring stays **deterministic, zero-LLM, and reproducible by hand**: surprise density is the same
  table-lookup terms recombined; the endpoint term is unchanged (ADR 0003).
- `eval/golden.json` gains an "unlikely pair" characterisation case once seed data supports one; the
  "journey" goldens are unaffected if the two archetypes are surfaced separately.
- Requires re-tuning `W_LENGTH` (removed or reshaped) and the interaction with `W_ENDPOINT` against
  `eval/`; watch that short obvious pairs never leak past the endpoint-surprise + trust gates.

## Update — as built

Implemented as **two explicit archetypes** (`sdb.schema.enums.Archetype`), surfaced together by
default (`sdb discover`, and `--archetype journey|unlikely|both`); each is a ranked list, honouring
"rank TILs in order of wow":

- **JOURNEY** — `surprise × trust` over `[3, 6]` hops (the existing wow score, ADR 0006).
- **UNLIKELY** — `endpoint_unexpectedness × trust` over `[1, 3]` hops. We rank by *endpoint
  improbability × trust* rather than raw "surprise density": density (total surprise ÷ hops) still
  rewarded obvious 1-hop neighbours, whereas the endpoint term is exactly "how worlds-apart is this
  destination." Both gate at `trust ≥ POSSIBLY_THRESHOLD`.

Two course corrections came out of building it:

1. **Prerequisite bug (ADR 0008).** Type B is only as honest as the co-occurrence data. Prototyping
   surfaced the false-positive "Rome → Mithraism" (Mithraism *was* Roman) — traced to 16 hallucinated
   seed QIDs that had emptied co-occurrence. Fixing those was a hard prerequisite; afterwards
   Mithraism correctly reads as *expected* and drops out of Rome's improbable pairs.
2. **Data, deferred by choice.** No Jai-Singh/Euclid-style fact was added, so on the current seed the
   best genuine improbable pair is "Roman Empire → Great Wall of China" (2 hops, worlds apart yet
   directly connected). Richer Type-B destinations await curated/harvested coverage, as anticipated.
