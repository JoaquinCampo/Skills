# Status pill

Categorical state that must read at a glance: healthy / degraded / failing, open / merged, active / archived. Use in table cells, list rows, card corners, and headers.

**Don't use for**: continuous values (use a stat or sparkline), actions (use a button), or more than ~5 distinct states in one view — beyond that, states stop being scannable.

## Markup

```html
<span class="k-pill ok"><span class="k-pill-dot"></span>Healthy</span>
<span class="k-pill warn"><span class="k-pill-dot"></span>Degraded</span>
<span class="k-pill crit"><span class="k-pill-dot"></span>Failing</span>
<span class="k-pill info"><span class="k-pill-dot"></span>Deploying</span>
<span class="k-pill neutral"><span class="k-pill-dot"></span>Archived</span>
```

Severity stripe — same semantics on a row or card edge, for tables and lists where a pill per row is too loud:

```html
<tr class="k-stripe crit"> … </tr>
```

## CSS

```css
.k-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.k-pill-dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.k-pill.ok      { color: var(--ok);     background: var(--ok-soft); }
.k-pill.warn    { color: var(--warn);   background: var(--warn-soft); }
.k-pill.crit    { color: var(--crit);   background: var(--crit-soft); }
.k-pill.info    { color: var(--accent); background: var(--accent-soft); }
.k-pill.neutral { color: var(--text-2); background: var(--surface-sunken); }

.k-stripe.ok   { box-shadow: inset 3px 0 0 var(--ok); }
.k-stripe.warn { box-shadow: inset 3px 0 0 var(--warn); }
.k-stripe.crit { box-shadow: inset 3px 0 0 var(--crit); }
```

## Rules

- State color is semantic and separate from the accent; `info` (accent-tinted) is for in-progress/neutral-active states only.
- The label carries the meaning; the color reinforces it. Never a colored dot with no text.
- Pick one device per surface — pills *or* stripes, not both encoding the same state.
