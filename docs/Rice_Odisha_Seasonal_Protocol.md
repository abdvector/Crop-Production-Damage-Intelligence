# Odisha Kharif rice study: protocol version 1

Declared 20 October 2026, before collecting the study weather, fitting any new model or reading start-year 2018–2022 numeric outcomes. One earlier NASA sample checked grid coordinates and units only. This is a prospective analysis plan for an already historical archive, not a registered clinical-style preregistration or a real-time data vintage.

## Question and geographic assumption

Can daily weather available by an end-of-August issue date improve district Kharif rice yield forecasts over recent-yield baselines in Odisha? The primary response is official DES yield in **kg/ha**, not acreage, total production, measured injury or causal damage. The secondary outcome is yield below 80% of the district's five-year reference.

Use all 30 Odisha source districts and the reviewed four name aliases. Fix spatial support to the pinned 2011 Census-derived DataMeet polygons. Major district reorganization preceded this study, but complete annual territorial equivalence is not certified. This is an explicit research assumption; neither the old geography audit nor its unverified flags is overwritten. Interpret results conditionally on that assumption. No claim of transfer to unseen districts, other crops or individual farms follows.

DES has 600 positive complete Odisha district-years for 1998–2017. The 30 records for 1997 have no positive complete triplets and supply no history. Do not fabricate them. After requiring Y−2 through Y−6 histories, the first possible model year is 2004. There are at most 420 development modelling rows for 2004–2017, in only 14 year clusters. District rows are not independent annual replications.

## Timing and inputs

Issue date: **31 August of agricultural start year Y**. Daily observation window: **1 June–24 August**, inclusive, in NASA local solar time. The seven-day buffer follows NASA's reported typical meteorology/solar delays, but does not prove actual historical publication availability. Current revised archives yield a retrospective timing-constrained evaluation.

ICAR-CRIDA's Khurda contingency plan, section 1.12, gives June–July Kharif paddy sowing for both rainfed and irrigated systems. This supports a broad early-season calendar choice, not verified district/year planting or flowering dates. Do not label fixed calendar windows as observed growth stages. August forecasts cannot observe later cyclones, floods, heat or management.

Use NASA POWER daily maximum/minimum temperature (C), precipitation (mm/day), relative humidity (%) and shortwave solar energy (MJ/m2/day). Retain provider-native grids, inspecting actual response coordinates separately for each parameter. Intersect rectangular grid footprints with district reference polygons and weight by polygon area in a spherical cylindrical equal-area projection. These are **whole-district area weights**, not rice-area or field weights. Coarse reanalysis is not a weather station measurement. Record all contributing cells and weights. Require complete coverage and valid daily values; do not silently fill or renormalize around missing cells.

Before fitting, reduce weighted daily series to 19 fixed predictors: June, July and 1–24 August rainfall totals, mean Tmax, mean Tmin, mean humidity and mean solar energy (15); whole-window longest spell of district-mean rain below 1 mm/day, number of days at least 1 mm/day, maximum rolling five-day rainfall, and 95th percentile Tmax (4). These are descriptive weather summaries, not measured drought/flood damage or a rice sterility threshold. No test-driven threshold search.

History predictors: Y−2…Y−6 yields, their mean and linear trend, agricultural start year, and district identity. A two-year reporting delay is assumed, not verified from historical DES releases. Never use current-year production/area, Y−1 yield, current-year target, post-cutoff weather, observed future phenology, target-derived district encodings or full-period normalizations as predictors. Current-year production/area stay audit-only. No protein, measured aluminium, soil, irrigation, fertilizer, satellite or cultivar-adoption input is claimed without a compatible dated linkage.

## Frozen comparisons and temporal evaluation

1. Development validation years **2010–2014**, with expanding training years 2004…Y−2. All preprocessing fits within each training fold. Compare equal-year mean MAE; ties break by RMSE then the candidate order below. Keep the same complete rows for all candidates. Publish missingness and exclusions rather than replacing bad observations with synthetic data.
2. Fixed candidate order: five-yield mean; last available yield; linear extrapolation of the five past yields (clipped at zero); history Ridge with alpha 1, 10, 100; history-plus-weather Ridge with alpha 1, 10, 100; history-plus-weather Random Forest (300 trees, min_samples_leaf 10, max_depth 4 then 8, random_state 42); history-plus-weather histogram gradient boosting (learning_rate .05, max_iter 150, max_leaf_nodes 7, min_samples_leaf 15, l2_regularization 1 then 10, random_state 42). Ridge scales numeric inputs and one-hot encodes districts; tree inputs use a fixed district encoding. Predict departures from the history mean and add that reference back. Clip final yields at zero. No wider tuning without a new documented exploratory study.
3. Choose once from development only. Generate rolling predictions for **2015–2017** using training through Y−2. Use their absolute errors divided by the history reference to calibrate an approximate 80% interval. Use the finite-sample quantile at ceil((n+1)*.8), capped at n. Lower bounds clip at zero. Report empirical coverage/width; dependent district/year observations and refitting invalidate distribution-free coverage claims.
4. Only after code, feature set, configuration selection and calibration are frozen, unlock **2018–2022** for final assessment. Predeclare sequential annual refitting through Y−2: a 2020 forecast may use 2018 labels, never 2019/2020 labels. These previously assessed outcomes may enter later fitting under this fixed rule but never tune configuration, variables or thresholds. Report this as sequential temporal assessment, not an untouched fixed-estimator holdout. If newer labels are unusable, report exclusions without changing the design to chase better scores.
5. Primary metric: equal-year mean MAE in kg/ha. Also report pooled MAE, RMSE, R squared, WAPE, baseline skill, yearly and district breakdowns, interval coverage and width. Compare paired errors with year-cluster bootstrap seed 42, 2,000 resamples; only five assessment years give weak uncertainty resolution. No performance superiority claim based on row-level p-values. Secondary low-yield classification: threshold the point forecast at 80% of its past-yield reference and report precision, recall, F1 and confusion counts; do not present uncalibrated risk probabilities. Report absence of either class explicitly.

## Data integrity and release

Save immutable protocol content and its SHA256 before bulk acquisition. Pin prepared labels, crosswalk and GeoJSON hashes. Cache raw responses locally with requested dates, URL, SHA256, units, fill value, sources and API version; record failure and resume without replacing successful caches silently. Acquisition may include intervening off-season days when requesting multi-year blocks, but derived data may use only each year's declared window. Weather acquisition does not read reserved yield cells.

The existing annual forecast/model, trial analyses and molecular experiments remain unchanged. Do not promote a new estimator to the main dashboard until its declared temporal comparison is complete. If results are weak, retain that finding. The main claim to test is incremental weather value, not a promised accuracy gain or proof of correct model specification.

## Sources

- [Official DES query](https://www.data.desagri.gov.in/website/apy-query-report-web), acquired and unit-checked in the [source audit](Rice_Official_Kharif_Source.md).
- [Odisha reference geography and documented limitations](Rice_Seasonal_Geography.md), with [state district register](https://odisha.gov.in/en/about-us/districts) and [Bargarh's reorganization history](https://bargarh.odisha.gov.in/en/about-district/about-us).
- [ICAR-CRIDA Khurda contingency plan, section 1.12](https://www.icar-crida.res.in/CP/Orissa/OUAT,%20Bhubaneswar/Orissa%2029-%20Khurdha%2004.10.2011.pdf).
- [NASA daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [native resolutions](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/) and [typical availability delays](https://power.larc.nasa.gov/docs/faqs/data/).
- Map attribution: DataMeet Community Maps Project, https://projects.datameet.org/maps/, CC BY 2.5 India, https://creativecommons.org/licenses/by/2.5/in/.
