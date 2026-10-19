# Regional rice yield forecasting rebuild

The main deliverable is an inference workflow: choose a historical district and agricultural year, forecast annual rice yield per hectare, inspect an approximate interval and compare against the subsequently recorded yield. The app opens this workflow by default. Earlier experiments are preserved in `src/rice_research_archive.py` and their original output directories.

## Research scope and motivation

Can early-monsoon climate improve annual district rice yield and low-yield-risk forecasts over recent-yield baselines? This is a regional administrative planning question, not an individual farmer diagnosis. Weather inputs are motivated by the district-level rice forecasting study of [De Clercq and Mahdi (2024)](https://arxiv.org/abs/2403.07967), which uses climate, vegetation and district yield data. This project builds its own smaller experiment; it does not reuse or claim that paper's reported scores. NDVI, molecular and aluminium predictors are not included without compatible district-year measurements.

ICRISAT supplies annual rice figures, not Kharif-only labels. Agricultural year Y corresponds to Y–Y+1; the source documentation establishes that 1966 means 1966–67 on PDF page 11 (printed page 6). The target is the source's administrative rice yield definition, not an asserted paddy grain measurement from a farm. Season mixing limits interpretation of weather associations.

## Sources and checks

Original source: [ICRISAT DLD, DOI 10.21421/D2/XFB1BZ](https://doi.org/10.21421/D2/XFB1BZ). Full citation and mandatory attribution are in the project README and accompany the derived table. The source catalogue and documentation PDF are preserved. The PDF's MD5 matches the provider's catalogue: `bc37f79834ea80bd1f6118e35cda7ebf`.

The DLD API returned 16,146 records, 1966–2017. Its APPORTIONED geography refers to historical districts; documentation describes reconstructing post-1966 district splits into parent units. The metadata prose contains inconsistent boundary-year wording, so the dated apportioned documentation controls this interpretation. Its description predates the last two API years. No current-boundary mapping is inferred from names.

Original area is thousands of hectares, production thousands of tonnes, yield kg/ha. Duplicate district-year keys are rejected; documented −1 sentinels and nonpositive area/production/yield cannot form valid targets. No upper-yield censoring, final-year outlier removal, or label correction occurs. The largest source-yield versus 1,000 × production/area discrepancy in the regional source is 15.47 kg/ha, reported without modifying labels. Rounded area/production can differ from published yield.

Scope is five states, with at least 14 positive yields and median rice area at least 10,000 ha in 1981–1997. This selects 50 districts independently of development, calibration and test performance. Modelling requires five complete lagged yields. The final table has 1,490 eligible district-years, 1987–2017. Earlier incomplete records remain in the original cache.

NASA POWER requests cover 1981–2017 at those 50 source representative coordinates. All required June–August months and units are checked; fill values are rejected. These are monthly mean daily maximum/minimum temperatures (C), mean daily rainfall (mm/day), and relative humidity (%). Rainfall is not a monthly total. No solar radiation, fabricated management values, surrogate protein scores or invented aluminium measurements are added.

A diagnostic against the existing geoBoundaries modern state polygons flags four source points: Balasore, Mayurbhanja, Bankura and Cooch Behar. Coastline/border precision and source errors are possible explanations; the screen is not historical centroid verification. Its source-boundary checksum and flags are in coordinate_screen.json. No coordinates or assessment rows were corrected or removed after evaluation. Source coordinates are not independently verified historical district centroids. Weather is a representative-point estimate without rice masks or district-wide aggregation. Reanalysis vintages are retrospective. These limitations prevent interpreting the weather comparison as a definitive test of weather's agronomic importance.

Raw government-data mirrors were inspected during source discovery, but the model uses the original provider API only. The paper's promised full code/data repository could not be located in the public material searched. The official data.gov.in page linked an APY CSV, but that endpoint timed out. Neither source was substituted silently for the downloaded DLD API records.

## Dated features and evaluation

Reference yield is the arithmetic mean of yields Y−2 through Y−6. The trend is the least-squares slope over those five years. Y−1 is excluded under an assumed two-year reporting delay; exact historical publication dates are not verified. Year, source coordinates and district/state indicators complete the historical feature block. Weather candidates add twelve June–August features. Target-year area and production only support source auditing and are never model features.

The seven declared candidates are recent mean, last available yield, extrapolated historical trend, History Ridge, Weather Ridge, Weather Random Forest and Weather histogram gradient boosting. Learned models predict kg/ha departures from the reference; forecasts are floored at zero. Training-only transformations encode geography and standardize numeric inputs. The protocol records fixed parameters and seed 42.

For each development year 1998–2005, fitting ends at Y−2. Pooled development MAE selects the model. History Ridge wins at 278.7 kg/ha, compared with 280.2 for Weather Ridge and 292.1 for the recent mean. No additional parameter search occurs. Before any model fitting, the draft protocol's fixed fit end was corrected from 2005 to 2004 so the earliest calibration year 2006 obeys the same availability assumption. The final protocol is hashed in selection.json.

The selected estimator is fitted through 2004 (840 records). Its 300 signed residuals from 2006–2011, divided by historical reference, calibrate an approximate 80% yield interval and an exploratory empirical probability below 80% of reference. Calibration does not choose the model. The local fitted artifact is saved before final assessment. The 2012–2017 assessment contains 300 records in 50 districts. Lagged yields for later forecast origins can include earlier assessment-year outcomes once two years have passed; the estimator itself remains frozen. This reflects sequential availability, not using future labels for training or selection.

## Results and limits

Selected History Ridge: MAE 449.95 kg/ha, RMSE 577.18, R squared 0.276, WAPE 19.95%. Recent mean: MAE 461.01, RMSE 584.12. Last available yield: MAE 444.36, RMSE 613.71. Historical trend: MAE 625.79, RMSE 852.45.

This is a modest RMSE improvement and mixed MAE result. The prototype serves yield estimation, but the evidence does not justify calling it highly accurate. Fixed fitting through 2004 is conservative and increasingly stale; a rolling-update policy would need separate documented evaluation, not retrospective tuning on these now-open results. Per-year R squared is negative in 2012 and 2014. Pooled R squared also reflects persistent regional differences.

Approximate 80% interval coverage is 80.67%, mean width 1,656.99 kg/ha. Coverage varies from 66% to 94% by year. The pooled residual distribution assumes a degree of transferability that is not established; these are empirical intervals, not formal guarantees.

Exploratory risk Brier is 0.09944 versus 0.10016 for development prevalence. ROC AUC is 0.394 and discrimination is poor. This tiny Brier difference does not establish useful early warning. The main screen withholds reliable-alert percentages; risk scores remain visible in the research evidence and CSV. They are not causal crop damage, disease diagnoses or money saved.

The application deliberately blocks years outside 2012–2017 for this artifact. It cannot produce a credible live 2026 forecast from an archive ending in 2017. Updated geographic-consistent yields, audited release dates, a frozen refresh policy and new-year validation are needed for current-season use. The current selected estimator does not need weather to make a point forecast, although the comparison table preserves the weather experiment.

## Reproduce and inspect

The sole app entry point is `python app.py`. Functional modules are imported, not alternative launchers. The dashboard downloads forecast results and inference templates without requiring targets or acreage. The selected history estimator accepts just district_id, year, yield_lag2, yield_lag3, yield_lag4, yield_lag5 and yield_lag6. It derives the historical mean, slope and geographic metadata automatically; weather is required only for a selected weather estimator. Historical input scenarios update the forecast.

The checked-in derived district table and small local model artifact support historical replay without network access. Raw API JSON and NASA caches stay local and are identified in source_manifest.json and weather_manifest.json. In a Python session with the project interpreter, call `acquire_source()`, `acquire_weather()` and `prepare()` from `src.rice_regional` to reconstruct inputs. Network access is needed only for missing original caches. Hash the reconstructed table against selection.json before assuming byte-identical reproduction; live sources may change.

`declare_protocol()` freezes the design; `run_study()` refuses to overwrite an existing selection or opened assessment. To reproduce fitting independently, use a separate checkout/output location while preserving the published outputs. Match the recorded scikit-learn 1.9.1 environment for the fitted model. Never load an uploaded pickle/joblib; the app checks its own local model checksum.

Verification performed: all 300 inference outputs reproduce saved predictions, intervals and probabilities; target/area/production perturbations have no effect; target-free inference works; all development fits obey the two-year cutoff; unknown geography, wrong state/coordinate combinations, inconsistent history summaries, impossible weather and out-of-period years are rejected. Streamlit AppTest verifies the default forecast screen, interactions and access to preserved research.
