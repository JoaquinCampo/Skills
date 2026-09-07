---
name: orchestrating-subagents
description: Use preemptively at the start of any session whose work decomposes into delegable units and whose main-thread context is worth protecting. A report, a large feature, a migration are examples, not the full set; the trigger is the shape (many token-heavy steps, compact results), not the task type. Also use whenever the user asks to delegate work to subagents. Invoke before context fills, not after.
---

# Orchestrating Subagents

## Overview
The main thread is the context manager: it holds the conversation, the judgment, and the
running state. In this mode, delegate by default. Offload reading, exploration, authoring,
and review to subagents; orchestrate, do not do the token-heavy work yourself. Apply this
preemptively: the point is that the main thread's context never fills, not that it recovers
once it has.

## How to offload
1. Shell reduction first for large data (grep/jq/awk to compact output): lossless, no
   spin-up, you control the filter.
2. Subagent when the reduction itself needs judgment, or the work is authoring or review.
3. Main thread only for decisions, user interaction, and synthesis of compact results.

## Use selective parallelism
Launch the critical-path child first. Parallelize genuinely independent work when the combined value justifies the additional usage, normally with 2 to 3 concurrent children. Prefer one strong agent over several weaker agents repeating the same work. Keep tightly coupled work linear when each result reshapes the next action.

Launch top-level subagents asynchronously. Time blocked waiting is wasted capacity: while children run, continue independent inspection, validation preparation, synthesis, or other useful work. Async reduces elapsed time, not token or quota usage. Call `wait()` only when no independent work remains and a child result is required to proceed.
- Plan as a dependency graph, not in document or list order: identify which units are
  independent, dispatch ready units together (parallel tool calls in one message), and
  hold back only what is genuinely blocked.
- Prefer pipelining over phase barriers: launch a unit's checker as soon as its maker returns, without waiting for unrelated tasks to finish.
- A shared target file pushes toward serialization. Usually better: parallelize generation,
  serialize integration (workers return content or patches, one integrator applies them in
  order).
- Watch for serial dispatch by default: if you are sending one subagent, waiting, then
  sending the next, ask what actually depends on what.

## The maker/checker loop
For each substantive unit of work:
1. Maker uses Luna high for bounded work, Terra high for larger multi-file work, or Sol medium for ambiguous substantive work.
2. Checker is a separate agent, never the maker. Use Luna xhigh for normal independent review and Sol high only for genuinely hard audits or final judgment.
3. Fixer uses Luna high for exact findings or Terra high when fixes require broad cross-file reasoning.
4. Verify with shell checks first, using Luna low only when model judgment is needed.

## Every delegation prompt carries
- A role ("you are an expert in..."), exact file paths, and what to read first.
- The user's constraints pushed down (no em-dashes (--), style and format rules).
- "Locate by content; line numbers are approximate."
- The expected return shape (a list, a diff summary, a verdict).
- Ordinary children must not delegate further. Only an explicitly selected fan-out orchestrator may spawn one bounded child layer, using explicit model tiers and self-contained prompts.
- On substantive work: consult the `advisor` before committing to an approach and before
  declaring done.

## Rules
- Set model and effort explicitly on every spawn. Use Luna low for mechanical search, Luna high for bounded work, Luna xhigh for quality-sensitive normal work, Terra high for larger multi-file work, Sol medium for ambiguous substantive work, and Sol high for hard judgment. Sol xhigh is advisor-only.
- Start with the cheapest reliable route and escalate only on uncertainty, failed validation, conflicting evidence, or meaningful risk.
- Avoid max effort, Terra xhigh, and broad Sol fan-out. Fan out only independent work whose value justifies the usage.
- Child delegation is disabled except for an explicitly selected fan-out orchestrator with one bounded child layer.
- Keep running state outside your context (todo list or scratch file) so done work is never re-derived.
- Run long tests, builds, servers, watchers, and log tails in the background when practical. Continue other useful work, inspect output only when needed, and clean up processes when finished.

## Common mistakes
- Reading a big file in the main thread "just to check": reduce it with jq/grep or delegate.
- Letting the maker grade its own output.
- Vague worker prompts: workers cannot ask back, they guess.
- Waiting until context is strained to start delegating; by then the heavy reads already
  happened.
