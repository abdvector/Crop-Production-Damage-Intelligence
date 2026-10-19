# Rice Yield Outlook

Birla Institute of Technology, Mesra
Department of Quantitative Economics and Data Science
Guide: Dr. Manish Kumar Pandey

The app estimates **annual district rice yield in kg/ha**, compares it with recent history, and reports an approximate uncertainty interval. Select a historical district and year to replay a forecast before revealing the recorded yield. Results and input templates can be downloaded. The selected model needs only district ID, forecast year and five past yields; reference, trend and location are filled automatically.

Research question: can weather through August improve annual district rice yield and low-yield-risk outlooks over recent-yield baselines in eastern India?

## Run

Run `.\.venv\Scripts\python.exe app.py` from PowerShell, or `python app.py` with the project environment active. `app.py` is the sole application entry point. Restart after edits because file watching is disabled. The current model artifact was fitted with scikit-learn 1.9.1; use that version to load it reproducibly.

## Data and forecasting design

- Original [ICRISAT District Level Database](https://doi.org/10.21421/D2/XFB1BZ), downloaded directly from the provider API: 16,146 district-year records covering 1966–2017. The documentation verifies agricultural-year labels, kg/ha yields and historical apportioned boundaries.
- The reduced modelling table contains **1,490 district-years from 1987–2017**, across **50 historical districts** in Bihar, Jharkhand, Odisha (Orissa in the source), Chhattisgarh and West Bengal. District eligibility uses 1981–1997 records only.
- [NASA POWER](https://power.larc.nasa.gov/) monthly maximum/minimum temperature, mean daily rainfall and relative humidity for June–August. These are reanalysis estimates at source district coordinates, not measured farm weather or district-wide crop averages.
- Yield history uses Y−2 to Y−6, with a conservative assumed two-year reporting delay. Actual release vintages are not verified. Same-year production, harvested area, Y−1 yields and post-August weather are excluded from predictors.
- Compare recent mean, last available yield, historical trend, Ridge, Random Forest and gradient boosting. Model selection uses expanding-window development years 1998–2005, with a one-year label embargo.
- The selected estimator fits through 2004. Years 2006–2011 calibrate residual intervals; 2012–2017 assess the frozen model. No tuning uses the latter outcomes.

## Results

Development selected **History Ridge**, a regularized forecast of departures from the five-year historical mean. Weather candidates did not improve development MAE and weather is therefore not used by the selected model.

| Later-year assessment: 300 district-years | MAE kg/ha | RMSE kg/ha |
| --- | ---: | ---: |
| Selected History Ridge | 450.0 | 577.2 |
| Five-year recent mean | 461.0 | 584.1 |
| Last available yield | 444.4 | 613.7 |
| Historical trend | 625.8 | 852.5 |

The selected model has R squared **0.276** and aggregate absolute percentage error (WAPE) **19.95%**. It modestly improves RMSE over both simple history baselines, but does not beat last available yield on MAE. This is mixed forecasting evidence, not high-precision forecasting.

The approximate 80% interval covers **80.7%** of later-year observations, with mean width **1,657 kg/ha**. Coverage varies from 66% to 94% by year; temporal dependence and nonstationarity prevent a coverage guarantee.

Low yield means below 80% of the district's historical reference. The exploratory risk score has Brier **0.0994**, versus **0.1002** for development prevalence, but ROC AUC **0.394** shows poor ranking. The main forecast screen therefore withholds operational risk percentages. A predicted yield shortfall is not a diagnosis of disease, aluminium toxicity, causal damage or financial loss.

## Molecular linkage audit

The [20 October molecular audit](docs/Rice_Molecular_Linkage_Audit.md) identifies a feasible trial-level extension: all 882 measured rice SNPs match the reference assembly; 89 markers have canonical protein-altering annotations, linked to 107 trial genotypes and 1,046 eligible yield records. A bounded check maps 11 measured markers to exact reference-sequence-matched public protein structures; six sites have local pLDDT at least 70 and exploratory reference-geometry descriptors. Protein confidence is not a tolerance or damage score.

The dashboard's **Molecular data audit** view exposes these links, inputs and the [completed controlled forecasting experiment](docs/Rice_Protein_Context_Experiment.md). Nine configurations use identical trial records and nested location validation. Adding structure context to all SNPs worsened equal-location RMSE from **963.8 to 965.1 kg/ha** and helped only 5 of 12 locations; the bootstrap improvement range crosses zero. Structure also failed to beat matched PCA and shuffled-annotation controls. These inputs do **not** establish a reliable protein-context forecasting benefit. Trial forecasting remains weak, with negative pooled R squared.

The selected regional estimator remains unchanged and does not use these protein features. Complete variety-specific protein sequences remain unverified; zero exact alias matches were found in the two published 3K tables checked. The earlier claim that full protein sequences were the only possible molecular route was too restrictive: reference protein context can annotate measured variants without reconstructing full cultivar proteins. These annotations represent existing SNP measurements, not independent new genotype observations.

## Forecast scope

The [20 October predictor linkage audit](docs/Rice_Predictor_Linkage_Audit.md) recomputes all regional source-label, five-lag and twelve-weather-column matches and documents separate field/trial coverage. All 1,490 district records have complete history/weather, but soil, management, cultivar adoption and measured aluminium are not linked to those district-year rows. The 4,801 matched 2018 farm management records belong to a different study. Observation-date truncation does not verify data publication timing; weather and yield release vintages remain limitations. The next acquisition priority is official season-specific rice labels, units and compatible district geography before further model training. See the dashboard's **Data and research scope** tab for the audit.

The app provides a working **historical forecasting prototype for 2012–2017**. It does not issue a live 2026 forecast from an archive ending in 2017. The target combines rice seasons and refers to historical 1966 districts; it is neither Kharif-only nor an individual field yield prediction.

For a current-season extension, obtain updated annual rice yield histories for matching geographic units, establish reporting availability, and validate on newer years before opening the forecast period. Weather is needed when retesting weather-based candidates. Verified district-year management/soil measurements can be tested later. Protein sequences and aluminium studies lack that linkage and remain supporting research.

See [the full regional report and reproduction steps](docs/Rice_Regional_Forecast.md), [the frozen protocol](data/processed/rice/regional_forecast/protocol.json), and [earlier studies](docs/Rice_Earlier_Research.md). The dashboard's Earlier research view preserves all previous trial, field, SNP and aluminium results.

## Attribution

Swamikannu, N.; Pingali, P. R.; Padmanabhan, J.; Ravula, P.; Gumma, M. K.; Mohammed, I. A.; Rathore, A. (2021). *District Level Data (DLD) and Dashboard for Agriculture and Allied-sectors in India*. ICRISAT Dataverse, V1. https://doi.org/10.21421/D2/XFB1BZ.

This data was provided by the International Crops Research Institute for the Semi-Arid Tropics (ICRISAT). ICRISAT bears no responsibility or liability for the analyses or interpretations of the data presented here. The Content is available at http://dataverse.icrisat.org/. Source terms are the ICRISAT Data Sharing Agreement; this project makes no CC BY claim for these data. This is a research and educational prototype.
