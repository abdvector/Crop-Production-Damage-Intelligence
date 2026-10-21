# First rice baseline results

Evaluated 11 October 2026. Default forecast date: 60 days after recorded seeding.

## Finding

The weather-plus-genetics model fails to outperform a training-mean predictor at held-out locations. The low-yield classifier also fails to outperform training prevalence. This is a negative initial research result, not a validated operational model.

| Model | MAE (kg/ha) | RMSE (kg/ha) | Pooled R squared | Bias (kg/ha) |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 840.071 | 1036.542 | -0.164074 | -30.698 |
| Weather Ridge | 1040.772 | 1221.127 | -0.615581 | -224.405 |
| Genetics Ridge | 849.647 | 1051.024 | -0.196830 | -61.654 |
| Weather + genetics Ridge | 1044.488 | 1228.902 | -0.636219 | -228.267 |

Bias is predicted minus observed yield. Metrics pool all out-of-fold predictions and weight records equally. Negative R squared indicates error larger than the pooled observed-mean reference; the explicit training-mean comparison separately measures a feasible fold-specific baseline.

Low-yield logistic regression Brier score: **0.305809**. Training-prevalence Brier score: **0.167305**. Lower is better. These probabilities are not externally calibrated and do not estimate measured disease damage or causal yield loss.

## Data and target

The [Nguyen et al. rice panel](https://doi.org/10.1186/s12284-023-00623-6) supplies adjusted grain-yield targets and linked markers. Yield is converted from t/ha to kg/ha and retains the published 14% moisture basis. Ten conflicting genotype/environment target records are excluded by the key audit, leaving 1,046 records, 107 genotypes, 15 environments and 12 locations.

NASA POWER daily gridded estimates link to recorded trial coordinates and dates. These are estimates, not trial weather-station measurements. The archive contains later weather, but predictor construction excludes it.

## Forecast features

The default cutoff is a first-pass operational assumption, not a literature-established universal best date. Days 0 through 60 are included: 61 observations per environment. Every date must be present once, selected weather values must be nonmissing, and the cutoff must precede harvest.

Fourteen weather features summarise seven recorded variables over the first 30 days and remaining days through the cutoff. Precipitation is summed; other variables are averaged. Marker inputs are 882 binary allele indicators using published allele orientation, not resistance scores.

These regressions use additive predictors. They do not yet model explicit genotype-by-weather interactions, physiological growth stages, soil effects or protein variation. Flowering dates, harvest weather and source full-season covariates are not used as predictors.

## Evaluation

Leave-one-location-out validation groups by country and location. All seasons and genotypes at the held-out location are excluded from its training fold. There are 12 folds. The same genotype can occur at other training locations; this evaluates location transfer, not unseen-genotype transfer or strictly future years.

Ridge alpha is fixed at 100. StandardScaler is fitted inside each training fold. No hyperparameter tuning or model selection was performed using held-out outcomes.

The low-yield label is yield strictly below the corresponding training fold's 20th percentile. Thresholds therefore vary by fold. Logistic regression uses weather plus markers with fixed C=0.1 and max_iter=2000. Its comparator predicts the training fold's low-yield prevalence. No universal agronomic damage threshold is implied.

## Reproduction and checks

Launch `python app.py` with the project interpreter, keep the 60-day selection and choose Run verified-data benchmark. Results are saved under `data/processed/rice/baseline/day_60/`:

- `metrics.csv`: four regression comparisons.
- `location_metrics.csv`: 48 regression fold summaries.
- `held_out_predictions.csv`: 4,184 regression and 1,046 risk predictions with source-row references.
- `forecast_windows.csv`: 15 actual forecast windows.
- `summary.json`: dimensions, assumptions, limitations and SHA-256 hashes of the five processed input files.

The loader refuses archived results if an input hash no longer matches. The app does not persist a deployment model or support arbitrary new-area prediction.

Verification checked that each eligible source record is predicted exactly once per regression model, weather windows stop on the forecast date and precede harvest, all 15 windows contain 61 days, and the Streamlit dashboard starts without application exceptions. These checks do not prove model specification or visual quality.

## Interpretation and next research step

There are 15 distinct environmental weather profiles, not 1,046 independent weather histories. Environmental diversity, site/year confounding, adjusted targets and missing management measurements constrain learning. These failures do not uniquely diagnose the cause or prove weather is uninformative.

Next examine training-only feature support, site differences and a small set of predeclared interaction/regularisation candidates using nested location validation. Preserve an untouched external evaluation set where feasible. Additional models and variables require evidence, rather than promises of improved accuracy. Error metrics alone cannot prove absence of model misspecification.

Protein embeddings remain excluded until complete sequence alleles are verifiably linked to yield genotypes. CIRAD aluminium data remain a separate study. Reference proteins and averages from another population cannot fill these missing inputs.
