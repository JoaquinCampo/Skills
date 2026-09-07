# Callout

A short block that must not be skimmed past: a caveat, a decision, a risk, a result. One or two per screen.

**Don't use for**: ordinary paragraphs (if everything is called out, nothing is), long content (use a section), or state on a data row (use `status-pill.md`).

## Markup

```html
<div class="k-callout warn">
  <strong class="k-callout-title">Partial data</strong>
  Metrics before June 12 predate the new event schema; comparisons across
  that boundary undercount by roughly 8%.
</div>
```

Variants: `info` (context, decisions), `ok` (verified result), `warn` (caveat, degraded confidence), `crit` (blocker, active risk). Unclassed = neutral aside.

## CSS

```css
.k-callout {
  padding: var(--sp-3) var(--sp-4);
  border-left: 3px solid var(--border-strong);
  border-radius: var(--r-sm);
  background: var(--surface-sunken);
  font-size: var(--fs-sm);
  line-height: 1.55;
  color: var(--text-2);
}
.k-callout-title {
  display: block;
  margin-bottom: 2px;
  font-weight: 600;
  color: var(--text);
}
.k-callout.info { background: var(--accent-soft); border-color: var(--accent); }
.k-callout.ok   { background: var(--ok-soft);     border-color: var(--ok); }
.k-callout.warn { background: var(--warn-soft);   border-color: var(--warn); }
.k-callout.crit { background: var(--crit-soft);   border-color: var(--crit); }
```

## Rules

- The title states the point ("Partial data"), not the category ("Warning") — the color already says that.
- Body text explains what it means for the viewer and what to do, in one or two sentences.
- No emoji or icon prefixes; the stripe and tint are the signal.
