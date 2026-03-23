# Model Selection for Time Series Forecasting

## Decision Framework

| Data characteristics | Recommended approach | Why |
|---|---|---|
| Short series (<100 obs), univariate | ETS, ARIMA, Theta | ML overfits with little data; classical methods dominated M1-M4 |
| Many short series (1000+) | Global ML model (LightGBM) with series_id feature | Pools information across series; M5 winner approach |
| Long single series (>1000 obs) | ML/DL become competitive; still benchmark vs classical | ML needs data to shine |
| Strong single seasonality | ETS (Holt-Winters), SARIMA | Well-understood, fast, proper prediction intervals |
| Multiple seasonalities | MSTL + model, or TBATS | STL handles only one; MSTL iteratively extracts multiple |
| Rich exogenous variables | LightGBM/XGBoost (tabular) or TFT (neural) | Trees naturally handle mixed-type features; M5 showed this decisively |
| Zero-shot / no task-specific data | Chronos-2, Moirai 2.0, TimesFM | Foundation models' key strength |
| Financial returns/prices | Naive baseline + GARCH for volatility | EMH: M6 showed 77% of participants couldn't beat benchmark |
| Intermittent demand (many zeros) | Croston's method, SBA, IMAPA | Specialized for sparse demand patterns |
| Need interpretability | Classical methods or SHAP on tree models | Clear components (trend, seasonal) in classical; SHAP for trees |
| Need calibrated uncertainty | ETS/ARIMA (parametric PI) or conformal prediction on any model | State-space models give proper PIs; ACI adapts to drift |

## Competition Evidence

### M4 (100K series, univariate):
- **Winner**: ES-RNN hybrid (~10% better than Comb benchmark)
- **12/17 top methods were combinations** of statistical approaches
- **All 6 pure ML methods failed** — none beat the Comb benchmark
- **Lesson**: Hybridize (statistical structure + ML), don't replace

### M5 (42K series, rich covariates):
- **Winner**: LightGBM ensemble with per-horizon direct models
- **Feature engineering was decisive**, not model architecture
- **First M-competition where ML beat all statistical methods**
- **Lesson**: When covariates exist, gradient boosting dominates

### M6 (financial, live):
- **Only 23.3% beat the forecasting benchmark**
- Simple covariance estimation won, not deep learning
- **Lesson**: Financial forecasting is extremely hard; simplicity wins

## The Combination Default

When uncertain, **combine 3-5 diverse methods**:

```python
# Strong default: average of ETS, ARIMA, Theta
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, AutoARIMA, Theta, SeasonalNaive

sf = StatsForecast(
    models=[
        AutoETS(season_length=m),
        AutoARIMA(season_length=m),
        Theta(season_length=m),
        SeasonalNaive(season_length=m),  # baseline
    ],
    freq=freq,
)
forecasts = sf.forecast(df=df, h=h)

# Simple combination
forecasts["combined"] = forecasts[["AutoETS", "AutoARIMA", "Theta"]].mean(axis=1)
```

50+ years of research (Bates & Granger 1969 through Wang et al. 2023): simple averaging is hard to beat.

## When to Use Deep Learning

Use DL/foundation models when:
- Zero-shot scenario (no training data for this specific task)
- Very long series with complex nonlinear patterns
- Multivariate with cross-series dependencies
- Transfer learning from related tasks

Avoid DL when:
- Series are short (<200 obs per series)
- Data has strong, regular seasonality (classical methods win)
- Computational budget is constrained
- You need well-calibrated prediction intervals
- High-frequency sub-minute data

## Python Ecosystem Map

| Need | Library | Notes |
|---|---|---|
| Fast statistical methods | `statsforecast` (Nixtla) | Up to 300x faster than statsmodels |
| ML-based forecasting | `mlforecast` (Nixtla) | Production-scale, Spark/Dask support |
| Neural methods | `neuralforecast` (Nixtla) | N-BEATS, TFT, PatchTST, 30+ models |
| Hierarchical reconciliation | `hierarchicalforecast` (Nixtla) | MinT, ERM, bottom-up, top-down |
| AutoML for time series | `AutoGluon-TimeSeries` | Ensembles diverse model families |
| Foundation models | `chronos-forecasting` (Amazon) | Chronos-2, best zero-shot |
| Full control, academic | `statsmodels` | State-space models, full diagnostics |
| Scikit-learn compatible | `skforecast` | Great docs, good for learning |
| R-style auto.arima | `pmdarima` | Hyndman-Khandakar algorithm |
