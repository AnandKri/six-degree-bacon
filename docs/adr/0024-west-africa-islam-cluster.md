# ADR 0024 — Breadth: the West Africa (Mali / Timbuktu) cluster + an Islam hub

- **Status:** accepted
- **Phase:** 2

## Context

The seed had no sub-Saharan Africa and, despite a whole Islamic Golden Age cluster (Abbasid, Baghdad,
House of Wisdom, al-Khwarizmi), no node for **Islam** itself. Medieval West Africa — the **Mali
Empire**, **Mansa Musa** (whose 1324 hajj is legendary), and **Timbuktu** (a great centre of
trans-Saharan trade and Islamic learning) — is a rich, widely-known region, but it only connects to
the rest of the world through Islam and the trans-Saharan trade. Adding an `islam` node both fixes
that gap (giving the existing Islamic cluster its religion) and provides the bridge that keeps West
Africa from being an island.

## Decision

Add five verified nodes — Mali Empire (Q184536, `history`), Mansa Musa (Q309333, `history`),
Timbuktu (Q9427, `geography`), Trans-Saharan trade (Q465279, `trade`), Islam (Q432, `religion`) —
with nine sourced statements:

- `mansa_musa part_of mali_empire`, `timbuktu located_in mali_empire`, `timbuktu influenced_by
  mansa_musa` — the internal West-African structure.
- `mali_empire connected_via_trade trans_saharan_trade`, `timbuktu on_trade_route
  trans_saharan_trade` — the gold/salt caravan economy.
- `mansa_musa influenced_by islam`, `timbuktu influenced_by islam` — the Islamic character of Mali
  and Timbuktu's scholarship.
- `islam follows zoroastrianism` (Islam succeeded Zoroastrianism in post-conquest Persia) and
  `abbasid_caliphate part_of islam` — the two edges that wire the new Islam hub into the existing
  graph (the Persia/Zoroastrian thread and the Islamic Golden Age cluster).

QIDs verified against Wikidata (label → Wikipedia article → `wikibase_item`); `validate-qids`
(81/81) → `build-cooccurrence` (81). The `islam follows zoroastrianism` edge keeps high trust (~0.86)
— no temporal-implausibility penalty, since Islam postdates Zoroastrianism's founding.

## Consequences

- **Five new topics** with genuine trans-continental reach — e.g. the flagship `Mansa Musa → Islam →
  Zoroastrianism → Mithra` (a West-African emperor to an Indo-Iranian deity), `Islam →
  Zoroastrianism → Persia → Silk Road`, and `Trans-Saharan trade → Timbuktu → Mansa Musa → Islam`.
  Mansa Musa's improbable pairs reach the Abbasid world in two hops. A property-based test locks that
  the cluster escapes West Africa through the Islam hub, which itself ties into the Persia/Zoroastrian
  thread.
- **Golden winners unchanged** (Roman Empire → India, Christianity → Paper, Euclid → India); no
  `eval/golden.json` change.
- Seed now **81 nodes / 116 statements** across 9 domains. Still zero-LLM, deterministic, and
  hand-reproducible; all checks green (91 tests).
