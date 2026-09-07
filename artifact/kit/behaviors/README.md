# Behaviors — reusable interaction code

Battle-tested vanilla-JS modules with **no visual opinion**. Unlike visual components,
sharing behavior code does not homogenize artifacts — it just prevents re-implementing
pan/zoom math badly. Copy the module's contents inline into the artifact's `<script>`
(artifacts are self-contained; never `<script src>`), style the class names it toggles
with the page's own tokens.

All modules: no dependencies, respect `prefers-reduced-motion`, safe to include together.

| Module | Gives you | Used for |
|---|---|---|
| `tooltip.js` | one fixed-position tooltip singleton for the whole page | charts, networks, matrices |
| `panzoom.js` | drag / wheel-zoom-at-cursor / pinch / fit on a canvas div | large graphs, maps, decision trees |
| `hoverdim.js` | hover isolates a node's ego-network, click pins, Esc unpins | citation/dependency/system graphs |
| `stepper.js` | step buttons + play-once-on-scroll (IntersectionObserver) | state-over-time widgets |
| `linechart.js` | data-driven line chart renderer with tabs + tooltip hooks | quantitative tradeoffs |

Wiring conventions the modules expect:

- `hoverdim`: nodes are elements matching `nodeSel` with `data-id`; edges match `edgeSel`
  with `data-a`/`data-b`. It toggles `dim` on the container, `hot` on nodes, `ehot` on
  edges — you style those.
- `stepper`: buttons carry `data-k`; you provide `apply(k)`; it manages `aria-pressed`
  and autoplay.
- `linechart`: pure function of `(svgEl, spec)`; call again to re-render for a tab switch.
- `panzoom`: `host` is the viewport (gets `grabbing` class), `canvas` the transformed
  child (`transform-origin: 0 0` required).
