# Rice forecasting reliability results

Evaluated 11 October 2026 at day 60 under [the declared protocol](Rice_Reliability_Protocol.md). Existing development trials were used; no new external validation dataset was acquired.

## Main finding

The main twelve-location benchmark still has pooled RMSE 1,004.8 kg/ha versus 1,036.5 for training mean. This update adds evaluation and presentation, not a new claim of improved point accuracy. Context and context/full-SNP selection have identical predictions. Genetic information has not demonstrated incremental benefit.

The paired, equal-location RMSE improvement is 32.4 kg/ha. Its descriptive 95% location-bootstrap range is **-111.5 to 170.1 kg/ha**. Equal-location MAE improvement is 50.2 kg/ha, with range **-78.9 to 193.8**. Both cross zero. RMSE improves in eight of twelve locations; MAE improves in seven. With overlapping cross-validation fits and only twelve locations, these ranges should not be presented as formal significance tests.

Training-only context-distance diagnostics flag Hyderabad 2019 dry season and Maputo 2020 wet season as farther from their nearest training environment than the largest training neighbour distance. This is a descriptive transfer warning, not proof that any feature caused the prediction error. Other trials also have individual inputs outside training ranges.

## Separate interval model

The deterministic split uses six fitting locations, four calibration locations, and two assessment locations: Mwea and Maputo. Calibration locations are Raipur, Dakawa, Maruteru and Hyderabad. Fitting includes Ahero, Los Banos, Gazipur, Cuttack, Nizmawna and Chokwe. Locations remain completely separated. Candidate selection uses the fitting locations only and selects context forest leaf=2.

| Procedure | Assessment RMSE (kg/ha) | 80% radius (kg/ha) | Mean 80% width (kg/ha) | Assessment row coverage |
| --- | ---: | ---: | ---: | ---: |
| Split context/full-SNP selection | 935.5 | 3375.4 | 6750.8 | 100% |
| Split training mean | 934.9 | 3290.0 | 6580.1 | 100% |

All 177 assessment rows and both assessment locations are covered. These wide intervals demonstrate limited precision. They do not show superior useful forecasting: the selected model is slightly worse than mean prediction on these two locations. Assessment R squared is about -2.45 for both procedures, partly reflecting the narrower yield variation within these assessment locations.

Only four independent location scores are used for calibration. The finite-sample rank for 80% is four, while 90% requires rank five and therefore an infinite radius. The unbounded 90% interval trivially covers every outcome; its coverage is not evidence of calibration. No finite 90% interval is claimed. These are intervals for the separate split model, not the main nested predictions.

The method follows the split-conformal order statistic described by [Angelopoulos and Bates](https://arxiv.org/abs/2107.07511), applied here to one maximum residual per location. Nominal coverage requires exchangeability of whole location datasets, an assumption not established for selected breeding trials across countries. The dataset has also been inspected previously. Two assessment locations cannot establish external calibration.

## Separate aluminium supporting analysis

The dashboard compares 334 families with complete paired published adjusted yields under ALU and LIM in the CIRAD study. Mean yields are 2,219.0 kg/ha in ALU and 1,941.0 kg/ha in LIM; mean LIM minus ALU is **-278.0 kg/ha**. ALU yield is higher for 240 of 334 families (71.9%). Do not assume that the condition named ALU must give a lower yield or reinterpret these observations as a damage percentage.

There is one independent site-season. Soil summaries show mean pH 4.39 and aluminium 2.32 cmol/dm3 in ALU, versus pH 5.19 and aluminium 0.53 in LIM. These condition summaries are not plot-level explanatory variables. Liming alters multiple properties, and this selected breeding population cannot establish a causal aluminium effect or transfer across regions. Published yields are preserved; harvested-area clarification remains pending. [Study and source methods](https://doi.org/10.1371/journal.pone.0307009).

## Reproduction and interpretation

Run python app.py. The default planting/full-SNP mode exposes Reliability and uncertainty and Aluminium supporting study. Update reliability report recomputes the reliability experiment without rerunning the main benchmark. Running the full planting benchmark also updates reliability. Other cutoffs require their own calculations; no day-60 intervals are reused.

Outputs in data/processed/rice/reliability/day_60 include location stability, environmental transfer, split membership, calibration scores, interval predictions/metrics and inner candidate scores. Hashes cover inputs, underlying benchmark predictions, implementation modules and generated CSVs. Code or data changes invalidate the loaded reliability report. No temporary scripts or additional app launchers are retained.

Verification passed: Python syntax; fully disjoint split membership; finite-sample quantile ranks; changed assessment labels leaving selected candidates, predictions, scores and interval bounds unchanged; changed calibration labels affecting scores but not model choice or point predictions; environmental diagnostics unchanged by target perturbation; coverage recomputation; all 334 complete aluminium pairs; and Streamlit dashboard checks covering both interval controls, all three evaluation modes and an uncomputed day-30 state.

This is a reproducible, transparent research project. Its evidence supports modest average yield skill, weak environmental transfer, no demonstrated incremental genetic benefit, and substantial uncertainty. It does not establish accurate field deployment, causal crop damage or monetary savings. Protein embeddings remain an optional future experiment contingent on verified variety-linked sequences.
