# Evaluation Metrics for Hazard/Survival Models

## Survival-Specific Metrics

### Concordance Index (Harrell's C)

Measures rank correlation between predicted risk and observed
event times. C = 0.5 is random, C = 1.0 is perfect.

```python
from sksurv.metrics import concordance_index_censored

# event_indicator: bool array (True = event observed)
# event_time: float array (time of event or censoring)
# estimate: float array (predicted risk, higher = more risk)
c_index, concordant, discordant, tied_risk, tied_time = (
    concordance_index_censored(
        event_indicator, event_time, estimate
    )
)
```

IPCW variant (less biased with heavy censoring):

```python
from sksurv.metrics import concordance_index_ipcw

# survival_train/test: structured array
#   dtype=[("event", bool), ("time", float)]
c_index, ipcw_c, *_ = concordance_index_ipcw(
    survival_train, survival_test, estimate, tau=max_time
)
```

### Time-Dependent AUC (Cumulative/Dynamic)

How well can the model distinguish sequences that will fail by
token t from those that will not?

```python
from sksurv.metrics import cumulative_dynamic_auc

times = np.array([50, 100, 150, 200, 300, 400])
auc_values, mean_auc = cumulative_dynamic_auc(
    survival_train, survival_test, risk_scores, times
)
# auc_values: AUC at each time point
# mean_auc: average across time points
```

### Brier Score and Integrated Brier Score

Mean squared error between predicted survival probability and
actual status, adjusted for censoring via IPCW:

```python
from sksurv.metrics import (
    brier_score,
    integrated_brier_score,
)

# surv_probs: 2D array (n_samples, n_times)
# Each row = predicted survival probabilities at each time
times = np.linspace(10, 400, 50)
_, bs_values = brier_score(
    survival_train, survival_test, surv_probs, times
)
ibs = integrated_brier_score(
    survival_train, survival_test, surv_probs, times
)
# Lower is better. Kaplan-Meier baseline IBS ~ 0.25
```

## Binary Classification Metrics (Horizon-Based)

When using the direct horizon labeling approach, standard
classification metrics apply:

```python
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_recall_curve,
    calibration_curve,
)

# For each horizon H:
auroc = roc_auc_score(y_true, y_prob)
auprc = average_precision_score(y_true, y_prob)
f1 = f1_score(y_true, y_prob > threshold)

# Calibration: are predicted probabilities reliable?
prob_true, prob_pred = calibration_curve(
    y_true, y_prob, n_bins=10, strategy="quantile"
)
```

## Recommended Evaluation Suite for HERALD

| Metric | Purpose | When to Use |
|--------|---------|-------------|
| AUROC | Discrimination (ranking) | Always |
| AUPRC | Discrimination with imbalance | Always (events are rare) |
| Brier Score | Calibration + discrimination | When probabilities matter |
| C-index | Sequence-level ranking | Comparing to survival baselines |
| Time-dep AUC | Performance across token positions | Understanding where model works |
| F1 @ threshold | Operational performance | Choosing intervention threshold |
| Precision @ 90% recall | False alarm rate at high sensitivity | Deployment decision |
