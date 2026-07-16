# ADR 0031 — Map-first UI: a bird's-eye view of the knowledge base, terminal-themed

- **Status:** accepted
- **Phase:** 2

## Context

The web UI (ADR 0013) and its static export (ADR 0015) were a single 820px column: type a topic, get
two cards. The knowledge base — 88 nodes, 123 sourced statements, 10 domains, grown cluster by cluster
across ADRs 0016–0026 — was never shown; a user could only ever see the 3 hops the ranker chose. The
only graph-drawing code in the repo, `sdb/viz.py`, renders a *single path* as a matplotlib PNG and is
orphaned (imported by nothing).

The ask: make the **map the product** — the whole graph on landing, musicmap.info-style domain
territories, search as an overlay, and a discovered route lighting up *in place* on the map — and
re-skin it to match the owner's portfolio ("minimal terminal": dark slate, a single teal accent, mono
type, square corners, no gradients).

Hard constraints inherited from ADR 0013/0015 (all enforced by tests):

- **Self-contained page**, no external assets: the packaged `index.html` must contain no `src=`,
  `cdn`, `https://`, or `http://`. This notably forbids the usual
  `document.createElementNS("http://www.w3.org/2000/svg", …)` — the literal `http://` alone fails CI.
- **One dual-mode page**, byte-identical between `sdb serve` and the static export.
- The UI is a **pure consumer of `discover()`** and must never change a score.

## Decision

Rebuild `sdb/static/index.html` as a map-first page, adding a graph payload but no engine change.

**Graph payload, same dual-mode seam as ADR 0015.** `graph_payload(graph)` (in `sdb/web.py`) returns
laid-out nodes (`compute_layout`, ADR 0030) + de-duplicated undirected edges; it is served live at a
new `/api/graph` route (computed once, cached) and baked into the static bundle under a new `graph`
key. Each hop in a result now also carries `from_id`/`to_id` (added to `_hop_payload`) so the page can
join a route step back to a map node and light it. The page probes `./data.json`: found → static
(read `graph`/`results`); absent → live (`/api/graph`, `/api/discover`). No second template to drift.

**SVG built as `innerHTML` strings, never `createElementNS`.** The `<svg>` shell is authored in the
HTML (the parser namespaces it — no `xmlns` needed); territories, edges, nodes, and the route are
composed as strings and assigned to group elements' `innerHTML`, which inherits the SVG namespace.
This keeps the map fully interactive with **zero `http://` in the page**, so the self-containment test
stays strict rather than being weakened.

**Terminal theme, CSS-variable based.** Dark-only slate (`--bg #0f172a`, panels `#1e293b`, borders
`#334155`), a single teal accent (`--accent #5eead4`) reserved entirely for the discovered route,
selection, hover, and glow; mono chrome (JetBrains Mono → system mono fallback) with Roboto for body
copy; square corners, flat fills, 1px dividers, no gradients (an SVG dot-grid gives the terminal
canvas without one). Colours stay CSS variables so `build-site --theme` can still re-skin.

**A realm taxonomy for colour — display-only, never scoring.** Colour cannot carry all 10 domains:
run against the actual slate surface, a 10-hue set fails the dataviz colourblind checks, and even the
standard 8-hue palette collapses to ΔE 2.5 (blue↔violet, protanopia) under the *all-pairs* test a
node-link map requires. So the 10 domains are grouped into **5 presentational realms** (World,
Expression, Knowledge, Power, Belief) used as soft territory tints, node fills, and labels; the exact
domain is always named in the tooltip/card. The 5 hues are teal-harmonised and validated all-pairs in
dark at worst ΔE **11.5**, with teal deliberately excluded so the route never competes with a realm.
**Scoring stays on the 10-domain axis** — the realm grouping exists only in the page.

The map itself: full-viewport pannable/zoomable SVG (wheel, drag, pinch; level-of-detail labels),
click a node → `discover` for that node → the route inks in teal, the field dims, and a card slides in
(side panel on desktop, bottom sheet on mobile) with the TIL, trust/surprise meters, the sourced
chain, a journey ⇄ improbable-pair toggle, and a `+ speculative` gate toggle.

## Consequences

- **The knowledge base is finally visible** — all 88 nodes as clustered territories, and the product
  moment (a surprising sourced route) reads at a glance because teal is the only thing that lights up.
- **No drift, no new dependency, no score touched.** The page stays byte-identical across `serve` and
  the static export (the packaged-page test still passes), the engine is untouched (a pure consumer of
  `discover()`), and the static bundle grew by the graph payload (~25 KB) plus the hop ids.
- **Honest costs.** Fonts use a system mono/sans stack (named JetBrains Mono / Roboto first): the
  self-contained rule forbids loading Google Fonts, and inlining ~100 KB of woff2 was judged not worth
  the page weight — a device with the fonts installed renders them, others get a clean fallback.
  Realm colour merges domains (myth + religion share one tint), and cross-domain bridge nodes sit
  between territories (per ADR 0030) — both mitigated by in-place labels.
- New tests: the graph payload (laid-out nodes, resolvable de-duplicated edges), hop `from_id`/`to_id`
  resolution, a `/api/graph` HTTP round-trip, and the static bundle's `graph` key. `sdb/viz.py` is
  left as-is (still orphaned; a separate cleanup). Still zero-LLM, deterministic, reproducible by hand;
  all checks green (120 tests).
