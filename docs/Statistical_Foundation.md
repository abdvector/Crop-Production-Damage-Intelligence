# Statistical foundation and revised analysis plan

Status: development-data foundation rebuilt on 21 October 2026. No new forecasting model has been fitted or selected. Original datasets, protocols, forecasts and models remain intact. New work lives in `data/processed/rice/foundation/` and `src/rice_foundation.py`. Rebuild it using `python app.py --audit-data`; launch the interface using `python app.py`.

## Scope and unit of observation

Main question: does early-season weather improve Odisha Kharif rice yield forecasts beyond historical yields? One observation is a district and agricultural start year. Y is official harvested yield in kg/ha, not acreage, measured injury or causal economic damage. Low yield is a secondary outcome defined against past yield; it must not be described as measured aluminium or disease damage.

The main study uses 30 districts, DES Kharif yield labels and NASA POWER daily weather, with fixed 2011 Census-derived DataMeet reference geography. The 600 development observations cover 1998–2017. Five yield histories Y−2…Y−6 leave 420 complete feature rows in 2004–2017. Earlier records are history sources, not incomplete records to impute. Annual five-state rice, farm surveys, breeding trials, proteins and aluminium experiments remain separate; their units and linkage do not support pooling into these district rows.

The 2018–2022 outcomes were already inspected in the earlier experiment. No code change, new split, or new name can make them unseen again. They may be used only as explicitly exploratory reanalysis for revised models. Independent confirmation requires genuinely new, compatible outcomes or a prospective evaluation. New data are not required to present the existing research honestly.

## Cleaning and integrity

The audit verifies original preparation hashes, unique district-year keys, 30 complete district histories, finite nonnegative development yields, source unit conversion, production/area consistency within 5.01 kg/ha, all historical lag lookups and exact reference/trend calculations. It checks complete predictor values in the eligible cohort, rain/humidity ranges, weather-day bounds and temperature ordering. The retained preparation receipts separately verify daily dates, provider units/fill values, native grids, contributing-cell physical ranges, valid polygons and spatial weights.

No synthetic observations, target imputation, silent join duplication or outlier clipping is allowed. Pooled 1.5-IQR flags are exported for source review and retained: an unusual yield may represent a real crop failure or a distinct district. This screening is not an independent sample significance test. Missingness, variable summaries and full Spearman predictor correlations are exported. Any later exclusion needs a measurement-based reason, stage, original value and sensitivity analysis; never remove a record because its prediction error is large.

## Predictor definition

The proposed numeric X has 25 columns: five historical yields, start year and 19 weather summaries. District code is a categorical variable, never an ordinal number. Y, current-year production and area are excluded. Source names are labels, not predictors. Historical mean/trend are exact combinations of the five lags: removed from proposed X, retained for baseline computation. The new numeric design has rank 25/25 and a standardized condition number around 35; this is descriptive, not proof of stable coefficients or optimal features. District one-hot encoding must drop a reference category when combined with an intercept to avoid an additional exact dependency.

| Variables | Units and definition |
|---|---|
| yield_lag2…yield_lag6 | kg/ha, exact district yields two through six start years earlier |
| agricultural_start_year | Calendar year; no target information |
| T2M_MAX_06/07/08 | Mean daily maximum temperature, Celsius |
| T2M_MIN_06/07/08 | Mean daily minimum temperature, Celsius |
| PRECTOTCORR_06/07/08 | Total rainfall, mm |
| RH2M_06/07/08 | Mean daily relative humidity, percent |
| ALLSKY_SFC_SW_DWN_06/07/08 | Mean daily shortwave solar energy, MJ/m²/day |
| longest_dry_spell_days | Maximum consecutive days with district-mean rain <1 mm/day |
| wet_days | Count of days with district-mean rain ≥1 mm/day |
| max_five_day_rain_mm | Largest consecutive five-day rainfall total |
| tmax_p95_c | 95th percentile of daily maximum temperatures, Celsius |

06 and 07 mean full June and July; 08 is 1–24 August. There are 85 observed days before an assumed 31 August issue date. These are calendar windows, not observed crop growth stages. Weather is whole-district area-weighted gridded estimation, not field station data or rice-area-weighted exposure. Reporting delays and historical release vintages remain assumptions.

## Four data figures

All figures use development observations only, not final assessment labels. PNG previews and vector SVG exports are reproducible. The UI Data & methods section shows one selected figure at a time.

1. Coverage heatmap: checks which district-years have labels; this does not certify temporal boundaries or availability vintages.
2. Annual district median and interquartile band: shows time variation and district spread. The band is not a confidence interval; the median is not an area-weighted state yield.
3. District boxplots: 20 years each, ordered by median. Outlying points remain in the dataset. Geographic differences can reflect many unmeasured factors.
4. Weather correlation heatmap: a readable representative subset; the full numeric matrix is also exported. Pooled rank correlation describes redundancy, not a causal relationship or independent significance.

## Model-specific checks, not a universal checklist of p-values

Ridge is a penalised linear predictor. Normal predictors are not required. Neither a Shapiro test nor normal errors are prerequisites for computing its point predictions. Assess functional form, forecast bias, error dependence, changing variance, stability and out-of-time error. Its coefficients are penalised associations, not causal effects; ordinary OLS coefficient p-values are inappropriate. With the original redundant history summaries, VIF would be infinite by construction; documenting and removing that redundancy is more informative than treating it as a test to pass.

Random Forest and histogram boosting do not require linearity, normality or equal error variance. They still need controlled complexity, temporal validation, adequate support, matched comparisons, error diagnostics and outlier sensitivity. Tree models can generalise poorly outside the training range.

The audit examines 210 existing selected-model forecasts from selection years 2009–2012 and calibration years 2014–2016. Errors are prediction minus observed, not fitted OLS residuals. It exports bias by year, residual-versus-prediction and absolute-error plots, a normal Q–Q plot, consecutive-year error association within districts, and annual descriptive Moran I. Spatial weights are a symmetric four-nearest-centroid graph using approximate locally scaled longitude/latitude distances. This graph is a declared diagnostic choice, not an adjacency or agronomic exposure model. Moran values are descriptive; no exchangeability-based p-values are asserted.

Observed pooled legacy mean error is approximately −284 kg/ha; consecutive-year error correlation is approximately 0.283. These flag underprediction and temporal structure for investigation, not a complete inferential conclusion. Error magnitude also varies with predicted yield (pooled Spearman approximately −0.308). Selected validation errors have selection optimism; calibration errors were used to construct intervals. Neither is an independent final performance test.

Do not concatenate districts into one artificial time series and run Durbin–Watson or Ljung–Box. Do not apply iid Breusch–Pagan, Shapiro or coefficient tests to pooled dependent forecast errors and claim assumptions passed. Spatial/year dependence, very short per-district sequences and model selection require appropriate interpretation. Revised-model diagnostics and, if inferential claims are needed, justified panel/dependence-aware inference must be assessed after fitting. No stationarity test mechanically licenses Ridge; examine trends, shifts and extrapolation, and compare time-aware performance.

## Frozen rules for the next modelling phase

This plan is written after seeing the legacy results. It governs exploratory redevelopment, not a retroactive preregistration. No further model fitting happens in the foundation build.

- Preserve three transparent baselines: recent five-yield mean, latest available yield and historical trend. Reference statistics are calculated only from available past labels.
- Compare history-only and history-plus-weather versions of **each** model family: Ridge, Random Forest and histogram boosting. This matched design separates weather benefit from changing the algorithm. Use a small declared grid, fixed seeds and the same cohort. Standardise numeric inputs only for Ridge and encode district as categorical inside each fold. Avoid automatic stepwise p-value selection.
- Proposed grid: Ridge alpha 1/10/100; Random Forest 300 trees, minimum leaf 10, maximum depth 4/8; histogram boosting learning rate 0.05, 150 iterations, maximum leaves 7, minimum leaf 15, L2 1/10, no random early stopping. Use seed 42, two threads, both predictor blocks for every configuration: 14 learned configurations plus three baselines. Fit deviations from the past-yield reference, add the reference back and clip predictions at zero. This is a computationally bounded comparison, not an exhaustive search. Any later change must be versioned before running the revised comparison.
- For exploratory nested rolling evaluation, outer years are 2012–2017; fit only through outer Y−2. Inner validation years run from 2008 to outer Y−2, each with fitting through inner Y−2 and a start in 2004. Inner folds select hyperparameters and optional feature blocks. Outer outcomes never tune that fold. This tests future years in known districts, not transfer to unseen locations. Only six outer years mean uncertainty remains substantial; earlier use of this archive prevents calling it an untouched external test.
- Fix primary selection to equal-year MAE, then RMSE and declared candidate order. Report RMSE, bias, WAPE, R², district/year errors and errors relative to every baseline. Compare whole weather blocks first; if testing individual subsets or nonlinear transformations, declare them and select within inner folds. Correlation plots over the full development period are descriptive, not globally fitted feature selectors for earlier folds.
- Compare weather-block ablation, deduplicated versus legacy history representation, influential-record sensitivity without automatic deletion, and limited declared timing sensitivities. Freeze sensitivity definitions before the next run. Keep primary and exploratory conclusions separate and disclose all comparisons.
- Plot out-of-time errors against forecasts, main inputs and year; examine within-district consecutive-year dependence and annual spatial patterns. Quantify year/district error variation and performance across yield ranges. Do not claim tests establish no misspecification or validate a causal interpretation.
- Compare model errors using paired year-level summaries; show individual-year differences. Bootstrap intervals over very few years are exploratory, with weak resolution and assumptions about dependence between years. Do not replace these with pooled row-level significance. Limit superiority claims accordingly.
- Uncertainty calibration must use only earlier labels available at each issue date and stay separate from hyperparameter selection and evaluation. Report interval width, coverage by year/district and an interval score; dependence and changing conditions prevent automatic distribution-free coverage guarantees. Do not manufacture narrow intervals to look useful.
- Low-yield flags retain the prespecified 80%-of-history definition. Report event count, confusion matrix, precision/recall and class imbalance. Do not call point thresholds calibrated probabilities; probability modelling requires a separate declared calibration/evaluation plan.
- Before confirmation, freeze exact code, feature definitions, parameters, preprocessing, timing and metrics; seek compatible unseen years or prospective outcomes. If unavailable, publish the work as exploratory historical research with explicit limitations.

## Readiness

The foundation is ready for controlled exploratory modelling. It is not a declaration that all assumptions are satisfied or that the old model is reliable. Geography, historical data vintages, genuine independent confirmation, model-specific post-fit diagnostics and operational usefulness remain separate questions. Do not reset the existing 2018–2022 holdout label to “unseen”.

Method references: [scikit-learn leakage and preprocessing guidance](https://scikit-learn.org/stable/common_pitfalls.html), [time-aware validation](https://scikit-learn.org/stable/modules/cross_validation.html), [Ridge and regularisation](https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification), and [Forecasting: Principles and Practice, diagnostics and evaluation](https://otexts.com/fpp3/toolbox.html).
