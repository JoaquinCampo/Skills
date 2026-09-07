# Data table

Rows the viewer scans, compares, and sorts through: services, runs, invoices, findings. The workhorse of utilitarian pages.

**Don't use for**: 2–3 key-value facts (use `definition-list.md`), or content read as narrative (use prose).

## Markup

```html
<div class="k-table-wrap">
  <table class="k-table">
    <thead>
      <tr>
        <th>Service</th>
        <th>Status</th>
        <th class="num">P95 (ms)</th>
        <th class="num">Errors / min</th>
        <th>Last deploy</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>checkout-api</td>
        <td><span class="k-pill ok"><span class="k-pill-dot"></span>Healthy</span></td>
        <td class="num">218</td>
        <td class="num">0.4</td>
        <td>2h ago</td>
      </tr>
      <tr class="k-stripe crit">
        <td>payments-worker</td>
        <td><span class="k-pill crit"><span class="k-pill-dot"></span>Failing</span></td>
        <td class="num">1,940</td>
        <td class="num">12.7</td>
        <td>41m ago</td>
      </tr>
    </tbody>
  </table>
</div>
```

## CSS

```css
.k-table-wrap {
  overflow-x: auto; /* wide tables scroll here — the page body never does */
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
}
.k-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}
.k-table th {
  position: sticky;
  top: 0;
  padding: 10px 14px;
  background: var(--surface);
  border-bottom: 1px solid var(--border-strong);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: left;
  color: var(--text-3);
  white-space: nowrap;
}
.k-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
.k-table tbody tr:last-child td { border-bottom: 0; }
.k-table tbody tr:hover { background: var(--surface-sunken); }
.k-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
```

## Rules

- Numbers right-aligned with `tabular-nums`; text left-aligned; never center columns.
- Match header alignment to its column (`th.num` right-aligns too).
- Sticky headers only pay off when the wrap or page scrolls vertically; harmless otherwise.
- One state device per table: pills in a status column *or* row stripes, not both.
- Format numbers consistently down a column (same precision, thousands separators).
- Empty state is a designed row — "No runs in this window", spanning all columns, `--text-3` — never a blank table body.
