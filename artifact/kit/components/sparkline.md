# Sparkline

An inline trend next to the number it explains — inside a stat tile, a table cell, or a definition value. It answers "which way is this going", not "what are the values".

**Don't use for**: anything needing axes, legends, or precise reading (use a real chart — see the `dataviz` skill), or fewer than ~6 points.

## Markup

Fixed dimensions; the SVG is decorative-with-meaning, so give it a label and hide it from the reading order:

```html
<svg class="k-spark" width="120" height="32" viewBox="0 0 120 32"
     role="img" aria-label="Error rate trend, last 14 days: falling">
  <path class="k-spark-area" d="M0,26 L9.2,24 L18.5,25 L27.7,20 L36.9,22 L46.2,16
    L55.4,18 L64.6,12 L73.8,14 L83.1,9 L92.3,11 L101.5,7 L110.8,8 L120,5
    L120,32 L0,32 Z"/>
  <path class="k-spark-line" d="M0,26 L9.2,24 L18.5,25 L27.7,20 L36.9,22 L46.2,16
    L55.4,18 L64.6,12 L73.8,14 L83.1,9 L92.3,11 L101.5,7 L110.8,8 L120,5"/>
  <circle class="k-spark-dot" cx="120" cy="5" r="2.5"/>
</svg>
```

## CSS

```css
.k-spark { display: block; overflow: visible; }
.k-spark-line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.5;
  stroke-linejoin: round;
}
.k-spark-area {
  fill: var(--accent);
  opacity: 0.12;
  stroke: none;
}
.k-spark-dot { fill: var(--accent); }

/* semantic variant when the trend itself is a judgment */
.k-spark.good .k-spark-line, .k-spark.good .k-spark-dot { stroke: var(--ok); fill: var(--ok); }
.k-spark.good .k-spark-line { fill: none; }
.k-spark.good .k-spark-area { fill: var(--ok); }
.k-spark.bad  .k-spark-line, .k-spark.bad .k-spark-dot { stroke: var(--crit); fill: var(--crit); }
.k-spark.bad  .k-spark-line { fill: none; }
.k-spark.bad  .k-spark-area { fill: var(--crit); }
```

## Generating the points

Map values to the viewBox in code, don't eyeball:

- `x_i = i / (n - 1) * width`
- `y_i = height - pad - (v_i - min) / (max - min) * (height - 2*pad)` with `pad ≈ 3`
- If `max === min`, draw a flat line at mid-height.
- Round to one decimal. The area path is the line path plus `L{width},{height} L0,{height} Z`.

## Rules

- Anatomy is line + faint area fill + emphasized endpoint. The endpoint dot is the "now" — always include it.
- Fixed `width`/`height` attributes — a sparkline never resizes with its container.
- The `aria-label` states the conclusion ("falling"), not the data.
- No axes, gridlines, or labels — the neighboring number provides the scale.
