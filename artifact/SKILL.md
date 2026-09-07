---
name: artifact
description: Use when building or improving HTML/CSS artifacts, React pages, dashboards, landing pages, explainers, demos, SVG diagrams, UI prototypes, or visual outputs where design quality, subject-specific treatment, responsive behavior, and render verification matter.
---

# Artifact

Approach this as the design lead at a small studio known for their versatility, giving every client a visual identity pitched at the treatment the task actually calls for. Make deliberate choices about palette, typography, and layout that are specific to this subject, and avoid templated designs.

## Read the request first

Calibrate treatment, not whether to design. A doc deserves the same craft as a landing page — what changes is the treatment that craft is delivered in.

Many requests call for a more utilitarian treatment: a plan, a memo, a demo. Make it polished: include real typographic hierarchy, considered spacing, and a proper palette, but avoid over-designing. Most pages do not need a flashy, gigantic hero. Keep flourishes tasteful and limited.

Some requests call for an editorial treatment: a landing page, a game, an app or tool they'll keep or share.

When unsure: a well-composed page is never the wrong answer; an over-designed visual identity sometimes is.

Fundamentals below apply to everything. The editorial process after that runs only when the read above says so.

## Start with the viewer mental model

Before layout or visuals, define what the viewer should understand at a glance:

- **Viewer**: who is looking at this and what pressure they are under.
- **Question**: the first question the artifact must answer.
- **Action**: what the viewer can decide, do, or inspect next.
- **Evidence**: the reason, source, state, or tradeoff that makes the action trustworthy.
- **Depth path**: what belongs in the first view versus what belongs lower on the page, in a detail panel, or behind interaction.

Users do not care how the system works behind the scenes unless that mechanism changes trust, timing, risk, or accountability. For operational explainers, prefer this order: what needs attention, who owns it, why it matters, where to act, what happened after action.

The first viewport must communicate the artifact's core idea without requiring the reader to understand implementation internals.

## Fundamentals for every artifact

**Honor what's already there** Look for an existing design system first — CLAUDE.md, a tokens or theme file, existing component styles. When one exists, apply it; everything below fills gaps and never overrides. Precedence is always: the user's own words, then the project's existing system, then your choices.

**Ground it in the subject.** If the subject isn't already clear, pin it: one concrete subject, its audience, and the page's single job. The subject's own world — its materials, instruments, vernacular — is where distinctive choices come from. Build with real content throughout, never lorem.

**Pair typefaces** Typography carries the page even when the page isn't about typography. The Artifact CSP blocks font CDNs, so don't link a webfont URL and risk a silent fallback. Instead inline the face as a @font-face data URI. Keep running text near 65 characters wide; set a type scale and stay on it; give headings `text-wrap: balance`, body text room to breathe, and uppercase labels a touch of letter-spacing.

**Choose neutrals, don't default to them.** A pure mid-grey reads as unconsidered; a grey with a slight hue bias toward the page's accent reads as chosen. Pure white and near-black are fine grounds when they suit the subject — the point is that the neutral was picked, not inherited.

**Design both themes.** The page renders in the viewer's theme: `prefers-color-scheme` carries the OS preference, and the viewer's toggle stamps `data-theme="dark"` / `data-theme="light"` on the root element, which must override the media query in both directions. The robust pattern is token-level: define the palette as custom properties on `:root`, redefine only the tokens under `@media (prefers-color-scheme: dark)` — style components through the tokens, never directly inside the media query — then redefine them again under `:root[data-theme="dark"]` and `:root[data-theme="light"]`. Give the second theme the same care as the first — don't naively invert; keep contrast legible and the accent working on both grounds. A design that deliberately commits to one visual world (a neon arcade screen, a letterpress invitation) may stay single-theme — make it a choice, not an omission.

**Let layout do the spacing.** Lay out sibling groups with flex or grid and `gap`, not per-element margins that silently collapse or double. Wide content — tables, code, diagrams — gets `overflow-x: auto` on its own container so the page body never scrolls sideways. Reach for `font-variant-numeric: tabular-nums` wherever digits line up in columns.

**Avoid AI-generated design** AI-generated design currently clusters around a few looks: warm cream (#F4F1EA) with a serif display and terracotta accent; near-black with a lone acid-green or vermilion pop; broadsheet hairline rules with dense columns; a purple-to-blue gradient hero on white; Inter or Space Grotesk as the "safe" face; emoji as section markers; everything centered; `rounded-lg` everywhere; accent bar/rail on rounded cards. Where the user pins down a visual direction, follow it exactly — their words always win, including when they ask for one of these looks. Where nothing is specified, don't spend that freedom on one of these defaults.

**Build cleanly** Be cognizant of overlapping elements, cascade collisions, silent font fallbacks; visual bugs hide in the gap between source and output. Close every non-void element, double-quote attributes, give keyboard focus a visible state, respect `prefers-reduced-motion`. For generative or decorative graphics, reach for Canvas or WebGL rather than hand-authoring long SVG path data.

**CSS rules** When writing the CSS, watch your selector specificities. It is easy to generate classes that cancel each other out — a type-based selector like `.section` fighting an element-based one like `.cta` over padding and margins between sections. Structure the cascade so it doesn't silently undo your spacing.

**Writing the copy** Words are design material, not decoration. Write from the user's side of the screen — name things by what people recognize, not how the system is built (a person manages *notifications*, not *webhook config*). Active voice; a control says exactly what happens ("Publish", then a toast that says "Published"). Errors explain what went wrong and how to fix it — no apologies, no vagueness. Specific beats clever.

**Structure is information** Structural devices, numbering, eyebrows, dividers, labels, should encode something true about the content, not decorate it. Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence - like a real process or a typed timeline where order carries information the reader needs. Question if choices like numbered markers actually make sense before incorporating them.

**When it's a UI, not a document** A dashboard or tool is scanned and operated, not read top-to-bottom, so the craft shifts from typography to information design. Surface the summary before the detail; encode state in form as well as number — a pill, a chip, a severity stripe — so what needs attention reads at a glance. Semantic color (good / warning / critical) is separate from the accent hue and doesn't count as your accent. Give sparklines and charts the same care as type: an area fill, a faint grid, an emphasized endpoint. What's interactive should look interactive.

## Use SVG when it clarifies complex ideas

SVG is the right tool when the artifact needs inspectable, precise, scalable meaning:

- Systems diagrams, architecture maps, process flows, timelines, dependency graphs, funnels, matrices, and conceptual maps.
- Labeled spatial relationships, arrows, callouts, annotations, and layered explanations.
- Lightweight charts, gauges, sparklines, badges, custom icons, and symbolic visual language.
- Interactive explainers where hover or click should reveal semantic parts of a diagram.

Build SVGs with meaningful structure:

- Use `viewBox`, grouped layers, labels, titles, descriptions, and readable ids or classes.
- Keep text real text when it should be selectable, searchable, or accessible.
- Use `<title>` and `<desc>` where the SVG carries important meaning.
- Prefer simple shapes, lines, paths, markers, masks, and patterns over opaque generated path soup.
- Put repeated values in CSS variables or shared classes.
- Make diagrams responsive with preserved aspect ratio and container constraints.

Do not avoid SVG just because it is visual code. Use it when it is the clearest representation of the idea. Use Canvas or WebGL instead when the visual is high-volume, generative, particle-based, heavily animated, or performance-sensitive. Use HTML/CSS for ordinary layout and controls.

Completion criterion: every SVG has a clear semantic reason to exist, no unreadable long path data unless unavoidable, and it remains legible at mobile and desktop widths.

## Efficient SVG iteration loop

SVGs fail when they are only technically valid. Treat complex SVG as an interface, not decoration.

Use this loop for system maps, flows, architecture diagrams, timelines, or dense conceptual visuals:

1. **Name the reader journey** in plain language, for example "prompt, route, review, decide, record."
2. **List the semantic objects** before drawing, including actors, states, decisions, evidence, actions, and hidden support layers.
3. **Assign visual priority**: primary user-facing objects are largest and highest contrast; implementation support is smaller, lower contrast, or lower on the canvas.
4. **Block the SVG first** with boxes, circles, labels, and arrows. Do not tune paths, gradients, or ornament until the reading order works.
5. **Render early** at desktop and mobile sizes. Inspect screenshots for clipped text, crossing connectors, tiny labels, and whether the first read is obvious.
6. **Patch one layer at a time**: text fit, then object spacing, then connectors, then color, then polish. Avoid rewriting the whole SVG unless the mental model is wrong.
7. **Keep a mobile strategy**: simplify, stack, or allow horizontal scroll for complex diagrams. Do not shrink dense SVG until labels become unreadable.

Prefer real text, grouped layers, reusable classes, and short connector paths. Use curved connectors only when they improve reading order. If the diagram contains a user-facing workflow, make the user-facing surface visually dominant and make backend machinery secondary.

Completion criterion: after desktop and mobile screenshots before completion, the SVG explains the idea at a glance, has no clipped text or collisions, and still preserves enough detail for inspection.

## Process

Before writing code, sketch a short design plan — a compact token system with color, type, and layout:
- **Color**: describe the palette as 4–6 named hex values.
- **Type**: typefaces for 2+ roles — a characterful display face used with restraint, a complementary body face, and a utility face for captions or data if needed.
- **Layout**: a layout concept in one or two sentences.

Then build, following the plan and deriving every color and type decision from it.

## When the request is editorial

The stance shifts: the client has already rejected proposals that felt templated, and is paying for a distinctive point of view. Make opinionated calls, and take one real aesthetic risk where it serves the work.

Review the design plan against the subject before building: if any part of it reads like the generic default you would produce for any similar page, revise that part, and note what you changed and why. Only after you've confirmed the plan's uniqueness do you write the code, following the revised plan exactly.

**Principles**

- The hero is a thesis: open with the most characteristic thing in the subject's world — headline, image, live demo, interactive moment.
- Typography carries the personality of the page. Pair the display and body faces deliberately, not the same families you would reach for on any other project, and set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself a memorable part of the design, not a neutral delivery vehicle for the content.
- Leverage motion deliberately. Think about where and if animation can serve the subject: a page-load sequence, a scroll-triggered reveal, hover micro-interactions, ambient atmosphere. An orchestrated moment usually lands harder than scattered effects; choose what the direction calls for. However, sometimes less is more, and extra animation contributes to the feeling that the design is AI-generated.
- Match complexity to the vision. Maximalist directions need elaborate execution; minimal directions need precision in spacing, type, and detail. Elegance is executing the chosen vision well.
- Spend your boldness in one place; keep everything around it quiet. If the accent fights the ground, shift it toward analogous or drop saturation rather than replacing it.

## Frontend rules for apps and tools

- Build the actual usable experience as the first screen for apps, tools, and games. Do not create a marketing landing page unless requested.
- Keep dashboards quiet, dense, and operational. Avoid oversized hero sections and decorative card grids.
- Use cards only for repeated items, modals, or genuinely framed tools. Do not put cards inside cards.
- Use icons for tool buttons when an icon is more recognizable than text.
- Use stable dimensions for boards, controls, counters, tiles, charts, and SVG canvases so hover states and dynamic labels do not shift layout.
- Do not scale font size with viewport width. Use fixed type scales and responsive layout instead.
- Ensure text never overlaps adjacent content or escapes controls.

## Flagship artifacts: devices, not components

When the artifact is a deliverable someone will study, share, or operate — an explainer, a system explorer, a study guide, a decision tool — build bespoke at the flagship tier. Reusable visual components cannot produce this tier — a shared kit is exactly what makes pages look generated.

**Declare the tier before building.** State explicitly whether you're building *utilitarian* (quick internal page, kit allowed) or *flagship*, so the user can correct the calibration in one word. Requests to be studied or shared default to flagship; the keyword "flagship" always means it. The flagship contract: identity (palette, three type faces, micro-flourishes) derived from the subject's own world; 10–20 purpose-built devices; 2–4 interactive devices that each explain something (hundreds of lines of JS is normal, not excessive); honesty devices wherever the source material is messy; and a minimum of three render→critique→patch passes — never present a first render as done.

Flagship workflow, in order:

1. `references/grounding.md` — extract real data BEFORE design: verbatim quotes tagged REAL/PARAPHRASED/ILLUSTRATIVE, numbers computed by script, graph layouts generated with Graphviz rather than hand-placed.
2. `references/devices.md` — the craft vocabulary: identity, structure, explanatory, interaction, and honesty devices, with the material→device selection table.
3. `kit/behaviors/` — copy-paste interaction modules with no visual opinion (tooltip, pan/zoom, hover-dim ego networks, stepper with scroll autoplay, data-driven line chart). Inline them; style their class hooks with the page's own tokens.
4. `references/iteration.md` — the render→critique→patch protocol, the 10-question quality rubric, the screenshot matrix (interaction states, 100% crops, mobile, console), and known cascade traps.

## Component kit

For quick utilitarian pages only — an internal dashboard, a memo, a status report where speed matters more than identity — reuse the kit in `kit/` instead of improvising parts. Never build a flagship artifact from kit parts, and never let the kit's neutral identity substitute for a subject-derived one.

How to use it:

1. Copy `kit/tokens.css` into the artifact and swap token *values* for the project's brand (palette, fonts); keep token *names*. Components read only tokens, so both themes keep working after a retheme.
2. Read only the component files the page needs, and paste their markup and CSS. Each file states when to use it, when not to, and its known failure mode.
3. `kit/gallery.html` renders every component in both themes — the source of truth is `kit/components/*.md`; if you change a component, update the gallery too, then screenshot it as the regression check.

Components:

- `kit/components/page-header.md` — quiet header: eyebrow, title, meta, actions. The anti-hero.
- `kit/components/stat-tile.md` — KPI row: value, unit, semantic delta, stable height.
- `kit/components/status-pill.md` — categorical state pills and row severity stripes.
- `kit/components/data-table.md` — scannable rows: overflow wrapper, sticky header, numeric alignment, empty state.
- `kit/components/callout.md` — info/ok/warn/crit blocks that must not be skimmed past.
- `kit/components/timeline.md` — typed events in real order, mono timestamps.
- `kit/components/definition-list.md` — key-value facts about one record.
- `kit/components/sparkline.md` — inline trend SVG: line, area, endpoint dot, point-generation math.
- `kit/components/svg-diagram.md` — diagram scaffold: lanes, nodes, edges, arrow marker, priority classes.

For full charts, follow the `dataviz` skill; the kit's semantic tokens (`--ok`/`--warn`/`--crit`) and accent are the shared vocabulary between both.

## Gotchas

- **Technically valid is not visually successful**: passing HTML, CSS, or SVG checks does not mean the artifact communicates. Render it and inspect the actual first read.
- **Implementation diagrams often bury the user**: if the artifact explains a workflow, make user-facing objects dominant and push machinery into a quieter support layer.
- **Dense SVGs collapse on mobile**: choose stacking, simplification, or horizontal scroll before shrinking labels until they are unreadable.
- **Generic polish hides weak structure**: shadows, gradients, and rounded cards cannot fix a missing mental model, unclear action, or weak evidence path.

## Verification before completion

For static HTML that can open directly, verify the file exists and inspect it in browser when feasible.

For apps or components, run the dev server when feasible and verify with browser screenshots:

- Desktop viewport.
- Mobile viewport (~375px), and confirm `document.body.scrollWidth === window.innerWidth`.
- Both light and dark themes when the surface is theme-aware.
- No body horizontal scroll.
- No obvious text overlap or clipped controls.
- SVGs and visual assets render nonblank and stay framed.
- **Every interactive state**, not just the initial render: each tab, each step, hover active, details open. Interaction states are where bugs hide.
- **At least one 100% crop** of a dense region — full-page screenshots downscale detail bugs (clipped text, wrong tints, misaligned baselines) into invisibility.
- **Browser console is clean** — zero errors.
- Motion respects `prefers-reduced-motion` when motion is significant.

For flagship-tier artifacts, verification is not one pass: follow the full protocol and quality rubric in `references/iteration.md`.

If browser verification is unavailable, state that limitation and run the strongest available static checks, such as lint, build, typecheck, or targeted HTML/CSS inspection.

Completion criterion: the artifact is implemented, visible, responsive, checked in both themes where applicable, and matches the treatment and visual plan.
