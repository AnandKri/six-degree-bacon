# ADR 0015 — Static-site export for free, zero-ops hosting

- **Status:** accepted
- **Phase:** 2

## Context

The web UI (ADR 0013) needs a Python backend, so it can't live on GitHub Pages (static files only).
But the engine is **deterministic** and the seed is small (41 topics), so every result is
precomputable — the "static-export graduation" flagged in ADR 0013. Goal: a truly free, zero-
maintenance deployment, with **no second UI to maintain**.

## Decision

`sdb build-site` pre-renders the whole graph into a static bundle, and the *same* page runs in either
mode with no transformation:

- **Dual-mode page.** `sdb/static/index.html` probes `fetch("./data.json")` on load. Found → static
  mode (client-side lookup); 404 → live mode (`/api/discover`). The exporter never rewrites the page,
  so the live and static UIs are byte-identical and cannot drift.
- **The bundle** (`sdb/site.py` → `build_site`): `data.json` carries a resolution `index`
  (`id`/`label`/`qid`/`aliases`, for client-side topic resolution and browsing) plus, per topic, both
  UI toggle states — `strict` (default `trust ≥ 0.50` gate) and `loose` (speculative, to the trust
  floor) — each the exact `discover_payload` the live server would return. Plus `index.html` and a
  `.nojekyll` marker. Output (git-ignored `site/`) is ~525 KB of JSON (tens of KB gzipped).
- **Deploy:** `uv run sdb build-site` then publish `site/` — e.g. push it to a `gh-pages` branch (or
  point Pages at `/docs`), or drop it on Netlify. No server, no runtime, no cost.

## Consequences

- A genuinely free, zero-ops hosting path, complementing the live `sdb serve` (Render / HF Docker
  Space / Fly.io) for full interactivity.
- Zero UI drift: one page, two data sources. The static render reuses the live payload shape, so it's
  already covered by the live round-trip test; new offline tests cover the bundle (every topic, both
  toggle states, strict ⊆ loose, page identity). Verified end-to-end: static hosting serves
  `index.html`+`data.json`, live mode still falls back to the API, and the page JS passes `node
  --check`.
- The static bundle is a *snapshot*: regenerate with `build-site` after any seed/co-occurrence
  change. It covers the 41 curated topics (free-text still resolves via label/alias/QID); arbitrary
  `--max-hops` and harvested overlays remain live-only.
