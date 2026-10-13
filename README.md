# Rice Yield and Low-Yield Risk Research

Institution: Birla Institute of Technology, Mesra

Department: Quantitative Economics and Data Science

Guide: Dr. Manish Kumar Pandey

## Research question

How accurately can rice yield per hectare be forecast 60 days after field establishment using early-season weather and planting information across different districts and years? Can verified management and soil measurements improve those predictions when matched data become available?

The dashboard now shows the Indian field-survey regression assessment alongside the earlier published rice-trial/SNP experiments, using NASA POWER weather estimates. Low-yield risk is secondary, not measured disease damage; the new field risk classifier is not yet trained. Protein embeddings remain future work awaiting verified variety-to-sequence links. Aluminium data belong to a separate CIRAD study. The restricted IRRI archive is not required for this project scope.

## Run

Run `python app.py` with the project interpreter. From PowerShell, the existing environment can be used with `.\.venv\Scripts\python.exe app.py`. For a new environment, install `requirements.txt` first. Stop the server with Ctrl+C. The sole application entry point is `app.py`; no separate launcher is required. Restart after source edits because file watching is disabled.

## Data and first baseline

Primary dataset: [Nguyen et al.](https://doi.org/10.1186/s12284-023-00623-6).

- 1,046 eligible yield records, excluding 10 conflicting genotype/environment records.
- 107 genotypes, 882 SNPs, 15 environments and 12 locations.
- Default cutoff: 60 days after seeding, including days 0 through 60.
- Entire locations are held out; preprocessing is fitted inside each training fold.
- Low-yield thresholds use each training fold's 20th yield percentile.

| Model | MAE (kg/ha) | RMSE (kg/ha) | R squared |
| --- | ---: | ---: | ---: |
| Training mean | 840.1 | 1036.5 | -0.164 |
| Weather Ridge | 1040.8 | 1221.1 | -0.616 |
| Genetics Ridge | 849.6 | 1051.0 | -0.197 |
| Weather + genetics Ridge | 1044.5 | 1228.9 | -0.636 |

The combined model does not beat the mean baseline. Low-yield classifier Brier score is 0.306 versus 0.167 for training prevalence; lower is better. These results do not establish reliable forecasting or monetary savings. There are only 15 distinct weather environments despite 1,046 yield records. Genotypes may occur in training and testing at different locations. See [the baseline report](docs/Rice_Baseline_Results.md) for the design and limitations.

## Improvement experiment

The first improvement used nested location validation. Its predeclared search tested stronger regularisation, five training-fitted genetic PCs, genetic/weather interactions and environment-level forests. Candidate choices used inner held-out locations only. It remains available through Evaluation method alongside the original baseline and latest experiment.

Nested selection reduced RMSE to **1,045.3 kg/ha** from 1,228.9, but the mean baseline is still better at 1,036.5. Risk Brier score improved to **0.174** from 0.306, but prevalence remains better at 0.167. Genetic candidates were never selected. These are development findings, not externally validated forecasting skill. See [the improvement report](docs/Rice_Improvement_Results.md) and [the declared protocol](docs/Rice_Improvement_Protocol.md).

## Latest planting and full-SNP experiment

The default Planting and full-SNP evaluation adds observed planting context, 15-day weather summaries and a relationship benchmark retaining all SNP information. RMSE is **1,004.8 kg/ha**, about **3.1% better** than training mean; eight locations improve and four worsen. Genetics adds no improvement to context selection. Risk falls back to prevalence. Physical density and primary irrigation/fertiliser/soil remain unresolved. See [results](docs/Rice_Context_Results.md), [paper comparison](docs/Rice_Paper_Comparison.md) and [data search](docs/Rice_Management_Data_Search.md). This remains development evidence with substantial errors.

## Indian field-survey extension

The field-level extension focuses on rice yield per hectare and low-yield risk at day 60 after field establishment. The Nayak et al. (2024) public archive has been downloaded and checked: **17,862 raw survey records from 2017–2019**, with **17,855 positive rice-yield records** eligible for initial weather-linkage checks. These counts differ from the paper's filtered sample. Daily NASA POWER temperature, rainfall, radiation and humidity are linked to all 17,855 candidates, with complete inclusive day-0-to-60 windows and no missing parameter-days. The first core regression comparison is now complete; management units/timing and full field GPS verification remain unresolved. Raw personal identifiers, exact field coordinates, row-level features and predictions stay local; GitHub contains aggregate audits and results.

See [the field survey audit](docs/Rice_Field_Survey_Audit.md), [the forecasting plan and required data](docs/Rice_Field_Forecasting_Plan.md) and [the daily weather protocol](docs/Rice_Field_Weather_Protocol.md). The existing trials and their reported results remain available.

The primary field cohort is **17,836 records** after excluding 19 coordinate/state mismatches while retaining them locally. Repeated signatures remain flagged, not deleted as presumed duplicate farms. The [cohort and validation protocol](docs/Rice_Field_Cohort_and_Validation.md) uses district folds with shared-weather-cell purging for development and reserved 2019 for assessment. Management diagnostics found 39 positive urea/DAP application entries with missing timing and 4,820 after day 60; product units and timing reference still need a questionnaire check.

The first comparison trained Ridge, Random Forest and gradient boosting against mean baselines. Development selected **Ridge alpha 1,000**. Its 2019 primary RMSE is **15,224.4 kg/ha**, almost identical to the global mean. Thirteen previously flagged source labels, reaching 400,000 kg/ha, dominate squared error. An unchanged-prediction diagnostic omitting those flags gives RMSE **1,447.8** versus **1,418.7** for the mean; it is not a replacement final test. Reliable forecasting is not established. See [the complete field results and limitations](docs/Rice_Field_Model_Results.md). The 2019 test has now been opened; further model improvements need a new independent assessment. No new field risk classifier has been trained.

[Raw-source tracing](docs/Rice_Yield_Source_Trace.md) verifies that all 17,862 project labels match the publisher's tonnes-to-kilograms conversion. The 13 extremes originate in source quantities/areas; actual entered units are still unconfirmed, and the 2017 quantity scope is unresolved. No labels or model results were changed. The source dictionary/questionnaire and any author-curated corrections are needed before repairing labels.

## Existing experiment files

The selectable Literature-guided validation experiment adds compact weather PLS, block-balanced genomic PLS and centred genetic/reaction-norm candidates, motivated by relevant rice studies. Day-60 RMSE is **982.5 kg/ha**, versus 1,004.8 previously and 1,036.5 for training mean. The gain occurs at Los Banos; eleven folds are unchanged, and genetic benefit remains negligible. This is development evidence, not reliable deployment. See [protocol](docs/Rice_Literature_Protocol.md) and [results](docs/Rice_Literature_Results.md). Earlier models and the default context mode remain available.

The Reliability and uncertainty tab reports paired whole-location bootstrap stability, training-only environmental transfer diagnostics, and a separate split prediction-interval experiment. The interval model uses six fitting, four calibration and two assessment locations; it is not the main twelve-fold model. Four calibration locations permit finite 80% intervals but unbounded 90% intervals. Coverage depends on exchangeability of locations, which is not established here. See [the reliability protocol](docs/Rice_Reliability_Protocol.md) and [results](docs/Rice_Reliability_Results.md).

The Aluminium supporting study tab compares 334 paired genetic families from CIRAD, with published soil-condition summaries. It is descriptive, uses a separate population and one site-season, and does not isolate a causal aluminium effect. Neither this study nor the optional restricted IRRI archive is substituted for missing primary-trial inputs.

- `app.py`: rice dashboard, benchmark controls, trial explorer and readiness status.
- `src/rice_baseline.py`: cutoff checks, predictor construction, grouped evaluation and result loading.
- `src/rice_validation.py`: nested candidate selection, training-only genetic compression and location diagnostics.
- `src/rice_context.py`: planting/weather features and full-SNP relationship kernels.
- `src/rice_reliability.py`: location stability, environmental novelty and separate split intervals.
- `src/rice_aluminium.py`: paired descriptive comparison of published CIRAD soil-condition yields.
- `src/rice_literature.py`: compact environmental PLS and centred genomic/reaction-norm adaptations.
- `data/raw/rice/`: original acquired sources.
- `data/processed/rice/`: audited tables, linkage maps and baseline results.
- `data/processed/rice/baseline/day_60/`: predictions, metrics, forecast windows and input SHA-256 hashes.
- `data/processed/rice/nested/day_60/`: nested results, inner scores, selected candidates, diagnostics and provenance.
- `data/processed/rice/context/day_60/`: new results, feature catalogue and within-trial rankings.
- `data/processed/rice/reliability/day_60/`: paired stability ranges, transfer diagnostics, interval split, calibration scores, assessment and hashes.
- `data/processed/rice/literature/day_60/`: separate literature-guided predictions, candidate selection, compact features and results.
- `docs/`: research question, audits, linkage boundaries and results.
- `Research Papers/` and `Presentation_Figures/`: retained documents and figures.

Earlier wheat prototype modules and model artifacts are retained for reference and are not used by the rice dashboard. Their simulated benchmarks are not evidence for this rice study. No temporary generation scripts or additional launchers were created.

The 89 MB supporting BAAP genetics archive is retained locally and excluded from Git. Its source URL and checksum are recorded in `data/raw/rice/baap_genetics_2018/download_manifest.json`. It is not required to run the primary rice benchmark.
