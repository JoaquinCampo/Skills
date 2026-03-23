# Classical Statistical Methods for Time Series

## ARIMA / SARIMA

### When to use
- Data exhibits autocorrelation (check ACF/PACF)
- Series is or can be made stationary through differencing
- No strong nonlinear patterns
- Short-to-medium term forecasts

### Order identification
- **d**: Use `ndiffs()` with KPSS test. Almost never > 2
- **D**: Use `nsdiffs()`. Apply seasonal differencing FIRST
- **p,q**: Let auto_arima search (Hyndman-Khandakar stepwise algorithm)
- **P,Q**: Typically 0-2 for seasonal terms

### Stationarity testing — always use BOTH:

| ADF result | KPSS result | Conclusion |
|---|---|---|
| Reject (stationary) | Fail to reject (stationary) | Stationary |
| Fail to reject | Reject (non-stationary) | Non-stationary — difference it |
| Reject | Reject | Trend-stationary — detrend or difference |
| Fail to reject | Fail to reject | Inconclusive |

### Key mistakes
- Over-differencing: if lag-1 ACF of differenced series < -0.5, you've over-differenced
- Not testing stationarity before modeling
- Ignoring seasonal differencing (apply it first — result may already be stationary)
- Blindly trusting auto_arima without checking residual diagnostics (Ljung-Box test)

```python
# Recommended: statsforecast (fastest)
from statsforecast.models import AutoARIMA
from statsforecast import StatsForecast
sf = StatsForecast(models=[AutoARIMA(season_length=12)], freq="MS")
forecast = sf.forecast(df=df, h=12)

# Alternative: pmdarima
import pmdarima as pm
model = pm.auto_arima(y, seasonal=True, m=12, stepwise=True,
                      information_criterion='aicc')
```

## Exponential Smoothing (ETS)

### Taxonomy
30 models: Error (A/M) x Trend (N/A/Ad) x Seasonal (N/A/M).

### Critical rules
- **Always use damped trends** unless you have strong domain knowledge for linear extrapolation. Damped consistently outperform linear for multi-step forecasts (Gardner & McKenzie 1985).
- **Avoid ETS(A,*,M)**: additive errors + multiplicative seasonality causes numerical instability
- **Multiplicative error models** require strictly positive data
- Need at least 2 full seasonal cycles (e.g., 24 months for annual seasonality)

### When ETS beats ARIMA
- Clear, describable trend and seasonal patterns
- Shorter series where parsimonious models preferable
- Automatic, fast, reliable forecasts at scale

```python
from statsforecast.models import AutoETS
sf = StatsForecast(models=[AutoETS(season_length=12)], freq="MS")
```

## Theta Method

- Won M3 competition. Hyndman proved it equals **SES with drift** (half the slope of linear trend).
- Strength: simplicity, implicit combination, robustness, minimal overfitting.
- Use as a strong baseline. Deseasonalize first for seasonal data.

```python
from statsforecast.models import Theta, OptimizedTheta
```

## STL / MSTL Decomposition

- **STL**: Seasonal-Trend decomposition using LOESS. Additive only (log-transform for multiplicative).
- **MSTL**: Handles multiple seasonalities (e.g., daily + weekly for hourly data).
- STL is decomposition only — pair with a forecasting model on the seasonally adjusted series.

### Key parameters
- `seasonal_window`: larger = more stable seasonality; `"periodic"` = fixed
- `trend_window`: should be >= 1.5x seasonal period
- Always set `robust=True` when outliers present

```python
# Multiple seasonalities
from statsmodels.tsa.seasonal import MSTL
mstl = MSTL(y, periods=[24, 168])  # daily + weekly for hourly data
result = mstl.fit()
```

## Preprocessing

### Box-Cox transforms
- Stabilize variance when it changes with level
- Guerrero's method for automatic lambda selection
- Log transform (lambda=0) is most common; simple lambda preferred
- Always back-transform forecasts (note: back-transform of means gives medians)

### Missing values
- Short gaps: linear interpolation or forward fill
- Longer gaps: seasonal interpolation
- Must handle before fitting ETS/ARIMA (recursive algorithms break on gaps)

### Outliers
- Investigate before removing — may carry real information
- STL with `robust=True` isolates outliers in remainder
- Options: robust methods, replacement, indicator variables, winsorization

## Hyndman's fpp3 Workflow

1. **Tidy and visualize** (time plots, seasonal plots, ACF)
2. **Transform** if needed (Box-Cox, calendar adjustments)
3. **Decompose** (STL) to understand components
4. **Fit multiple models** (ETS, ARIMA, Theta + naive baselines)
5. **Check residuals** (uncorrelated, zero mean, constant variance, normal)
6. **Evaluate** via walk-forward cross-validation
7. **Select or combine** best models
8. **Produce forecasts** with prediction intervals (80% and 95%)
