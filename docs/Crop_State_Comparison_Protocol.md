# Fixed crop-state comparison

Implementation declared 22 October 2026 after the four v3 exports were inspected and before fitting this extension. This implements the comparison already specified in `Crop_State_Extension.md`. The evaluation outcomes have been seen in earlier experiments: all results are exploratory, not a fresh independent test.

The import audit accepts 420 unique district/start-year records for 2004–2017 and complete surface soil moisture. After the already declared 25% valid-cropland coverage rule, NDVI is missing in 45 June, 358 July and 391 August records. Do not lower the threshold after observing this coverage, omit difficult rows or call imputed vegetation an observed measurement.

## Fixed design

- Target: official Odisha Kharif rice yield, kg/ha. Same 30 district references and 420 input rows for all methods.
- Evaluation: six annual folds, 2012–2017; each fits all 2004…Y−2 rows, predicting all 30 districts in Y. This gives 180 evaluation records per method. No fit uses outcomes from Y−1 or Y.
- Methods: recent mean benchmark; history forest; history/weather forest; history/weather/crop-state forest. No hyperparameter search, nested winner selection or promotion of a test-set winner.
- History X: five lagged yields Y−2…Y−6, start year and district identity. Weather adds the existing 19 summaries. Crop-state adds six exported variables, with three NDVI missingness indicators.
- The historical mean is reconstructed from the five lagged yields, used as the benchmark and offset. Forests fit yield minus that mean, then add the mean back and clip negative predictions to zero. Do not add the exact lag-derived mean/trend as redundant Xs.
- All three forests: 300 trees, max depth 4, min leaf size 10, random seed 42, max_features 1.0, bootstrap true, squared-error criterion. Two local worker threads. District one-hot encoding drops one reference level; all fitting years contain all districts.
- Fit medians using training X only. Missingness indicators are defined for all three NDVI months, even if one training column has no missing cells. Fail if any numeric training column is entirely missing. The forecast target column is explicitly excluded from all preprocessing and inference.
- Keep timing, mixed-cropland proxy definition, quality rules and fixed-boundary assumptions from the acquisition protocol. No future maps, current-year area/production, protein or aluminium features are introduced.

## Validation and reporting

Verify the import receipts, one-to-one keys, unchanged outcome labels, lag/reference arithmetic, complete fitting cohorts, finite observed inputs, nonnegative labels and all forecast/fitting cutoffs. Record training missingness and imputation medians, fitting MAE, evaluation MAE and numeric inputs outside the fitting range. A successful numerical check is not proof of predictive adequacy.

Random Forest point prediction does not require Gaussian predictors or normally distributed errors. It can still overfit, extrapolate poorly and fail when years/geographies differ. Report overall MAE, RMSE, R squared, mean bias, WAPE, year/district errors, scatterplots, residual patterns and vegetation availability. Any low-yield threshold counts are descriptive, not reliable disease/damage alerts.

For augmentation, compare full forest against history/weather forest and recent mean on the same rows. Report all six paired annual MAE differences. Resample the six entire years with replacement (10,000 draws, seed 42) to describe uncertainty in the average change. This assumes exchangeable years despite possible serial dependence; with six years its percentile interval is exploratory and cannot establish broad external validity. Do not use district-row resampling to pretend there are 180 independent seasons.

Save predictions, metric tables, diagnostics, figures and an input/code/environment/output checksum receipt separately from all earlier studies. Completed reruns verify receipts without fitting again. No existing dashboard model is replaced by this experiment. A results note records the actual finding after the run.
