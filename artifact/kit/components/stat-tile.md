# Stat tile

A single number the viewer monitors or compares, in a row of 3–5 at the top of a dashboard or report.

**Don't use for**: prose summaries (use a callout), more than ~6 values (promote to a table), or a number with no unit or comparison context — a bare number answers no question.

## Markup

```html
<div class="k-stats">
  <div class="k-stat">
    <span class="k-stat-label">Error rate</span>
    <span class="k-stat-value">0.42<span class="k-stat-unit">%</span></span>
    <span class="k-stat-delta k-delta-good">▼ 0.11 pts vs last week</span>
  </div>
  <div class="k-stat">
    <span class="k-stat-label">P95 latency</span>
    <span class="k-stat-value">218<span class="k-stat-unit">ms</span></span>
    <span class="k-stat-delta k-delta-bad">▲ 34 ms vs last week</span>
  </div>
  <div class="k-stat">
    <span class="k-stat-label">Deploys</span>
    <span class="k-stat-value">12</span>
    <span class="k-stat-delta k-delta-flat">— unchanged</span>
  </div>
</div>
```

## CSS

```css
.k-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--sp-3);
}
.k-stat {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  min-height: 100px; /* stable: value/delta changes must not shift layout */
  padding: var(--sp-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
}
.k-stat-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-3);
}
.k-stat-value {
  font-size: var(--fs-2xl);
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.k-stat-unit {
  margin-left: 2px;
  font-size: var(--fs-md);
  font-weight: 500;
  color: var(--text-2);
}
.k-stat-delta {
  margin-top: auto;
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
}
.k-delta-good { color: var(--ok); }
.k-delta-bad  { color: var(--crit); }
.k-delta-flat { color: var(--text-3); }
```

## Rules

- Good/bad is semantic, not directional: a *drop* in error rate is `k-delta-good`. Decide per metric.
- Encode direction with the glyph and words, not color alone (▲/▼ plus "vs last week").
- Keep `min-height` so live values, longer deltas, or missing deltas don't reflow the row.
- A sparkline (see `sparkline.md`) slots between value and delta when trend matters.
