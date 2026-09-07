# Flagship iteration protocol

Devices (see `devices.md`) are the vocabulary; this is the process that gets a page from
"rendered correctly" to "at the bar." The reference artifacts were not produced in one
pass and neither will yours be. Budget a minimum of three render→critique→patch cycles
for any flagship artifact. Do not present a first render as done.

## Pass 0 — Brief before code

Write a short content spec before any HTML (a few lines per item, in your working notes
or the plan):

- **Sections**: what each part says, in reading order. Name the one thing each section
  must make the reader understand.
- **Devices per section**: which catalog devices carry each section, and the one place
  the page takes an aesthetic risk.
- **Data needed**: every number, quote, and relationship the page will show — and its
  source. If a datum has no source, it is ILLUSTRATIVE and must be labeled as such.
  (See `grounding.md`; do this extraction BEFORE design.)
- **Running example**: which single concrete case threads through the whole piece.
- **Interaction budget**: which 2–4 interactive devices, and what each one explains
  that a static image couldn't.

## Pass 1 — Structure and identity, no polish

Build the full skeleton with real content: all sections, the identity tokens, typography,
the static form of every visualization. Blocked, not tuned — reading order first
(the same rule as the SVG loop in SKILL.md). Render and fix only *broken* things:
overflow, collisions, dead JS, console errors.

## Pass 2 — Critique against the rubric

Render fresh screenshots and answer every rubric question in writing. Screenshots to
take before critiquing:

| Capture | Why |
|---|---|
| Full page, desktop width | reading order, rhythm, band alternation |
| Hero at 100% crop | conviction check — this is the first impression |
| Each interactive device in EACH state (every tab, every step, hover active, details open) | interaction states are where bugs and laziness hide |
| One dense section cropped at 100% | full-page shots downscale away detail bugs (clipped text, misaligned baselines, wrong tints) |
| Mobile width (~375px) full page | non-negotiable; check body scrollWidth == innerWidth too |
| Browser console | zero errors, zero warnings you can't explain |

The rubric — answer each, honestly, in one line:

1. **Conviction**: does the hero commit (scale, subject-derived atmosphere, a flourish),
   or is it a title with padding?
2. **Identity**: could this palette + type belong to any other subject? If yes, it's not
   derived from this one.
3. **Running example**: is one concrete case threaded through, or do sections float
   abstract?
4. **Interaction budget**: does each interactive device explain something? Name it.
   A widget that only decorates gets cut.
5. **Conclusions in words**: does every chart, matrix, network, and heatmap have its
   takeaway written next to it ("read the bottom row…")?
6. **Honesty**: are provenance/confidence/unresolved devices present wherever the
   material is messy? Did anything get silently tidied?
7. **Slop check**: scan for the generic-AI list in SKILL.md (centered everything,
   rounded-card grids, accent rails, emoji markers, timid type).
8. **Density**: is anything padded to look substantial? Cut it. Is anything cramped
   because two sections compete? Band-separate them.
9. **Reading order**: cover the screen and reveal the first viewport only — do you know
   what the page is about and want to scroll?
10. **States**: every interactive state captured above looks intentional, including
    empty/edge states.

A useful upgrade when stakes are high: give the screenshots + the Pass 0 brief (NOT the
code) to a fresh-eyes critic — a subagent that answers the rubric without knowing what
was hard to build. Builders grade their own effort; critics grade the page.

## Pass 3+ — Patch one layer at a time

Fix in this order, re-rendering between layers; never rewrite wholesale unless the
Pass 0 brief itself was wrong:

1. content and reading order → 2. type and spacing → 3. color and emphasis →
4. interaction feel (transitions, hover, focus) → 5. ornament.

**Stop condition**: a critique pass where every rubric answer is clean and the
verification captures show no defects. Two consecutive clean passes for anything
client-facing.

## Known cascade traps (each has burned a real page)

- An element selector for page chrome (`footer`, `header`, `section`) restyling the same
  element used inside a component (`.quote footer`). Scope page chrome with a class.
- `details` markers: hide `::-webkit-details-marker` AND set `list-style:none` on summary.
- Fixed tooltips positioned from `clientX/Y` break if an ancestor creates a containing
  block (`transform`, `filter`) — keep the tooltip a direct child of `body`.
- Auto-playing widgets: gate behind `prefers-reduced-motion` and play ONCE
  (IntersectionObserver + disconnect), never loop.
- Canvas heroes: cap `devicePixelRatio` at 2 and pause under reduced motion, or you ship
  a fan-spinner.
