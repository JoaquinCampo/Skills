---
name: advisor
description: Use when the user asks to consult the advisor, wants transcript-aware strategic guidance, wants a second opinion on ongoing agent work, provides a transcript for review, is stuck, is choosing between candidates, or wants to know whether completed work is ready. Always run the advisor as a separate GPT 5.6 Sol xhigh agent with the exact recovered advisor system prompt.
---

# Advisor

Use this skill to reproduce the Claude Advisor workflow in Codex. The advisor must be a separate model call so it can judge the main agent's work from the outside.

## Dispatch Requirement

Always run the advisor with:

- `model: "gpt-5.6-sol"`
- `reasoning_effort: "xhigh"`
- system prompt: the exact contents of `references/advisor_system_prompt.md`
- user message: the full available transcript of the agent's task, tool calls, tool results, failed attempts, current plan, and self-checks

Do not answer inline as the advisor when a subagent or separate model-call mechanism is available. If the runtime cannot spawn a separate `gpt-5.6-sol` call with xhigh reasoning, say that exact behavior is unavailable and ask for the runtime to be upgraded rather than silently using an older model family.

## Transcript Construction

Pass the richest transcript the environment can provide:

- original user request and constraints
- every relevant tool call and result
- errors, retries, dead ends, and corrections
- current files or diffs under consideration
- previous advisor advice, if any
- the agent's current question, if there is one

If there is no explicit question, ask the advisor to follow the recovered prompt exactly: infer where the agent is and give direct actionable advice.

## Prompt Files

- `references/advisor_system_prompt.md`: exact advisor system prompt to use for the separate model call.
- `references/advisor_prompt.md`: original recovered note that this skill was derived from.

Completion criterion: the returned advice came from a separate `gpt-5.6-sol` xhigh advisor call using `references/advisor_system_prompt.md`, or the response clearly states why exact advisor behavior could not be run.
