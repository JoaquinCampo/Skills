/* hoverdim.js — hover a graph node to isolate its ego-network; click pins; Esc unpins.
   Markup contract:
     container (svg or div) holds nodes matching nodeSel with data-id="…"
     and edges matching edgeSel with data-a="…" data-b="…".
   It toggles classes only — YOU style them:
     container.dim  .node:not(.hot) { opacity:.2 }   container.dim .edge:not(.ehot) { opacity:.1 }
   Usage:
     HoverDim(svg, { nodeSel: 'g.n', edgeSel: '.edge',
                     onFocus(id, el){ card.show(id) }, onBlur(){ card.hide() } });
   Nodes get tabindex for keyboard focus (Tab + Enter to pin). */
function HoverDim(container, opts) {
  const nodes = [...container.querySelectorAll(opts.nodeSel)];
  const edges = [...container.querySelectorAll(opts.edgeSel)];
  const nb = {};
  nodes.forEach(n => (nb[n.dataset.id] = new Set()));
  edges.forEach(e => {
    nb[e.dataset.a]?.add(e.dataset.b);
    nb[e.dataset.b]?.add(e.dataset.a);
  });
  let pinned = null;

  function clear() {
    container.classList.remove('dim');
    container.querySelectorAll('.hot,.ehot').forEach(x => x.classList.remove('hot', 'ehot'));
  }
  function focus(id) {
    clear();
    container.classList.add('dim');
    nodes.forEach(n => {
      if (n.dataset.id === id || nb[id]?.has(n.dataset.id)) n.classList.add('hot');
    });
    edges.forEach(e => {
      if (e.dataset.a === id || e.dataset.b === id) e.classList.add('ehot');
    });
    opts.onFocus?.(id, nodes.find(n => n.dataset.id === id));
  }
  function blur() {
    if (pinned) { focus(pinned); return; }
    clear();
    opts.onBlur?.();
  }

  nodes.forEach(n => {
    n.setAttribute('tabindex', '0');
    n.addEventListener('pointerenter', () => { if (!pinned) focus(n.dataset.id); });
    n.addEventListener('pointerleave', blur);
    n.addEventListener('focus', () => { if (!pinned) focus(n.dataset.id); });
    n.addEventListener('blur', blur);
    const pin = () => {
      pinned = pinned === n.dataset.id ? null : n.dataset.id;
      pinned ? focus(pinned) : (clear(), opts.onBlur?.());
    };
    n.addEventListener('click', pin);
    n.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pin(); } });
  });
  addEventListener('keydown', e => {
    if (e.key === 'Escape' && pinned) { pinned = null; clear(); opts.onBlur?.(); }
  });
  return { focus, clear, neighbors: nb };
}
