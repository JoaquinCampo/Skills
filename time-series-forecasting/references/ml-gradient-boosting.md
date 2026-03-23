# ML / Gradient Boosting for Time Series

## Model Choice

| Model | Best for | Key advantage |
|---|---|---|
| **LightGBM** | Default choice. Speed-critical, large datasets | Fastest, native categoricals, M5 winner |
| **CatBoost** | Many categorical features, minimal tuning | Ordered boosting (built-in temporal leakage protection) |
| **XGBoost** | General purpose, robust baseline | Mature, well-documented |

## Feature Engineering (~60% of accuracy)

### 1. Lag features (most important)
- Lags at known periodicities: 7 for daily/weekly, 24 for hourly/daily, 365 for yearly
- Contiguous recent lags (1..p) for short-term dynamics
- Seasonal lags at multiples (7, 14, 21, 28)

**Critical rule**: When predicting h steps ahead, only lags >= h are valid at inference. This is the #1 leakage source.

```python
# WRONG for horizon h=7: lags 1-6 unavailable at inference
for lag in [1, 2, 3, 7, 14, 28]:
    df[f"lag_{lag}"] = df["target"].shift(lag)

# CORRECT for horizon h=7: only lags >= 7
for lag in [7, 14, 21, 28]:
    df[f"lag_{lag}"] = df["target"].shift(lag)
```

### 2. Rolling window statistics
- Multiple window sizes: short (3-7), medium (14-30), long (60-90+)
- Stats: mean, std, min, max, quantiles
- **Always shift by at least 1** (or by h) to avoid including current target

```python
# WRONG: includes y_t in the rolling window
df["rolling_mean_7"] = df["target"].rolling(7).mean()

# CORRECT: excludes y_t
df["rolling_mean_7"] = df["target"].shift(1).rolling(7).mean()

# MOST CORRECT for horizon h=7
df["rolling_mean_7"] = df["target"].shift(7).rolling(7).mean()
```

### 3. Calendar features
- Day of week, month, day of month, week of year, quarter
- Is weekend, is holiday (use `holidays` library)
- Hour, minute for sub-daily data
- Integer encoding works fine for trees (no need for one-hot)

### 4. Fourier features for complex seasonality
- K Fourier pairs for period m: sin(2*pi*k*t/m), cos(2*pi*k*t/m) for k=1..K
- K=3-5 for weekly, K=5-10 for yearly seasonality
- Prevents needing 365 dummy variables

### 5. Target encoding and group stats
- Encode categorical groups with historical target statistics (use only past data!)
- Group aggregations: mean/median/std per store, category, region
- Difference features: week-over-week change, deviation from rolling mean

## The Trend Extrapolation Problem

**Trees CANNOT extrapolate trends.** Predictions bounded by training target range.

Workarounds:
1. **Differencing**: model y_t - y_{t-1} instead of y_t
2. **Detrending**: linear model for trend, tree for residuals
3. **Target normalization**: divide by rolling mean
4. **Hybrid**: linear model (trend) + tree model (nonlinear patterns)

```python
# Detrending approach
from sklearn.linear_model import LinearRegression
trend_model = LinearRegression()
trend_model.fit(df[["time_index"]], df["target"])
df["detrended"] = df["target"] - trend_model.predict(df[["time_index"]])
# Train tree on detrended, add trend back at prediction
```

## Multi-Step Forecasting Strategies

| Strategy | How | Best for |
|---|---|---|
| **Recursive** | 1 model, feed predictions back | Short horizons (1-5 steps) |
| **Direct** | H models, one per horizon | Medium-long horizons; M5 winner |
| **DirRec** | H models with previous predictions as features | Maximum accuracy |
| **MIMO** | 1 model outputs all H steps | Speed, preserves inter-step dependencies |

## Global vs Local Models

- **Global beats local** when series are short (<100 obs) or numerous (1000+)
- One LightGBM on all series with series_id as categorical = standard approach
- For cold-start (new series with no history), global models can still forecast

```python
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd
from lightgbm import LGBMRegressor

fcst = MLForecast(
    models=[LGBMRegressor(n_estimators=500, learning_rate=0.05)],
    freq="D",
    lags=[1, 7, 14, 28],
    lag_transforms={
        7: [RollingMean(window_size=7), RollingStd(window_size=7)],
        28: [RollingMean(window_size=28)],
    },
    date_features=["dayofweek", "month"],
)
fcst.fit(df)  # global model across all series
forecasts = fcst.predict(h=28)
```

## Temporal Cross-Validation

**Never random CV for time series.**

### Expanding window (stable processes):
```
Fold 1: [=====Train=====][Test]
Fold 2: [========Train========][Test]
Fold 3: [===========Train===========][Test]
```

### Sliding window (concept drift):
```
Fold 1: [===Train===][Test]
Fold 2:  [===Train===][Test]
Fold 3:   [===Train===][Test]
```

### Gap between train and test = forecast horizon h:
```
[=====Train=====]---gap=h---[Test]
```

### For financial data: add purging + embargo (de Prado)

## LightGBM Starting Hyperparameters

```python
params = {
    "n_estimators": 1000,       # Use early stopping
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,    # Increase for noisy data
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
}
```

## Kaggle Winning Pattern

```
Feature engineering (60% of effort)
  -> Lags at key periodicities
  -> Rolling stats at multiple windows
  -> Calendar + holiday + event features
  -> Price / exogenous features
  -> Group encodings
Per-horizon direct models (28 models for 28-day forecast)
  -> LightGBM (primary) + XGBoost (diversity)
Simple ensemble (average)
  -> Post-processing (clip negatives, round, reconcile)
```

## Libraries

| Library | Best for |
|---|---|
| **mlforecast** (Nixtla) | Production scale, millions of series |
| **skforecast** | Learning, medium-scale, great docs |
| **sktime** | Academic research, composable pipelines |
| **darts** | Mixed statistical + ML models |
