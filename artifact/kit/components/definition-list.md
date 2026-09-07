# Definition list

A handful of key-value facts about one thing: metadata, configuration, spec, summary of a record. The right tool when a table would have only one row.

**Don't use for**: comparing multiple records (use `data-table.md`) or more than ~10 pairs (group into sections).

## Markup

```html
<dl class="k-dl">
  <dt>Environment</dt>   <dd>production (eu-west-1)</dd>
  <dt>Version</dt>       <dd class="mono">v2.14.3</dd>
  <dt>Owner</dt>         <dd>payments-team</dd>
  <dt>Status</dt>        <dd><span class="k-pill ok"><span class="k-pill-dot"></span>Healthy</span></dd>
  <dt>Last incident</dt> <dd>none in 90 days</dd>
</dl>
```

## CSS

```css
.k-dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--sp-2) var(--sp-5);
  margin: 0;
  font-size: var(--fs-sm);
}
.k-dl dt {
  color: var(--text-3);
  white-space: nowrap;
}
.k-dl dd {
  margin: 0;
  color: var(--text);
  overflow-wrap: anywhere; /* long ids/urls wrap instead of overflowing */
}
.k-dl dd.mono {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}

/* narrow containers: stack pairs */
@media (max-width: 480px) {
  .k-dl { grid-template-columns: 1fr; gap: 2px; }
  .k-dl dd { margin-bottom: var(--sp-2); }
}
```

## Rules

- Keys in domain language ("Owner", not "assignee_id"); values concrete, never empty — write "none in 90 days", not a blank.
- Identifiers, versions, and hashes go in `.mono`.
- Values can embed other kit parts (a pill, a time) — keys stay plain text.
