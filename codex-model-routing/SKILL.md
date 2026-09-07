---
name: codex-model-routing
description: Use when spawning Codex subagents or Codex threads and choosing among GPT 5.6 Luna, Terra, and Sol with the appropriate effort. Use this with orchestrating-subagents whenever delegation involves model overrides, reasoning effort, Explore agents, checker/fixer loops, or fan-out work.
---

# Codex Model Routing

## Principle
Always choose the cheapest GPT 5.6 route that can reliably do the delegated job, and make the model and effort explicit. The main thread keeps judgment and synthesis; subagents return compact evidence, patches, or verdicts.

GPT 5.6 reasoning efforts do **not** map one-to-one to GPT 5.5. Start lower than the similarly named GPT 5.5 effort: `gpt-5.6-sol` at `low` is the default starting point for a Codex conversation or low-risk main-thread judgment. Escalate only when the task provides evidence that it needs more reasoning.

Use only the GPT 5.6 family exposed by Codex CLI 0.144 or newer: `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`. If these ids are unavailable, stop and ask for the runtime to be upgraded rather than silently routing to an older family.

## Routing table

| Model | Effort | Use for | Guidance |
| --- | --- | --- | --- |
| `gpt-5.6-luna` | `low` | Bounded mechanical search, inventory, and verification support | Use only when synthesis is not required. |
| `gpt-5.6-luna` | `high` | Small, bounded implementation and routine work | Default economical worker route. |
| `gpt-5.6-luna` | `xhigh` | Quality-sensitive normal coding and independent review | Use when normal work needs stronger reasoning. |
| `gpt-5.6-terra` | `high` | Larger multi-file implementation | Use for substantial cross-file reasoning. |
| `gpt-5.6-sol` | `low` | Default Codex conversation and low-risk main-thread judgment | The GPT 5.6 default. Do not treat it as equivalent to GPT 5.5 low. |
| `gpt-5.6-sol` | `medium` | Serious daily work and ambiguous substantive tasks | First escalation when Sol low is insufficient. |
| `gpt-5.6-sol` | `high` | Architecture, hard debugging, difficult review, and final judgment | Reserve for work that genuinely needs judgment. |
| `gpt-5.6-sol` | `xhigh` | Exceptionally hard advisor work | Do not use for ordinary subagents. |

Start with the cheapest reliable route. For primary Codex conversations, start at Sol low; for delegated workers, start with the applicable Luna or Terra route. Escalate only when uncertainty, failed validation, conflicting evidence, or task risk justifies it. Avoid max effort, Terra xhigh, and broad Sol fan-out because their quality gain usually does not justify the usage.

Prefer one strong agent over several weaker agents repeating the same work. Launch the critical-path child first, parallelize only independent units whose combined value justifies the usage, and normally cap concurrency at 2 to 3 children. Pipeline dependent checks as soon as prerequisites finish. Async reduces elapsed time, not token or quota usage; use blocked time for independent work and call wait only when the next result is required.

## Spawn policy
Every Codex delegation plan should state:

- `model`
- `reasoning_effort`
- role
- exact paths
- what to inspect first
- user constraints
- expected return shape

Do not omit the model unless the platform forbids model overrides. If the platform forbids overrides, say that in the plan and keep the task bounded.

## Explore defaults
For Codex Explore-style work, use Luna low only for bounded mechanical search:

- repo or file reconnaissance
- finding examples of a pattern
- reading logs or terminal output
- collecting candidate files and line references

Escalate to Luna high when exploration requires synthesis, Luna xhigh for quality-sensitive normal analysis, Terra high for larger multi-file work, Sol medium for ambiguous substantive work, and Sol high only when the result requires architecture or difficult judgment.

## Prompt shape
Use self-contained prompts. Include enough context that the subagent does not need the main thread.

```json
{
  "model": "gpt-5.6-luna",
  "reasoning_effort": "low",
  "role": "Explore agent",
  "task": "Find every place this project defines subagent model routing. Return paths, approximate lines, and a compact summary.",
  "paths": [
    "/absolute/path/to/repo"
  ],
  "constraints": [
    "Locate by content; line numbers are approximate.",
    "Return evidence only; do not edit files."
  ]
}
```

For maker/checker/fixer loops:

- Maker: Luna high for bounded work, Terra high for larger multi-file work, Sol medium for ambiguous substantive work.
- Checker: Luna xhigh for normal independent review, Sol high for hard final judgment.
- Fixer: Luna high for exact findings, Terra high when fixes require broad cross-file reasoning.
- Verifier: shell checks first, Luna low only when model judgment is needed.

## Completion check
Before dispatching, verify that every worker has:

- explicit model and reasoning effort
- a bounded task
- exact inputs
- a return format that is smaller than the context it consumes
- no need to ask clarifying questions
