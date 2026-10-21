# Rice forecasting improvement protocol

Declared 11 October 2026 before evaluating this candidate set.

## Scope

Keep the original audited observations, 60-day forecast cutoff and 12 outer location groups. Preserve the first results in `baseline/day_60/`. This is a development comparison on a dataset already inspected; nested validation does not turn it into a new independent external test.

## Diagnostic motivation

The first audit found eight of twelve held-out locations had at least one weather feature outside the corresponding training range. Within-environment residual variance is about 316,422 (kg/ha)^2 versus overall variance 923,865 (kg/ha)^2. This descriptive decomposition suggests substantial environment differences; it does not identify their cause.

## Fixed candidate set

Regression candidates:

- Training mean.
- Weather Ridge, alpha in {100, 1000, 10000}.
- Weather plus five genetic principal components, Ridge alpha in {100, 1000, 10000}.
- Weather plus five genetic principal components and their weather interactions, Ridge alpha in {1000, 10000}.
- Weather random forest fitted to environment mean yields, 128 trees, minimum leaf environments in {2, 4}, random seed 42.

Two procedures are evaluated: weather-only selection (mean, weather Ridge, environment forest) and weather-plus-genetics selection (the full set). This tests whether making genetics available improves the entire selection procedure; it does not isolate protein effects.

Risk candidates: training prevalence, or logistic regression with weather alone or weather plus five genetic PCs, C in {0.001, 0.01}. Thresholds are the training-only 20th yield percentile, recomputed independently for every inner and outer split. Probabilities are exploratory and not externally calibrated.

## Selection and preprocessing

For each outer held-out location, select each procedure using leave-one-location-out splits confined to the outer training locations. Minimise the average location mean squared error for regression and average location Brier score for risk. Give each location equal weight in selection. Refitting uses all outer training records; no outer target determines candidate selection.

Fit marker scaling and PCA on unique training genotypes only. Transform validation/test markers using those fitted transforms. Fit weather scaling on unique training environments only. Standardise expanded predictors on training records before Ridge/logistic regression. Interactions are products of standardised weather and genetic PC inputs, not measured molecular responses. Fit environment forests to one weather profile and observed mean target per training environment, so repeated genotypes do not create additional independent weather profiles.

Report both pooled record-weighted metrics and equal-location summaries, full outer predictions, chosen candidates, inner scores, extrapolation diagnostics and source hashes. Preserve disappointing results. No adaptive expansion of this grid after looking at outer performance in this experiment.

Methods references: [scikit-learn nested validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html), [grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data), and [PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html).
