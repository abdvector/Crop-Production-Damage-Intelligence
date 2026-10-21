# Revised modelling protocol, version 1

Declared before executing this revised comparison, 21 October 2026. This is exploratory redevelopment of an already inspected archive, not a new independent confirmation. The foundation plan remains unchanged. No 2018–2022 labels are read by this run.

## Aim and methods

Predict Odisha district Kharif rice yield, kg/ha, with information notionally available on 31 August. Follow the foundation's 600 development observations and 420 complete-history observations. Retain the two-year assumed reporting delay, whole-district weather and fixed reference boundaries. Do not infer causal damage, protein effects or aluminium effects.

Seventeen configurations: recent mean, last available yield, historical trend; and history-only/history-plus-weather Ridge alpha 1/10/100, Random Forest maximum depth 4/8 (300 trees, minimum leaf 10), histogram boosting L2 1/10 (150 iterations, learning rate .05, seven leaves, minimum leaf 15, no random early stopping). Seed 42, two numerical threads. District inventory is fixed at 30; encoding drops the first category. Ridge scales numeric X on fitting data only. All learned models predict deviation from the historical reference, add the reference back and floor yield at zero. Mean/trend are baseline auxiliaries, not duplicate X columns.

Outer years: 2012–2017. Each outer fold fits through Y−2; inner validation runs from 2008 through Y−2, with its own fitting through inner year−2 starting in 2004. Selection uses equal-year MAE, RMSE then candidate order. Choose the overall pipeline and, separately, each family/predictor-block control using inner scores only. Record every selection and configuration prediction. Predictions for identical candidate/year/fitting data may be cached; outer outcomes never affect earlier fitting or selection. Do not choose a deployment winner by sorting outer scores.

## Diagnostics and interpretation

Before fitting, require valid source hashes, keys, finite X/Y, correct past lags, positive reference, nonnegative targets, known districts and the temporal cutoff. Record numeric rank, condition number and predictor correlations; reject constant numeric inputs. Full-rank OLS assumptions are not a requirement for penalised fitting, but redundancies are documented. Record fitting error versus out-of-time error and numeric out-of-range counts (the year predictor necessarily extrapolates).

For each nested strategy, report MAE/RMSE/bias/WAPE/R², per-year and district errors, low-yield confusion counts, forecast-error versus prediction plots, absolute-error patterns, Q–Q shape, consecutive-year within-district error association and annual descriptive Moran I using the foundation's fixed symmetric four-nearest-centroid graph. Show error bias and dispersion by year and predicted-yield quartile. These diagnose predictive adequacy, not causal specification.

Use paired annual MAE differences and whole-year bootstrap 95% intervals (2,000 samples, seed 42), with individual years visible. Six possibly dependent years do not support confirmatory superiority. These intervals assume exchangeable year clusters and are explicitly exploratory. No iid normality, Breusch–Pagan, OLS t/F or pooled time-series test is used to license Ridge or trees. No unsupported p-value is turned into a pass label. Gaussian predictor distributions are not required; residual normality is not needed for point prediction. Dependence and nonconstant variance matter for inference and intervals and cannot be repaired merely by switching algorithms.

Checks are classified as data/numerical validity (enforced), diagnostic evidence (measured), or scope/inference limitation (unresolved). No aggregate "all assumptions passed" claim. A statistically insignificant diagnostic is not proof of correct specification. Ordinary regression coefficient significance and causal interpretation are outside scope.

## Prespecified sensitivities

1. Weather information timing: rerun the same nested selection using only June/July monthly weather (10 weather columns); drop all five August columns and all four whole-window extremes. This is an input-availability sensitivity at the same 31 August issue date, not a claim about an earlier issue date. All choices stay inside inner folds.
2. Redundant representation: refit each outer-selected learned configuration adding historical mean/trend back to X, without retuning the winner. Report the prediction/error change; this is a sensitivity, never a replacement selected from outer outcomes.
3. Unusual training year: identify the training year with greatest mean absolute deviation from the historical reference, using training outcomes only. Refit the same selected configuration without that year's training rows. Retain all evaluation rows and the original data. This is a stress test, not authorised outlier deletion or a new winning model. Baseline predictions remain unchanged.

## Intervals: separate branch with disjoint selection/calibration labels

Freeze the configuration selected for outer year 2012 using inner labels 2008–2010. Generate its rolling calibration predictions for 2012–2014 with fitting through each year−2 (90 errors). These calibration labels are not used to choose this branch's configuration. Freeze the 80% absolute-relative-error quantile using rank ceil((90+1)*.8), then evaluate this separate fixed-configuration branch in 2016–2017, when all calibration labels are available under the assumed delay. Annual refits still end at Y−2. It is not the adaptively reselected nested strategy, and calibration observations may enter later fitting once available. Report coverage, width, 80% interval score and per-year values. Dependence, annual refitting and only two interval assessment years prevent a distribution-free guarantee or operational reliability claim.

## Release

Save a run declaration containing protocol/code/input hashes and library versions before fitting. On completion, hash all outputs; completed reruns verify rather than overwrite. Existing models and results remain untouched. Save tables and scientific PNG/SVG figures under `data/processed/rice/revised_modelling/`, and a readable result report under `docs/`. Present the nested overall selection process as the primary method, matched weather contrasts as secondary, and sensitivity/interval branches separately. Additional improvements require a new version and transparent exploratory labelling.

References: [Ridge](https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification), [nested validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html), [forecast diagnostics](https://otexts.com/fpp3/toolbox.html), [regression and prediction intervals](https://otexts.robjhyndman.com/fpp3/regression-intro.html).
