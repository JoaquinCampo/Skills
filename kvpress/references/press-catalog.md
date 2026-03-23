# kvpress Press Catalog

Detailed documentation for every press class in kvpress. Organized by category.

Read this file when you need specific parameter details, paper references, or implementation notes for a particular press.

## Table of Contents

1. [Score-Based Presses (ScorerPress subclasses)](#score-based-presses)
2. [Non-Score-Based Presses](#non-score-based-presses)
3. [Wrapper Presses](#wrapper-presses)
4. [Experimental / Decoding-Time Presses](#experimental-presses)

---

## Score-Based Presses

All inherit from `ScorerPress` which inherits from `BasePress`. They implement `score()` returning `(batch, num_kv_heads, seq_len)` — higher = more important = kept.

### RandomPress
- **Paper**: Baseline (no paper)
- **Import**: `from kvpress import RandomPress`
- **Parameters**: `compression_ratio: float`, `seed: int | None = None`
- **Scoring**: Uniform random scores
- **Attention needed**: No
- **Use case**: Degradation baseline to measure how much a real method helps vs random eviction

### KnormPress
- **Paper**: https://arxiv.org/abs/2406.11430
- **Import**: `from kvpress import KnormPress`
- **Parameters**: `compression_ratio: float`
- **Scoring**: `-keys.norm(dim=-1)` — keys with smaller L2 norms score higher (are more important)
- **Attention needed**: No
- **Insight**: Outlier keys with large norms tend to be less semantically important. This is counterintuitive but empirically validated.

### SnapKVPress
- **Paper**: https://arxiv.org/abs/2404.14469
- **Import**: `from kvpress import SnapKVPress`
- **Parameters**: `compression_ratio: float`, `window_size: int = 64`, `kernel_size: int = 5`
- **Scoring**: Attention patterns from the last `window_size` tokens, smoothed with a pooling kernel
- **Attention needed**: Computes its own window attention internally (does NOT require `attn_implementation="eager"`)
- **Insight**: What recent tokens attend to is a good proxy for what future tokens will attend to
- **Subclass**: `PyramidKVPress` extends this with per-layer budget allocation

### ExpectedAttentionPress
- **Paper**: https://arxiv.org/abs/2510.00636v1 (the kvpress paper itself)
- **Import**: `from kvpress import ExpectedAttentionPress`
- **Parameters**: `compression_ratio: float`, `n_future_positions: int = 512`, `n_sink: int = 4`, `use_covariance: bool = True`, `use_vnorm: bool = True`, `epsilon: float = 0.0`
- **Scoring**: Statistical model of expected future attention using query mean/covariance + RoPE rotation, optionally rescaled by value norms
- **Attention needed**: No (uses query statistics from current context)
- **Insight**: Best quality among simple presses. Predicts what future queries will attend to rather than using past attention as a proxy.

### ExpectedAttentionStatsPress
- **Paper**: Same as ExpectedAttentionPress
- **Import**: `from kvpress import ExpectedAttentionStatsPress`
- **Parameters**: Same as parent + `dataset_name: str = "kmfoda/booksum"`, `num_samples: int = 100`, `sample_seq_len: int = 1000`
- **Requires**: Pre-computed query statistics from HF Hub for the specific model
- **Note**: Uses pre-computed dataset statistics instead of context-dependent ones. Faster but less adaptive.

### StreamingLLMPress
- **Paper**: https://arxiv.org/abs/2309.17453
- **Import**: `from kvpress import StreamingLLMPress`
- **Parameters**: `compression_ratio: float`, `n_sink: int = 4`
- **Scoring**: Binary — score=1 for first `n_sink` tokens and last `n_recent` tokens, score=0 for everything in between
- **Attention needed**: No
- **Insight**: First few tokens are "attention sinks" that stabilize softmax. Recent tokens carry local context. Everything in the middle is discarded.
- **n_recent calculation**: `n_recent = seq_len * (1 - compression_ratio) - n_sink`
- **For paper match**: Wrap with `KeyRerotationPress` to fix RoPE positions after pruning

### TOVAPress
- **Paper**: https://arxiv.org/abs/2401.06104
- **Import**: `from kvpress import TOVAPress`
- **Parameters**: `compression_ratio: float`
- **Scoring**: Attention weight of the last token in the sequence, averaged across heads
- **Attention needed**: Uses `attentions` from forward pass if available, otherwise computes window attention with window=1
- **Insight**: The last token's attention pattern is a surprisingly good global importance indicator

### ObservedAttentionPress
- **Paper**: Related to H2O (https://arxiv.org/abs/2306.14048)
- **Import**: `from kvpress import ObservedAttentionPress`
- **Parameters**: `compression_ratio: float`
- **Scoring**: Average attention weight across ALL query positions from the prefill forward pass
- **Attention needed**: YES — **requires** `attn_implementation="eager"` on model load. Will assert-fail otherwise.
- **Performance**: Significantly slower than flash/sdpa attention due to materializing the full attention matrix
- **Insight**: Uses actual observed attention during prefilling, not a proxy or estimate

### QFilterPress
- **Paper**: https://arxiv.org/abs/2503.02812
- **Import**: `from kvpress import QFilterPress`
- **Parameters**: `compression_ratio: float`
- **Scoring**: Dot product between keys and learned filter vectors loaded from HF Hub
- **Requires**: Pre-trained Q-filter parameters from `nthngdy/` on HF Hub (not all models supported)

### KeyDiffPress
- **Paper**: https://arxiv.org/abs/2504.15364
- **Import**: `from kvpress import KeyDiffPress`
- **Parameters**: `compression_ratio: float`
- **Scoring**: Negative cosine similarity between each key vector and the average key pattern
- **Attention needed**: No
- **Insight**: Keeps tokens with distinctive key representations, prunes those similar to the average
- **Paper replication**: Use `BlockPress(press=KeyDiffPress(...), block_size=N)`

### LagKVPress
- **Paper**: https://arxiv.org/abs/2504.04704
- **Import**: `from kvpress import LagKVPress`
- **Parameters**: `compression_ratio: float`, `n_sink: int = 4`, `lag_size: int = 128`, `cross_scoring: bool = False`
- **Scoring**: Lag-relative information between sequence partitions (key + value based)
- **Attention needed**: No

### CURPress
- **Paper**: https://arxiv.org/abs/2509.15038
- **Import**: `from kvpress import CURPress`
- **Parameters**: `compression_ratio: float`, `num_sinks: int = 4`, `leverage_type: str = "kv_product"`, `use_random_leverage: bool = False`, `use_local_approximation: bool = True`, `local_window_size: int = 16`
- **Scoring**: Approximate leverage scores for keys (k²) and values (v²), combined as `k² * v²` by default
- **Attention needed**: No

### KVzapPress
- **Paper**: https://arxiv.org/abs/2601.07891
- **Import**: `from kvpress import KVzapPress`
- **Parameters**: `compression_ratio: float`, `model_type: str = "mlp"` (or `"linear"`)
- **Scoring**: Learned lightweight surrogate model (linear or MLP) applied to hidden states
- **Requires**: Pre-trained KVzap model from `nvidia/KVzap-{type}-{model_name}` on HF Hub
- **Designed for**: Pair with `DMSPress` for decoding-time compression

### LeverageScorePress
- **Paper**: https://arxiv.org/pdf/2507.08143v1 (Compactor)
- **Import**: `from kvpress import LeverageScorePress`
- **Parameters**: `compression_ratio: float`, `sketch_dimension: int = 48`
- **Scoring**: Approximate statistical leverage scores on pre-RoPE key embeddings via Gaussian sketch + Cholesky decomposition

### NonCausalAttnPress
- **Paper**: https://arxiv.org/pdf/2507.08143v1 (Compactor)
- **Import**: `from kvpress import NonCausalAttnPress`
- **Parameters**: `compression_ratio: float`, `chunk_size: int = 256`
- **Scoring**: Non-causal chunked attention column-sums, z-normalized

### CompactorPress
- **Paper**: https://arxiv.org/pdf/2507.08143v1
- **Import**: `from kvpress import CompactorPress`
- **Parameters**: `compression_ratio: float`, `sink_size_start: int = 8`, `sink_size_end: int = 4`, `chunk_size: int = 256`, `sketch_dimension: int = 48`, `blending: float | None = None`
- **Scoring**: Blends LeverageScorePress and NonCausalAttnPress scores
- **Note**: `blending` defaults to `compression_ratio` if None

### CriticalKVPress
- **Paper**: https://arxiv.org/abs/2502.03805
- **Import**: `from kvpress import CriticalKVPress`
- **Parameters**: `press: ScorerPress`, `epsilon: float = 1e-4`, `first_stage_ratio: float = 0.5`
- **Scoring**: Two-stage — first stage uses base scorer, second rescales by L1 norm of `W_o @ values`
- **Note**: This is also a wrapper — it takes another ScorerPress as input

---

## Non-Score-Based Presses

### ThinKPress
- **Paper**: https://arxiv.org/abs/2407.21018
- **Import**: `from kvpress import ThinKPress`
- **Parameters**: `key_channel_compression_ratio: float = 0.0`, `window_size: int = 32`
- **Type**: Dimension compression (zeroes out key channels, not sequence positions)
- **Note**: Does NOT reduce memory currently (same tensor shape, zeroed dims). Useful combined with sequence presses via `ComposedPress`.

### SimLayerKVPress
- **Paper**: https://arxiv.org/abs/2410.13846
- **Import**: `from kvpress import SimLayerKVPress`
- **Parameters**: `lazy_threshold: float = 1.0`, `n_last: int = 1`, `n_recent: int = 1024`, `n_initial: int = 4`
- **Type**: Layer-adaptive — identifies "lazy" layers where attention concentrates on initial+recent tokens, applies StreamingLLM-style compression only to those
- **Recommended thresholds**: Llama3=0.9, Llama2=0.65, Mistral=0.8, Qwen=0.85
- **Note**: `compression_ratio` is computed dynamically (read-only property)

### DuoAttentionPress
- **Paper**: https://arxiv.org/abs/2410.10819
- **Import**: `from kvpress import DuoAttentionPress`
- **Parameters**: `head_compression_ratio: float = 0.0`, `on_the_fly_scoring: bool = False`
- **Type**: Head-adaptive — splits heads into retrieval (full cache) and streaming (sink+recent only)
- **Note**: Uses pre-computed attention patterns for supported models

### FinchPress
- **Paper**: https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00716/125280
- **Import**: `from kvpress import FinchPress`
- **Parameters**: `compression_ratio: float`, `chunk_length: int | None = None`, `normalize_scores: bool = True`, `rerotate_keys: bool = True`
- **Type**: Prompt-guided — SnapKV-style but with dynamic window size based on delimiter token position
- **Requires**: Call `update_model_and_tokenizer()` on the press to set delimiter token before use

### KVzipPress
- **Paper**: https://arxiv.org/abs/2505.23416
- **Import**: `from kvpress import KVzipPress`
- **Parameters**: `compression_ratio: float`, `layerwise: bool = False`, `n_sink: int = 4`, `kvzip_plus_normalization: bool = False`
- **Type**: Context reconstruction via multiple forward passes
- **Warning**: 2-3x computational overhead compared to single prefill
- **Note**: Own `__call__` context manager — NOT compatible with ComposedPress

### FastKVzipPress
- **Paper**: https://arxiv.org/abs/2601.17668
- **Import**: `from kvpress import FastKVzipPress`
- **Type**: Learned gate architecture predicts token importance
- **Note**: Own `__call__` context manager. Loads pre-trained gates from HF Hub per model. Added in v0.5.1.

---

## Wrapper Presses

These wrap other presses to modify their behavior.

### ComposedPress
- **Import**: `from kvpress import ComposedPress`
- **Parameters**: `presses: list[BasePress]`
- **Mechanism**: Chains presses sequentially. Each operates on the output of the previous.
- **Effective keep ratio**: Product of `(1 - ratio)` across all presses
- **Limitations**: Cannot contain AdaKVPress or KVzipPress. May break if a press depends on features invalidated by a prior press.

### AdaKVPress
- **Paper**: https://arxiv.org/abs/2407.11550
- **Import**: `from kvpress import AdaKVPress`
- **Parameters**: `press: ScorerPress`, `alpha_safeguard: float = 0.20`
- **Mechanism**: Head-wise adaptive — prunes bottom scores across ALL heads jointly, with safeguard minimum per head
- **Important**: Uses attention_patch mechanism (fake keys where `exp(<q,k>) ≈ 0`) — does NOT reduce peak memory
- **Requires**: NOT `attn_implementation="eager"` (incompatible)

### ChunkPress
- **Paper**: FINCH
- **Import**: `from kvpress import ChunkPress`
- **Parameters**: `press: ScorerPress`, `chunk_length: int = 1024`
- **Mechanism**: Applies ScorerPress independently to fixed-size chunks for uniform compression

### ChunkKVPress
- **Paper**: https://arxiv.org/abs/2502.00299
- **Import**: `from kvpress import ChunkKVPress`
- **Parameters**: `press: ScorerPress`, `chunk_length: int = 20`
- **Mechanism**: Computes global importance scores, then selects proportionally from each chunk

### BlockPress
- **Paper**: https://arxiv.org/abs/2504.15364 (KeyDiff)
- **Import**: `from kvpress import BlockPress`
- **Parameters**: `press: ScorerPress`, `block_size: int = 128`
- **Mechanism**: Block-wise iterative compression — processes sequence in non-overlapping blocks

### PerLayerCompressionPress
- **Import**: `from kvpress import PerLayerCompressionPress`
- **Parameters**: `press: ScorerPress`, `compression_ratios: list[float]`
- **Mechanism**: Different compression ratio per transformer layer
- **Warning**: Experimental, only works with flash attention

### KeyRerotationPress
- **Import**: `from kvpress import KeyRerotationPress`
- **Parameters**: `press: ScorerPress`
- **Mechanism**: Re-applies RoPE positional encoding after compression so remaining tokens have correct positions
- **Use case**: Wrap StreamingLLMPress to match the original paper's implementation

### CriticalAdaKVPress
- **Import**: `from kvpress import CriticalAdaKVPress`
- **Mechanism**: CriticalKV + AdaKV combined

---

## Experimental Presses

### DecodingPress
- **Import**: `from kvpress import DecodingPress`
- **Parameters**: `base_press: ScorerPress | AdaKVPress`, `compression_interval: int = 512`, `target_size: int = 2048`, `hidden_states_buffer_size: int = 256`
- **Type**: Decoding-time compression — accumulates hidden states during generation, compresses every N steps
- **Note**: Added in v0.4.0. Experimental.

### PrefillDecodingPress
- **Import**: `from kvpress import PrefillDecodingPress`
- **Parameters**: `prefilling_press: BasePress | None`, `decoding_press: DecodingPress | None`
- **Mechanism**: Combines separate compression strategies for prefill and decoding phases

### DMSPress
- **Paper**: https://arxiv.org/abs/2506.05345
- **Import**: `from kvpress import DMSPress`
- **Parameters**: `press: ScorerPress`, `threshold: float | None`, `sliding_window_size: int = 128`, `decoding: bool = False`
- **Mechanism**: Threshold-based adaptive compression — evicts tokens with scores below threshold instead of using a fixed ratio
- **Note**: `compression_ratio` is dynamically computed (read-only). Works during both prefill and decoding.

---

## Version History

| Version | Date | Key additions |
|---------|------|---------------|
| 0.5.1 | Feb 2026 | FastKVzipPress |
| 0.5.0 | Jan 2026 | Transformers v5, KVzapPress, DMSPress |
| 0.4.0 | Dec 2025 | CURPress, CompactorPress, DecodingPress |
| 0.3.0 | Sep 2025 | Major release |
| 0.2.x | Jun-Aug 2025 | KVzipPress, FinchPress, BlockPress |
