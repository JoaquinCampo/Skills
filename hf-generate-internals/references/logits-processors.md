# LogitsProcessor Pipeline

**Source**: `generation/logits_process.py` (3218 lines)

## How It Works

```python
class LogitsProcessorList(list):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs):
        for processor in self:
            scores = processor(input_ids, scores)
        return scores
```

Each processor receives `(input_ids, scores)` and returns modified `scores`.
- `input_ids`: `(batch_size, current_seq_length)` — full sequence so far
- `scores`: `(batch_size, vocab_size)` — current step's logits in float32
- Returns: `(batch_size, vocab_size)` — modified scores

Processors are applied **sequentially** in list order. Each processor sees
the output of the previous one.

## Processing Order

Built in `_get_logits_processor()` (line 1025-1246 of `generation/utils.py`).

### Always-Active Processors

These are added regardless of `do_sample` setting:

| Order | Processor | Trigger |
|-------|-----------|---------|
| 1 | `UnbatchedClassifierFreeGuidanceLogitsProcessor` | `guidance_scale` set |
| 2 | `SequenceBiasLogitsProcessor` | `sequence_bias` set |
| 3 | `EncoderRepetitionPenaltyLogitsProcessor` | encoder-decoder + penalty |
| 4 | `RepetitionPenaltyLogitsProcessor` | `repetition_penalty != 1.0` |
| 5 | `NoRepeatNGramLogitsProcessor` | `no_repeat_ngram_size > 0` |
| 6 | `EncoderNoRepeatNGramLogitsProcessor` | encoder-decoder + ngram |
| 7 | `NoBadWordsLogitsProcessor` | `bad_words_ids` set |
| 8 | `MinLengthLogitsProcessor` | `min_length > 0` |
| 9 | `MinNewTokensLengthLogitsProcessor` | `min_new_tokens > 0` |
| 10 | `PrefixConstrainedLogitsProcessor` | `prefix_allowed_tokens_fn` |
| 11 | `ForcedBOSTokenLogitsProcessor` | `forced_bos_token_id` |
| 12 | `ForcedEOSTokenLogitsProcessor` | `forced_eos_token_id` |
| 13 | `InfNanRemoveLogitsProcessor` | Always (safety) |
| 14 | `ExponentialDecayLengthPenalty` | `exponential_decay_length_penalty` |
| 15 | `SuppressTokensLogitsProcessor` | `suppress_tokens` |
| 16 | `SuppressTokensAtBeginLogitsProcessor` | `begin_suppress_tokens` |
| 17 | **User-defined processors** | Custom `logits_processor` arg |

User-defined processors are merged: if a custom processor has the same type as
a built-in one, it replaces the default. Otherwise, it's appended.

### Sampling-Only Processors

Gated by `if generation_config.do_sample:` (line 1186):

| Order | Processor | What it does |
|-------|-----------|-------------|
| 18 | `TemperatureLogitsWarper` | `scores = scores / temperature` |
| 19 | `TopHLogitsWarper` | Entropy-based filtering |
| 20 | `TopKLogitsWarper` | Keep top-k, set rest to `-inf` |
| 21 | `TopPLogitsWarper` | Nucleus: keep cumsum < p, set rest to `-inf` |
| 22 | `MinPLogitsWarper` | Min-p filtering |
| 23 | `TypicalLogitsWarper` | Typical decoding |
| 24 | `EpsilonLogitsWarper` | Epsilon sampling |
| 25 | `EtaLogitsWarper` | Eta sampling |

### Final Processors (Always Last)

| Order | Processor | Trigger |
|-------|-----------|---------|
| 26 | `WatermarkingProcessor` | `watermarking_config` set |
| 27 | `LogitNormalization` | `renormalize_logits=True` |

`LogitNormalization` applies `log_softmax`, converting scores to proper
log-probabilities. Always placed last to normalize after all modifications.

## Key Processor Implementations

### TemperatureLogitsWarper

```python
def __call__(self, input_ids, scores):
    return scores / self.temperature
# temperature > 1.0 → flatter distribution (more random)
# temperature < 1.0 → sharper distribution (more deterministic)
# temperature = 1.0 → no-op (but processor is still in the list)
```

### TopKLogitsWarper

```python
def __call__(self, input_ids, scores):
    top_k = min(self.top_k, scores.size(-1))
    indices_to_remove = scores < torch.topk(scores, top_k)[0][..., -1, None]
    scores = scores.masked_fill(indices_to_remove, self.filter_value)  # -inf
    return scores
```

### TopPLogitsWarper (Nucleus Sampling)

```python
def __call__(self, input_ids, scores):
    sorted_logits, sorted_indices = torch.sort(scores, descending=False)
    cumulative_probs = sorted_logits.softmax(dim=-1).cumsum(dim=-1)
    sorted_indices_to_remove = cumulative_probs <= (1 - self.top_p)
    # ... mask and scatter back to original positions
    return scores.masked_fill(indices_to_remove, -inf)
```

### RepetitionPenaltyLogitsProcessor

```python
def __call__(self, input_ids, scores):
    for i in range(scores.shape[0]):
        for token_id in set(input_ids[i].tolist()):
            if scores[i, token_id] < 0:
                scores[i, token_id] *= self.penalty
            else:
                scores[i, token_id] /= self.penalty
    return scores
# penalty > 1.0 → discourages repetition
# Applied to ALL previously generated tokens
```

## Implications for Greedy Decoding

With `do_sample=False` (the default), **none of the sampling processors are
added**. The only processors that could modify scores are:

1. RepetitionPenaltyLogitsProcessor (if `repetition_penalty != 1.0`)
2. NoBadWordsLogitsProcessor (if `bad_words_ids` set)
3. MinLength / MinNewTokens processors
4. InfNanRemoveLogitsProcessor (always, but only fixes NaN/Inf)
5. Any custom user-defined processors

If none of these are configured (which is Herald's case), `output_scores`
gives you essentially the raw model logits in float32.

## Writing Custom Processors

```python
class MyLogitsProcessor(LogitsProcessor):
    def __call__(
        self,
        input_ids: torch.LongTensor,     # (batch, seq_len)
        scores: torch.FloatTensor,        # (batch, vocab_size)
    ) -> torch.FloatTensor:
        # Modify scores in-place or return new tensor
        # Example: boost token 42
        scores[:, 42] += 10.0
        return scores

# Usage:
from transformers import LogitsProcessorList
processors = LogitsProcessorList([MyLogitsProcessor()])
outputs = model.generate(..., logits_processor=processors)
```

Custom processors see `input_ids` including the prompt AND all previously
generated tokens, so they can implement context-dependent logic.

## Gotchas

1. **Processor order matters**: Temperature is applied BEFORE top-k/top-p.
   If you add a custom processor, it gets inserted among the always-active
   group (position 17), before any sampling warpers. If you need it after
   sampling warpers, you can't use the standard `logits_processor` argument.

2. **In-place modification is allowed but risky**: Processors CAN modify the
   `scores` tensor in-place. But if `output_scores=True`, the saved scores
   reflect the in-place modifications from ALL subsequent processors, not
   just the current one. Return a new tensor if you need clean saved scores.

3. **`-inf` means "impossible"**: Top-k/top-p warpers set filtered tokens to
   `-inf`, not zero. After softmax, `-inf` becomes 0.0 probability. If you
   see `-inf` in saved scores, that's expected from sampling processors.

4. **Custom processor replaces same-type default**: If your custom processor
   is a subclass of a built-in one (e.g., `RepetitionPenaltyLogitsProcessor`),
   it replaces the default rather than running alongside it.
