# Evaluation Methodology for Time Series Forecasting

## Metrics

### Recommended defaults

| Scenario | Metric | Why |
|---|---|---|
| **Default** | **MASE** | Scale-free, handles zeros, symmetric, benchmarks vs naive, single unambiguous definition |
| Multiple series, different scales | MASE or GMRAE | |
| Stakeholders need percentages | **WAPE** (never MAPE) | MAPE is asymmetric, undefined at zero, biased toward low forecasts |
| Intermittent / sparse demand | MASE | MAPE/sMAPE explode near zero |
| Probabilistic forecasts | **CRPS** + coverage | CRPS generalizes MAE to distributions |
| Per-quantile accuracy | Quantile loss / Pinball loss | |
| Competition-style | MASE + sMAPE (M4), WRMSSE (M5) | |

### Metrics to avoid
- **MAPE**: undefined at zero, asymmetric, biased. Penalizes over-forecasts more than under-forecasts.
- **sMAPE**: at least 4 inconsistent definitions in literature. Hyndman explicitly recommends avoiding it: "I would not recommend using any of them."
- Both explode with near-zero actuals.

### MASE interpretation
- `MASE < 1`: better than seasonal naive
- `MASE = 1`: equivalent to seasonal naive
- `MASE > 1`: worse than seasonal naive (something is wrong)

Formula: `mean(|e_t|) / mean(|y_t - y_{t-m}|)` where m = seasonal period.

## Train/Test Splitting

### Random splitting is WRONG
Destroys temporal order, causes data leakage, produces unrealistic (optimistic) results.

### Walk-forward validation (gold standard)
1. Train on initial window
2. Forecast next h steps
3. Record errors
4. Advance origin by 1+ steps
5. Retrain (or update) model
6. Repeat

```
Origin 1: Train[1..T1]  -> Forecast[T1+1..T1+h]
Origin 2: Train[1..T2]  -> Forecast[T2+1..T2+h]
Origin 3: Train[1..T3]  -> Forecast[T3+1..T3+h]
```

### Expanding vs sliding window
- **Expanding**: training set grows. Best for stable processes, small datasets.
- **Sliding**: fixed training size. Best for concept drift, when recent data matters more.

### Gap between train and test
Insert gap = forecast horizon h. Ensures no overlap between last training observation's prediction window and test set.

### Financial data: purging + embargo (de Prado)
- **Purging**: remove training samples whose label horizon overlaps test period
- **Embargo**: exclude buffer of observations after test fold from training
- **CPCV** (Combinatorial Purged CV): superior for detecting backtest overfitting

### How many origins?
- Minimum: 5-10 for stable error estimates
- Ideal: as many as computationally feasible
- For expensive models: retrain every k steps, update between retrains

## Baseline Models (mandatory)

| Method | Forecast | Use when |
|---|---|---|
| **Naive** | y_hat = last value | Random walk data (finance) |
| **Seasonal naive** | y_hat = same season last year | Strong seasonality |
| **Mean** | y_hat = historical average | Stationary, no trend |
| **Drift** | Last value + average change | Linear trend |

If your model can't beat seasonal naive, investigate before claiming results. A 2025 paper ("Mind the naive forecast!") documents published ML methods failing to beat naive when properly evaluated.

## Data Leakage Prevention Checklist

- [ ] Split data BEFORE any preprocessing
- [ ] Fit all transformations (scaling, PCA, imputers) on training data only
- [ ] Decomposition (STL, etc.) within each CV fold separately
- [ ] Rolling features computed using only past data at each time step
- [ ] External features realistically available at forecast time
- [ ] Hyperparameter search uses only train + validation (never test)
- [ ] No feature has unrealistically high correlation with target

### Most insidious leakage: global normalization

```python
# WRONG: leaks test statistics into training
scaler.fit(full_data)
full_data_scaled = scaler.transform(full_data)
train, test = split(full_data_scaled)

# CORRECT: fit only on training data
train, test = split(full_data)
scaler.fit(train)
train_scaled = scaler.transform(train)
test_scaled = scaler.transform(test)
```

This applies to ALL preprocessing: scaling, PCA, imputation, decomposition, smoothing.

## Uncertainty Quantification

### Parametric (ARIMA/ETS)
- Based on residual variance + distributional assumptions
- First-step interval: `y_hat +/- 1.96 * sigma`
- Limitation: assumes normally distributed, homoscedastic residuals

### Bootstrap prediction intervals
- Resample from fitted residuals, simulate future paths
- No normality assumption required
- Computationally expensive

### Conformal prediction (distribution-free)
- **EnbPI** (Xu & Xie, ICML 2021): first conformal method for time series, no exchangeability needed
- **ACI** (Gibbs & Candes, 2021): adapts alpha online for distribution shifts — better adaptation than EnbPI
- Recent benchmarks: ACI meets/exceeds 90% target coverage; EnbPI can fail under strong shift

### Quantile regression
- Directly estimate conditional quantiles (0.025, 0.5, 0.975)
- No distributional assumptions
- Risk: quantile crossing — use monotone quantile regression to fix

### Calibration assessment
- Empirical coverage should match nominal level
- PIT histogram should be uniform
- Track coverage in production: 95% interval should cover 95% of actuals

## Forecast Combination

Simple averaging of 3-5 diverse methods is one of the most reliable strategies (50+ years of evidence):

1. Start with simple average (equal weights)
2. Ensure diversity: combine models from different families (ETS + ARIMA + ML)
3. Don't combine highly correlated models
4. Validate the combination on held-out data

Weighted combinations often **don't** outperform simple averaging — weight estimation introduces error that offsets theoretical gains.

## Pre-Publication Checklist

Before claiming "our method outperforms SOTA":
1. [ ] Compared against naive and seasonal naive baselines?
2. [ ] Proper temporal train/test split (not random)?
3. [ ] Walk-forward validation with multiple origins?
4. [ ] All preprocessing fit on training data only?
5. [ ] Appropriate metrics (MASE, not just MAPE)?
6. [ ] Statistical significance tested (Diebold-Mariano)?
7. [ ] Multiple forecast horizons evaluated?
8. [ ] Probabilistic forecast quality reported?
9. [ ] Residuals checked for autocorrelation?
10. [ ] No future information in features?
