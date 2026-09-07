# Page header

The quiet header for utilitarian pages: eyebrow, title, context line, optional actions. This is the anti-hero — it orients, then gets out of the way.

**Don't use for**: editorial pages (those open with a thesis, designed bespoke).

## Markup

```html
<header class="k-page-header">
  <div>
    <span class="k-eyebrow">Weekly report</span>
    <h1 class="k-title">Checkout reliability — week 27</h1>
    <div class="k-meta">
      <span>Jun 29 – Jul 5, 2026</span>
      <span>·</span>
      <span>Generated Jul 3, 14:20 UTC</span>
    </div>
  </div>
  <div class="k-header-actions">
    <button class="k-btn">Export</button>
    <button class="k-btn primary">Share</button>
  </div>
</header>
```

## CSS

```css
.k-page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
  padding-bottom: var(--sp-4);
  margin-bottom: var(--sp-5);
  border-bottom: 1px solid var(--border);
}
.k-eyebrow {
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
}
.k-title {
  margin: var(--sp-1) 0;
  font-family: var(--font-display);
  font-size: var(--fs-2xl);
  font-weight: 650;
  line-height: 1.15;
  color: var(--text);
  text-wrap: balance;
}
.k-meta {
  display: flex;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  color: var(--text-3);
}
.k-header-actions {
  display: flex;
  gap: var(--sp-2);
}
.k-btn {
  padding: 6px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--r-sm);
  background: var(--surface);
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}
.k-btn:hover { background: var(--surface-sunken); }
.k-btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
}
.k-btn.primary:hover { filter: brightness(1.08); }
```

## Rules

- The eyebrow classifies (what kind of page), the title names the subject, the meta line dates and scopes it. Don't repeat one in another.
- Buttons say what happens ("Export", "Share") — one `primary` at most.
- Omit the actions block entirely when there are no real actions; never decorative buttons.
- The `·` separators are presentational; keep meta items short enough to wrap gracefully on mobile.
