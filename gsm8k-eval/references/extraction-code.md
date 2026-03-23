# Production Answer Extraction Implementation

Complete, battle-tested extraction code handling all known GSM8K answer formats.

## Multi-Pattern Extractor

```python
import re


# Priority 1: #### delimiter (official GSM8K format)
HASH_RE = re.compile(r"####\s*(-?[\d,\.]+)")

# Priority 2: \boxed{} (LaTeX format, math-trained models)
BOXED_RE = re.compile(r"\\boxed\{([^}]+)\}")

# Priority 3: "The answer is X" (CoT format from Wei et al. 2022)
ANSWER_IS_RE = re.compile(
    r"[Tt]he\s+(?:final\s+)?answer\s+is[:\s]*\$?(-?[\d,\.]+)"
)

# Priority 4: "ANSWER: X" or "Answer: X" (OpenAI simple-evals format)
ANSWER_COLON_RE = re.compile(r"(?i)answer\s*:\s*\$?(-?[\d,\.]+)")

# Priority 5: Last number in text (ultimate fallback)
LAST_NUMBER_RE = re.compile(r"(-?[\d,]+\.?\d*)")


def normalize_number(s: str) -> str:
    """Normalize an extracted number string.

    Strips commas, trailing periods, and converts whole floats to ints.
    Since GSM8K answers are always positive integers, the float-to-int
    conversion is safe and catches rounding artifacts like "42.0".
    """
    s = s.strip().replace(",", "").rstrip(".")
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except ValueError:
        pass
    return s


def extract_answer(text: str) -> str | None:
    """Extract numeric answer from model output.

    Tries multiple patterns in priority order, taking the LAST match
    for each pattern (because CoT outputs contain many intermediate
    numbers — the answer is typically last).

    Returns normalized string or None if no number found.
    """
    # Priority 1: #### format (last match)
    matches = HASH_RE.findall(text)
    if matches:
        return normalize_number(matches[-1])

    # Priority 2: \boxed{} format (last match)
    matches = BOXED_RE.findall(text)
    if matches:
        # Content inside \boxed might include non-numeric chars
        num = re.search(r"-?\d[\d,]*\.?\d*", matches[-1])
        if num:
            return normalize_number(num.group())

    # Priority 3: "The answer is X" (last match)
    matches = ANSWER_IS_RE.findall(text)
    if matches:
        return normalize_number(matches[-1])

    # Priority 4: "Answer: X" (last match)
    matches = ANSWER_COLON_RE.findall(text)
    if matches:
        return normalize_number(matches[-1])

    # Priority 5: Last number in text
    matches = LAST_NUMBER_RE.findall(text)
    if matches:
        return normalize_number(matches[-1])

    return None


def extract_ground_truth(answer_field: str) -> str:
    """Extract ground truth from GSM8K answer field.

    The answer field looks like:
    "Natalia sold 48/2 = <<48/2=24>>24 clips...\n#### 72"

    Returns the normalized number after ####.
    """
    return answer_field.split("####")[-1].strip().replace(",", "")


def is_correct(
    model_output: str,
    ground_truth: str,
    tolerance: float = 1e-6,
) -> bool:
    """Check if model output matches ground truth.

    Args:
        model_output: Full model-generated text
        ground_truth: Already-extracted ground truth (e.g., "72")
        tolerance: Numeric tolerance for float comparison

    Returns True if the extracted answer matches ground truth.
    """
    extracted = extract_answer(model_output)
    if extracted is None:
        return False

    gt = normalize_number(ground_truth)

    # Fast path: string equality
    if extracted == gt:
        return True

    # Slow path: numeric comparison (catches "72" vs "72.0")
    try:
        return abs(float(extracted) - float(gt)) < tolerance
    except ValueError:
        return False


def is_correct_strict(model_output: str, ground_truth: str) -> bool:
    """Official-style string comparison (no numeric fallback).

    Matches the behavior of OpenAI's official is_correct():
    string equality after comma removal. Use this when you need
    exact reproducibility with official benchmarks.
    """
    extracted = extract_answer(model_output)
    if extracted is None:
        return False
    gt = ground_truth.strip().replace(",", "")
    return extracted == gt
```

## Majority Voting (Self-Consistency)

```python
from collections import Counter


def majority_vote(
    model_outputs: list[str],
    extraction_fn=extract_answer,
) -> str | None:
    """Return the most common answer from sampled reasoning paths.

    For use with self-consistency (Wang et al. 2022).
    Requires multiple samples per question (temperature > 0).

    Args:
        model_outputs: List of model-generated texts (k samples)
        extraction_fn: Function to extract answer from each output

    Returns the majority answer, or None if no valid answers found.
    """
    answers = [extraction_fn(output) for output in model_outputs]
    valid = [a for a in answers if a is not None]
    if not valid:
        return None
    return Counter(valid).most_common(1)[0][0]


def majority_accuracy(
    all_outputs: list[list[str]],
    ground_truths: list[str],
    k: int | None = None,
) -> float:
    """Compute maj@k accuracy across the test set.

    Args:
        all_outputs: List of [k model outputs] per question
        ground_truths: List of ground truth answers
        k: Number of samples to use (None = use all)

    Returns accuracy as a float in [0, 1].
    """
    correct = 0
    for outputs, gt in zip(all_outputs, ground_truths):
        samples = outputs[:k] if k else outputs
        voted = majority_vote(samples)
        if voted is not None and is_correct_from_answer(voted, gt):
            correct += 1
    return correct / len(ground_truths)


def is_correct_from_answer(
    extracted: str, ground_truth: str
) -> bool:
    """Compare already-extracted answer to ground truth."""
    gt = normalize_number(ground_truth)
    if extracted == gt:
        return True
    try:
        return abs(float(extracted) - float(gt)) < 1e-6
    except ValueError:
        return False
```

## LM Evaluation Harness Compatibility

If you need to match the exact behavior of `lm-evaluation-harness`:

```python
# strict-match filter: extract from #### format
STRICT_RE = re.compile(r"####\s*(-?[0-9\.\,]+)")

# flexible-extract filter: last number (with $ tolerance)
FLEXIBLE_RE = re.compile(r"(-?[$0-9.,]{2,})|(-?[0-9]+)")

# Normalization applied before exact_match comparison
NORMALIZE_PATTERNS = [
    (re.compile(r","), ""),           # strip commas
    (re.compile(r"\$"), ""),          # strip dollar signs
    (re.compile(r"(?s).*#### "), ""), # strip everything before ####
    (re.compile(r"\.$"), ""),         # strip trailing period
]


def harness_normalize(text: str) -> str:
    """Apply lm-evaluation-harness normalization."""
    text = text.lower()
    for pattern, replacement in NORMALIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()
```
