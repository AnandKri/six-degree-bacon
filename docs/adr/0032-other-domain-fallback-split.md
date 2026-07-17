# ADR 0032 — Split the harvest fallback out of `culture` into a dedicated `other` domain

- **Status:** accepted
- **Phase:** 2

## Context

`Domain` declares ten thematic realms, and `sdb/harvest/mapping.py` assigns one to every harvested
node from its `P31` class. Anything unmapped fell back to `DOMAIN_FALLBACK`, which was
**`Domain.CULTURE`** — making `culture` simultaneously:

1. a **substantive realm** a curated node could legitimately belong to, and
2. the **"we don't know" bucket** for every unclassified harvest node.

Those two meanings are incompatible, and the data shows the second had entirely swallowed the first:

| source | `culture` nodes |
| --- | --- |
| `data/seed.json` (curated, 88 nodes) | **0** |
| `data/harvest/roman_2hop.json` (40 nodes) | **24** |
| `data/harvest/q34266.json` (9 nodes) | **8** |

So `culture` was ~100% harvest fallout and 0% culture. This is not cosmetic — the domain is a
**scoring input**: `_domain_jumps` (`W_DOMAIN = 2.0`, the second-heaviest surprise weight) counts a
hop as surprising whenever consecutive nodes' domains differ. Unclassified nodes sharing an identity
with a real realm means a hop into unmapped fallout scored as a genuine cross-domain leap, and a hop
between two *mutually unrelated* unmapped nodes scored as no jump at all. It also misled the map:
`culture` sits in the UI's `expression` realm beside `art`, so unclassified harvest nodes rendered as
a confident amber "Expression" territory.

ADR 0009 attacked this from the supply side, growing `INSTANCE_OF_DOMAIN` by ~44 classes to *reduce*
fallout. That was right and remains right, but it cannot fix the category error: no P31 table is ever
complete, so there will always be fallout, and it should not be wearing a real realm's clothes.

This blocks the intended next step — a Renaissance cluster is the natural way to populate `culture`
and `art`, and curating real culture nodes into the same bucket as unmapped fallout would make the
realm permanently unreadable.

## Decision

Add **`Domain.OTHER = "other"`** and set `DOMAIN_FALLBACK = Domain.OTHER`.

`OTHER` is explicitly *not* a realm: it is the absence of a classification. Three properties keep it
honest:

- **No `P31` class may map to it.** A test asserts `DOMAIN_FALLBACK not in INSTANCE_OF_DOMAIN.values()`,
  so it can only ever be reached by falling through — never by classification. If a class genuinely
  belongs in a realm, that realm must be a real one.
- **No curated node may use it.** It is a harvest-only bucket.
- **It is appended to the enum, never inserted.** `sdb/layout.py:121` builds
  `domain_index = {domain: i for i, domain in enumerate(Domain)}` and seeds positions by
  `(domain, id)`, so the enum's *ordinal order is load-bearing*: inserting `OTHER` mid-enum would
  shift every existing node's seed position and silently change the map, breaking ADR 0030's
  byte-identical guarantee. Appending leaves ordinals 0–9 untouched. **Verified:** the seed's layout
  hashes to `406304a0fb63448a` both before and after this change.

The UI gains a `realmOf(dom)` helper returning `REALM[dom] || "unclassified"` and a neutral grey
`--unclassified` tint. Unclassified nodes are deliberately **absent from the legend**: the legend
documents the five substantive realms, and "unclassified" is not a sixth kind of thing. Previously an
unmapped domain would have produced a `n-undefined` class with no matching CSS — a silent
degradation — so this also makes the map robust to any future domain.

## Alternatives rejected

- **Keep `culture` as the fallback and just curate into it.** The two meanings stay fused; every
  future culture node is diluted by fallout, and `_domain_jumps` keeps scoring fallout as a realm.
- **Give `other` its own realm and legend row.** Presents "we couldn't classify this" as a peer of
  Belief and Knowledge, and adds a permanent legend row for something absent from the shipped map
  (the curated seed has no `other` nodes).
- **Drop unclassified nodes at harvest time.** Loses real connectivity — an unmapped node is still a
  true, sourced link — and would silently shrink harvests.

## Consequences

- `culture` is now free to become a **real realm** with zero fallout in it — the precondition for the
  Renaissance cluster (which targets `culture` + `art`, the two empty/near-empty realms).
- Unclassified harvest nodes stop earning spurious `W_DOMAIN` credit against a substantive realm, and
  stop rendering as a confident "Expression" territory.
- **Existing snapshots in `data/harvest/` are stale** — they have `"domain": "culture"` baked in from
  the old fallback. They are git-ignored local artifacts; re-run `sdb harvest` to regenerate. No
  committed data changes, so **no `build-cooccurrence` or `eval/golden.json` re-characterisation is
  needed** (the curated seed is untouched and has no `other` nodes).
- The map is unchanged for the shipped seed (byte-identical layout, no `other` nodes to draw).
- Zero-LLM, deterministic, hand-reproducible. All green (ruff, format, mypy, **122 tests**).
