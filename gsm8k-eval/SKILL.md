---
name: gsm8k-eval
description: >
  GSM8K evaluation protocol: answer extraction (####, \boxed, CoT), accuracy scoring,
  prompt formatting, few-shot exemplars, dataset loading, pitfalls. Use when: GSM8K,
  grade school math, openai/gsm8k, #### delimiter, parse_gsm8k_answer, detect_answer_failure,
  load_gsm8k, format_chat, math benchmark scoring, gsm8k few-shot, chain-of-thought eval.
---

# GSM8K Evaluation Protocol

## Dataset at a Glance

| Property | Value |
|----------|-------|
| HuggingFace ID | `openai/gsm8k` (config: `main`) |
| Paper | Cobbe et al. 2021 "Training Verifiers to Solve Math Word Problems" |
| Train / Test | 7,473 / 1,319 (8,792 total) |
| Fields | `question` (str), `answer` (str) |
| Answer format | `{reasoning}\n#### {positive_integer}` |
| Final answers | **Always positive integers >= 1** |

Load with:
```python
from datasets import load_dataset
ds = load_dataset("openai/gsm8k", "main", split="test")
```

Extract ground truth:
```python
gt = example["answer"].split("####")[-1].strip().replace(",", "")
```

A `socratic` config exists (answers include sub-questions) but `main` is standard.

---

## Answer Format Rules

The answer field contains step-by-step reasoning followed by `#### {integer}`:

```
Natalia sold 48/2 = <<48/2=24>>24 clips in May.
Natalia sold 48+24 = <<48+24=72>>72 clips altogether.
#### 72
```

Key constraints from the annotation guidelines:
- Final answers are **always positive integers** (>= 1). No negatives, no zero, no decimals.
- Intermediate steps may use decimals, but the final answer after `####` is always an integer.
- `<<expr=result>>` are calculator annotations for the training verifier. Strip them when displaying.
- Problems require 2-8 steps using only elementary arithmetic (+, -, *, /).
- Large numbers may have commas: `#### 1,200` — always strip commas before comparison.

---

## Answer Extraction

### The Official OpenAI Pattern

From `github.com/openai/grade-school-math/dataset.py`:

```python
import re

ANS_RE = re.compile(r"#### (\-?[0-9\.\,]+)")
INVALID_ANS = "[invalid]"

def extract_answer(completion):
    match = ANS_RE.search(completion)  # search(), not match()
    if match:
        match_str = match.group(1).strip()
        match_str = match_str.replace(",", "")
        return match_str
    else:
        return INVALID_ANS

def is_correct(model_completion, gt_example):
    gt_answer = extract_answer(gt_example["answer"])
    assert gt_answer != INVALID_ANS
    return extract_answer(model_completion) == gt_answer  # string equality
```

The official comparison is **string equality** after comma removal. This means `"72"` != `"72.0"`.

### Why Models Often Don't Output `####`

Instruct/chat models are trained on conversational data, not GSM8K's annotation format. They typically output answers as:
- "The answer is 42." (CoT style from Wei et al.)
- "**42**" (markdown bold)
- `\boxed{42}` (LaTeX, math-trained models)
- Just the number at the end of reasoning

Only models specifically prompted with `####` examples or base models with few-shot `####` exemplars reliably produce the `####` format. Build extraction with fallbacks.

### Multi-Pattern Extraction (Priority Order)

When extracting from model output, try these patterns in order. For each pattern, take the **last** match (models may reference earlier numbers in their reasoning):

1. **`####` delimiter** — `r"####\s*([\d,.\-]+)"` — Official format
2. **`\boxed{}`** — `r"\\boxed\{([^}]+)\}"` — LaTeX math models
3. **"The answer is X"** — `r"[Tt]he\s+(?:final\s+)?answer\s+is[:\s]*\$?([\d,.\-]+)"` — CoT style
4. **"Answer: X"** — `r"(?i)answer\s*:\s*\$?([\d,.\-]+)"` — simple-evals style
5. **Last number in text** — `r"(-?[\d,]+\.?\d*)"` with last match — Ultimate fallback

See `references/extraction-code.md` for a complete production implementation.

### Normalization

After extraction, normalize before comparison:
```python
def normalize(s: str) -> str:
    s = s.strip().replace(",", "").rstrip(".")
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except ValueError:
        pass
    return s
```

This handles commas (`1,234` -> `1234`), trailing periods (`42.` -> `42`), and float-to-int (`42.0` -> `42`). Since GSM8K answers are always integers, converting `float -> int` is safe and catches rounding artifacts.

### Comparison Strategy

```python
def answers_match(extracted: str, ground_truth: str) -> bool:
    a, b = normalize(extracted), normalize(ground_truth)
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return False
```

String comparison first (fast path), numeric fallback (catches `"72"` vs `"72.00"`).

---

## Evaluation Methodology

### Standard Protocol

- **Metric**: Exact match accuracy = correct / total
- **Test set**: All 1,319 test examples
- **Decoding**: Greedy (`temperature=0.0`, `do_sample=False`) for deterministic eval
- **Stop sequences**: `["Question:", "</s>", "<|im_end|>"]`

### Few-Shot Configurations

| Config | Source | N-shot | Format |
|--------|--------|--------|--------|
| 0-shot | Common for instruct models | 0 | System prompt + question |
| 5-shot | LM Eval Harness default | 5 | `Question: {q}\nAnswer:` |
| 8-shot CoT | Wei et al. 2022 (NeurIPS) | 8 | `Q: {q}\nA:` with reasoning |
| 10-shot | UK BEIS inspect_evals | 10 | `ANSWER: $ANSWER` format |

The 5-shot and 8-shot CoT are **different configs** in lm-evaluation-harness (`gsm8k.yaml` vs `gsm8k-cot.yaml`). Don't confuse them.

### Prompt Formats

**LM Eval Harness standard (5-shot)**:
```
Question: {question}
Answer:
```

**LM Eval Harness CoT (8-shot, Wei et al.)**:
```
Q: {question}
A:
```

**Zero-shot CoT (Kojima et al. 2022)**:
```
Q: {question}
A: Let's think step by step.
```

**Instruct/chat models**:
```python
messages = [
    {"role": "system", "content": "Solve the following math problem step by step. ..."},
    {"role": "user", "content": question},
]
tokenizer.apply_chat_template(messages, add_generation_prompt=True)
```

The 8-shot CoT exemplars (Wei et al. 2022) use "The answer is {N}." format — NOT `####`. See `references/exemplars.md` for all 8 exemplars.

### Self-Consistency / maj@k

From Wang et al. 2022 (ICLR 2023):
1. Sample k diverse reasoning paths (`temperature=0.5-0.7`)
2. Extract the final answer from each path
3. Return the majority vote answer
4. Report as `maj@k` (e.g., `maj1@40`)

```python
from collections import Counter

def majority_vote(answers: list[str]) -> str | None:
    valid = [a for a in answers if a is not None]
    if not valid:
        return None
    return Counter(valid).most_common(1)[0][0]
```

Typical improvement: +10-18% accuracy over greedy (e.g., PaLM 540B: 57% greedy -> 74.4% with 40 samples).

---

## Common Pitfalls

These are the mistakes that trip up nearly every GSM8K evaluation implementation:

### Extraction Pitfalls

1. **First vs last number**: CoT outputs contain many intermediate numbers. Always extract the **last** match of your pattern, not the first. The official `ANS_RE.search()` returns the first `####`, which works for ground truth but not for model outputs that may include `####` in reasoning.

2. **Units in output**: Models write "$42" or "42 dollars". Strip `$` signs and text units before extraction. The LM Eval Harness normalizes `\$` away.

3. **Commas**: "1,234" must become "1234". Always `.replace(",", "")`. Forgetting this silently fails on ~5% of answers.

4. **Trailing periods**: "The answer is 42." — the period gets captured. Strip with `.rstrip(".")`.

5. **Rounding artifacts**: A model solving via decimals may output "42.0" or "41.999...". Since answers are always integers, `int(float(x))` is safe and catches these.

6. **`\boxed{}` fallback**: Math-trained models (Qwen-Math, DeepSeek-Math) output `\boxed{42}`. Without this fallback, you lose all their answers.

### Comparison Pitfalls

7. **String vs numeric**: The official code uses string equality: `"72" != "72.0"`. Normalize both sides to integers before comparing, or use numeric fallback.

8. **Multiple `####` markers**: If a model outputs `####` more than once, use the **last** match. The official regex with `search()` finds the first, which is correct for ground truth but not for model reasoning that may quote the format.

### Dataset Pitfalls

9. **Data contamination**: GSM8K is heavily contaminated in many models' training data. The GSM1k study (Zhang et al. 2024, NeurIPS) found accuracy drops of up to 13% on fresh problems vs the original test set. Phi and Mistral families are particularly affected. Frontier models (GPT-4, Claude, Gemini) show minimal contamination.

10. **Label noise**: GSM8K-Platinum (Vendrow et al. 2025) audited the test set and found ~8% of problems have issues: 110 removed (ambiguous/inconsistent) and 10 had wrong ground-truth answers. Performance "plateauing" at ~95% is partly label noise, not model limitations.

11. **Benchmark saturation**: Frontier models exceed 95% on GSM8K (2024+). Many recent model releases have stopped reporting it. For frontier differentiation, use MATH, GSM8K-Platinum, or GSM-Symbolic.

---

## LM Evaluation Harness Details

The harness (`lm-evaluation-harness`) uses two extraction filters chained together:

**strict-match**:
```yaml
filter:
  - function: "regex"
    regex_pattern: "#### (\\-?[0-9\\.\\,]+)"
  - function: "take_first"
```

**flexible-extract** (fallback):
```yaml
filter:
  - function: "regex"
    group_select: -1  # last match
    regex_pattern: "(-?[$0-9.,]{2,})|(-?[0-9]+)"
  - function: "take_first"
```

Normalization regexes strip commas, `$`, everything before `####`, and trailing periods before exact match comparison.

---

## Reporting Checklist

When reporting GSM8K scores in a paper or evaluation:

- Number of few-shot examples and their source (train split random? fixed Wei et al. exemplars?)
- Prompt format (especially for instruct models — system prompt wording matters)
- Extraction method (strict `####`, flexible last-number, multi-pattern)
- Decoding strategy (greedy vs sampling; if sampling: temperature, top_k, num_samples)
- Whether `maj@k` or `pass@k` is used (and what k)
- Whether using original test set or GSM8K-Platinum

---

## Key References

| Paper | Year | Contribution |
|-------|------|-------------|
| Cobbe et al. | 2021 | Introduced GSM8K dataset + verifier approach |
| Wei et al. | 2022 | 8-shot CoT prompting (NeurIPS 2022) |
| Wang et al. | 2022 | Self-consistency / maj@k (ICLR 2023) |
| Kojima et al. | 2022 | Zero-shot CoT ("Let's think step by step") |
| Gao et al. | 2023 | PAL: Program-Aided Language Models (ICML) |
| Chen et al. | 2023 | Program of Thoughts prompting (TMLR) |
| Zhang et al. | 2024 | GSM1k contamination study (NeurIPS) |
| Vendrow et al. | 2025 | GSM8K-Platinum (fixed 110+10 bad labels) |

---

## Quick Reference

```
Dataset:     openai/gsm8k, config="main", split="test"
Size:        train=7473, test=1319
Fields:      question (str), answer (str)
Format:      {reasoning}\n#### {positive_integer}
Answers:     ALWAYS positive integers >= 1
GT extract:  answer.split("####")[-1].strip().replace(",","")
Official RE: r"#### (\-?[0-9\.\,]+)"  then .replace(",","")
Comparison:  String equality after normalization (prefer numeric fallback)
Standard:    5-shot (harness default) or 8-shot CoT (Wei et al.)
Greedy:      temperature=0.0, do_sample=False
maj@k:       temperature=0.5-0.7, k=40+ samples, majority vote
Stop:        ["Question:", "</s>", "<|im_end|>"]
Saturation:  Frontier models >95% (2024+)
```
