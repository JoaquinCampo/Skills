# SVG diagram scaffold

Shared conventions for system maps, flows, and architecture diagrams — the defs, classes, and layer structure to start from so every diagram in a document reads as one system. Pair with the skill's "Efficient SVG iteration loop" for the design process itself.

**Don't use for**: charts (see `dataviz`), decorative/generative graphics (use Canvas), or anything expressible as a list or table.

## Scaffold

```html
<div class="k-diagram-wrap">
<svg class="k-diagram" viewBox="0 0 720 300" role="img"
     aria-label="Request flow: client through gateway to services">
  <defs>
    <marker id="k-arrow" viewBox="0 0 8 8" refX="7" refY="4"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L8,4 L0,8 Z" class="k-arrowhead"/>
    </marker>
  </defs>

  <!-- layer order = z-order: lanes, then edges, then nodes, then labels -->
  <g class="k-lanes">
    <rect class="k-lane" x="8" y="8" width="704" height="130"/>
    <text class="k-lane-label" x="24" y="30">USER-FACING</text>
    <rect class="k-lane" x="8" y="150" width="704" height="140"/>
    <text class="k-lane-label" x="24" y="172">SUPPORT</text>
  </g>

  <g class="k-edges">
    <path class="k-edge" d="M188,80 H300" marker-end="url(#k-arrow)"/>
    <path class="k-edge dashed" d="M370,110 V190" marker-end="url(#k-arrow)"/>
  </g>

  <g class="k-nodes">
    <g class="k-node primary">
      <rect x="60" y="52" width="128" height="56" rx="6"/>
      <text x="124" y="76">Client</text>
      <text class="k-node-sub" x="124" y="93">web + mobile</text>
    </g>
    <g class="k-node">
      <rect x="300" y="52" width="140" height="56" rx="6"/>
      <text x="370" y="84">API gateway</text>
    </g>
    <g class="k-node support">
      <rect x="300" y="196" width="140" height="52" rx="6"/>
      <text x="370" y="226">Audit log</text>
    </g>
  </g>
</svg>
</div>
```

## CSS

```css
.k-diagram-wrap { overflow-x: auto; } /* diagram scrolls here, never the page */
.k-diagram {
  display: block;
  width: 100%;
  height: auto;      /* viewBox preserves aspect */
  max-width: 760px;
  min-width: 560px;  /* below this, labels shrink past legibility — scroll instead */
  font-family: var(--font-body);
}
.k-lane { fill: var(--surface-sunken); rx: 8px; }
.k-lane-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  fill: var(--text-3);
}
.k-edge {
  fill: none;
  stroke: var(--text-3);
  stroke-width: 1.5;
}
.k-edge.dashed { stroke-dasharray: 4 4; }
.k-arrowhead { fill: var(--text-3); }

.k-node rect { fill: var(--surface); stroke: var(--border-strong); stroke-width: 1.5; }
.k-node text {
  fill: var(--text);
  font-size: 13px;
  font-weight: 600;
  text-anchor: middle;
}
.k-node .k-node-sub { fill: var(--text-3); font-size: 11px; font-weight: 400; }
.k-node.primary rect { fill: var(--accent-soft); stroke: var(--accent); }
.k-node.support rect { stroke: var(--border); }
.k-node.support text { fill: var(--text-2); }
```

## Rules

- Inline the SVG in the HTML so page CSS (and both themes) style it — never an `<img>`.
- Layer groups in z-order: lanes → edges → nodes → free labels. Name groups by meaning.
- Visual priority: `primary` nodes are accent-tinted and user-facing; `support` nodes are quieter and lower on the canvas. Machinery never outweighs the user surface.
- Straight or single-bend connectors, `marker-end` arrowheads, no crossings if reordering can avoid them; `dashed` = async/optional.
- Real `<text>` (selectable, themeable), ≥11px at rendered size. If labels don't fit at mobile width, restructure — stack lanes, or let the container scroll horizontally — don't shrink type.
- Center text in nodes with `text-anchor: middle` at the rect's midpoint x; check every label for clipping before completion.
