# Odisha protocol: timing amendment before modelling

Declared 20 October 2026 during weather acquisition, before any new model fitting, configuration selection, calibration or access to reserved numeric yields. This amendment supersedes the evaluation-year assignments in [version 1](Rice_Odisha_Seasonal_Protocol.md). All other choices, including weather dates, geography, predictors, algorithms, grids and metrics, remain unchanged. The original JSON declaration is retained as `protocol_v1.json`.

Version 1 applied the assumed two-year reporting delay to fitting rows and yield-history features but failed to apply it consistently to configuration-selection labels and interval-calibration labels. Selecting with 2014 outcomes would be too late for a 2015 calibration forecast; calibrating with 2017 outcomes would be too late for the first 2018 assessment forecast. Those assignments are withdrawn before running them.

The corrected assignments are:

| Purpose | Agricultural start years | Information constraint |
| --- | --- | --- |
| Initial eligible fitting rows | 2004 onward | Five histories Y−2 through Y−6 |
| Expanding validation for configuration selection | **2009–2012** | Each year's fit ends at Y−2; latest selection label 2012 is assumed available in 2014 |
| First timing gap | **2013** | Not a selection or calibration target; may enter later fitting when two years old |
| Rolling uncertainty calibration | **2014–2016** | Configuration selected using labels through 2012; each fit ends at Y−2 |
| Second timing gap | **2017** | Not an interval-calibration target; may enter assessment fitting from 2019 |
| Sequential final assessment | **2018–2022** | Interval calibration ends at 2016, assumed available for first issue in 2018; each fit ends at Y−2 |

The four selection years have 120 development validation rows. The three calibration years have 90 rows but only three year clusters. The first validation forecast trains on 2004–2007, or 120 rows; the last trains on 2004–2010, or 210 rows. Fitting for assessment starts with 390 rows through 2016, if all declared inputs are valid. These are counts implied by known development coverage, not observed assessment performance. Previously reported 420 rows for 2004–2017 remains the size of the complete development modelling pool, not the number of independent years or a single training fold.

This corrects internal timing consistency under an **assumed** two-year publication delay. It does not verify historical DES release dates. Calibration coverage remains empirical, with dependence, few years and rolling refits preventing a distribution-free guarantee. No metrics or results have been used to choose these corrected dates.
