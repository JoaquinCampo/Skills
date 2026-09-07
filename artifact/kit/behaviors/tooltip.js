/* tooltip.js — one fixed tooltip for the whole page.
   Usage:
     const tip = Tooltip();                       // creates and appends the element
     el.addEventListener('pointermove', e => tip.show('<b>label</b><br>detail', e));
     el.addEventListener('pointerleave', () => tip.hide());
   Style via the .tip class (background, font, radius) — module sets only positioning.
   Keep the element a direct child of <body>: an ancestor with transform/filter would
   break position:fixed. */
function Tooltip() {
  const el = document.createElement('div');
  el.className = 'tip';
  el.style.cssText =
    'position:fixed;z-index:70;pointer-events:none;opacity:0;transition:opacity .12s;max-width:260px;';
  document.body.appendChild(el);
  const pad = 14;
  return {
    show(html, e) {
      el.innerHTML = html;
      el.style.opacity = 1;
      this.move(e);
    },
    move(e) {
      // flip to the left of the cursor near the right edge
      const w = el.offsetWidth, h = el.offsetHeight;
      let x = e.clientX + pad, y = e.clientY - 10;
      if (x + w > innerWidth - 8) x = e.clientX - w - pad;
      if (y + h > innerHeight - 8) y = innerHeight - h - 8;
      el.style.left = x + 'px';
      el.style.top = Math.max(8, y) + 'px';
    },
    hide() { el.style.opacity = 0; },
  };
}
