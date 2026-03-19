# Diagram Type Conventions

What Claude gets wrong without guidance. Read only the section for the current diagram type.

## Choosing a Type

| Use Case | PlantUML Type | When to Pick |
|----------|---------------|--------------|
| Request lifecycle, API call flow, multi-service interaction | **Sequence** | Multiple actors/services exchanging messages in order |
| Entity relationships, model fields, table structure | **Class/Entity** | New models, schema changes, relationship constraints |
| Pipeline, branching logic, processing flows | **Activity** (new syntax) | Flows with conditionals, loops, fork/join |
| Status lifecycle, enum-driven transitions | **State** | Status fields, document lifecycle |
| System boundaries, service layers, deployment | **Component** | Integrations, service architecture, infrastructure |
| Mind maps, concept grouping | **MindMap** | Brainstorming, feature decomposition |
| Gantt charts, timelines | **Gantt** | Project planning, migration timelines |

---

## Sequence Diagrams

Claude's default: plain `participant X` with no visual layering. Fix:

- **Name participants as role + code name** in italics — not just "Service" or "DB":
  ```
  participant "Router\n//ContractRouter//" as Router #DBEAFE
  ```
- **Color each participant by architectural layer** (see `color-palette.md`) — without this, all participants look identical and the diagram loses its layering signal
- **Participant order = left-to-right data flow**: input → processing → storage → external. Claude tends to order alphabetically or by first mention
- Use `activate`/`deactivate` for every service call to show lifetimes
- Use `alt`/`else` for success vs error branching

---

## Class / Entity Diagrams

Claude's default: dumps all columns and omits constraints. Fix:

- **Only include fields relevant to the story** — if the diagram is about relationships, show FKs and cardinality, not `created_at` and `updated_at`
- **Show constraints explicitly**: `CHECK(...)`, `UNIQUE`, `NOT NULL` via `*` prefix
- **Mark keys with stereotypes**: `* id : UUID <<PK>>`, `* org_id : UUID <<FK>>`
- **Cardinality on every relationship**: `||--o{`, `}o--||`, `||--||` — Claude often omits this or uses wrong notation
- Use `--` separator between key fields and non-key attributes

---

## Activity Diagrams

Claude's default: monochrome flows with unlabeled branches. Fix:

- **Color-code outcomes** — this is the key differentiator from a generic flowchart:
  - Error/rejection paths: `#FFCDD2` (light red)
  - Success outcomes: `#C8E6C9` (light green)
- **Label every decision branch** with the actual condition, not just "yes"/"no"
- Use `fork`/`fork again`/`end fork` for parallel processing — Claude sometimes uses `|swimlane|` instead, which is wrong for parallelism

---

## State Diagrams

Claude's default: flat state list without sub-states. Fix:

- **Use nested `state X { }` blocks** for any state that has internal steps — Claude tends to flatten everything into one level, losing the hierarchy
- **Label every transition with the trigger/action** — not just the target state name
- Color terminal/error states with `#FFCDD2` when the diagram has both success and failure endpoints

---

## Component Diagrams

Claude's default: groups by feature, not architecture. Fix:

- **Group by architectural boundary** (API, Service, Storage, External) — not by feature. A `ContractRouter` and `AuthMiddleware` belong in the same API group even though they're different features
- **Use stereotypes for theme integration**: `<<api>>`, `<<service>>`, `<<storage>>`, `<<external>>` — these hook into the shared theme's color palette automatically
- Max 3-4 groups per diagram. If you need more, the diagram scope is too wide
