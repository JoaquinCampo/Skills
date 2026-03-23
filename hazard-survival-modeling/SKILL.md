---
name: hazard-survival-modeling
description: >
  Use when implementing labeling.py, features.py, train.py, or code involving
  hazard/survival modeling, person-period data expansion, horizon labels,
  catastrophe prediction, XGBoost survival (survival:cox, survival:aft,
  binary:logistic), discrete-time survival, censoring, competing risks,
  C-index, Brier score, scale_pos_weight, or GroupKFold for sequences.
allowed-tools: Read, Grep, Glob, Agent
---

# Hazard & Survival Modeling for Sequential Token Prediction

Reference skill for implementing survival analysis and hazard
modeling in the HERALD project. Covers theory, discrete-time
models, XGBoost integration, horizon-based labeling, evaluation
metrics, and practical implementation patterns for predicting
catastrophic failures in KV-cache compressed LLM generation.

---

## 1. Survival Analysis Fundamentals

### Core Functions

**Survival function** S(t) -- probability of surviving beyond t:

```
S(t) = Pr{T >= t} = 1 - F(t)
```

**Hazard function** h(t) -- instantaneous event rate at t, given
survival to t:

```
h(t) = lim_{dt->0} Pr{t <= T < t+dt | T >= t} / dt = f(t) / S(t)
```

**Cumulative hazard** H(t):

```
H(t) = integral_0^t h(u) du
```

**Key relationship** -- survival from cumulative hazard:

```
S(t) = exp{-H(t)}
```

In words: the probability of surviving to t equals the exponent
of the negative cumulative hazard up to t.

### Discrete-Time Formulation (Token Sequences)

For HERALD, time is inherently discrete: each token position is
a time step. The discrete hazard at step j is a *conditional
probability* (not a rate):

```
lambda_j = Pr{T = t_j | T >= t_j}
```

The discrete survival function is the product of complements:

```
S(t_j) = product_{k=1}^{j-1} (1 - lambda_k)
```

This says: to survive to step j, the model must avoid
catastrophe at every prior step.

### Censoring in HERALD Context

- **Right-censoring**: generation ends normally (EOS) before
  catastrophe -- we know no catastrophe occurred up to that
  token, but cannot observe what would happen beyond it.
- **Administrative censoring**: generation hits max_tokens with
  no catastrophe detected -- the sequence was cut short.
- **No left-censoring**: we always observe from token 0.
- **Interval censoring**: not applicable -- we observe every
  token position.

### Competing Risks (Multiple Failure Modes)

HERALD detects multiple catastrophe types: looping,
non_termination, coherence_collapse. These are competing risks:

- **Cause-specific hazard**: h_k(t) = instantaneous rate of
  failure type k at t, given no failure of any type before t.
- **Sub-distribution hazard** (Fine-Gray): models the
  cumulative incidence of each cause accounting for competition.

For HERALD's binary "any catastrophe" framing, competing risks
collapse to a single hazard. For per-type prediction, train
separate models per catastrophe type or use multi-label
discrete-time classification.

Implementation options for competing risks:
1. **Separate binary classifiers**: One XGBoost per failure type
   (simplest, allows different feature importance per type).
2. **Multi-class person-period**: Target is
   {0: no_event, 1: looping, 2: non_termination, 3: amnesia}.
   Use `objective='multi:softprob'` in XGBoost.
3. **DeepHit-style** (Lee et al., AAAI 2018): joint distribution
   over (time, event type) -- overkill for HERALD.

---

## Gotchas

1. **The low-perplexity trap.** Degenerated/repetitive text
   has paradoxically LOW perplexity because repetitive patterns
   are highly predictable. Do NOT use low entropy or high
   top1_prob as evidence of "healthy" generation. Monitor
   entropy *dynamics* (delta_h, rolling_std) not absolutes.

2. **Never split person-period rows randomly.** All tokens from
   a sequence MUST stay in the same fold. Use `GroupKFold` on
   `run_id`. Random splitting leaks future tokens of a sequence
   into training, inflating metrics dramatically.

3. **sksurv cannot handle time-varying covariates.** HERALD's
   token-level features change every step. scikit-survival's
   `GradientBoostingSurvivalAnalysis` takes one feature vector
   per sequence — it cannot use per-token signals. Use the
   person-period binary classification approach instead.

4. **scale_pos_weight is critical.** Person-period expansion
   creates extreme class imbalance (event=1 at only 1 of
   hundreds of token rows per sequence). Without
   `scale_pos_weight = n_neg / n_pos`, XGBoost will predict
   ~0 everywhere and appear to have good logloss.

5. **Compression ratio is a label proxy, not a feature.** If
   you include compression_ratio as an XGBoost feature, the
   model may shortcut to "high compression = catastrophe"
   rather than learning logit signal patterns. Consider
   training per-compression-ratio models or stratifying.

6. **Repetition onset is gradual, not abrupt.** Repetition
   neurons activate progressively over tens of tokens before
   full loop lock-in (Hiraoka & Inui, NAACL 2025). This means
   horizon-based prediction IS feasible for looping — the
   warning window exists.

---

## 2. Discrete-Time Survival Models

### The Binary Classification Equivalence (The Core Trick)

The discrete-time hazard model has a binomial likelihood that is
*identical* to binary classification on person-period (long
format) data. This is the key insight enabling XGBoost usage:

> Any binary classifier trained on expanded person-period data
> is implicitly estimating discrete-time hazard probabilities.

**Advantages over continuous-time models:**
- Handles ties in event times naturally (common in token data)
- No proportional hazards assumption required
- Any binary classifier (XGBoost, NN, SVM) can be used directly
- Flexible non-linear hazard functions (not limited to monotonic)
- Time-varying covariates handled naturally (features change per
  token)

**Reference**: Spooner et al. (2022), "Survival prediction
models: introduction to discrete-time modeling." BMC Med Res
Methodol. Also: Berger et al. (2022), PMC9316420.

### Person-Period Data Expansion

Original format (one row per sequence):

```
run_id | event_time | event_occurred | features...
seq_0  | 145        | 1 (looping)    | ...
seq_1  | 512        | 0 (censored)   | ...
```

Expanded person-period format (one row per token per sequence):

```
run_id | token_pos | event_this_step | features_at_t...
seq_0  | 0         | 0               | entropy=2.1, ...
seq_0  | 1         | 0               | entropy=2.3, ...
...
seq_0  | 145       | 1               | entropy=8.7, ...
seq_1  | 0         | 0               | entropy=1.8, ...
...
seq_1  | 511       | 0               | entropy=2.0, ...
```

Rules for expansion:
- Each sequence contributes rows for tokens 0..T_i
- Event indicator = 1 ONLY at the catastrophe onset token
- Censored sequences have event = 0 for ALL their rows
- After the event row, no more rows for that sequence
- Time-varying covariates (token signals) are naturally included

### Python Implementation Pattern

```python
import pandas as pd
import numpy as np


def expand_to_person_period(
    run_results: list[dict],
    horizon: int | None = None,
) -> pd.DataFrame:
    """Expand run results to person-period (long) format.

    Each row = one (sequence, token_position) observation.
    Event indicator = 1 only at the catastrophe onset token.

    Args:
        run_results: list of RunResult dicts with 'signals',
            'catastrophe_onsets', 'num_tokens_generated', etc.
        horizon: if set, only include tokens up to this position
            (administrative censoring at horizon).
    """
    rows = []
    for run in run_results:
        # Find earliest catastrophe onset (any type)
        onsets = run.get("catastrophe_onsets", {})
        event_time = min(onsets.values()) if onsets else None
        n_tokens = run["num_tokens_generated"]

        max_t = n_tokens
        if horizon is not None:
            max_t = min(max_t, horizon)
        if event_time is not None and event_time < max_t:
            max_t = event_time + 1  # include event token

        for t in range(max_t):
            signals = run["signals"][t]
            row = {
                "run_id": run["prompt_id"],
                "token_pos": t,
                "event": 1 if (event_time is not None
                               and t == event_time) else 0,
                # Token-level features from signals
                "entropy": signals["entropy"],
                "top1_prob": signals["top1_prob"],
                "top5_prob": signals["top5_prob"],
                "h_alts": signals["h_alts"],
                "avg_logp": signals["avg_logp"],
                "delta_h": signals.get("delta_h"),
                "kl_div": signals.get("kl_div"),
                "top10_jaccard": signals.get("top10_jaccard"),
                "eff_vocab_size": signals["eff_vocab_size"],
                "tail_mass": signals["tail_mass"],
                "logit_range": signals["logit_range"],
                # Context features
                "compression_ratio": run["compression_ratio"],
                "press": run["press"],
            }
            rows.append(row)

    return pd.DataFrame(rows)
```

### Link Functions

Two standard choices for the discrete-time hazard model:

**Logit link** (logistic regression / XGBoost default):

```
logit(lambda_j) = alpha_j + beta * X
log(lambda_j / (1 - lambda_j)) = alpha_j + beta * X
```

- Interprets coefficients as log-odds ratios
- Best when time is truly discrete (tokens ARE discrete)
- Natural for XGBoost with `binary:logistic` objective

**Complementary log-log link**:

```
log(-log(1 - lambda_j)) = alpha_j + beta * X
```

- Discrete-time analog of continuous proportional hazards (Cox)
- Coefficients have proportional hazards interpretation
- More appropriate when discretizing continuous time

**For HERALD: use logit link.** Token positions are inherently
discrete, and XGBoost's `binary:logistic` objective directly
optimizes the logit-linked hazard model.

---

## 3. XGBoost for Survival Analysis

Three approaches compared: native `survival:cox`, native
`survival:aft`, and binary classification on person-period data.
**HERALD uses Approach C (binary:logistic on person-period).**

See `references/xgboost-approaches.md` for full code examples,
hyperparameter table, survival curve computation, sksurv
comparison, and the detailed comparison table.

---

## 4. Horizon-Based Labeling for HERALD

### The H-Token-Ahead Prediction Problem

HERALD's goal: at token position t, predict whether a
catastrophe will occur within the next H tokens.

```
label(t, H) = 1 if catastrophe onset in [t+1, t+H], else 0
```

This is a **sliding window binary label** -- a practical
simplification of survival analysis for real-time prediction.

### Labeling Strategies

#### Strategy A: Exact Hazard (Person-Period)

Train on person-period data where event=1 only at the exact
onset token. The model learns the instantaneous hazard. Then
compute P(event within H) from survival:

```python
# P(catastrophe within next H tokens | survived to t)
# = 1 - product_{k=t+1}^{t+H} (1 - lambda_hat(k))
def prob_within_horizon(hazard_preds, t, H):
    window = hazard_preds[t+1 : t+1+H]
    return 1.0 - np.prod(1.0 - window)
```

#### Strategy B: Direct Horizon Label (Simpler, Recommended)

Label each token position directly with the horizon binary:

```python
def create_horizon_labels(
    signals: list[dict],
    catastrophe_onset: int | None,
    horizon: int,
) -> np.ndarray:
    """Create binary labels: will catastrophe occur within
    next H tokens?

    Args:
        signals: per-token signal dicts
        catastrophe_onset: token index of catastrophe start,
            or None if no catastrophe
        horizon: lookahead window in tokens

    Returns:
        labels: array of 0/1 for each token position
    """
    n = len(signals)
    labels = np.zeros(n, dtype=np.int32)

    if catastrophe_onset is not None:
        # Tokens within H steps before onset get label 1
        start = max(0, catastrophe_onset - horizon)
        end = catastrophe_onset  # onset itself is the event
        labels[start:end] = 1
        # The onset token and after also get 1
        labels[catastrophe_onset:] = 1

    return labels
```

This directly trains XGBoost to answer: "given features at
token t, will catastrophe happen within H tokens?"

#### Strategy C: Multi-Horizon Prediction

Train separate models (or a single model with horizon as a
feature) for multiple horizons:

```python
HORIZONS = [1, 5, 10, 25, 50]

for H in HORIZONS:
    labels = create_horizon_labels(signals, onset, horizon=H)
    # Train model_H or add H as feature column
```

This lets the system choose the intervention threshold: early
warning (H=50) vs precise alarm (H=1).

### Dynamic Prediction / Landmarking

Landmarking adapts survival models to sequential data by
defining "landmark times" at which predictions are made:

- At each token position t (the landmark), build features from
  tokens [0..t] and predict future catastrophe
- The prediction is conditional on surviving to t
- Different from static prediction: features accumulate over time

For HERALD, every token position IS a landmark. The model
naturally does dynamic prediction because token-level features
capture the evolving state of generation.

### Temporal Label Smoothing

Near catastrophe boundaries, labels are noisy (is the model
about to fail at token 99 or 101?). Temporal label smoothing
modulates confidence based on proximity to events:

```python
def smooth_labels(
    labels: np.ndarray,
    catastrophe_onset: int | None,
    sigma: float = 5.0,
) -> np.ndarray:
    """Apply Gaussian-weighted label smoothing near onset."""
    if catastrophe_onset is None:
        return labels.astype(float)

    smooth = labels.astype(float)
    for t in range(len(labels)):
        if labels[t] == 0:
            dist = catastrophe_onset - t
            if 0 < dist <= 3 * sigma:
                smooth[t] = np.exp(-0.5 * (dist / sigma) ** 2)
    return smooth
```

Reference: Yeche et al. (2023), "Temporal Label Smoothing for
Early Event Prediction." ICML.

---

## 5. Evaluation Metrics

See `references/evaluation-metrics.md` for full code examples
(C-index, time-dependent AUC, Brier/IBS, binary classification
metrics, calibration curves).

**Quick reference — recommended suite for HERALD:**

| Metric | Purpose | When |
|--------|---------|------|
| AUROC | Discrimination | Always |
| AUPRC | Imbalanced discrimination | Always |
| Brier Score | Calibration | When probs matter |
| C-index | Sequence ranking | Survival baselines |
| F1 @ threshold | Operational | Deployment |
| Precision @ 90% recall | False alarm rate | Deployment |

---

## 6. Practical Implementation Patterns

### Feature Engineering for Token-Level Survival

HERALD's `TokenSignals` provides per-token features. For the
hazard model, augment with rolling statistics:

```python
WINDOW_SIZES = [5, 10, 25]
BASE_FEATURES = [
    "entropy", "top1_prob", "top5_prob", "h_alts",
    "avg_logp", "delta_h", "kl_div", "top10_jaccard",
    "eff_vocab_size", "tail_mass", "logit_range",
]

def engineer_features(
    signals_df: pd.DataFrame,
    windows: list[int] = WINDOW_SIZES,
) -> pd.DataFrame:
    """Add rolling statistics to token-level signals.

    Computed per-sequence (grouped by run_id).
    """
    df = signals_df.copy()

    for feat in BASE_FEATURES:
        for w in windows:
            grp = df.groupby("run_id")[feat]
            df[f"{feat}_mean_{w}"] = grp.transform(
                lambda x: x.rolling(w, min_periods=1).mean()
            )
            df[f"{feat}_std_{w}"] = grp.transform(
                lambda x: x.rolling(w, min_periods=1).std()
            )
            df[f"{feat}_max_{w}"] = grp.transform(
                lambda x: x.rolling(w, min_periods=1).max()
            )
            df[f"{feat}_min_{w}"] = grp.transform(
                lambda x: x.rolling(w, min_periods=1).min()
            )

    # Position features
    df["token_pos_frac"] = (
        df["token_pos"]
        / df.groupby("run_id")["token_pos"].transform("max")
    )

    # Rate-of-change features
    for feat in ["entropy", "kl_div", "top1_prob"]:
        grp = df.groupby("run_id")[feat]
        df[f"{feat}_diff1"] = grp.diff(1)
        df[f"{feat}_diff5"] = grp.diff(5)

    return df
```

### Handling Class Imbalance

Catastrophes are rare in early tokens, creating severe
imbalance in person-period data:

1. **scale_pos_weight**: Set to n_negative / n_positive in
   XGBoost params. Simple and effective.

2. **Subsampling negatives**: Keep all positive rows, randomly
   sample negative rows at a fixed ratio (e.g., 10:1).

3. **Focal loss**: Custom XGBoost objective that down-weights
   easy negatives. Useful when `scale_pos_weight` alone gives
   too many false positives.

```python
# Simple negative subsampling
def subsample_negatives(
    df: pd.DataFrame,
    neg_ratio: float = 10.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Keep all positive rows, subsample negatives."""
    pos = df[df["event"] == 1]
    neg = df[df["event"] == 0]
    n_keep = int(len(pos) * neg_ratio)
    neg_sample = neg.sample(
        n=min(n_keep, len(neg)), random_state=seed
    )
    return pd.concat([pos, neg_sample]).sort_index()
```

### Cross-Validation for Survival Data

**Critical**: do NOT split person-period rows randomly. Split
by *sequence* (run_id) to prevent data leakage.

```python
from sklearn.model_selection import GroupKFold

def survival_cv_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate CV splits grouped by sequence.

    Ensures all tokens from a sequence are in the same fold.
    """
    gkf = GroupKFold(n_splits=n_splits)
    groups = df["run_id"].values
    splits = []
    for train_idx, val_idx in gkf.split(df, groups=groups):
        splits.append((train_idx, val_idx))
    return splits
```

For temporal awareness (important if compression ratios or
model versions change over time), use time-ordered splits where
training set precedes validation set in experiment order.

### End-to-End Training Pipeline

```python
import json
import xgboost as xgb
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
)


def train_hazard_predictor(
    results_dir: Path,
    horizon: int = 10,
    output_dir: Path = Path("models"),
) -> dict:
    """Train XGBoost hazard predictor from sweep results.

    Returns dict of evaluation metrics.
    """
    # 1. Load results
    results = []
    for f in sorted(results_dir.glob("*.json")):
        with open(f) as fh:
            results.extend(json.load(fh))

    # 2. Expand to person-period format
    pp_df = expand_to_person_period(results)

    # 3. Engineer features
    pp_df = engineer_features(pp_df)

    # 4. Create horizon labels
    for run_id, group in pp_df.groupby("run_id"):
        run = next(r for r in results
                   if r["prompt_id"] == run_id)
        onsets = run.get("catastrophe_onsets", {})
        onset = min(onsets.values()) if onsets else None
        labels = create_horizon_labels(
            group.to_dict("records"), onset, horizon
        )
        pp_df.loc[group.index, "label"] = labels

    # 5. Split by sequence
    splits = survival_cv_splits(pp_df, n_splits=5)
    train_idx, val_idx = splits[0]

    feature_cols = [c for c in pp_df.columns
                    if c not in {"run_id", "token_pos",
                                 "event", "label", "press"}]
    X_train = pp_df.iloc[train_idx][feature_cols]
    y_train = pp_df.iloc[train_idx]["label"]
    X_val = pp_df.iloc[val_idx][feature_cols]
    y_val = pp_df.iloc[val_idx]["label"]

    # 6. Train XGBoost
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    params = {
        "objective": "binary:logistic",
        "eval_metric": ["logloss", "aucpr"],
        "tree_method": "hist",
        "learning_rate": 0.05,
        "max_depth": 6,
        "min_child_weight": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": float(n_neg / max(n_pos, 1)),
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "seed": 42,
    }
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=1000,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=50,
        verbose_eval=100,
    )

    # 7. Evaluate
    y_pred = model.predict(dval)
    metrics = {
        "horizon": horizon,
        "auroc": roc_auc_score(y_val, y_pred),
        "auprc": average_precision_score(y_val, y_pred),
        "n_train": len(y_train),
        "n_val": len(y_val),
        "event_rate_train": float(n_pos / len(y_train)),
        "best_iteration": model.best_iteration,
    }

    # 8. Save
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(
        str(output_dir / f"hazard_H{horizon}.json")
    )

    return metrics
```

---

## 7. HERALD-Specific Design Decisions

### Why Binary Classification over Native Survival

| Criterion | Binary (person-period) | survival:cox | survival:aft |
|-----------|----------------------|--------------|--------------|
| Time-varying features | Native | No | No |
| Calibrated probabilities | Yes | No (risk only) | Dist-dependent |
| Proportional hazards | Not assumed | Required | Not assumed |
| Non-linear hazard | Flexible | Baseline only | Parametric |
| Standard eval tools | sklearn | sksurv only | sksurv only |
| Implementation complexity | Low | Medium | Medium |

### Token Signals -> Survival Features Mapping

HERALD `TokenSignals` fields map directly to survival features:

| Signal | Survival Role | Pre-Catastrophe Behavior |
|--------|--------------|--------------------------|
| entropy | Instantaneous risk indicator | Spikes before looping; regime change at hallucination onset |
| top1_prob | Confidence proxy | Drops before failure; paradoxically HIGH during degeneration (low perplexity trap) |
| kl_div | Distributional shift | Spikes at regime change between normal and degenerate generation |
| top10_jaccard | Vocabulary stability | Drops near looping onset as model locks into token subset |
| delta_h | Entropy acceleration | Sustained positive = danger; negative = recovery |
| tail_mass | Distribution diffuseness | Increases before coherence collapse |
| logit_range | Pre-softmax confidence | Narrows before failure |
| eff_vocab_size | Effective token diversity | Collapses as model enters repetition attractor |
| h_alts | Alternative-token entropy | Drops when model becomes over-committed to single path |

### Critical Signal Interpretation Pitfalls

**The low-perplexity trap**: Degenerated/repetitive text has
paradoxically LOW standalone perplexity because repetitive
patterns are highly predictable. Do NOT use low entropy or
high top1_prob as evidence of "healthy" generation. Monitor
entropy *dynamics* (delta_h, rolling_std) rather than absolute
levels.

**Repetition neuron progressive activation**: Research shows
specific neurons progressively activate *before* full loop
engagement (Hiraoka & Inui, NAACL 2025). This means the
warning window for repetition is gradual (tens of tokens),
not abrupt -- making horizon-based prediction feasible.

**Autocorrelation as leading indicator**: FFT-based
autocorrelation in token ID sequences (SpecRA approach)
reveals periodicity robustly, even with minor variations
(number increments, spelling changes). After one repetition
period P, looping is detectable ~P tokens before full lock-in.

### Recommended Horizons for HERALD

- **H=1**: Next-token hazard (raw signal, good for analysis)
- **H=5**: Very short-term (tactical intervention)
- **H=10**: Short-term (default, ~2-3 sentence lookahead)
- **H=25**: Medium-term (paragraph-level early warning)
- **H=50**: Long-term (strategic planning, highest recall)

### Compression Context

The 90% compression ratio is a critical threshold where all
architectures exhibit a sharp catastrophe "safety cliff"
(Ananthanarayanan et al., arXiv:2603.01426). Two distinct
failure mechanisms at this cliff:
1. **Token erasure**: answer-critical tokens are globally
   evicted from the KV cache
2. **Representational rigidity**: tokens survive but routing
   flexibility collapses

For GSM8K specifically, performance deteriorates significantly
below 20% cache budget. Low budgets paradoxically produce
LONGER reasoning traces (non-termination risk).

### Intervention When Hazard Exceeds Threshold

When predicted h(t) > threshold, viable interventions:

1. **Dynamic temperature** (EDT/AdapT): increase temperature
   at high-entropy tokens to allow exploration away from
   degenerate mode.
2. **Rollback-resample** (CARE framework): discard last K
   tokens, regenerate with different sampling parameters.
3. **Decoding strategy switch**: move from greedy to nucleus
   sampling; add contrastive search degeneration penalty.
4. **Reduce compression**: allocate more KV cache if resources
   permit (trade memory for quality).
5. **Early termination**: if failure is imminent and
   irrecoverable, stop generation and report.

Threshold tuning: use precision-recall curves at each horizon
to find the operating point that balances false alarm rate vs
detection sensitivity for the intended deployment.

---

## 8. References

See `references/papers-and-software.md` for the complete list
of papers (survival modeling, LLM failure detection, KV-cache
compression) and software documentation links (scikit-survival,
XGBoost, XGBSE, Rodriguez GLM notes).
