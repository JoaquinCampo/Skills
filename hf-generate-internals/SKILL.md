---
name: hf-generate-internals
description: HF Transformers generate() internals — scores vs logits, LogitsProcessors, KV cache, StoppingCriteria, chat templates. Use when code calls model.generate(), output_scores, output_logits, return_dict_in_generate, GenerateDecoderOnlyOutput, LogitsProcessor, StoppingCriteria, past_key_values, DynamicCache, apply_chat_template, do_sample, or num_beams.
---

# HuggingFace Transformers Generation Internals

Reference for HF Transformers generation pipeline internals, verified against
**transformers 5.3.0** source code. Covers the full path from `model.generate()`
to output tensors.

## Extension Files

| File | Content |
|------|---------|
| `references/generate-loop.md` | `generate()` entry point, mode dispatch, `_sample()` loop structure, token selection, prefill |
| `references/scores-and-logits.md` | `output_scores` vs `output_logits`, tensor shapes, float32 conversion, `GenerateDecoderOnlyOutput`, memory, `compute_transition_scores()` |
| `references/logits-processors.md` | `LogitsProcessorList`, processing order, always-active vs sampling-only processors, key implementations |
| `references/kv-cache.md` | Cache class hierarchy, `DynamicCache`, attention mask / position_id updates, kvpress interaction |
| `references/stopping-criteria.md` | `StoppingCriteria` interface, built-in criteria, custom stopping, when checked in the loop |
| `references/chat-templates.md` | `apply_chat_template()`, Jinja2 rendering, `add_generation_prompt`, `continue_final_message`, tokenization patterns |

## Quick Decision Tree

```
What do you need from generation?
│
├─ Per-token logit features    → output_scores=True (see scores-and-logits.md)
│  └─ Need truly raw logits?   → output_logits=True (bypasses LogitsProcessors)
│
├─ Custom stopping logic       → StoppingCriteria subclass (see stopping-criteria.md)
│
├─ Modify token probabilities  → LogitsProcessor subclass (see logits-processors.md)
│
├─ KV cache compression/debug  → past_key_values / DynamicCache (see kv-cache.md)
│
├─ Chat-formatted prompts      → tokenizer.apply_chat_template() (see chat-templates.md)
│
└─ Understand the loop itself  → _sample() internals (see generate-loop.md)
```

## Critical Facts

1. **scores != logits**: `.scores` are post-LogitsProcessor, `.logits` are raw model output. Both are pre-softmax. With `do_sample=False` and no custom processors, they're identical.

2. **Greedy and sampling share `_sample()`**: In v5.3.0, there is no separate `_greedy_search()`. The `do_sample` flag controls behavior inside the same method.

3. **Always float32**: Logits are converted to float32 before processing (line 2754), regardless of model precision (float16/bfloat16).

4. **Score shape**: Each element of `outputs.scores` is `(batch_size, vocab_size)` — one tensor per generated token.

5. **Memory cost**: For Qwen2.5-7B (vocab=152064), 512 tokens of scores costs ~296 MB per batch element in float32.

6. **Sampling processors are gated**: Temperature, top-k, top-p warpers are only added when `do_sample=True`. With greedy decoding, scores pass through the pipeline essentially unmodified.

7. **Left-pad required**: Decoder-only models require left-padding for batched generation. HF warns if right-padding is detected.

## Review Checklist

```
□ Using return_dict_in_generate=True with output_scores=True?
□ Indexing scores correctly? scores[t] is (batch, vocab), not (vocab,)
□ Know whether scores are pre- or post-processor for your use case?
□ Not holding all score tensors on GPU unnecessarily? (move to CPU or process inline)
□ Padding direction correct for batched generation? (left-pad for decoder-only)
□ StoppingCriteria returns BoolTensor of shape (batch,)?
□ Custom LogitsProcessor signature: (input_ids: LongTensor, scores: FloatTensor) -> FloatTensor?
□ Chat template rendered with add_generation_prompt=True for generation?
```
