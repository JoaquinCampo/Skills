# Industry Tools and Forecasting at Scale

## Nixtla Ecosystem (recommended default)

The dominant open-source ecosystem with unified API across all method families:

| Library | Purpose | Key strength |
|---|---|---|
| **statsforecast** | Statistical methods (ARIMA, ETS, Theta, CES, MSTL, 30+) | Up to 300x faster than statsmodels |
| **mlforecast** | ML methods (LightGBM, XGBoost) with proper lag features | Scales to millions via Spark/Dask/Ray |
| **neuralforecast** | Neural methods (N-BEATS, N-HiTS, TFT, PatchTST, 30+) | Unified training API |
| **hierarchicalforecast** | Reconciliation (MinT, ERM, bottom-up, top-down) | Coherent hierarchical forecasts |
| **utilsforecast** | Evaluation metrics, plotting, CV utilities | |
| **TimeGPT** | Foundation model API | Commercial, zero-shot |

## Prophet (Meta)

- Additive regression: piecewise linear/logistic trend + Fourier seasonality + holidays
- **Best for**: quick baselines, stakeholder-facing decompositions, daily data with strong seasonality
- **Limitations**: consistently underperforms tuned ARIMA, XGBoost, neural methods in benchmarks
- **Verdict**: Use for EDA and quick prototyping, not production accuracy

## Amazon Forecasting Stack

- **DeepAR**: Global probabilistic RNN. Good for many related series with covariates.
- **AutoGluon-TimeSeries**: AutoML ensemble of diverse model families. Recommended default for automated model selection — ensembling consistently outperforms hand-tuned single models.
- **Chronos-2**: Foundation model. Best covariate support, 300+ forecasts/sec. Leads fev-bench.

## Uber Orbit

- Bayesian structural time series
- Good for causal impact estimation and intervention analysis
- Use when you need Bayesian inference + structural decomposition

## Hierarchical Forecasting

### When it matters
Any data with natural aggregation structure: store > department > product, national > state > city, company > division > team.

### Approaches

| Method | How | When |
|---|---|---|
| **Bottom-up** | Forecast most granular, aggregate up | Default for global ML models (M5 winner) |
| **Top-down** | Forecast aggregate, distribute down | Fast, less accurate at granular level |
| **Middle-out** | Forecast at intermediate level | Balance of accuracy across levels |
| **MinT (optimal reconciliation)** | Adjust all levels simultaneously to minimize total variance | Best accuracy; use shrinkage estimator for covariance |

### MinT with shrinkage should be standard whenever a hierarchy exists. It improves accuracy AND ensures coherence.

```python
from hierarchicalforecast.core import HierarchicalReconciliation
from hierarchicalforecast.methods import MinTraceShrink

reconciler = HierarchicalReconciliation(reconcilers=[MinTraceShrink()])
reconciled = reconciler.reconcile(Y_hat_df=forecasts, Y_df=actuals, S=summing_matrix)
```

## Automated Model Selection

### AutoGluon-TimeSeries (recommended)
```python
from autogluon.timeseries import TimeSeriesPredictor
predictor = TimeSeriesPredictor(
    prediction_length=24,
    eval_metric="MASE",
).fit(train_data, time_limit=3600)  # 1 hour budget
predictions = predictor.predict(train_data)
leaderboard = predictor.leaderboard()
```

### Other AutoML options
- **auto_arima** (pmdarima): within ARIMA family only
- **AutoETS** (statsforecast): within ETS family only
- **AutoTS**: open-source, tries many model families

### When automation works well
- Many series to forecast (can't hand-tune each)
- Diverse model families in the ensemble
- Sufficient compute budget for model search

### Risks
- May miss domain-specific feature engineering opportunities
- Black-box nature can hide evaluation errors
- Still need proper temporal validation setup

## MLOps for Forecasting Pipelines

### Retraining strategy
- Statistical models (cheap): retrain at every forecast origin
- ML models: retrain periodically (weekly/monthly) with data updates between
- Neural models: retrain less frequently, fine-tune on recent data

### Concept drift detection
- Monitor forecast accuracy over time with rolling MASE
- DDM (Drift Detection Method), KSWIN (Kolmogorov-Smirnov Windowing)
- Alert when accuracy degrades beyond threshold
- Add cooling period after retraining to avoid thrashing

### Production monitoring
- Track empirical coverage of prediction intervals
- Monitor feature distributions for shift
- Compare against always-updated naive baseline
- Dashboard: MASE over time, coverage, feature drift

## Domain-Specific Guidance

| Domain | Recommended approach | Key considerations |
|---|---|---|
| **Demand / supply chain** | LightGBM with price + calendar features, hierarchical reconciliation | Intermittent demand (Croston's), promotions, stockouts |
| **Financial (returns)** | Accept naive is hard to beat; GARCH for volatility | Purged CV, EMH, risk management > prediction |
| **Energy load** | CNN-LSTM hybrids, weather covariates | Multiple seasonalities, weather-dependent |
| **Epidemiological** | Compartmental models + foundation model ensembles | Domain constraints, limited history |
| **Weather / climate** | DL foundation models approaching NWP parity | Spatial + temporal, physics-informed |
| **Retail sales** | Global LightGBM, M5-style features | Rich covariates are key differentiator |
