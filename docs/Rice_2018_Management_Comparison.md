# 2018 management comparison

Completed 19 October 2026. The documented 2018 management inputs provide a **modest improvement in development validation**, strongest for the fixed Ridge model. This experiment does not evaluate a new season, repair 2019 yield labels or establish reliable deployment accuracy. Earlier results remain unchanged.

## Inputs and cohort

The 2018 form documents fertiliser product kilograms per plot and application days after field sowing/transplanting. Features cover five named products with all three top-dressing events available: urea, DAP, MoP, SSP and zinc sulphate. Each product contributes basal kg/ha and cumulative product kg/ha through day 60. These ten fields describe product mass, not total N/P/K supply. Mixture grades, other fertilisers and nutrient composition are not represented; an absence of these predictors must not be interpreted as zero nutrient supply.

Plot acres are converted using 0.40468564224 hectares per acre. The area screen requires a positive conversion factor and positive stored plot acres agreeing with local plot size divided by the factor, within 1% and 0.001 acre. This is an arithmetic screen, not independently measured area validation. It differs from the publisher's approximate 0.4 factor and is documented rather than silently changing the source target labels.

Positive quantities require a compatible product-selection response. A zero is accepted only with an explicit compatible non-use/other-product response; blank selections and selected-product zero amounts remain unknown. Undated positive applications and negative/contradictory amounts are not converted to zeros. An event dated after day 60 contributes nothing to the early sum. A cumulative sum is missing if any necessary component is unknown; partial sums are not treated as complete doses. No application date is guessed. Known future event quantities cannot change an early dose feature.

Of 7,443 publisher source rows, 5,012 have complete management fields and 4,810 also pass area arithmetic. Intersecting the already established rice/state/weather cohort leaves **4,801 records across 45 district labels**. Thus 2,631 of the 7,432 eligible primary 2018 records are omitted for area or management completeness. The same 4,801 records are used for every baseline and input block. Complete-report selection may bias the study population; results should not be extrapolated to all surveyed farms.

## Declared design

`management_2018/protocol.json` was saved before model fitting, with input lists, feature hash, seed, fixed models and split rules. The three fixed models are Ridge alpha 1,000, Random Forest with 200 trees/minimum leaf 50, and histogram gradient boosting with 15 leaves. No hyperparameter search or winner-based final-test claim is made. This is a development sensitivity after earlier 2018 results had already been inspected, not a new untouched assessment.

Three matched input blocks are compared:

1. Weather through day 60, planting timing/method, variety labels and state/district context.
2. The same inputs plus reported soil texture and plot-level irrigation availability.
3. The same static-context inputs plus ten timed product-mass fields.

All blocks use the same district fold assignments and shared-weather-cell purge. Fitting sizes are 2,380–2,973, validation sizes 851–1,031 per fold. No retained fitting row shares a district label or any parameter's weather source cell with validation. Encoders, numeric imputation and scaling fit on each training split only. Management fields in the primary cohort are complete; missingness indicators from future survey events are not added as predictors. The retrospective reconstruction and completeness selection still limit claims about prospective availability.

## Results on the matched cohort

| Model | Weather/planting RMSE | Plus static context RMSE | Plus static and timed products RMSE | Final MAE | Final R squared |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ridge alpha 1,000 | 1,391.7 | 1,384.4 | 1,357.7 | 1,075.2 | 0.172 |
| Random Forest, leaf 50 | 1,475.6 | 1,483.9 | 1,462.4 | 1,116.2 | 0.040 |
| Gradient boosting, 15 leaves | 1,477.0 | 1,452.0 | 1,452.0 | 1,108.7 | 0.053 |

All errors are kg/ha. The global training-mean baseline has RMSE 1,530.1 and MAE 1,195.2; the state-mean baseline has RMSE 1,415.7 and MAE 1,098.4. These baselines are refitted separately inside each training fold.

Ridge's complete augmentation reduces RMSE by **34.0 kg/ha (2.44%)** relative to its weather/planting block. Static context contributes 7.3 kg/ha; timed products contribute another **26.7 kg/ha (1.93%)** relative to static context. The fully augmented Ridge has about 4.1% lower RMSE than the state mean and 11.3% lower RMSE than the global mean on this same development cohort. The small gain must be considered alongside the remaining error and limited transfer evidence.

Adding all context lowers RMSE in four of five folds for each model. Ridge's descriptive paired district-bootstrap gain interval is approximately 17.6–49.7 kg/ha for all additions and 10.3–42.0 for timed products beyond static context. These resampling ranges are not a formal spatially valid significance test: district independence/exchangeability is not established. Random Forest and boosting ranges span no improvement. Boosting's incremental product RMSE gain beyond static context is effectively zero, despite a lower MAE.

The experiment therefore supports a limited predictive contribution of the reconstructed management block for this cohort and Ridge configuration. It does not establish a causal fertiliser effect, a universal benefit across models, a monetary saving or reliable future-year skill. State results, fold results and paired changes are published so pooled gains can be inspected for heterogeneity.

## Reproduction and verification

`src/rice_field_management.py` prepares features from the publisher's `data` R object, declares the experiment, runs the fixed comparisons and produces aggregate diagnostics. It does not introduce another app launcher. Original records, features and predictions stay local; aggregate protocol, audits and metrics are published. The temporary R reader is removed after use.

Checks cover boundary days 60/61, missing/contradictory selections, future-quantity invariance, one-to-one record mapping, identical cohorts/folds across blocks, district/weather separation, source hashes, independently reproduced metrics and preservation of the earlier selection/assessment files. The app shows these findings in the Indian field study tab.

The next verification need is an independent year/source with matched management definitions and checked yield labels. The existing 2019 assessment is already opened and its suspect labels remain unresolved. No 2017/2019 management definitions or corrected yields were inferred for this experiment.
