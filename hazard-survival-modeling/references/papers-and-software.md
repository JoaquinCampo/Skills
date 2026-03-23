# References — Papers and Software

## Key Papers

### Discrete-Time Survival Modeling
- Tutz & Schmid (2016). "Modeling Discrete Time-to-Event Data."
  Springer. -- Definitive reference for discrete-time models.
- Allison (2014). "Event History and Survival Analysis." Sage.
  -- Accessible intro to discrete-time survival (green book).
- Spooner et al. (2022). "Survival prediction models: an
  introduction to discrete-time modeling." BMC Med Res Method.
  -- ML classifiers for discrete-time survival.
- Chheang & Pungpapong (2024). "Binary and Multi-label ML
  Models for Discrete-Time Survival Analysis." ACM CMLDS.
  -- XGBoost on person-period data.

### Event Prediction and Label Smoothing
- Yeche et al. (2023). "Temporal Label Smoothing for Early
  Event Prediction." ICML. -- Label smoothing near events.
- Lee et al. (2018). "DeepHit: A Deep Learning Approach to
  Survival Analysis with Competing Risks." AAAI.

### LLM Failure Detection
- Hiraoka & Inui (2025). "Repetition Neurons: How Do Language
  Models Produce Repetitions?" NAACL. -- Pre-repetition signals,
  progressive neuron activation before loop lock-in.
- Ananthanarayanan et al. (2026). "Understanding the Physics
  of KV Cache Compression." arXiv:2603.01426. -- 90% safety
  cliff, GER metric, two failure mechanisms (token erasure,
  representational rigidity).
- Chen et al. (2025). "The Pitfalls of KV Cache Compression."
  arXiv:2510.00231. -- Instruction amnesia, selective
  degradation under compression.

### Additional LLM/Catastrophe Literature
- SpecRA (OpenReview, 2025) -- FFT-based autocorrelation for
  repetition detection in LLM agents.
- EDT (arXiv:2403.14541, 2024) -- Entropy-based dynamic
  temperature sampling.
- CARE (arXiv:2509.06982, 2025) -- Rollback-resample
  intervention framework.
- Confidence Regulation Neurons (NeurIPS 2024) -- Token
  frequency neurons modulating output distribution.

## Software Documentation

- **scikit-survival**: https://scikit-survival.readthedocs.io/
  Key functions: concordance_index_censored,
  concordance_index_ipcw, cumulative_dynamic_auc,
  brier_score, integrated_brier_score,
  GradientBoostingSurvivalAnalysis
- **XGBoost survival**: https://xgboost.readthedocs.io/en/
  stable/tutorials/aft_survival_analysis.html
  Objectives: survival:cox, survival:aft, binary:logistic
- **XGBSE**: https://loft-br.github.io/xgboost-survival-
  embeddings/
  Classes: XGBSEDebiasedBCE, XGBSEStackedWeibull
- **Rodriguez GLM notes** (Princeton):
  https://grodri.github.io/glms/notes/c7s6
  Discrete-time models derivations
