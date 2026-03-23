# Common Pitfalls in Time Series Forecasting

## Data Handling Pitfalls

### 1. Random train/test split
**Problem**: Shuffling destroys temporal order, leaks future into training.
**Fix**: Always split chronologically. Never shuffle time series data.

### 2. Global normalization
**Problem**: Fitting scaler on full data (including test) before splitting.
**Fix**: Split first, fit scaler on training data only, transform test with training statistics.

```python
# WRONG
scaler.fit(full_data)
train, test = split(scaler.transform(full_data))

# CORRECT
train, test = split(full_data)
scaler.fit(train)
train_scaled, test_scaled = scaler.transform(train), scaler.transform(test)
```

This applies to ALL preprocessing: scaling, PCA, imputation, decomposition, smoothing, differencing statistics.

### 3. Decomposition before splitting
**Problem**: STL/EMD/wavelet on full series leaks future structure into training components.
**Fix**: Decompose within each CV fold separately, using only training data.

### 4. Rolling features including current value
**Problem**: `df["target"].rolling(7).mean()` at time t includes y_t.
**Fix**: Shift by at least 1 (or by forecast horizon h).

```python
# WRONG
df["rolling_mean_7"] = df["target"].rolling(7).mean()

# CORRECT
df["rolling_mean_7"] = df["target"].shift(1).rolling(7).mean()

# MOST CORRECT for horizon h
df["rolling_mean_7"] = df["target"].shift(h).rolling(7).mean()
```

### 5. Lag features unavailable at inference
**Problem**: Using lag_1 through lag_6 when forecast horizon is 7 — these values won't exist at prediction time.
**Fix**: For direct models with horizon h, only use lags >= h.

## Modeling Pitfalls

### 6. Trees can't extrapolate trends
**Problem**: Gradient boosting predictions bounded by training target range. Systematic under/over-prediction when test has higher/lower values.
**Fix**: Detrend (linear model for trend, tree for residuals), difference, or normalize by rolling mean.

### 7. Over-differencing
**Problem**: Differencing a stationary series introduces artificial negative autocorrelation.
**Detection**: lag-1 ACF of differenced series < -0.5.
**Fix**: Use ADF + KPSS together. Almost never need d > 2.

### 8. Undamped trends in ETS
**Problem**: Linear trends extrapolate forever, producing unrealistic long-range forecasts.
**Fix**: Use damped trends by default. Damped consistently outperform linear for multi-step forecasts.

### 9. Complex model on small data
**Problem**: Neural networks on <200 observations per series overfit catastrophically.
**Fix**: Use classical methods (ETS, ARIMA, Theta) for short series. ML needs data.

### 10. Ignoring multiple seasonalities
**Problem**: Modeling only one seasonal pattern when data has multiple (e.g., hourly data has daily + weekly + yearly).
**Fix**: Use MSTL decomposition, TBATS, or neural models designed for multiple seasonalities.

## Evaluation Pitfalls

### 11. Using MAPE on near-zero data
**Problem**: MAPE is undefined when y_t = 0 and explodes near zero. Also asymmetric.
**Fix**: Use MASE (always safe) or WAPE (if percentages needed).

### 12. No baseline comparison
**Problem**: Reporting accuracy without naive/seasonal naive benchmark. Results are uninterpretable.
**Fix**: Always include seasonal naive. MASE directly encodes this comparison.

### 13. Single train/test split
**Problem**: One evaluation point is unreliable — could be lucky or unlucky.
**Fix**: Walk-forward validation with 5+ origins.

### 14. Confusing in-sample fit with forecast quality
**Problem**: Model with enough parameters fits training perfectly. Says nothing about generalization.
**Fix**: Only evaluate on held-out temporal test sets.

### 15. Cherry-picking forecast horizons
**Problem**: Reporting accuracy only at horizons where your model looks best.
**Fix**: Report across all horizons.

### 16. Not testing statistical significance
**Problem**: Better average performance may be due to chance.
**Fix**: Diebold-Mariano test for pairwise comparison. Friedman test with Nemenyi post-hoc for multiple methods.

## Production Pitfalls

### 17. Stale models
**Problem**: Data-generating process evolves; model trained on old data degrades.
**Fix**: Monitor rolling MASE in production. Retrain when accuracy degrades. Set up drift detection (DDM, KSWIN).

### 18. Ignoring external shocks
**Problem**: Holidays, promotions, policy changes, pandemics invalidate historical patterns.
**Fix**: Include event indicators in features. Have a process for manual forecast adjustments.

### 19. Not monitoring prediction interval coverage
**Problem**: Your "95% interval" actually covers only 80% of actuals in production.
**Fix**: Track empirical coverage continuously. Use ACI (conformal prediction) for adaptive intervals.

### 20. Trusting foundation model benchmarks
**Problem**: Data contamination inflates reported zero-shot results by 47-184%.
**Fix**: Always run your own evaluation on your data. Don't trust published numbers.

## Pre-Modeling Checklist

Before writing any model code:
- [ ] Visualized the data (time plot, seasonal plot, ACF)?
- [ ] Identified trend, seasonality, and their nature (additive vs multiplicative)?
- [ ] Checked for missing values, outliers, structural breaks?
- [ ] Determined the forecast horizon and how predictions will be used?
- [ ] Set up proper temporal validation before any modeling?
- [ ] Established naive baselines?

## Pre-Publication Checklist

Before claiming "our method outperforms SOTA":
- [ ] Compared against naive and seasonal naive baselines?
- [ ] Proper temporal train/test split (not random)?
- [ ] Walk-forward validation with multiple origins?
- [ ] All preprocessing fit on training data only?
- [ ] Appropriate metrics (MASE, not just MAPE)?
- [ ] Statistical significance tested?
- [ ] Multiple forecast horizons evaluated?
- [ ] Probabilistic forecast quality reported?
- [ ] Residuals checked for autocorrelation?
- [ ] No future information in features?
