# Deep Learning and Foundation Models for Time Series

## Neural Forecasting Architectures

| Model | Type | Key innovation | Best for |
|---|---|---|---|
| **N-BEATS** | MLP-based | Basis expansion, interpretable mode | Univariate, strong baseline |
| **N-HiTS** | MLP-based | Multi-rate signal sampling | Long horizons, hierarchical |
| **DeepAR** | Autoregressive RNN | Probabilistic, global model | Many related series |
| **TFT** | Transformer + attention | Multi-horizon, variable selection | Rich covariates + interpretability |
| **PatchTST** | Transformer | Patching (subsequence tokens) | Long-range dependencies |
| **iTransformer** | Inverted Transformer | Attention over variables, not time | Multivariate |
| **TSMixer** | MLP-Mixer | Channel + time mixing, no attention | Efficient multivariate |

## The Patching Revolution

PatchTST's key insight: treat subsequences as tokens (like words in NLP), not individual time points. This resolved the tokenization problem that plagued earlier time series transformers. Models after PatchTST (iTransformer, TSMixer, TimeXer) all build on this.

## The DLinear Debate (Resolved)

Zeng et al. (AAAI 2023) showed simple linear models beat most Transformers. The lesson:
- **Proper tokenization (patching + channel independence) makes transformers effective**
- The problem was architecture design, not attention itself
- **Always test simple baselines** — DLinear showed many published results had weak baselines

## Foundation Models (2024-2026)

| Model | Developer | Params | Key strength |
|---|---|---|---|
| **Chronos-2** | Amazon (Oct 2025) | 120M | Best covariate support, 300+ forecasts/sec, highest skill score on fev-bench (0.473) |
| **Moirai 2.0** | Salesforce | Various | #1 on GIFT-Eval, any-variate, quantile forecasting |
| **TimesFM** | Google | ~200M | Strong zero-shot, few-shot ICF matching supervised fine-tuning |
| **Sundial** | ICML 2025 Oral | Large | Flow-matching loss (no discrete tokenization), 1T time points, SOTA point + probabilistic |
| **Lag-Llama** | | | LLM architecture adapted for time series |
| **TimeGPT** | Nixtla | Undisclosed | First commercial TSFM, API-based |
| **Reverso** | Feb 2026 | 0.2M | Matches models 20-100x its size |
| **FlowState** | IBM | 9.1M | Top-10 GIFT-Eval at tiny size |

### Key findings:
- **Chronos-2** leads on fev-bench (skill score 0.473)
- **Moirai 2.0** leads on GIFT-Eval
- **Efficiency is the new frontier**: Reverso (0.2M params) competitive with 100x larger models
- **Few-shot in-context fine-tuning** (TimesFM-ICF, ICML 2025): matches supervised fine-tuning without gradient updates

### Data contamination warning:
TSFM-Bench found that some benchmark datasets were in pretraining data of TimesFM, UniTS, TTM — leading to **47-184% lower MSE** due to memorization. Many reported zero-shot results are overly optimistic. Always run your own evaluation.

## Where Foundation Models Excel

- Zero-shot scenarios (no task-specific training data)
- Cross-domain generalization
- Minimal preprocessing acceptable
- Covariate-informed tasks (Chronos-2 shows large gap here)

## Where Foundation Models Struggle

- **High-frequency data** (sub-minute): not enough pretraining data at these frequencies
- **Financial time series**: nearly impossible to beat naive (M6 evidence)
- **Highly specialized domains**: where domain-specific LightGBM with engineered features still wins
- **Strong regular seasonality**: no TSFM obtains statistically significant improvement over MSTL (seasonal-trend decomposition) for data with pronounced daily/weekly seasonality
- **Well-calibrated uncertainty**: classical methods still have better-calibrated prediction intervals

## When to Use Deep Learning

**Use when:**
- Long series with complex nonlinear patterns
- Multivariate with cross-series dependencies
- Zero-shot / transfer learning
- Very large datasets (millions of series)

**Avoid when:**
- Series are short (<200 obs)
- Strong regular seasonality (classical wins)
- Computational budget constrained
- Need well-calibrated prediction intervals
- High-frequency sub-minute data

## Practical Usage

```python
# Chronos-2 (zero-shot)
from chronos import ChronosPipeline
pipeline = ChronosPipeline.from_pretrained("amazon/chronos-t5-large")
forecast = pipeline.predict(context=torch.tensor(y), prediction_length=24)
median = forecast.median(dim=1)

# NeuralForecast (training neural models)
from neuralforecast import NeuralForecast
from neuralforecast.models import NBEATS, TFT, PatchTST

nf = NeuralForecast(
    models=[
        NBEATS(h=24, input_size=48, max_steps=500),
        PatchTST(h=24, input_size=48, max_steps=500),
    ],
    freq="H",
)
nf.fit(df=train_df)
forecasts = nf.predict()

# AutoGluon-TimeSeries (automated ensemble)
from autogluon.timeseries import TimeSeriesPredictor
predictor = TimeSeriesPredictor(prediction_length=24).fit(train_data)
predictions = predictor.predict(train_data)
```
