# Free rice-study replication: feasibility check

Checked 22 October 2026. **The shared sample is usable for learning the method; it is not sufficient to reproduce the full paper or establish an August-issued forecast. No new model was fitted or substituted into the app.**

Reference: Bowden, C., Foster, T. and Parkes, B. (2023), *Identifying links between monsoon variability and rice production in India through machine learning*, Scientific Reports 13, 2446. [Open article](https://doi.org/10.1038/s41598-023-27752-8). Full article methods were read through the Europe PMC open-access XML service for PMC9918484 when the publisher redirected to its identity service.

## What was actually obtained and checked

The author's Figshare releases provide [R code v3](https://doi.org/10.6084/m9.figshare.21371625.v3) and [sample data v1](https://doi.org/10.6084/m9.figshare.21395373.v1), both CC BY 4.0. Original downloads and metadata are preserved in `data/raw/rice/bowden_2023/`, with publisher MD5 verification and local SHA256 receipts. The R script is external reference material, not an application launcher; it was read, not executed.

The R sample was parsed into a standard dataframe. Its 355 rows cover 71 historical district references across Bihar, Haryana, Punjab and Uttar Pradesh in 1980–1984. It has 27 columns, unique state/district/year keys and no missing cells. A readable conversion is saved at `data/processed/rice/bowden_2023/sample_data.csv`; `inspection.json` records the checks and source/output hashes. The temporary inspection packages were removed, leaving no new application dependency.

Example first record: Bhagalpur, Bihar, 1980; rice yield 1170.89 kg/ha; seasonal rainfall about 1034.29 mm; irrigated rice proportion 0.23046. These are real entries from the author's processed sample, not newly acquired field measurements or synthetic data.

## What the supplied model does

The target is the relative detrended yield anomaly, `dt_norm_rice_yield_kgha`. For every sample row, the stored target matches `(yield - LOWESS trend) / LOWESS trend`. The trend and anomaly are already present in the shared input. The R script does not reconstruct the raw weather aggregation and detrending pipeline.

The nine actual predictors in the script are:

| Source variable | Meaning |
| --- | --- |
| `mean_tmin` | Seasonal mean daily minimum temperature |
| `mean_tmax` | Seasonal mean daily maximum temperature |
| `agdd` | Accumulated growing degree days |
| `dswrf_sum` | Seasonal downwelling shortwave radiation sum |
| `total_p` | Seasonal total precipitation |
| `rainy_prop` | Proportion of rainy days |
| `onset_allYears_dev` | Monsoon onset deviation from the district's all-year average |
| `rice_irri_prop` | Irrigated share of rice area |
| `season_length` | Monsoon season length |

The R script contains a random 75% split and ordinary fold resampling for tuning, an interactive tree-count choice, and then 100 Random Forest runs with different seeds. Its final example uses 500 trees and mtry 3. It reports out-of-bag errors, permutation importance and accumulated local effect plots. It does not contain our required later-year chronological forecasting test. A local R runtime was not found, and original R execution was not attempted.

## Why the reported performance is not our forecast result

The paper uses May 1–September 30 conditions. It removes state-specific LOWESS trends before analysing weather-related anomalies. It reports roughly 33% of out-of-bag yield-anomaly variation explained; the higher 87% figure includes restored temporal trends and spatial terms. These are different targets/information sets from our August-cutoff raw-yield forecast and must not be described as directly comparable forecasting accuracy.

For a forecasting adaptation, trend fitting, normalization, onset reference averages, model selection and any imputation must use training/history only. September observations and current-year irrigation statistics cannot be treated as August-available without verifying their publication dates. Availability and definition checks must precede modelling.

## Decision

- **Learning/demo of the author's processed-sample method:** feasible; the actual code and sample are available locally. A five-year demonstration would not reproduce the full study's scores.
- **Exact full-paper reproduction:** not ready. The shared package omits the full 1966–2017 prepared study table and the raw-to-processed construction code. The paper names public ICRISAT and Princeton PGF sources, but full source acquisition/assembly was not verified in this check.
- **Replacement for our forecasting model:** not justified. This is primarily historical crop-climate analysis, not independently demonstrated August forecasting or labelled damage prediction.

No full archive download, paid access, author contact, new training run or dashboard modification is needed to make this decision. The useful verified lessons are to investigate irrigation and monsoon timing carefully, distinguish raw yield from anomalies, and validate a forecast chronologically rather than adopt an impressive-looking OOB score.
