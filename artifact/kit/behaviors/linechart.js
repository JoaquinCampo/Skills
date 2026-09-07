/* linechart.js — data-driven line chart into an <svg viewBox>. Re-call to re-render
   (tabs switch datasets through the same renderer — never hardcode paths).
   Usage:
     const spec = {
       W: 760, H: 400, m: { l: 52, r: 20, t: 18, b: 46 },
       x: { min: 0, max: 50, ticks: [0,10,20,30,40,50], label: 'SESSION DEPTH' },
       y: { min: 25, max: 100, step: 10, label: '% SURVIVING' },
       series: [ { name: 'Heavy', color: '#27508D', pts: [[1,96],[5,94],…] }, … ],
       endLabels: true,                       // print last value beside each line
       gridColor: '#D4C9A8', tickColor: '#7C7258',
       font: 'ui-monospace,monospace',
     };
     LineChart(svgEl, spec, tip);             // tip: a Tooltip() instance or null
   Emits circles with data-series / data-x / data-y for the tooltip. */
function LineChart(svg, spec, tip) {
  const { W, H, m } = spec;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const sx = x => m.l + (x - spec.x.min) / (spec.x.max - spec.x.min) * (W - m.l - m.r);
  const sy = y => H - m.b - (y - spec.y.min) / (spec.y.max - spec.y.min) * (H - m.t - m.b);
  const fx = spec.font || 'ui-monospace,monospace';
  let o = '';
  for (let y = spec.y.min + (spec.y.step - (spec.y.min % spec.y.step)) % spec.y.step;
       y <= spec.y.max; y += spec.y.step) {
    o += `<line x1="${m.l}" y1="${sy(y)}" x2="${W - m.r}" y2="${sy(y)}" stroke="${spec.gridColor}" stroke-width="0.7"/>`;
    o += `<text x="${m.l - 9}" y="${sy(y) + 4}" text-anchor="end" font-size="11" fill="${spec.tickColor}" font-family="${fx}">${y}</text>`;
  }
  for (const x of spec.x.ticks)
    o += `<text x="${sx(x)}" y="${H - m.b + 22}" text-anchor="middle" font-size="11" fill="${spec.tickColor}" font-family="${fx}">${x}</text>`;
  if (spec.x.label) o += `<text x="${W - m.r}" y="${H - 10}" text-anchor="end" font-size="11" fill="${spec.tickColor}" font-family="${fx}">${spec.x.label}</text>`;
  if (spec.y.label) o += `<text x="${m.l}" y="${m.t - 4}" font-size="11" fill="${spec.tickColor}" font-family="${fx}">${spec.y.label}</text>`;
  for (const s of spec.series) {
    o += `<polyline points="${s.pts.map(p => sx(p[0]).toFixed(1) + ',' + sy(p[1]).toFixed(1)).join(' ')}"
           fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linejoin="round"/>`;
    for (const p of s.pts)
      o += `<circle cx="${sx(p[0])}" cy="${sy(p[1])}" r="4.5" fill="${s.color}" stroke="#fff" stroke-width="1.5"
             data-series="${s.name}" data-x="${p[0]}" data-y="${p[1]}"/>`;
    if (spec.endLabels) {
      const last = s.pts[s.pts.length - 1];
      o += `<text x="${sx(last[0]) - 4}" y="${sy(last[1]) - 9}" text-anchor="end" font-size="10.5"
             font-weight="700" fill="${s.color}" font-family="${fx}">${last[1]}</text>`;
    }
  }
  svg.innerHTML = o;
  if (tip && !svg.dataset.tipWired) {
    svg.dataset.tipWired = '1';
    svg.addEventListener('pointermove', e => {
      const t = e.target;
      if (t.tagName === 'circle' && t.dataset.series)
        tip.show(`<b>${t.dataset.series}</b><br>x ${t.dataset.x} · y ${t.dataset.y}`, e);
      else tip.hide();
    });
    svg.addEventListener('pointerleave', () => tip.hide());
  }
}
