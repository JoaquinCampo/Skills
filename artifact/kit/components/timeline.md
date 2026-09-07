# Timeline

Typed events in real order: an incident log, a release history, a project narrative. Use only when order carries information the reader needs — otherwise it's a decorated list.

**Don't use for**: unordered items (use a list or table) or two-column layouts of "steps" that aren't actually sequential.

## Markup

```html
<ol class="k-timeline">
  <li class="crit">
    <time class="k-time">14:02</time>
    <div class="k-event-title">Error rate crosses 5% on checkout-api</div>
    <div class="k-event-body">Alert fired; on-call paged.</div>
  </li>
  <li>
    <time class="k-time">14:11</time>
    <div class="k-event-title">Root cause identified</div>
    <div class="k-event-body">Bad config in the 14:00 deploy of payments-worker.</div>
  </li>
  <li class="ok">
    <time class="k-time">14:19</time>
    <div class="k-event-title">Rolled back — error rate recovered</div>
  </li>
</ol>
```

## CSS

```css
.k-timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}
.k-timeline li {
  position: relative;
  padding: 0 0 var(--sp-4) var(--sp-5);
}
.k-timeline li::before { /* marker */
  content: "";
  position: absolute;
  left: 0;
  top: 5px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--surface);
  border: 2px solid var(--text-3);
}
.k-timeline li::after { /* rail */
  content: "";
  position: absolute;
  left: 6px;
  top: 20px;
  bottom: 2px;
  width: 1px;
  background: var(--border);
}
.k-timeline li:last-child { padding-bottom: 0; }
.k-timeline li:last-child::after { display: none; }
.k-timeline li.ok::before   { border-color: var(--ok);   background: var(--ok); }
.k-timeline li.warn::before { border-color: var(--warn); background: var(--warn); }
.k-timeline li.crit::before { border-color: var(--crit); background: var(--crit); }

.k-time {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.k-event-title {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text);
}
.k-event-body {
  font-size: var(--fs-sm);
  color: var(--text-2);
}
```

## Rules

- Type events with marker color (`ok`/`warn`/`crit`); leave routine events neutral so the typed ones stand out.
- Timestamps in one consistent grain (all clock times, or all relative) in the mono face.
- Titles state what happened; bodies are optional and short.
- Long timelines: group by day with a small uppercase date label between groups rather than repeating full dates per event.
