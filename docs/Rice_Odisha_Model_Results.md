# Odisha Kharif rice: completed temporal comparison

The declared comparison is complete. Development selected **History Ridge, alpha 10**, before the 2018–2022 outcomes were opened. On those later years, its MAE is **516.8 kg/ha** and RMSE is **634.6 kg/ha**. It improves average error over the two simple history baselines, but the gain is uncertain across five years. Negative R squared, weak low-yield detection and very wide intervals limit practical forecasting claims.

## Data and execution

- Official DES Kharif rice yields: 30 Odisha districts, 600 development district-years for 1998–2017 and 150 assessment district-years for 2018–2022. All 150 newer labels pass the previously declared area, nonnegative-value and rounding checks. No assessment rows are excluded. The largest source yield versus production/area difference is 4.972 kg/ha, within the declared 5.01 tolerance.
- NASA daily weather: 500 checked responses, reduced to 63,750 district-day estimates and 19 fixed weather summaries per district-year. Weather ends on 24 August for a 31 August issue date. Whole-district area weights use fixed 2011 reference polygons; annual territorial equivalence and rice-area weighting are not established.
- Predictors: Y−2…Y−6 yields, their reference mean and trend, year, district and, for weather candidates, the 19 summaries. Current-year area/production are audit fields only. No protein, aluminium, soil or management measurements are claimed as district predictors.
- Selection: 13 configurations, four expanding validation years 2009–2012 and 120 common validation rows per configuration. All transforms use fitting rows only. Development-selected MAE is 442.7 kg/ha, versus 466.6 for the recent mean. Weather candidates did not win selection.
- Calibration: 90 rolling predictions for 2014–2016, with selection fixed. The 73rd ordered relative absolute error gives a relative half-width of 1.10994 times the historical reference. Outcomes, selection, code, inputs, runtime and calibration were pinned before assessment access.
- Assessment: five sequential forecasts per district for 2018–2022, each fitted through Y−2. Fitting counts rise from 390 rows in 2018 to 510 in 2022. Earlier assessment labels enter later fitting only under that fixed two-year-delay rule. This is not a fixed-estimator untouched holdout or a verified real-time data-vintage backtest.

## Later-year results

With 30 records in every assessment year, equal-year and pooled MAE coincide. All configurations are reported; this table does not choose a new winner.

| Configuration | MAE kg/ha | RMSE kg/ha | R squared |
| --- | ---: | ---: | ---: |
| Recent mean | 577.7 | 682.0 | -0.213 |
| Last available yield | 561.1 | 748.0 | -0.459 |
| Historical trend | 720.6 | 966.1 | -1.433 |
| History Ridge, alpha 1 | 599.8 | 723.8 | -0.366 |
| **History Ridge, alpha 10: selected in development** | **516.8** | **634.6** | **-0.050** |
| History Ridge, alpha 100 | 484.3 | 593.8 | 0.081 |
| Weather Ridge, alpha 1 | 659.7 | 779.8 | -0.585 |
| Weather Ridge, alpha 10 | 564.5 | 674.8 | -0.187 |
| Weather Ridge, alpha 100 | 496.0 | 597.0 | 0.071 |
| Weather Random Forest, depth 4 | 405.3 | 535.7 | 0.252 |
| Weather Random Forest, depth 8 | 405.9 | 536.1 | 0.251 |
| Weather histogram boosting, L2 1 | 450.4 | 559.5 | 0.184 |
| Weather histogram boosting, L2 10 | 450.8 | 555.2 | 0.197 |

The selected model's WAPE is **20.94%**, and mean bias is **−362.3 kg/ha**, indicating underprediction on these records. Negative R squared means its squared errors exceed those of a constant equal to the assessment-set mean; that mean would not itself be known to a forecaster at issue time.

The selected model reduces MAE by 60.9 kg/ha against the recent mean and 44.2 against last available yield. Year-cluster bootstrap 95% ranges are **−27.1 to 154.0** and **−27.0 to 132.6 kg/ha**, respectively. Both cross zero. Five assessment years provide limited uncertainty resolution; these are descriptive comparisons, not proof of broad superiority or correct model specification.

The development-chosen weather Ridge control improves assessment MAE by 20.8 kg/ha against the development-chosen history Ridge, with a year-bootstrap range of **−68.7 to 118.2**. This does not establish a reliable weather benefit. Random Forest's 405.3 kg/ha result is a promising secondary observation, but it was not selected in development. Promoting it after inspecting assessment would reuse those outcomes for selection. Its comparison against a history Ridge also changes both the algorithm and inputs, so it does not isolate weather's effect. A fresh future-period assessment and matched history-only tree controls are needed for that claim; they are not quietly added to this completed experiment.

## Uncertainty and low-yield findings

The approximate 80% interval covers **100%** of assessment outcomes, with mean width **4,256 kg/ha**. That width is too large to support a high-precision claim. Coverage alone is not evidence of useful uncertainty: the calibration period contained large normalized errors, and rolling refits, few years and dependence prevent a distribution-free guarantee. The interval was not narrowed after seeing assessment.

Low yield means observed yield below 80% of the five-past-yield reference. There are **nine** such observations. Thresholding the selected point forecast flags seven records: **2 true positives, 5 false positives, 7 false negatives and 136 true negatives**. Precision is **28.6%**, recall **22.2%**, and F1 **0.25**. These flags are weak; no calibrated risk probability or measured damage diagnosis is supplied.

## What can be presented

This project provides a real-data, season-specific forecasting pipeline, documented source units and geography assumptions, daily weather integration, tree and linear comparisons, explicit timing controls, later-year results and negative findings. The evidence does not support claims of proven financial savings, reliable injury detection, protein-driven district forecasting, universal transfer or operational current-season accuracy.

The original annual model and earlier molecular/field experiments are preserved. The app's **Odisha Kharif study** workspace exposes this separate historical replay, performance tables, source exclusions, input summaries and downloads. `app.py` remains the sole launcher.

Reproduce in the recorded project environment by importing `run_development` and `run_assessment` from `src.rice_odisha_model`, running development first. Completed runs verify their frozen receipts instead of selecting again. New source or code versions require a separately documented study; the completed assessment is no longer uninspected data.

See the [original design](Rice_Odisha_Seasonal_Protocol.md), [timing amendment](Rice_Odisha_Timing_Amendment.md), [implementation rules](Rice_Odisha_Model_Implementation.md), and [machine-readable outputs](../data/processed/rice/odisha_seasonal/model/summary.json).
