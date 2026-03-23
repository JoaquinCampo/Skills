# KV Cache Internals

**Source**: `transformers/cache_utils.py`

## Cache Class Hierarchy

```
CacheLayerMixin (ABC)           ← per-layer cache interface
├── DynamicLayer                # Grows via torch.cat
├── DynamicSlidingWindowLayer   # Crops to sliding_window after update
├── StaticLayer                 # Pre-allocated, fixed size
└── StaticSlidingWindowLayer

Cache                           ← container of CacheLayerMixin objects
├── DynamicCache                # Default for generation
├── StaticCache                 # For torch.compile / export
├── QuantizedCache              # Quantized KV storage
└── EncoderDecoderCache         # Wraps self-attn + cross-attn caches
```

The old `tuple[tuple[torch.Tensor, torch.Tensor], ...]` format for
`past_key_values` is **gone** in v5.3.0. Passing tuples raises an error.

## DynamicCache

**Source**: `cache_utils.py`, line 906

The default cache created during generation:

```python
# Created in _prepare_cache_for_generation() (line 1803)
model_kwargs["past_key_values"] = DynamicCache(config=self.config.get_text_config())
```

### Internal Structure

- Contains a **list of CacheLayerMixin objects**, one per model layer
- Each layer stores two tensors:
  - `keys`: `[batch_size, num_heads, seq_len, head_dim]`
  - `values`: `[batch_size, num_heads, seq_len, head_dim]`
- If model config specifies sliding window for some layers, those layers
  use `DynamicSlidingWindowLayer` instead of `DynamicLayer`

### Update Operation

```python
# Inside each attention layer:
cache.update(key_states, value_states, layer_idx)

# DynamicLayer.update():
self.keys = torch.cat([self.keys, key_states], dim=-2)    # concat along seq dim
self.values = torch.cat([self.values, value_states], dim=-2)
return self.keys, self.values
```

During generation, each step concatenates one new position. After 512 steps
of a 7B model, the cache holds:

```
Memory = num_layers × 2 × batch × heads × seq_len × head_dim × dtype_bytes

Qwen2.5-7B (28 layers, 4 KV heads, head_dim=128, float16):
  28 × 2 × 1 × 4 × 512 × 128 × 2 bytes ≈ 57 MB per 512 tokens
```

## How Cache Flows Through the Generation Loop

```
1. _prepare_cache_for_generation()
   └→ Creates empty DynamicCache

2. _prefill(input_ids, ...)
   └→ Full forward pass on prompt
   └→ Cache now holds KV for all prompt tokens

3. _update_model_kwargs_for_generation(outputs, ...)
   └→ model_kwargs["past_key_values"] = outputs.past_key_values

4. prepare_inputs_for_generation(input_ids, past_key_values=cache, ...)
   └→ Returns only the LAST token as input_ids (cache has the rest)
   └→ Sets cache_position for the new token

5. model(**model_inputs)
   └→ Each attention layer calls cache.update(new_k, new_v, layer_idx)
   └→ Returns outputs with updated past_key_values

6. Back to step 3 for next iteration
```

## Attention Mask and Position IDs During Generation

**Source**: `_update_model_kwargs_for_generation()`, line 883

After each token is generated:

```python
# Attention mask: append a 1 for the new token
attention_mask = torch.cat(
    [attention_mask, attention_mask.new_ones((..., 1))],
    dim=-1
)
# Shape grows: (batch, seq_len) → (batch, seq_len + 1)

# Position IDs: increment from last position
next_position_ids = position_ids[..., -1:] + 1

# Cache position: increment counter
next_cache_position = cache_position[-1] + 1
```

The 2D attention mask `(batch, seq_len)` flows through the generation loop.
The model's `prepare_inputs_for_generation()` may internally create a 4D
causal mask from this, but the loop only manages the 2D version.

## How Cache Interacts with kvpress

The kvpress library compresses KV caches via a context manager:

```python
from kvpress import StreamingLLMPress

press = StreamingLLMPress(compression_ratio=0.875)
with press(model):
    outputs = model.generate(...)
```

Inside the context manager:
1. kvpress monkey-patches the model's attention layers
2. During prefill, the full KV cache is computed normally
3. **After prefill**, the press compresses the cache by removing/merging entries
4. Subsequent decode steps use the compressed (smaller) cache
5. The model attends over fewer positions → different attention patterns → different logits

This is exactly what Herald exploits: the logit signals after compression
reflect the model operating with degraded context, and these signal changes
are detectable before catastrophic failures manifest.

### What compression looks like in the cache

```
Before compression (after prefill):
  cache.keys[layer_idx].shape = [1, heads, 512, head_dim]  # 512 prompt tokens

After StreamingLLM compression at 0.875:
  cache.keys[layer_idx].shape = [1, heads, 64, head_dim]   # 64 tokens kept
  # Keeps first few "sink" tokens + most recent window
```

## StaticCache (for torch.compile)

Pre-allocates cache tensors at a fixed `max_cache_len`:

```python
cache = StaticCache(
    config=model.config,
    batch_size=1,
    max_cache_len=1024,
    device=device,
    dtype=torch.float16,
)
```

Uses `StaticLayer` which overwrites at `cache_position` indices instead of
concatenating. Required for `torch.compile` because dynamic shapes from
`torch.cat` cause graph breaks.

## Common Pitfalls

1. **Don't pass tuples as past_key_values**: v5.3.0 requires Cache objects.
   Use `DynamicCache.from_legacy_cache(past_key_values)` if converting from
   old code.

2. **Cache lives on GPU**: It's on the same device as the model. For long
   sequences, this is a significant memory cost. Use `cache.to("cpu")` for
   offloading if needed.

3. **Cache position tracking**: The `cache_position` tensor tracks which
   positions in the cache are filled. This is separate from `position_ids`
   (which tracks position encodings).

4. **Clearing cache between runs**: If reusing a model across different
   prompts, the cache is recreated by `generate()` automatically. But if
   calling the model manually, pass `past_key_values=None` to start fresh.
