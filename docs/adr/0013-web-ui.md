# ADR 0013 — Interactive web UI (`sdb serve`)

- **Status:** accepted
- **Phase:** 2

## Context

The engine reached a usable MVP (CLI only). A visual interface was a documented graduation ("a web
UI, Gradio on a free HF Space — only when earned"), now earned: non-engineers need to try it, and the
project needs something demo-able and deployable. The constraint is unchanged — local-first, minimal
cost, zero-LLM, everything behind an interface.

## Decision

Ship a **zero-dependency** web UI, `sdb serve`, over Python's stdlib :mod:`http.server` rather than
Gradio. It wraps the existing `discover()` with **no engine change**:

- `sdb/web.py` — a threaded server with two routes: `/` serves one self-contained page
  (`sdb/static/index.html`, inline CSS/JS, no external assets — packaged as data, loaded via
  `importlib.resources`), and `/api/discover` returns JSON. The request handler is a thin shell over
  `discover_payload()`, a pure, offline-testable function that turns a topic into a JSON-friendly
  dict (journey + improbable-pair cards, each with the phrased hop chain, TIL, trust/surprise, and
  sources).
- `PORT` is read from the environment, so free hosts (Render, a Hugging Face **Docker** Space,
  Fly.io, Cloud Run) run it as-is; `--host 0.0.0.0` for deployment.

**Why stdlib over Gradio.** It matches the project's demonstrated ethos (the Wikidata client is
stdlib `urllib`, "no new dependencies" — ADR 0004): the core stays dependency-light, the page is a
single reviewable artifact, and it deploys anywhere Python runs. Gradio would add a heavy stack
(fastapi/uvicorn/pandas) for UI we can hand-write cleanly.

**Determinism → a static-export path (documented, not yet built).** Because results are deterministic
and the seed is small, the same payloads can be pre-rendered into a static bundle that GitHub
Pages/Netlify host for free; the live server is the interactive path, the static export the zero-ops
one.

## Consequences

- `sdb serve` gives interactive local testing and a deployable demo with no new runtime dependency.
- Tested offline: `discover_payload` (structure, not-found, speculative gate) plus a real localhost
  HTTP round-trip (page + JSON + 404) on an ephemeral port — no external network.
- The engine is untouched; the UI is a pure consumer of `discover()`, so it can never change a score.
- GitHub Pages cannot host the *live* Python app; the static-export graduation covers that when built.
