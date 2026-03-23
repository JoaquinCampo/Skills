# Score Tensors, Output Logits, and GenerateDecoderOnlyOutput

## output_scores vs output_logits

These are two **separate** parameters that capture different stages of the
logit processing pipeline:

```
Model forward pass
    │
    ▼
raw logits (vocab_size,)  ← captured by output_logits=True  → outputs.logits
    │
    ▼
LogitsProcessorList.__call__()
    │
    ▼
processed scores (vocab_size,)  ← captured by output_scores=True  → outputs.scores
    │
    ▼
Token selection (argmax or multinomial)
```

### The Critical Distinction

| | `.scores` | `.logits` |
|-|-----------|-----------|
| **What** | Post-LogitsProcessor scores | Raw model output logits |
| **When captured** | After all processors run | Before any processor |
| **Pre/post softmax** | Pre-softmax (logit space) | Pre-softmax (logit space) |
| **Affected by temperature** | Yes (if `do_sample=True`) | Never |
| **Affected by top-k/top-p** | Yes (if `do_sample=True`) | Never |
| **Affected by repetition penalty** | Yes (if set) | Never |
| **Parameter** | `output_scores=True` | `output_logits=True` |
| **Shape per step** | `(batch_size, vocab_size)` | `(batch_size, vocab_size)` |

### When scores == logits

With `do_sample=False` (greedy) and **no custom LogitsProcessors**, the only
processors in the pipeline are non-sampling ones. If none of these are triggered
(no `repetition_penalty`, no `min_length`, no `bad_words_ids`, etc.), then
`scores` and `logits` are **identical** (both are the raw model output in float32).

This is the case for Herald's current configuration.

### When they differ

- `do_sample=True`: Temperature divides scores, top-k/top-p set entries to `-inf`
- `repetition_penalty` set: Penalizes already-generated token scores
- `no_repeat_ngram_size` set: Sets repeated n-gram continuations to `-inf`
- Any custom `LogitsProcessor` passed to `generate()`

## GenerateDecoderOnlyOutput

**Source**: `generation/utils.py`

```python
@dataclass
class GenerateDecoderOnlyOutput(ModelOutput):
    sequences: torch.LongTensor        # (batch, total_seq_len) including prompt
    scores: tuple[torch.FloatTensor]    # if output_scores=True
    logits: tuple[torch.FloatTensor]    # if output_logits=True
    attentions: tuple                   # if output_attentions=True
    hidden_states: tuple                # if output_hidden_states=True
    past_key_values: Cache              # if use_cache=True
```

### Fields Detail

| Field | Returned when | Shape / type |
|-------|---------------|--------------|
| `sequences` | Always (with `return_dict_in_generate`) | `(batch, prompt_len + num_generated)` |
| `scores` | `output_scores=True` | Tuple of `num_generated` tensors, each `(batch, vocab_size)` |
| `logits` | `output_logits=True` | Tuple of `num_generated` tensors, each `(batch, vocab_size)` |
| `attentions` | `output_attentions=True` | Tuple of tuples (per layer) of attention tensors |
| `hidden_states` | `output_hidden_states=True` | Tuple of tuples (per layer) of hidden state tensors |
| `past_key_values` | `use_cache=True` | `Cache` instance (DynamicCache by default) |

### Type Aliases

```python
GenerateNonBeamOutput = GenerateDecoderOnlyOutput  # alias
# For beam search: GenerateBeamDecoderOnlyOutput (includes beam_indices)
```

### Accessing Generated Token IDs

```python
outputs = model.generate(**inputs, return_dict_in_generate=True, output_scores=True)

# Full sequence (prompt + generated)
full_sequence = outputs.sequences[0]  # (total_seq_len,)

# Generated tokens only
input_len = inputs["input_ids"].shape[1]
generated_ids = outputs.sequences[0, input_len:]  # (num_generated,)

# Decode
text = tokenizer.decode(generated_ids, skip_special_tokens=True)
```

## Score Tensor Indexing

```python
# outputs.scores is a tuple of length num_generated_tokens
# Each element: (batch_size, vocab_size)

# Score for step t, batch element b:
step_scores = outputs.scores[t]        # (batch, vocab)
single_scores = outputs.scores[t][b]   # (vocab,)

# Score of the actually selected token at step t:
token_id = outputs.sequences[b, input_len + t]
selected_score = outputs.scores[t][b, token_id]  # scalar

# Full vocabulary log-probabilities at step t:
log_probs = F.log_softmax(outputs.scores[t][b], dim=-1)  # (vocab,)
```

## compute_transition_scores()

**Source**: `generation/utils.py`, line 1323

Built-in utility to extract the score of each selected token:

```python
transition_scores = model.compute_transition_scores(
    outputs.sequences,
    outputs.scores,
    normalize_logits=False,   # True → applies log_softmax first
)
# Returns: (batch, num_generated_tokens)
```

With `normalize_logits=True`, returns proper log-probabilities. Without it,
returns raw (post-processor) logit values for the selected tokens.

Herald does NOT use this — it processes the full vocabulary distribution at
each step (entropy, top-k, KL divergence, etc.), which requires the full
score tensor, not just the selected token's score.

## Memory Considerations

Score tensors are stored on the same device as the model. For large vocabularies,
this adds up quickly:

```
Memory per step = batch_size × vocab_size × 4 bytes (float32)

Examples (batch_size=1):
  Qwen2.5-7B:  vocab=152,064  → 594 KB/step  → 297 MB for 512 steps
  Llama-3-8B:  vocab=128,256  → 500 KB/step  → 250 MB for 512 steps
  GPT-2:       vocab= 50,257  → 196 KB/step  →  98 MB for 512 steps
```

### Strategies to Manage Memory

```python
# 1. Process scores inline (don't store them all)
# — Requires a custom LogitsProcessor that extracts features during generation

# 2. Move to CPU after generation
scores_cpu = tuple(s.cpu() for s in outputs.scores)

# 3. Only request what you need
# output_scores=True but output_logits=False (or vice versa)

# 4. Use output_logits instead of output_scores when you need raw values
# (avoids duplicate storage if you'd otherwise need both)
```

### The `del outputs` Pattern

In the generation loop (line 2801), HF explicitly does `del outputs` after
extracting needed values. Without this, the first iteration's outputs object
(which includes logits for ALL prefill positions, not just the last one) would
remain in memory. The `copy=True` in the float32 conversion ensures the
extracted logits don't hold a reference to the original tensor.

## Gotchas

1. **`scores` and `logits` are both pre-softmax** — neither is a probability
   distribution. Apply `F.softmax()` or `F.log_softmax()` yourself. The name
   "scores" is misleading if you expect probabilities.

2. **Don't request both unless needed**: `output_scores=True` and
   `output_logits=True` together stores TWO copies of `(batch, vocab_size)`
   per step. For Qwen2.5-7B that's ~594 MB/step combined.

3. **Scores tuple length == num generated tokens**, NOT total sequence length.
   `len(outputs.scores) != outputs.sequences.shape[1]`. The scores don't
   include the prompt positions.

4. **With greedy + no custom processors, scores == logits**: Don't store both.
   Pick one. Herald correctly uses only `output_scores=True`.

5. **Score tensors stay on GPU**: They're allocated on the model's device.
   For long generations, move to CPU incrementally or process inline to avoid
   OOM.
