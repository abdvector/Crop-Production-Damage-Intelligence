# Nested rice model improvement results

Evaluated 11 October 2026 using the candidate set recorded in [Rice_Improvement_Protocol.md](Rice_Improvement_Protocol.md). Original results remain in `data/processed/rice/baseline/day_60/`; this experiment is in `data/processed/rice/nested/day_60/`.

## Outcome

The nested selection procedure reduced pooled RMSE by about 14.9% relative to the original fixed weather-plus-genetics Ridge model, from 1,228.902 to 1,045.330 kg/ha. It still performs slightly worse than the training-mean baseline, so this does not establish useful out-of-location forecasting skill.

| Procedure | MAE (kg/ha) | RMSE (kg/ha) | R squared | Equal-location RMSE (kg/ha) |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 840.071 | 1036.542 | -0.164074 | 983.710 |
| Nested weather selection | 870.439 | 1045.330 | -0.183898 | 998.243 |
| Nested weather + genetics selection | 870.439 | 1045.330 | -0.183898 | 998.243 |

Weather-only and full-set selection chose identical candidates and produced identical predictions. No genetic candidate was selected. That is evidence of no added value for these particular compressed-genetic candidates in this development experiment; it does not show that rice genetics or protein embeddings are generally irrelevant.

The selected regression procedure used the environment forest with minimum leaf size two in nine outer folds, the training mean in two, and weather Ridge alpha=10000 in one. It improved on the mean predictor in four of twelve locations, matched it in two and was worse in six.

Low-yield Brier score fell from 0.305809 in the original classifier to **0.174222**, about 43.0% lower. Training prevalence remains better at **0.167305**. Inner validation selected prevalence in eleven folds and weather logistic regression with C=0.001 in one. The single logistic choice increased error at Mwea; this choice was made before reading that outer fold's outcomes. These probabilities are not externally calibrated or measured damage estimates.

## What changed

Eleven regression candidates and five risk candidates were fixed before fitting. Each outer location was excluded from an inner leave-one-location-out search over the remaining eleven locations. Selection used equal-location mean squared error or Brier score; reporting includes both pooled record-weighted errors and equal-location regression errors.

Scaling and five-component genetic PCA were fitted within every training split; SNP scaling and PCA used unique training genotypes. Weather scaling used unique training environments. Environment forests fitted one mean-yield observation per training environment. Genetic interaction terms used products of weather and genetic PCs, not inferred molecular measurements. Post-cutoff weather, test yields, future flowering observations and unlinked soil/protein information were excluded from predictor construction.

## Diagnostics and limits

Eight locations have at least one weather feature beyond their corresponding training minimum/maximum. This simple range check flags extrapolation; being inside all ranges does not establish multivariate support. It neither proves the cause of an error nor establishes a valid application domain.

Only fifteen distinct weather environments and twelve locations are available. Published adjusted targets, source marker filtering, missing management variables, and location/year confounding remain. Nested validation controls this fixed parameter search, but the dataset was already inspected while developing the project. An independent external evaluation is still needed for strong generalisation claims. Neither R squared nor any error metric proves absence of misspecification.

Do not expand the candidate grid merely to improve these observed outer scores. The next substantive step is improving independently verified environmental coverage and trial-linked management/soil information, then evaluating a predeclared model on genuinely new trials. Protein inputs remain conditional on verified variety links. The current baseline remains the defensible reference rather than a deployment claim.

## Saved evidence

Verification passed for source-hash consistency, one prediction per source record per procedure, recomputed aggregate errors, inner choices matching their recorded scores, training transforms remaining unchanged when test predictors are perturbed, predictions remaining unchanged when test yields are replaced, and dashboard switching between both evaluations and uncomputed cutoff dates. No temporary test scripts were retained.

`metrics.csv`, `location_metrics.csv`, `held_out_predictions.csv`, `inner_selection_scores.csv`, `location_diagnostics.csv`, `forecast_windows.csv` and `summary.json` record predictions, choices and scores. The summary includes input SHA-256 hashes, the implementation hash, software versions and the complete candidate grid. The dashboard exposes both experiments and reports whether the procedure beats the training mean.

Methods: [nested validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) and [grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
