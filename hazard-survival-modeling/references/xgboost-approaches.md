# XGBoost for Survival Analysis — Detailed Approaches

## Approach A: Native `survival:cox` Objective

```python
import xgboost as xgb

params = {
    "objective": "survival:cox",
    "eval_metric": "cox-nloglik",
    "tree_method": "hist",
    "learning_rate": 0.1,
    "max_depth": 4,
}
# Labels: positive = event time, negative = censored time
y_train = np.where(event_indicator, time, -time)
dtrain = xgb.DMatrix(X_train, label=y_train)
model = xgb.train(params, dtrain, num_boost_round=500)
# Output: log hazard ratios (risk scores), NOT probabilities
```

Limitations:
- Outputs risk scores, not survival probabilities
- Assumes proportional hazards
- Cannot handle time-varying covariates naturally

## Approach B: Native `survival:aft` Objective

```python
params = {
    "objective": "survival:aft",
    "eval_metric": "aft-nloglik",
    "aft_loss_distribution": "normal",  # or "logistic", "extreme"
    "aft_loss_distribution_scale": 1.0,
    "tree_method": "hist",
}
dtrain = xgb.DMatrix(X_train)
dtrain.set_float_info("label_lower_bound", y_lower)
dtrain.set_float_info("label_upper_bound", y_upper)
# Supports interval censoring via [lower, upper] bounds
# Uncensored: lower == upper
# Right-censored: upper = +inf
# Left-censored: lower = 0
```

Limitations:
- Sensitive to distribution choice and scale hyperparameter
- Outputs expected survival time, not probabilities
- Hard to get calibrated survival curves

## Approach C: Binary Classification on Person-Period Data (RECOMMENDED)

```python
import xgboost as xgb

# Data already in person-period (long) format
# y = event indicator per (sequence, token) row
params = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "tree_method": "hist",
    "learning_rate": 0.05,
    "max_depth": 6,
    "min_child_weight": 10,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "scale_pos_weight": n_neg / n_pos,  # class imbalance
    "reg_alpha": 0.1,  # L1 regularization
    "reg_lambda": 1.0,  # L2 regularization
}
dtrain = xgb.DMatrix(X_pp_train, label=y_pp_train)
dval = xgb.DMatrix(X_pp_val, label=y_pp_val)

model = xgb.train(
    params,
    dtrain,
    num_boost_round=1000,
    evals=[(dtrain, "train"), (dval, "val")],
    early_stopping_rounds=50,
    verbose_eval=100,
)

# Output: P(event at token t | survived to t, features_t)
# This IS the discrete-time hazard: lambda(t|x)
hazard_probs = model.predict(dval)
```

**Why this is best for HERALD:**
1. Token features are naturally time-varying (signals change
   every token) -- person-period format handles this natively
2. No proportional hazards assumption
3. Output is directly the hazard probability (calibrated)
4. Can compute survival curves from hazard estimates
5. XGBoost handles the class imbalance well with
   `scale_pos_weight`
6. Standard binary classification tooling works (AUROC, AUPRC)

## Computing Survival Curves from Hazard Predictions

```python
def hazard_to_survival(hazard_probs: np.ndarray) -> np.ndarray:
    """Convert discrete hazard probabilities to survival curve.

    Args:
        hazard_probs: array of P(event at t | survived to t)
            for t = 0, 1, ..., T

    Returns:
        survival: array where survival[t] = P(survive past t)
    """
    return np.cumprod(1.0 - hazard_probs)


def hazard_to_cumulative(
    hazard_probs: np.ndarray,
) -> np.ndarray:
    """Convert discrete hazards to cumulative hazard.

    Uses the discrete analog: H(t) = -sum(log(1 - lambda_k))
    """
    return -np.cumsum(np.log(1.0 - np.clip(
        hazard_probs, 0, 1 - 1e-10
    )))
```

## Key Hyperparameters for Survival Tasks

| Parameter | Typical Range | Notes |
|-----------|--------------|-------|
| max_depth | 3-8 | Deeper for complex hazard patterns |
| learning_rate | 0.01-0.1 | Lower with more boosting rounds |
| min_child_weight | 5-50 | Higher to prevent fitting noise in rare events |
| scale_pos_weight | n_neg/n_pos | Critical for imbalanced events |
| subsample | 0.6-0.9 | Stochastic gradient boosting |
| colsample_bytree | 0.6-0.9 | Feature subsampling per tree |
| reg_alpha | 0-1 | L1 sparsity on leaf weights |
| reg_lambda | 1-10 | L2 ridge on leaf weights |
| num_boost_round | 200-2000 | Use early stopping |
| early_stopping_rounds | 20-100 | Monitor validation logloss |

## scikit-survival Alternative (Comparison)

```python
from sksurv.ensemble import GradientBoostingSurvivalAnalysis

# Structured array: (event_bool, time_float)
y_surv = np.array(
    [(bool(e), float(t)) for e, t in zip(events, times)],
    dtype=[("event", bool), ("time", float)],
)

model = GradientBoostingSurvivalAnalysis(
    loss="coxph",
    learning_rate=0.1,
    n_estimators=100,
    max_depth=3,
    subsample=0.8,
    dropout_rate=0.1,
    random_state=42,
)
model.fit(X_train, y_surv_train)
risk_scores = model.predict(X_test)
surv_fns = model.predict_survival_function(X_test)
chf_fns = model.predict_cumulative_hazard_function(X_test)
```

**Not recommended for HERALD** because it cannot handle
time-varying covariates (token-level features) natively. The
person-period binary classification approach is superior.

## Comparison Table

| Criterion | Binary (person-period) | survival:cox | survival:aft |
|-----------|----------------------|--------------|--------------|
| Time-varying features | Native | No | No |
| Calibrated probabilities | Yes | No (risk only) | Dist-dependent |
| Proportional hazards | Not assumed | Required | Not assumed |
| Non-linear hazard | Flexible | Baseline only | Parametric |
| Standard eval tools | sklearn | sksurv only | sksurv only |
| Implementation complexity | Low | Medium | Medium |
