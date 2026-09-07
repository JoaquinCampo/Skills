# Device catalog — the craft vocabulary for flagship artifacts

Distilled from two reference artifacts that set the bar: an interactive decision-tree
explorer (app treatment) and a long-form paper study guide (editorial-didactic treatment).
What transfers between great artifacts is NOT a shared design system — each derived its
identity from its subject (stationery cream + Iowan Old Style for a paper-goods brand;
teal/lime + Charter for an academic guide). What transfers is this vocabulary of devices.

**Effort calibration**: the bar for a flagship artifact is 10–20 purpose-built devices,
several hundred lines of hand-written interaction JS, and multiple custom visualizations.
A page with one font stack, one accent, and zero interactivity is a utilitarian page —
fine when asked for, never the ceiling.

---

## 1 · Identity devices

**Subject-derived palette.** Name 6–12 CSS custom properties from the subject's world, not
from a neutral system: `--ground/--paper/--ink/--rule` for a stationery brand;
`--ink/--teal/--lime/--coral` for an academic guide. Include at least one *warm/alarm*
tone reserved for "unresolved / watch out" semantics.

**Three-face type system.** A characterful serif for display and reading
(`Charter`, `Iowan Old Style` — real stacks, not Georgia-by-default), a sans for UI and
captions, and a mono doing heavy labeling duty.

*Practical stacks that actually resolve* — webfont CDNs are CSP-blocked and data-URI
embedding is rarely worth it, so the reference artifacts use faces that ship with the
viewer's OS. Pick per subject, and put a real fallback chain behind each:

| Voice | Stack | Resolves as |
|---|---|---|
| Bookish, warm serif | `"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif` | Iowan (mac) / Palatino (win) |
| Rational, academic serif | `"Charter","Bitstream Charter","Sitka Text",Cambria,Georgia,serif` | Charter (mac) / Sitka-Cambria (win) |
| Literary, high-contrast | `"Hoefler Text","Baskerville Old Face",Baskerville,Georgia,serif` | Hoefler (mac) / Baskerville (win) |
| Sturdy news serif | `Superclarendon,"Bookman Old Style",Georgia,serif` | Superclarendon (mac) / Bookman (win) |
| Humanist sans | `Seravek,"Gill Sans Nova",Ubuntu,Calibri,"DejaVu Sans",sans-serif` | Seravek (mac) / Gill Sans Nova (win) |
| Geometric sans | `"Avenir Next",Avenir,Montserrat,Corbel,"URW Gothic",sans-serif` | Avenir (mac) / Corbel (win) |
| Neutral UI sans | `system-ui,-apple-system,"Segoe UI",sans-serif` | native |
| Labeling mono | `ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace` | SF Mono (mac) / Cascadia (win) |

Never let a display role silently fall back to the body face — if the stack can't
guarantee character, choose a different voice deliberately.

The mono is the workhorse of craft:

```css
.eyebrow { font-family: var(--mono); font-size: .72rem; letter-spacing: .16em;
           text-transform: uppercase; color: var(--accent); font-weight: 600; }
```
Every section, box, viz, and figure gets a mono eyebrow. This one device does more for
"designed, not generated" than any palette choice.

**Display type with conviction.** Hero titles at `clamp(3.4rem, 14vw, 8.5rem)`,
`line-height: .86`, `letter-spacing: -.045em`. Timid 28px "page titles" read as generated.

**Wordmark detail.** One micro-flourish in the brand: an italic ampersand in the accent
color, a decode-subtitle bolding the letters of an acronym. Cheap, memorable, specific.

## 2 · Structure devices (long-form)

**Width tiers.** Prose is measure-limited; visualizations and panels break out to full width:

```css
.wrap > * { max-width: var(--measure); }        /* --measure: 82ch */
.wrap > .viz, .wrap > .box, .wrap > figure, .wrap > table { max-width: 100%; }
```

**Reading progress + sticky mono TOC.** 3px fixed progress bar (`--lime`), and a sticky
translucent nav (`backdrop-filter: blur(10px)`) with mono links. Signals "this is a
document you inhabit," costs ~15 lines.

**Full-bleed bands.** Alternate page-ground sections with dark ink-ground bands for
figures, worked examples, and the verdict. The dark band resets attention and makes
figures feel curated (`figure` inside a light shell with
`box-shadow: 0 18px 40px -28px rgb(...)`).

**Numbered parts with learning objectives.** `PART 3 / THE IDEA` eyebrow + "By the end
of this part you can…" list on a dark panel. Only when content is genuinely pedagogical.

## 3 · Explanatory devices

**Semantic box taxonomy.** Not one callout — a *typed system* the reader learns:
Intuition (green, builds the picture) / Key idea (teal, remember this) / Watch out
(coral, notation trap). Each `border-left: 3px` + tinted ground + mono header. Define
2–4 types per page, use them consistently, never mix roles.

**The running example.** One concrete entity (a token `p2`, one product SKU) threaded
through the ENTIRE artifact as an inline chip:

```css
.tk { font-family: var(--mono); padding: 1px 6px; border-radius: 5px;
      background: rgba(21,122,134,.12); color: var(--teal-deep); font-weight: 600; }
```
Every abstract claim gets grounded by returning to the same example with real numbers.
This is the single strongest didactic device in the reference set.

**Worked example panels.** Dark panel, numbered circle steps, mono `calc` blocks with the
result highlighted (`.res { color: var(--lime); font-weight: 700 }`). Real, reproducible
numbers — "computed, not hand-waved."

**Progressive disclosure, typed.** `<details>` in two flavors: `▸ refresher` (prerequisite
material, mono summary) and `Q` self-tests (square Q badge, answer padded under it).
Disclosure isn't just hiding content — it assigns the reader a role (skip / try first).

**Hand-built equation typography.** Fractions, roots, and sums in pure HTML/CSS
(`.frac`, `.sqrt::before { content:"√" }`, `.sum`), color-coding variables vs operators.
No MathJax (CSP), no images. Equation numbers match the source paper.

**Pull quotes and verdict grids.** A serif italic pull quote per major part; a closing
pro/con card grid (`vcard.pro` lime headers / `vcard.con` coral) that renders judgment
instead of trailing off.

## 4 · Interaction devices

Interaction is explanation, not decoration. Budget for it.

**Hover-focus with global dim.** The single highest-value graph interaction: hovering a
node dims everything else and highlights the ego-network:

```css
.host.dim g.node { opacity: .26 }  .host.dim g.edge { opacity: .10 }
.host.dim g.node.hot, .host.dim g.node.hot2 { opacity: 1 }
```
Index nodes/edges by id on load; on hover add `hot` to the node, `hot2` to neighbors,
`ehot` to incident edges. Click pins; Esc or × unpins.

**Detail card on click.** Floating card (bottom-left, `transform/opacity` transition) with
the node's full story: mono id, type badges, rows with mono uppercase keys, branch list
where each target is a clickable jump (`centerOn` pans the canvas to it, briefly pulses).

**Pan/zoom canvas for large graphs.** Don't shrink a big graph — make it a space:
`transform: translate(tx,ty) scale(s)` on a canvas div, pointer events for drag + pinch,
wheel-zoom centered on cursor, a `⤢ fit` button, zoom clamped `[.12, 5]`. Dot-grid
background (`radial-gradient(var(--rule) 1px, transparent 1px); background-size: 24px 24px`)
so motion is legible.

**Worked-path highlight.** A "follow one real case through the system" toggle: gold
stroke + `drop-shadow` glow on the on-path nodes/edges, with a floating panel narrating
the case (`basis: REAL` vs `ILLUSTRATIVE` badge). Turns a static diagram into a story.

**Step-through widget.** For any process with states: buttons `t=0 … t=3`, the visual
updates with CSS transitions (pruned cells fade + shrink), a big tabular-nums readout,
and — the polish move — auto-play once when scrolled into view:

```js
const io = new IntersectionObserver(es => { /* step through once, 900ms cadence */ },
                                    { threshold: 0.4 });
```
Gate all auto-motion behind `prefers-reduced-motion`.

**Data-driven chart with tabs + tooltip.** Charts are built from a `DATA` object and a
render function — never hardcoded paths — so tabs (model variants, segments) re-render
the same frame. One fixed-position mono tooltip element serves the whole page.

**Ambient hero canvas.** A `<canvas>` behind the hero animating the artifact's own
subject (an attention grid, value-ramped cells), masked with `radial-gradient` so text
stays readable, `requestAnimationFrame` paused under reduced-motion. Atmosphere earned
from the subject, not a stock gradient.

## 5 · Honesty devices

These make an artifact trustworthy, and agents skip them most:

- **Provenance badges**: `REAL` vs `ILLUSTRATIVE` on every worked example and number.
- **Confidence chips**: `conf-low/medium/high` pills on claims and open questions.
- **Unresolved state**: dashed alarm-colored outline for nodes/branches the source
  material leaves broken — plus a "dead end" treatment in link lists. Never silently
  tidy incomplete source material.
- **Mechanism badges**: when a system mixes rule/LLM/human steps, badge every node with
  which one executes it (distinct tint per mechanism, legend included).
- **Open questions panel**: a notes drawer listing what the source doesn't answer,
  tagged and confidence-rated, with a mono provenance footer (what was generated from
  what, when).

## 6 · App-shell treatment (when the artifact is a tool)

When the subject is a system to *explore* rather than a document to *read*:
`height: 100dvh; overflow: hidden` app frame — top bar (wordmark + segment pill nav +
action buttons), full-viewport canvas host, floating chrome (context chip top-left,
legend bottom-left, zoom controls bottom-right, slide-in notes panel with scrim).
Legend swatches mirror actual node shapes (circle = entry, diamond = decision,
rounded = terminal, dashed = unresolved). Everything overlaid, translucent
(`rgba(paper,.92)` + `backdrop-filter: blur(6px)`), so the canvas stays the hero.

---

## Choosing devices

Pick by what the material needs explained, not by availability:

| Material calls for… | Reach for |
|---|---|
| A branching system, a graph, a map | pan/zoom canvas, hover-dim, detail cards, worked path |
| Teaching a hard idea | running example, semantic boxes, worked panels, self-tests, step-through |
| A quantitative tradeoff | data-driven chart with tabs, matrix with highlighted cells |
| Messy/incomplete source | unresolved states, confidence chips, provenance badges, open-questions panel |
| A first impression | display type with conviction, ambient subject-derived canvas, decode subtitle |

Compose 10–20 of these per flagship artifact. Derive the palette and faces from the
subject first; the devices then inherit that identity.
