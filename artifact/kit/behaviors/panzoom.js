/* panzoom.js — drag / wheel-zoom-at-cursor / pinch / fit for a large canvas.
   Markup:
     <div id="host" style="position:relative;overflow:hidden;touch-action:none">
       <div id="canvas" style="position:absolute;top:0;left:0;transform-origin:0 0;width:max-content">
         …big SVG or content…
       </div>
     </div>
   Usage:
     const pz = PanZoom(host, canvas, { min: .12, max: 5 });
     fitBtn.onclick = pz.fit;   plusBtn.onclick = () => pz.zoomBy(1.25);
     pz.centerOn(el)            // pan so el is centered (e.g. jump-to-node)
   Toggles 'grabbing' on host while dragging — style the cursor yourself. */
function PanZoom(host, canvas, opts = {}) {
  const min = opts.min ?? 0.12, max = opts.max ?? 5;
  const s = { tx: 0, ty: 0, sc: 1 };
  const ptrs = new Map();
  let pinchD = 0;

  function apply() {
    canvas.style.transform = `translate(${s.tx}px,${s.ty}px) scale(${s.sc})`;
  }
  function zoomAt(f, px, py) {
    const ns = Math.min(max, Math.max(min, s.sc * f));
    f = ns / s.sc;
    s.tx = px - (px - s.tx) * f;
    s.ty = py - (py - s.ty) * f;
    s.sc = ns;
    apply();
  }
  function fit() {
    const hr = host.getBoundingClientRect();
    const cw = canvas.scrollWidth, ch = canvas.scrollHeight;
    if (!cw || !ch) return;
    s.sc = Math.min(max, Math.max(min, Math.min(hr.width / cw, hr.height / ch) * 0.92));
    s.tx = (hr.width - cw * s.sc) / 2;
    s.ty = (hr.height - ch * s.sc) / 2;
    apply();
  }

  host.addEventListener('wheel', e => {
    e.preventDefault();
    const r = host.getBoundingClientRect();
    zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  host.addEventListener('pointerdown', e => {
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    host.setPointerCapture(e.pointerId);
    if (ptrs.size === 1) host.classList.add('grabbing');
  });
  host.addEventListener('pointermove', e => {
    const p = ptrs.get(e.pointerId);
    if (!p) return;
    if (ptrs.size === 1) {
      s.tx += e.clientX - p.x;
      s.ty += e.clientY - p.y;
      apply();
    } else if (ptrs.size === 2) {
      const [a, b] = [...ptrs.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinchD) {
        const r = host.getBoundingClientRect();
        zoomAt(d / pinchD, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
      }
      pinchD = d;
    }
    p.x = e.clientX; p.y = e.clientY;
  });
  const up = e => {
    ptrs.delete(e.pointerId);
    if (ptrs.size < 2) pinchD = 0;
    if (ptrs.size === 0) host.classList.remove('grabbing');
  };
  host.addEventListener('pointerup', up);
  host.addEventListener('pointercancel', up);

  function centerOn(el) {
    const nr = el.getBoundingClientRect(), hr = host.getBoundingClientRect();
    s.tx += hr.left + hr.width / 2 - (nr.left + nr.width / 2);
    s.ty += hr.top + hr.height / 2 - (nr.top + nr.height / 2);
    apply();
  }

  fit();
  return { fit, zoomAt, zoomBy: f => {
    const hr = host.getBoundingClientRect();
    zoomAt(f, hr.width / 2, hr.height / 2);
  }, centerOn, state: s };
}
