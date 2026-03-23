---
name: time-series-forecasting
description: >
  Use when writing, reviewing, or planning time series forecasting code.
  Triggers on: ARIMA, ETS, Theta, SARIMA, statsforecast, mlforecast, neuralforecast,
  XGBoost/LightGBM/CatBoost for time series, PatchTST, N-BEATS, TFT, Chronos, TimesFM, Moirai,
  MASE, MAPE, CRPS, temporal CV, walk-forward validation, prediction intervals, conformal prediction,
  data leakage in time series, demand forecasting, hierarchical forecasting, lag features, rolling features.
---

# Time Series Forecasting Best Practices

This is a **router skill**. It contains universal principles inline and delegates detailed guidance to reference files loaded on demand. **Always read the relevant reference files before giving advice.**

## Universal Principles (always apply)

1. **Always benchmark against naive methods.** Seasonal naive is the minimum bar. Use MASE (< 1 = beating naive).
2. **Combine forecasts.** Simple average of 3-5 diverse methods is one of the most reliable strategies across 40+ years of evidence (M1 through M6).
3. **Simplicity first.** Complexity increases forecast error by 27% on average (Armstrong & Green, 25 studies). Only add complexity with clear evidence it helps on YOUR data.
4. **Never shuffle time series.** All splits, CV, and preprocessing must respect temporal order.
5. **Fit preprocessing on training data only.** Scaling, decomposition, imputation — all must be computed without future information.
6. **Feature engineering > model choice** when covariates are available (~60% of accuracy in ML approaches).
7. **Trees cannot extrapolate trends.** Detrend or difference before using gradient boosting.
8. **Report prediction intervals.** Point forecasts alone are insufficient for decision-making.
9. **Foundation models are not universally superior.** They struggle with high-frequency (<1min), financial, and specialized domains.
10. **Be skeptical of published benchmarks.** Data contamination inflates foundation model zero-shot results by 47-184%.

## Decision Router

Based on the user's scenario, read the relevant reference files from `references/` in this skill directory.

### Which references to load:

| User scenario | Load these references |
|---|---|
| "Which model should I use?" / model selection | `model-selection.md` |
| Working with ARIMA, ETS, Theta, STL, stationarity | `classical-methods.md` |
| Using XGBoost/LightGBM/CatBoost, feature engineering | `ml-gradient-boosting.md` |
| Neural networks, transformers, foundation models | `deep-learning-foundation.md` |
| Metrics, validation, backtesting, data leakage | `evaluation-methodology.md` |
| Production pipelines, tools, hierarchical forecasting | `industry-tools-scale.md` |
| Debugging poor results, reviewing code for mistakes | `common-pitfalls.md` |

### Quick model selection (without loading references):

```
Few series + short (<100 obs) + univariate?
  -> Classical: ETS, ARIMA, Theta. Combine 3-5.

Many series (1000+) + rich covariates (prices, calendar)?
  -> Global LightGBM with engineered features.

Zero-shot / no training data / quick baseline?
  -> Foundation model: Chronos-2 or Moirai 2.0.

Multiple seasonalities (hourly data with daily+weekly)?
  -> MSTL decomposition + downstream model.

Hierarchical data (store > dept > product)?
  -> Bottom-up with MinT reconciliation. Load industry-tools-scale.md.

Financial time series?
  -> Accept that most methods won't beat naive. Use purged CV.
```

### Quick metric selection (without loading references):

```
Default metric?                    -> MASE (always safe)
Multiple series, different scales? -> MASE or GMRAE
Stakeholders need percentages?     -> WAPE (never MAPE)
Intermittent / sparse demand?      -> MASE (never MAPE/sMAPE)
Probabilistic forecasts?           -> CRPS + coverage
```

## How to use this skill

1. Read this SKILL.md first to understand the user's scenario.
2. Load 1-3 relevant reference files based on the router table above.
3. Apply universal principles regardless of which references you load.
4. When in doubt, load `common-pitfalls.md` — most forecasting failures are evaluation/leakage errors, not model choice errors.
