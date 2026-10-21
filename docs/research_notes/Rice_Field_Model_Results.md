# Rice field regression: first declared comparison

The first field-survey regression experiment is complete. Ridge alpha 1,000 was selected using only 2017–2018 development results. **Reliable temporal forecasting is not established.** The 2019 primary result is almost identical to the mean baseline, and a label-quality diagnostic also fails to improve on that baseline. This regression milestone fitted no classifier; the subsequent [2018 risk comparison](Rice_2018_Low_Yield_Risk.md) is a separate development experiment.

## Data and design

The previously declared cohort contains 17,836 records. Development uses 13,615 records from 2017–2018; the reserved 2019 assessment contains 4,221 records. The 21 numeric inputs are four early-season calendar-window summaries for temperature, radiation, humidity and rainfall, plus establishment day-of-year. Four categorical inputs describe state, district, reported variety and establishment method. Weather windows end at day 60. Fertiliser rates, irrigation totals, soil chemistry, proteins, harvest information, retrospective stresses and calendar year are excluded as predictors.

Five district-held-out development folds remove fitting rows sharing any weather source cell with assessment rows. The temporal development comparison fits 2017 and evaluates 2018. All transformations fit on the fitting split. Model selection minimises the declared equal-weight combination of geographic and temporal RMSE, each normalised by its global-mean baseline. The model configuration and selection were saved before 2019 assessment. A global mean or state mean could win; an ML model was not guaranteed to be selected.

## All development candidates

| Candidate | Geographic RMSE, kg/ha | 2018 RMSE, kg/ha | Selection objective |
| --- | ---: | ---: | ---: |
| Global mean | 1,367.4 | 1,537.9 | 1.0000 |
| State mean | 1,294.2 | 1,534.3 | 0.9721 |
| Ridge alpha 100 | 1,225.7 | 1,694.2 | 0.9990 |
| Ridge alpha 1,000 | 1,263.5 | 1,450.1 | 0.9335 |
| Random Forest, leaf 20 | 1,275.6 | 1,592.9 | 0.9843 |
| Random Forest, leaf 50 | 1,277.6 | 1,578.5 | 0.9804 |
| Gradient boosting, 15 leaves | 1,288.4 | 1,612.3 | 0.9953 |
| Gradient boosting, 31 leaves | 1,298.9 | 1,611.1 | 0.9988 |

Random Forest and histogram gradient boosting were both trained and evaluated. Neither won the declared development objective. Ridge 100 did better geographically but worse temporally than Ridge 1,000; the combined objective selected the stronger regularisation. Development superiority did not translate into meaningful 2019 accuracy.

## Primary 2019 assessment: original declared cohort

| Model | Records | MAE, kg/ha | RMSE, kg/ha | R squared | Bias, kg/ha |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global mean | 4,221 | 1,719.3 | 15,226.8 | -0.000488 | -336.3 |
| Selected Ridge | 4,221 | 1,721.3 | 15,224.4 | -0.000179 | -300.7 |
| State mean | 4,221 | 1,702.7 | 15,229.1 | -0.000796 | -438.0 |

The selected model's RMSE is only about 0.015% lower than the global mean; MAE is slightly worse. That is not a useful demonstrated forecasting gain. The descriptive district bootstrap gives an RMSE-gain interval of approximately -18.0 to +10.3 kg/ha; it spans no gain. This resampling does not establish independent or exchangeable districts and is not a calibrated prediction interval.

## Yield-label diagnostic: original predictions retained

The source audit flagged 13 yields above 15,000 kg/ha **before modelling**; all occur in 2019. The largest source-derived label is 400,000 kg/ha. Those 13 observations contribute about 99.1% of squared error. The original cohort deliberately retained review flags, so these results remain the primary assessment. The labels need source/unit verification; they are not repaired automatically.

To diagnose influence, retain the original trained models and predictions and calculate metrics on the 4,208 records without that pre-existing flag. No models are refitted and selection is unchanged.

| Model | Diagnostic MAE, kg/ha | Diagnostic RMSE, kg/ha | Diagnostic R squared |
| --- | ---: | ---: | ---: |
| Global mean | 1,074.8 | 1,418.7 | -0.051 |
| Selected Ridge | 1,077.1 | 1,447.8 | -0.095 |
| State mean | 1,057.9 | 1,412.1 | -0.041 |

This is a sensitivity diagnostic on an already opened assessment, not a replacement untouched test, a validated biological exclusion or an improved model. It shows that weak transfer remains even when the extreme labels are omitted. The pre-existing 15,000 threshold does not prove every flagged yield is wrong or every remaining yield is accurate.

## Interpretation and next work

The assessment includes 727 records in a state absent from development and 3,882 in new district labels. It therefore combines temporal and geographic transfer. State, district, seen/unseen-context and macro-district results are published alongside the aggregate results. The small Odisha assessment has only 26 records; estimates there are especially limited.

The findings support a reproducible negative-result benchmark, not a deployment or savings claim. Before improving the model, verify suspect yield units and obtain the survey questionnaire for management definitions. Further model changes must use development data for tuning and need an additional independent season/source for a new final assessment: 2019 is now opened and cannot be called an untouched test again. The original benchmark and this full assessment must remain available.

The subsequent [raw-source trace](Rice_Yield_Source_Trace.md) confirms all project conversions and traces the extremes to the publisher's stored quantities/areas. It does not confirm replacement values. The original assessment remains unchanged; 2017 quantity scope and some 2018 arithmetic differences also need source clarification.

The subsequent [2018 risk comparison](Rice_2018_Low_Yield_Risk.md) uses its own declared candidate/validation protocol, training-only 20th-percentile thresholds and prevalence baselines. No risk accuracy is inferred from these regression results. Adding protein/aluminium predictors still requires matched observations.

## Reproduction and checks

`src/rice_field_model.py` reads the frozen feature allowlist and candidate list, validates cohort/split hashes, performs development selection, saves the selection checkpoint, and only then fits the selected configuration and prespecified mean baselines for 2019. It refuses automatic reruns once assessment or selection files exist. This protects the opened test from silent reselection; it does not replace an independent external assessment.

Aggregate metrics, configuration, versions and hashes are published in `data/processed/rice/india_field_survey/model/`. Row-level predictions remain local and ignored by Git. There is no extra app launcher or temporary retained test script. No interactive field forecast or fitted deployment artifact is claimed. The application displays the saved assessment in the Indian field study tab.
