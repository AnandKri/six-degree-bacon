# ADR 0033 — Renaissance cluster (populating `culture` and `art`, and relieving the starved classical starts)

- **Status:** accepted
- **Phase:** 2

## Context

Two of the ten curated domains were effectively unused: **`culture` had 0 nodes** and **`art` had 1**
(Homer). Domain is not decoration — `_domain_jumps` carries `W_DOMAIN = 2.0`, the second-heaviest
surprise weight — so two of the ten realms that generate cross-domain surprise were contributing
nothing. ADR 0032 was a prerequisite: while `culture` doubled as the harvest fallback, anything
curated into it would have been indistinguishable from unmapped fallout.

The second motivation came from a measurement, not a hunch. Sweeping all 88 starts for the
improbable-pair archetype (the open follow-up recorded in `HANDOVER.md` §5):

- **16 starts** surfaced a destination their own Wikipedia article already links — the definition of
  unsurprising (`plato ⇢ Alexander the Great`, `constantinople ⇢ Constantine the Great`).
- **12 of those were "starved"**: *every* candidate within the pair's 1–2 hop range (ADR 0027) was
  directly co-occurring. No scoring change can fix those — there is no distant destination to rank.
  Every starved start had graph-degree 1–4, so its 2-hop reach was its own cluster.

That independently re-confirms ADR 0014's conclusion — **breadth is the higher-leverage
investment** — and sharpens it: what peripheral nodes need is not neighbours but **edges that escape
their cluster**. The Renaissance is the cluster that does the most work per node: it fills both empty
realms *and* hands `plato` and `constantinople` a way out of the classical core.

## Decision

Add **10 nodes / 17 statements**, seed **88 → 98 nodes / 123 → 140 statements**.

Nodes — `culture`: Renaissance, Renaissance humanism · `art`: Leonardo da Vinci, Michelangelo,
Mona Lisa · `geography`: Florence · `genealogy`: House of Medici · `science`: Printing press ·
`history`: Johannes Gutenberg, Fall of Constantinople.

Domains follow established seed convention rather than intuition: inventions are `science`
(matching paper/gunpowder/compass), so the press is `science` and **Gutenberg is `history`** — the
mirror of `cai_lun → paper`, already in the graph.

Three **independent bridges** keep it from being an island — the cluster is connected even if any one
is removed:

1. **Antiquity** — `renaissance_humanism --influenced_by--> plato` (Ficino's Medici-funded Platonic
   Academy translated Plato's complete works) and `--> ancient_greece`.
2. **Byzantium** — `renaissance --influenced_by--> fall_of_constantinople --located_in-->
   constantinople`.
3. **China** — `printing_press --influenced_by--> paper`, reaching `cai_lun` and the Silk Road. This
   is the cluster's best TIL: **Gutenberg → Printing press → Paper → Silk Road** — Europe's printing
   revolution ran on a Chinese invention.

### What was deliberately *not* claimed

- **Chinese movable type → Gutenberg.** The popular direct-transmission story is genuinely contested
  by historians. The graph instead asserts only the documented part — the press printed on *paper*,
  whose westward transmission (Talas 751 → Abbasid papermaking → Europe) is textbook. The China
  bridge survives without an overclaim. Correctness is the north star; a "better" TIL is not worth a
  disputed edge.
- **`copernicus --part_of--> renaissance`** — written, then **removed after measuring it**. It
  hijacked ADR 0019's flagship: Copernicus's top journey became
  `Copernicus → Renaissance → Florence → House of Medici`, and al-Tusi fell out of the top 4
  entirely. The edge is the vaguest of the set (`part_of` a cultural *era*, for a figure whose
  defining context is the Ptolemy→al-Tusi lineage), it traded a genuine wow for a walking tour with
  a dull endpoint, and the science↔culture bridge already exists via `renaissance_humanism → plato`.
  Removing it restored `Copernicus → al-Tusi → Euclid → …` to #1. Recorded because the failure mode
  generalises: **a dense new sub-cluster can out-compete on domain jumps and hijack an existing
  flagship** — the metric to watch when adding any cluster.

## Consequences

- **`culture` 0 → 2, `art` 1 → 4, `genealogy` 2 → 3.** No curated node uses `other` (locked by test).
- **Both predicted starved starts relieved** — `plato ⇢ Renaissance humanism` and
  `constantinople ⇢ Renaissance` are now genuinely *unlinked* destinations. Directly-co-occurring
  pair winners: **16/88 (18.2%) → 15/98 (15.3%)**.
- **Trojan War became a confident topic.** `ancient_greece --influenced_by--> renaissance_humanism`
  gives it a strict (non-`possibly`) journey — `Trojan War → Homer → Ancient Greece → Renaissance
  humanism`. This *broke a test on an improvement*: `test_site` had pinned "speculative topic" to
  `trojan_war`. Rewritten as a property over all 98 topics (strict never contains a `possibly` card;
  strict ⊆ loose — verified: 0 displacements; strictly additive for at least one topic). More robust
  and no longer a bet on one topic's evidence level.
- **`test_layout::test_single_node_domain_is_placed` likewise de-pinned** — it asserted "the seed has
  a single-node domain (`art`)", which this ADR falsified. The invariant (a lone node's domain
  centroid is itself → zero cohesion force, no 0/0) is real; it now runs on a constructed graph, so
  seed composition can't break it again.
- `eval/golden.json` needed **no re-characterisation** — no locked winner shifted.
- All 98 QIDs verified live (`validate-qids`); **4 of 11 from-memory QID guesses were wrong** again
  (Renaissance humanism is Q846933 not Q179277; printing press Q144334; Fall of Constantinople
  Q160077; House of Medici Q170022) — the ADR 0008 failure mode, caught by the recipe.
- Co-occurrence rebuilt for 98 nodes. Zero-LLM, deterministic, hand-reproducible. All green (ruff,
  format, mypy, **125 tests**).
