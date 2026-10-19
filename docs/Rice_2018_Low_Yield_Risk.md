# 2018 low-yield-risk comparison

Completed 19 October 2026. Logistic regression, Random Forest and histogram gradient boosting were fitted on the matched 2018 cohort. **No tested ML configuration beats the state-prevalence baseline on the declared primary Brier metric.** Some models improve on the weaker global baseline and have modest ranking ability, but calibrated operational risk is not established.

## Target and data

The experiment uses the same 4,801 complete-report records, 45 district labels, input blocks and five district/weather-purged folds as the 2018 regression-management study. Each model/input block sees identical fitting and validation records. No 2017/2019 features are inferred, and the existing 2019 assessment and regression results are unchanged.

Within each fold, compute the 20th percentile of **fitting yields only**, using a linear quantile. A yield strictly below that value is a low-yield event in both fitting and validation. Ties mean fitting prevalence need not equal exactly 20%. Cutoffs range from **3,330 to 4,000 kg/ha**; validation event rates range from **5.7% to 39.7%**. The pooled validation event rate is 22.25%.

This defines relative low-yield risk, not a measured damage percentage, disease label, causal yield loss or a single fixed absolute yield cutoff. Thresholds vary between folds. Pooled Brier score therefore evaluates the cross-fitted procedure; it must not be interpreted as calibration against one common kg/ha threshold. ROC AUC and average precision are computed within each fold and then averaged rather than pooling incompatible target definitions.

## Declaration and models

The risk protocol was saved before fitting. Fixed candidates are logistic regression C=1, Random Forest with 200 trees/minimum leaf 50, and histogram gradient boosting with 15 leaves. The three input blocks are weather/planting/context, plus reported soil texture and irrigation access, and plus ten timed fertiliser-product-mass features. These definitions and the cohort match the earlier management study.

Training-only encoders, scaling and imputation are fitted inside each fold. There are no class weights, oversampling, hyperparameter search, validation-label recalibration or operational decision-threshold selection. The global baseline predicts fitting prevalence. The state baseline predicts fitting-state prevalence, with global fallback for states absent from fitting. No baseline receives validation labels.

The primary metric is pooled cross-fitted **Brier score**, where lower is better. Secondary diagnostics are log loss, mean within-fold ROC AUC, mean within-fold average precision, probability bias and ten fixed equal-width calibration bins. No classification accuracy/F1 headline is used, and no probability-to-action threshold is inferred from the held-out outcomes.

## All configurations

| Model | Input block | Brier score | Mean fold ROC AUC | Log loss |
| --- | --- | ---: | ---: | ---: |
| Global training prevalence | Baseline | 0.1738 | 0.500 | 0.5325 |
| State training prevalence | Baseline | **0.1594** | 0.580 | 0.8046 |
| Logistic | Weather/planting | 0.1639 | 0.636 | 0.5144 |
| Logistic | Plus static context | 0.1636 | 0.644 | 0.5116 |
| Logistic | Plus static and timed products | 0.1642 | 0.653 | 0.5094 |
| Random Forest | Weather/planting | 0.1734 | 0.557 | 0.5339 |
| Random Forest | Plus static context | 0.1742 | 0.558 | 0.5349 |
| Random Forest | Plus static and timed products | 0.1699 | 0.585 | 0.5242 |
| Gradient boosting | Weather/planting | 0.1827 | 0.542 | 0.5735 |
| Gradient boosting | Plus static context | 0.1772 | 0.580 | 0.5530 |
| Gradient boosting | Plus static and timed products | 0.1721 | 0.622 | 0.5406 |

Logistic with static context has the lowest observed ML Brier score, approximately 5.85% below the global baseline, but still worse than the state baseline. This is a descriptive comparison of the fixed candidates, not a selected final model or an independent-test improvement.

Timed product masses improve Random Forest and boosting Brier scores relative to their core blocks. They slightly worsen logistic Brier score despite increasing its ROC AUC and reducing log loss. The regression study's modest dose-related improvement therefore does not imply a universal improvement in low-yield probabilities.

The state baseline has the strongest Brier score but poor log loss: some state-level fitting estimates are zero, which incurs large log-loss penalties when validation contains events. That baseline should not be treated as a deployment-ready probability estimate. A smoothed state estimator would be a new declared development candidate, not a correction applied after observing these results.

## Calibration and limits

Fully augmented logistic predicts mean risk 18.81%, versus 22.25% observed for the cross-fitted event definition. Its ten-bin absolute calibration-error diagnostic is about 0.085, with variation by probability bin. The lower global-baseline error is about 0.029, but a constant predictor has no within-fold ranking ability. Small calibration bins are unstable, and an aggregate mean near the event rate does not demonstrate calibration throughout the probability range.

The app displays the raw held-out reliability-bin counts, mean probability and observed event rate for each candidate/block. These are diagnostic summaries; no recalibration model has been fitted or independently validated. A single year, selected complete-report sample, changing fold cutoffs and spatial dependence limit generalisation. These probabilities must not be advertised as verified local damage risk or used to claim savings.

The next steps are a fixed, defendable deployment risk definition, independent-year/source validation, and a separate calibration design using training/calibration data rather than opened final-test labels. Prediction intervals for yield are a separate remaining task. The suspect 2019 yield labels remain unresolved.

## Reproduction and preservation

`src/rice_field_risk.py` declares the protocol, reconstructs the matched membership, derives training-only thresholds, fits fixed classifiers and writes metrics/calibration tables. `protocol.json` records the input definitions, feature hash and comparison rules. The pipeline validates earlier result hashes before and after fitting and refuses automatic reruns of a completed risk experiment. Row-level probabilities remain local; aggregate outputs are published under `data/processed/rice/india_field_survey/risk_2018/`. `app.py` remains the sole application entry point.
