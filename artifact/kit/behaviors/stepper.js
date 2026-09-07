/* stepper.js — step buttons + optional play-once-when-scrolled-into-view.
   Usage:
     Stepper({
       buttons: document.querySelectorAll('#steps button'),  // each has data-k="0..N"
       apply(k) { …render state k… },                        // you own the rendering
       autoplay: { observe: gridEl, interval: 900 },         // optional
     });
   Manages aria-pressed on the buttons. Autoplay runs ONCE (IntersectionObserver,
   threshold .4) and is skipped entirely under prefers-reduced-motion. */
function Stepper(opts) {
  const btns = [...opts.buttons];
  const maxK = Math.max(...btns.map(b => +b.dataset.k));
  function apply(k) {
    opts.apply(k);
    btns.forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.k === k)));
  }
  btns.forEach(b => b.addEventListener('click', () => apply(+b.dataset.k)));
  apply(0);

  const reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;
  if (opts.autoplay && !reduce) {
    const io = new IntersectionObserver(es => {
      es.forEach(e => {
        if (!e.isIntersecting) return;
        io.disconnect();
        let k = 0;
        const iv = setInterval(() => {
          k++;
          if (k > maxK) { clearInterval(iv); return; }
          apply(k);
        }, opts.autoplay.interval ?? 900);
      });
    }, { threshold: 0.4 });
    io.observe(opts.autoplay.observe);
  }
  return { apply };
}
