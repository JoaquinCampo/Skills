# 8-Shot Chain-of-Thought Exemplars (Wei et al. 2022)

These are the canonical 8 exemplars from Wei et al. 2022 (NeurIPS), used in
`gsm8k-cot.yaml` in lm-evaluation-harness and the MGSM multilingual benchmark.

**Format note**: These exemplars end with "The answer is {N}." — they do NOT
use the `####` format. The `####` format is for dataset ground truth annotation,
not for prompting. Models prompted with these exemplars will output answers in
"The answer is {N}." format. Extract accordingly.

**Prompt template**: Each exemplar uses `Q:` / `A:` format:
```
Q: {question}
A: {chain-of-thought reasoning}. The answer is {N}.
```

---

## Exemplar 1

Q: There are 15 trees in the grove. Grove workers will plant trees in the grove today. After they are done, there will be 21 trees. How many trees did the grove workers plant today?

A: There are 15 trees originally. Then there were 21 trees after some more were planted. So there must have been 21 - 15 = 6. The answer is 6.

## Exemplar 2

Q: If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?

A: There are originally 3 cars. 2 more cars arrive. 3 + 2 = 5. The answer is 5.

## Exemplar 3

Q: Leah had 32 chocolates and her sister had 42. If they ate 35, how many pieces do they have left in total?

A: Originally, Leah had 32 chocolates. Her sister had 42. So in total they had 32 + 42 = 74. After eating 35, they had 74 - 35 = 39. The answer is 39.

## Exemplar 4

Q: Jason had 20 lollipops. He gave Denny some lollipops. Now Jason has 12 lollipops. How many lollipops did Jason give to Denny?

A: Jason started with 20 lollipops. Then he had 12 after giving some to Denny. So he gave Denny 20 - 12 = 8. The answer is 8.

## Exemplar 5

Q: Shawn has five toys. For Christmas, he got two toys each from his mom and dad. How many toys does he have now?

A: Shawn started with 5 toys. If he got 2 toys each from his mom and dad, then that is 4 more toys. 5 + 4 = 9. The answer is 9.

## Exemplar 6

Q: There were nine computers in the server room. Five more computers were installed each day, from Monday to Thursday. How many computers are now in the server room?

A: There were originally 9 computers. For each of 4 days, 5 more computers were added. So 4 * 5 = 20 computers were added. 9 + 20 = 29. The answer is 29.

## Exemplar 7

Q: Michael had 58 golf balls. On Tuesday, he lost 23 golf balls. On Wednesday, he lost 2 more. How many golf balls did he have at the end of Wednesday?

A: Michael started with 58 golf balls. After losing 23 on Tuesday, he had 58 - 23 = 35. After losing 2 more, he had 35 - 2 = 33. The answer is 33.

## Exemplar 8

Q: Olivia has $23. She bought five bagels for $3 each. How much money does she have left?

A: Olivia had 23 dollars. 5 bagels for 3 dollars each will be 5 x 3 = 15 dollars. So she has 23 - 15 = 8 dollars left. The answer is 8.

---

## Usage in Code

To construct the 8-shot CoT prompt:

```python
EXEMPLARS = [
    {
        "q": "There are 15 trees in the grove. Grove workers will plant trees in the grove today. After they are done, there will be 21 trees. How many trees did the grove workers plant today?",
        "a": "There are 15 trees originally. Then there were 21 trees after some more were planted. So there must have been 21 - 15 = 6. The answer is 6.",
    },
    {
        "q": "If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?",
        "a": "There are originally 3 cars. 2 more cars arrive. 3 + 2 = 5. The answer is 5.",
    },
    {
        "q": "Leah had 32 chocolates and her sister had 42. If they ate 35, how many pieces do they have left in total?",
        "a": "Originally, Leah had 32 chocolates. Her sister had 42. So in total they had 32 + 42 = 74. After eating 35, they had 74 - 35 = 39. The answer is 39.",
    },
    {
        "q": "Jason had 20 lollipops. He gave Denny some lollipops. Now Jason has 12 lollipops. How many lollipops did Jason give to Denny?",
        "a": "Jason started with 20 lollipops. Then he had 12 after giving some to Denny. So he gave Denny 20 - 12 = 8. The answer is 8.",
    },
    {
        "q": "Shawn has five toys. For Christmas, he got two toys each from his mom and dad. How many toys does he have now?",
        "a": "Shawn started with 5 toys. If he got 2 toys each from his mom and dad, then that is 4 more toys. 5 + 4 = 9. The answer is 9.",
    },
    {
        "q": "There were nine computers in the server room. Five more computers were installed each day, from Monday to Thursday. How many computers are now in the server room?",
        "a": "There were originally 9 computers. For each of 4 days, 5 more computers were added. So 4 * 5 = 20 computers were added. 9 + 20 = 29. The answer is 29.",
    },
    {
        "q": "Michael had 58 golf balls. On Tuesday, he lost 23 golf balls. On Wednesday, he lost 2 more. How many golf balls did he have at the end of Wednesday?",
        "a": "Michael started with 58 golf balls. After losing 23 on Tuesday, he had 58 - 23 = 35. After losing 2 more, he had 35 - 2 = 33. The answer is 33.",
    },
    {
        "q": "Olivia has $23. She bought five bagels for $3 each. How much money does she have left?",
        "a": "Olivia had 23 dollars. 5 bagels for 3 dollars each will be 5 x 3 = 15 dollars. So she has 23 - 15 = 8 dollars left. The answer is 8.",
    },
]


def build_cot_prompt(question: str) -> str:
    parts = []
    for ex in EXEMPLARS:
        parts.append(f"Q: {ex['q']}\nA: {ex['a']}")
    parts.append(f"Q: {question}\nA:")
    return "\n\n".join(parts)
```

## Extraction for CoT Format

When using these exemplars, models output "The answer is {N}." Extract with:

```python
import re

ANSWER_IS_RE = re.compile(
    r"[Tt]he\s+(?:final\s+)?answer\s+is[:\s]*\$?(-?[\d,\.]+)"
)

def extract_cot_answer(text: str) -> str | None:
    matches = ANSWER_IS_RE.findall(text)
    if matches:
        return matches[-1].replace(",", "").rstrip(".")
    return None
```
