---
name: kvpress
description: "kvpress (NVIDIA) KV-cache compression for HuggingFace LLMs. Use when: kvpress imports, compression_ratio, press(model) context managers, StreamingLLMPress, SnapKVPress, ExpectedAttentionPress, TOVAPress, KnormPress, KV-cache eviction, token pruning during generation, or attention sink methods."
---

# kvpress — KV-Cache Compression for LLMs

kvpress is an NVIDIA library that compresses the KV cache of HuggingFace transformers models during generation, reducing memory usage at the cost of potential quality degradation.

- **Repository**: https://github.com/NVIDIA/kvpress
- **Paper**: https://arxiv.org/abs/2510.00636v1
- **Version**: 0.5.1+ (requires transformers v5+)
- **License**: Apache 2.0

## Core Concept

A "press" is a callable object that wraps a model as a context manager. Inside the context, forward hooks on every attention layer intercept the KV cache after prefilling and prune it according to the press's strategy. Generation then proceeds with the compressed cache.

```python
from kvpress import StreamingLLMPress

press = StreamingLLMPress(compression_ratio=0.5)

with torch.no_grad(), press(model):
    outputs = model.generate(**inputs, max_new_tokens=256)
```

## compression_ratio — The #1 Gotcha

```
compression_ratio = fraction of KV pairs to REMOVE (not keep)
```

| compression_ratio | Effect |
|---|---|
| `0.0` | No compression (keep 100%) |
| `0.5` | Remove 50%, keep 50% |
| `0.875` | Remove 87.5%, keep 12.5% |
| `1.0` | **Invalid** (assertion fails) |

Internal calculation: `n_kept = int(seq_len * (1 - compression_ratio))`

If your code uses "fraction to keep" semantics, convert: `kvpress_ratio = 1.0 - keep_fraction`

## Context Manager Mechanics

When you call `press(model)`:

1. **Validates** model architecture (warning if unsupported, not an error)
2. **Registers** `forward_hook(with_kwargs=True)` on every `model.model.layers[i].self_attn`
3. **Yields** control — your `model.generate()` runs here
4. **Removes** all hooks on context exit

The hooks fire **only during prefill** (when `q_len == k_len`). During autoregressive generation, hooks are still registered but skip compression. This means:

- Compression is a one-time operation at the start of generation
- All generated tokens see the same compressed cache
- There is no ongoing compression during token-by-token generation (unless using DecodingPress)

### Safe to use with:
- `output_scores=True` — hooks operate on KV cache, not logits
- `return_dict_in_generate=True` — no interference
- `do_sample=False` (greedy) or `do_sample=True` (sampling)
- `StoppingCriteria` — works normally

## Supported Models

```python
SUPPORTED_MODELS = (
    LlamaForCausalLM,       # Llama 2, 3, 3.1, 3.2
    MistralForCausalLM,     # Mistral 7B, etc.
    Phi3ForCausalLM,        # Phi-3
    Qwen2ForCausalLM,       # Qwen2, Qwen2.5
    Qwen3ForCausalLM,       # Qwen3
    Gemma3ForConditionalGeneration,  # Gemma 3
)
```

The check is a **warning**, not a hard block. Models with `model.model.layers[].self_attn` structure may work even if not listed.

## Class Hierarchy

```
BasePress (dataclass, context manager)
├── ScorerPress (score-based pruning, has compression_ratio)
│   ├── StreamingLLMPress    — position-based: keep sinks + recent
│   ├── SnapKVPress          — attention of recent tokens
│   ├── KnormPress           — key vector L2 norms
│   ├── ExpectedAttentionPress — predicted future attention
│   ├── TOVAPress            — last-token attention weight
│   ├── ObservedAttentionPress — full prefill attention (needs eager)
│   ├── RandomPress          — random baseline
│   ├── KeyDiffPress         — key distinctiveness
│   ├── LagKVPress           — lag-relative information
│   ├── CURPress             — leverage scores
│   ├── KVzapPress           — learned surrogate (needs HF weights)
│   ├── QFilterPress         — learned filters (needs HF weights)
│   ├── LeverageScorePress   — statistical leverage via Cholesky
│   ├── NonCausalAttnPress   — non-causal chunked attention
│   ├── CompactorPress       — blends leverage + non-causal attn
│   ├── PyramidKVPress       — extends SnapKV
│   └── CriticalKVPress      — two-stage with value norms
├── ThinKPress               — dimension compression (channels, not sequence)
├── SimLayerKVPress          — layer-adaptive (lazy layer detection)
├── DuoAttentionPress        — head-adaptive (retrieval vs streaming)
├── FinchPress               — prompt-guided, delimiter-based
├── KVzipPress               — context reconstruction (2-3x overhead)
├── FastKVzipPress           — learned gates
└── Wrappers:
    ├── ComposedPress        — chains multiple presses
    ├── AdaKVPress           — head-wise adaptive (wraps ScorerPress)
    ├── ChunkPress           — chunk-wise uniform compression
    ├── ChunkKVPress         — semantic chunk selection
    ├── BlockPress           — block-wise iterative
    ├── PerLayerCompressionPress — per-layer ratios
    ├── KeyRerotationPress   — RoPE fix after pruning
    ├── DecodingPress        — compression during decoding (experimental)
    ├── PrefillDecodingPress — separate prefill + decoding strategies
    └── DMSPress             — threshold-based adaptive

For detailed per-press documentation (parameters, papers, requirements), read:
`references/press-catalog.md`

## Quick Reference: Choosing a Press

### No special setup needed (just compression_ratio):
| Press | Strategy | Attention needed? | Best for |
|---|---|---|---|
| StreamingLLMPress | Keep sinks + recent tokens | No | Simple baseline, predictable behavior |
| SnapKVPress | Recent tokens' attention patterns | No (computes own) | Good general-purpose quality |
| KnormPress | Key vector norms | No | Fast, no attention compute |
| ExpectedAttentionPress | Predicted future attention | No | Best quality (NVIDIA's method) |
| TOVAPress | Last token's attention | Optional | Lightweight attention-based |
| RandomPress | Random eviction | No | Degradation baseline |
| KeyDiffPress | Key distinctiveness | No | Unique key preservation |

### Needs `attn_implementation="eager"`:
| Press | Why |
|---|---|
| ObservedAttentionPress | Uses full prefill attention matrix |

### Needs pre-trained weights from HF Hub:
| Press | Weights from |
|---|---|
| QFilterPress | `nthngdy/` (not all models) |
| KVzapPress | `nvidia/KVzap-{type}-{model}` |
| FastKVzipPress | Per-model on HF Hub |
| ExpectedAttentionStatsPress | Pre-computed query stats |

### Special context managers (incompatible with ComposedPress):
| Press | Why |
|---|---|
| KVzipPress | Multi-pass, 2-3x overhead |
| FastKVzipPress | Own `__call__` implementation |
| AdaKVPress | Uses attention_patch mechanism |

## Common Patterns

### Basic usage
```python
from kvpress import SnapKVPress

press = SnapKVPress(compression_ratio=0.5)
with torch.no_grad(), press(model):
    out = model.generate(**inputs, max_new_tokens=512)
```

### Baseline (no compression) — use nullcontext
```python
from contextlib import nullcontext

ctx = press(model) if press is not None else nullcontext()
with torch.no_grad(), ctx:
    out = model.generate(**inputs, max_new_tokens=512)
```

### Composing presses
```python
from kvpress import ComposedPress, SnapKVPress, ThinKPress

press = ComposedPress([
    SnapKVPress(compression_ratio=0.3),
    ThinKPress(key_channel_compression_ratio=0.2),
])
# Effective keep ratio = (1-0.3) * (1-0.2) = 0.56
```

### Head-wise adaptive compression
```python
from kvpress import AdaKVPress, SnapKVPress

press = AdaKVPress(
    press=SnapKVPress(compression_ratio=0.5),
    alpha_safeguard=0.20,  # min 20% kept per head
)
# Note: does NOT reduce peak memory (uses fake keys)
# Note: requires NOT attn_implementation="eager"
```

### StreamingLLM matching the original paper
```python
from kvpress import StreamingLLMPress, KeyRerotationPress

press = KeyRerotationPress(
    press=StreamingLLMPress(compression_ratio=0.8)
)
```

### Per-layer compression ratios
```python
from kvpress import PerLayerCompressionPress, SnapKVPress

ratios = [0.2] * 8 + [0.5] * 16 + [0.8] * 8  # 32 layers
press = PerLayerCompressionPress(
    press=SnapKVPress(compression_ratio=0.0),  # ratio overridden
    compression_ratios=ratios,
)
```

### Dynamic factory for multiple press types
```python
from kvpress import (
    ExpectedAttentionPress,
    KnormPress,
    SnapKVPress,
    StreamingLLMPress,
    TOVAPress,
)

PRESS_REGISTRY: dict[str, type] = {
    "streaming_llm": StreamingLLMPress,
    "snapkv": SnapKVPress,
    "knorm": KnormPress,
    "expected_attention": ExpectedAttentionPress,
    "tova": TOVAPress,
}

def get_press(name: str, compression_ratio: float):
    if name == "none":
        return None
    cls = PRESS_REGISTRY[name]
    return cls(compression_ratio=compression_ratio)
```

## Gotchas

1. **compression_ratio is fraction to REMOVE**. `0.9` keeps only 10%. This is counterintuitive — double-check any code that sets this value.

2. **Prefill-only by default**. The cache is compressed once during prefill. Tokens generated afterward all see the same compressed cache. If you need ongoing compression during generation, use `DecodingPress` (experimental).

3. **ObservedAttentionPress needs eager attention**. Load the model with `attn_implementation="eager"` or it will assert-fail. This is significantly slower than flash/sdpa attention.

4. **AdaKVPress does NOT save memory**. It uses "fake keys" (where `exp(<q,k>) ≈ 0`) instead of actually removing entries. The cache stays the same size. It improves quality but not memory.

5. **ComposedPress limitations**. Cannot contain AdaKVPress or KVzipPress. Presses that depend on attention weights may break if a prior press changes keys/values.

6. **Model architecture requirement**. The model must expose `model.model.layers[].self_attn`. This is standard for Llama/Mistral/Qwen/Phi3 but not universal.

7. **Hooks persist until context exit**. If an exception occurs inside `with press(model):`, hooks are still cleaned up (finally block). But if you create hooks manually without the context manager, you must remove them yourself.

8. **Quantized caches work**. kvpress handles `QuantizedCache` transparently — dequantizes before scoring, re-quantizes after compression.

9. **Batch size**. All presses support `batch_size >= 1`. Score tensors are shaped `(batch, num_kv_heads, seq_len)`.

10. **Multi-GPU**. Supported via `accelerate` device_map. Hooks register on actual model layers regardless of device placement.

## Score-Based vs Non-Score-Based

**ScorerPress subclasses** implement `score(module, hidden_states, keys, values, attentions, kwargs)` returning `(batch, num_kv_heads, seq_len)`. Higher score = more important = kept. Bottom-k scored tokens are pruned via `topk`.

Categories of scoring:
- **Position-based**: StreamingLLMPress (sinks + recent)
- **Key geometry**: KnormPress, KeyDiffPress, LeverageScorePress, CURPress
- **Attention-based**: SnapKVPress, TOVAPress, ObservedAttentionPress, NonCausalAttnPress
- **Statistical modeling**: ExpectedAttentionPress
- **Learned**: QFilterPress, KVzapPress
- **Random**: RandomPress

**Non-score presses** use fundamentally different mechanisms: dimension pruning (ThinKPress), layer selection (SimLayerKVPress), head classification (DuoAttentionPress), multi-pass reconstruction (KVzipPress), or learned gates (FastKVzipPress).
