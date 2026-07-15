# ADR 0028 — The TIL is a single quantized claim, not a hop-by-hop recitation

- **Status:** accepted
- **Phase:** 2

## Context

The template narrator emitted the path twice over. It restated every hop as a semicolon-separated
list and then appended a generic meta-closer:

```
TIL: Mansa Musa was influenced by Islam; Islam followed Zoroastrianism. It connects Mansa Musa
to Zoroastrianism across 2 domains and 2 steps — an unexpected thread.
```

Two problems. First, **every caller already renders the hop chain as arrows directly above the TIL**
(CLI, `sdb serve`, and the static site share `discover_payload`), so reciting it in prose added noise,
not information — and the closer's "2 domains and 2 steps" duplicates the hop count in the card header
and the metrics beneath it. Second, and more importantly, it reads as *directions* rather than a
*fact*. The product's best results are single quantized claims — "Elizabeth II descends from Odin",
"Japan's imperial family traces to the sun goddess" — and the narrator was actively working against
that shape.

## Decision

Compose the TIL as **one sentence that states the connection**, with the repeated subject elided into
relative clauses: the first hop in full, then `", {who|which} {phrase} {node}"` per subsequent hop.
Drop the meta-closer entirely; the hop chain stays where it belongs, as the **evidence** rendered
above the claim, and the stats stay in the metrics line.

The relative pronoun comes from a small documented lookup on the node's `type` (`_PERSONAL_TYPE_WORDS`
— "emperor", "deity", "king", "philosopher"…, matched word-wise so "legendary emperor" resolves), so a
person reads "who" and everything else "which". Unrecognised types fall back to "which", correct for
the great majority of node types (places, states, works, languages). Still zero-LLM, deterministic,
and every node label on the path appears exactly once (the narrative-faithfulness test still holds).

## Consequences

- **The TILs now read as facts**, which is the whole point:

  ```
  TIL: Elizabeth II claimed descent from Alfred the Great, who was part of House of Wessex,
       which claimed descent from Odin.
  TIL: Naruhito claimed descent from Jimmu, who claimed descent from Amaterasu.
  TIL: Buddhism influenced Woodblock printing.
  ```

- **No engine change.** Scoring, ranking and the archetypes are untouched; this is presentation only,
  behind the existing `narrate()` seam. An optional free/local LLM narrator remains a later upgrade
  behind that same signature, with this template as the guaranteed fallback.
- Tests lock the format (exactly one sentence, no restated chain, no closer) and the animacy rule.
- **Review Finding 3 needs no action.** Cross-archetype `score` values are not comparable
  (`surprise × trust` vs `endpoint_unexpectedness × trust`), but neither UI presents them as such: the
  page already labels "surprise" vs "improbability" using each archetype's own component, and the CLI
  prints `wow … (surprise × trust)` vs `improbable … (improbability × trust)`. The raw `score` appears
  only in the JSON API, where `archetype` sits beside it. Recorded so it is not re-litigated.
- Known cosmetic nit, pre-existing and unchanged: labels carry no article, so a clause can read "was
  part of House of Wessex". Inserting "the" deterministically would need a per-node article rule; not
  worth the fragility.
