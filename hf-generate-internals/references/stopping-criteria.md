# StoppingCriteria

**Source**: `generation/stopping_criteria.py` (518 lines)

## Interface

```python
class StoppingCriteria(ABC):
    def __call__(
        self,
        input_ids: torch.LongTensor,      # (batch_size, current_seq_length)
        scores: torch.FloatTensor,         # (batch_size, vocab_size)
        **kwargs,
    ) -> torch.BoolTensor:
        # Returns: (batch_size,) — True means STOP this sequence
        raise NotImplementedError
```

Key points:
- `input_ids` includes the full sequence (prompt + generated so far)
- `scores` is the current step's processed scores (post-LogitsProcessor)
- Must return a `BoolTensor` of shape `(batch_size,)`, not a scalar bool
- Each element independently controls whether that batch element stops

## StoppingCriteriaList

```python
class StoppingCriteriaList(list):
    def __call__(self, input_ids, scores, **kwargs) -> torch.BoolTensor:
        is_done = torch.full(
            (input_ids.shape[0],), False, device=input_ids.device, dtype=torch.bool
        )
        for criteria in self:
            is_done = is_done | criteria(input_ids, scores, **kwargs)
        return is_done
```

Any single criterion returning True stops that sequence. They're OR'd together.

## When Checked in the Generation Loop

```python
# After token selection and appending to input_ids (line 2796 in _sample):
unfinished_sequences = unfinished_sequences & ~stopping_criteria(input_ids, scores)
this_peer_finished = unfinished_sequences.max() == 0
```

The check happens **after**:
1. LogitsProcessors have been applied
2. Token has been selected (argmax or multinomial)
3. Token has been appended to `input_ids`

So `input_ids` passed to StoppingCriteria already includes the just-generated token.

## Built-in Criteria

Added automatically in `_get_stopping_criteria()`:

| Criterion | Added when | What it checks |
|-----------|-----------|----------------|
| `MaxLengthCriteria` | Always | `input_ids.shape[-1] >= max_length` |
| `MaxTimeCriteria` | `max_time` set | `time.time() - initial_time > max_time` |
| `EosTokenCriteria` | `eos_token_id` set | Last generated token == eos_token_id |
| `StopStringCriteria` | `stop_strings` set | Generated text contains stop string |
| User-defined criteria | `stopping_criteria` arg | Appended after built-ins |

### EosTokenCriteria

```python
class EosTokenCriteria(StoppingCriteria):
    def __call__(self, input_ids, scores, **kwargs):
        # Check if last token is any of the eos tokens
        is_done = torch.isin(input_ids[:, -1], self.eos_token_id)
        return is_done
```

Supports multiple EOS tokens (e.g., Llama 3 uses `<|eot_id|>` and `<|end_of_text|>`).

### MaxTimeCriteria

```python
class MaxTimeCriteria(StoppingCriteria):
    def __call__(self, input_ids, scores, **kwargs):
        elapsed = time.time() - self.initial_timestamp
        return torch.full(
            (input_ids.shape[0],), elapsed > self.max_time,
            dtype=torch.bool, device=input_ids.device
        )
```

Returns True for ALL batch elements when time exceeds threshold — it's a
global stop, not per-sequence.

## Writing Custom StoppingCriteria

```python
class MyStoppingCriteria(StoppingCriteria):
    def __init__(self, max_entropy: float):
        self.max_entropy = max_entropy

    def __call__(
        self,
        input_ids: torch.LongTensor,
        scores: torch.FloatTensor,
        **kwargs,
    ) -> torch.BoolTensor:
        # Example: stop if entropy of current scores exceeds threshold
        probs = F.softmax(scores, dim=-1)
        entropy = -(probs * probs.log()).sum(dim=-1)  # (batch,)
        return entropy > self.max_entropy

# Usage:
criteria = StoppingCriteriaList([
    MyStoppingCriteria(max_entropy=5.0),
])
outputs = model.generate(..., stopping_criteria=criteria)
```

### Herald's Custom Stopping

Herald uses a timeout-based criterion:

```python
class _TimeoutCriteria(StoppingCriteria):
    def __init__(self, timeout_seconds: float):
        self.timeout = timeout_seconds
        self.start_time = time.time()

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        return (time.time() - self.start_time) > self.timeout
```

Note: Herald's implementation returns a `bool` instead of `torch.BoolTensor`.
This works because HF's code handles it, but returning a proper BoolTensor of
shape `(batch_size,)` is the correct contract. Since Herald always uses
batch_size=1, the scalar bool works fine in practice.

## Interaction with Finished Sequences

Once a sequence is marked as finished (via stopping criteria or EOS), the
generation loop pads subsequent tokens with `pad_token_id`:

```python
# Line 2787 in _sample():
next_tokens = next_tokens * unfinished_sequences + pad_token_id * (1 - unfinished_sequences)
```

This means in batched generation, finished sequences get padding while
unfinished ones continue. The loop only breaks when ALL sequences are finished.

## Gotchas

1. **Return `BoolTensor(batch_size,)`, not `bool`**: The contract requires a
   per-sequence tensor. Returning a scalar `bool` works for batch_size=1 but
   silently breaks batched generation (all sequences stop/continue together).

2. **`input_ids` already includes the just-generated token**: StoppingCriteria
   is called AFTER the new token is appended. So `input_ids[:, -1]` is the
   token that was just selected, not the previous one.

3. **`scores` argument is the CURRENT step only**: It's `(batch, vocab_size)`
   for the current step, not a history. To access past scores, you'd need to
   store them yourself in the criteria's `__init__` state.

4. **MaxTimeCriteria is global, not per-sequence**: When time runs out, ALL
   sequences stop — there's no way to let some finish if they're close to EOS.
   Herald's `_TimeoutCriteria` has this same behavior.
