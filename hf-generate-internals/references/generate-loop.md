# The Generation Loop

## generate() Entry Point

**Source**: `generation/utils.py`, `GenerationMixin.generate()`

### Key Parameters

```python
model.generate(
    input_ids,                    # (batch, seq_len) or via **inputs
    max_new_tokens=512,           # max tokens to generate
    do_sample=False,              # greedy (False) or sampling (True)
    num_beams=1,                  # beam search if > 1
    temperature=1.0,              # only when do_sample=True
    top_k=50,                     # only when do_sample=True
    top_p=1.0,                    # only when do_sample=True
    output_scores=True,           # return post-processor scores
    output_logits=True,           # return raw model logits
    return_dict_in_generate=True, # return GenerateDecoderOnlyOutput
    stopping_criteria=None,       # StoppingCriteriaList
    logits_processor=None,        # LogitsProcessorList
    attention_mask=None,          # (batch, seq_len)
    use_cache=True,               # enable KV cache
)
```

### Internal Steps (from source comments)

1. Handle kwargs/config — merges `**kwargs` into `generation_config`
2. Set generation parameters — `logits_processor`, `stopping_criteria`
3. Define model inputs — `_prepare_model_inputs()`
4. Define other model kwargs — attention mask, position_ids, encoder outputs
5. Prepare input_ids — decoder-only vs encoder-decoder
6. Prepare max_length — resolves `max_new_tokens` to absolute `max_length`
7. Prepare cache — `_prepare_cache_for_generation()` creates DynamicCache
8. Prepare logits processors and stopping criteria — builds full pipeline
9. Call decoding method — dispatches to `_sample`, `_beam_search`, etc.

## Mode Dispatch

**Source**: `generation/configuration_utils.py`, line 472, `get_generation_mode()`

```
num_beams=1, do_sample=False  →  GREEDY_SEARCH  →  _sample()
num_beams=1, do_sample=True   →  SAMPLE          →  _sample()
num_beams>1, do_sample=False  →  BEAM_SEARCH     →  _beam_search()
num_beams>1, do_sample=True   →  BEAM_SAMPLE     →  _beam_search()
+ assistant_model              →  ASSISTED_GENERATION (overrides above)
```

**Critical**: In v5.3.0, `GREEDY_SEARCH` and `SAMPLE` both map to `_sample()`:

```python
# generation/utils.py, lines 132-143
GENERATION_MODES_MAPPING = {
    GenerationMode.SAMPLE: "_sample",
    GenerationMode.GREEDY_SEARCH: "_sample",       # SAME method
    GenerationMode.BEAM_SEARCH: "_beam_search",
    GenerationMode.BEAM_SAMPLE: "_beam_search",
    GenerationMode.ASSISTED_GENERATION: "_assisted_decoding",
}
```

## The _sample() Loop

**Source**: `generation/utils.py`, starting at line ~2700

### Loop Structure (pseudocode)

```python
def _sample(self, ...):
    # 1. Initialize accumulators
    scores = ()          # post-processor scores
    raw_logits = ()      # raw model logits
    unfinished_sequences = torch.ones(batch_size)

    # 2. Prefill: run model on full input sequence
    model_outputs = self._prefill(input_ids, ...)
    # Extracts: logits, cache, hidden_states, attentions

    # 3. Decode loop
    while True:
        # a. Prepare inputs (uses cache, only last token as input)
        model_inputs = self.prepare_inputs_for_generation(...)

        # b. Forward pass (single token)
        outputs = self(**model_inputs)

        # c. Update model kwargs (cache, attention_mask, position_ids)
        model_kwargs = self._update_model_kwargs_for_generation(outputs, ...)

        # d. Extract logits for last position, convert to float32
        next_token_logits = outputs.logits[:, -1, :].to(
            copy=True, dtype=torch.float32, device=input_ids.device
        )

        # e. Apply logits processors
        next_token_scores = logits_processor(input_ids, next_token_logits)

        # f. Accumulate scores/logits
        if output_scores:
            scores += (next_token_scores,)
        if output_logits:
            raw_logits += (next_token_logits,)

        # g. Token selection
        if do_sample:
            probs = nn.functional.softmax(next_token_scores, dim=-1)
            next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
        else:
            next_tokens = torch.argmax(next_token_scores, dim=-1)

        # h. Pad finished sequences (replace with pad_token_id)
        next_tokens = next_tokens * unfinished_sequences + pad_token_id * (1 - unfinished_sequences)

        # i. Append to input_ids
        input_ids = torch.cat([input_ids, next_tokens[:, None]], dim=-1)

        # j. Check stopping criteria
        unfinished_sequences = unfinished_sequences & ~stopping_criteria(input_ids, scores)
        if unfinished_sequences.max() == 0:
            break

        # k. Delete outputs (memory management)
        del outputs

    return GenerateDecoderOnlyOutput(sequences=input_ids, scores=scores, ...)
```

### Key Details

**float32 conversion** (line 2754): Model output logits may be float16/bfloat16,
but are ALWAYS copied and converted to float32 before any processing. The
`copy=True` prevents keeping a reference to the full logits tensor from the
first iteration (which includes all prefill positions).

**Prefill stage** (`_prefill()`, line 3727): New in v5.3.0. Handles the initial
forward pass on the full input, including optional chunked prefill for very long
contexts (`prefill_chunk_size` parameter). Returns model outputs + initializes cache.

**logits_to_keep optimization** (line 2482): If the model supports it, sets
`model_kwargs["logits_to_keep"] = 1` so the model only computes logits for the
last position during generation (not all positions). Saves significant compute.

**Memory: `del outputs`** (line 2801): Explicitly deletes the model outputs
reference after extracting what's needed. Without this, the first iteration's
outputs (which include logits for ALL prefill positions) would stay in memory.

## Token Selection

### Greedy (`do_sample=False`)

```python
next_tokens = torch.argmax(next_token_scores, dim=-1)
```

The argmax operates on **post-processor** scores. Since no sampling processors
are active in greedy mode, this is argmax of essentially raw logits (unless
custom processors are set).

### Sampling (`do_sample=True`)

```python
probs = nn.functional.softmax(next_token_scores, dim=-1)
next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
```

Scores have already been modified by temperature, top-k, top-p warpers before
this point. The softmax converts to probabilities, then multinomial samples.

### Score-Token Relationship

The saved `scores[t]` corresponds to the full vocabulary distribution BEFORE
token selection at step t. The actually selected token is `sequences[prompt_len + t]`.
To get the score of the selected token:

```python
# Manual extraction
selected_score = scores[t][batch_idx, sequences[0, prompt_len + t]]

# Or use the built-in utility
transition_scores = model.compute_transition_scores(
    outputs.sequences, outputs.scores, normalize_logits=True
)
# Returns (batch, num_generated_tokens) of per-token log-probs
```

## Gotchas

1. **`scores[t]` is NOT the logit of the selected token** — it's the full
   `(batch, vocab_size)` distribution. Use `compute_transition_scores()` or
   manual indexing to get the score of the actually selected token.

2. **First iteration logits are huge**: The prefill forward pass produces
   logits for ALL input positions. The `del outputs` + `copy=True` pattern
   prevents this from leaking into memory. If you modify the loop, preserve this.

3. **`do_sample=False` still goes through `_sample()`**: Don't look for a
   `_greedy_search()` method — it doesn't exist in v5.3.0. Both greedy and
   sampling are handled by `_sample()` with a flag check.

4. **`max_new_tokens` vs `max_length`**: `max_new_tokens` is relative to
   input length; `max_length` is absolute. If both are set, `max_new_tokens`
   takes precedence. Always prefer `max_new_tokens` to avoid prompt-length
   dependent behavior.
