# Field-level rice forecasting plan

## Research question

How accurately can rice yield per hectare and low-yield risk be forecast 60 days after field establishment using information available by that date, and do verified management and soil inputs improve forecasts beyond weather and planting information across held-out districts and years?

This is the proposed main field-survey study. The existing trial/genetic experiments remain a separate benchmark. No improved forecast accuracy is claimed from acquiring this dataset.

## Targets

Primary Y: reported harvested rice yield in kg/ha, with source units and moisture convention documented. Secondary Y: whether yield falls below a threshold defined using training data only. Compare a district/context-relative definition and a simple training quantile only within a declared validation protocol. This is low-yield risk, not proven disease damage, causal loss or a percentage of damage attributable to a stressor.

Actual damage modelling additionally needs observed, consistently defined damage labels, their dates and preferably an appropriate comparison yield. Existing post-season ordinal severity reports may support a separate stress classification study, but are not a substitute for measured yield-loss percentages.

## Required data and proposed X blocks

| Block | Data needed | Current status |
| --- | --- | --- |
| Target and identifiers | Field-season yield, year, district, establishment date, location linkage | Acquired; filtering, repeated coordinates and yield convention need checks |
| Planting | Calendar timing, establishment method, credible variety categories | Acquired; reconcile category names and unseen-variety handling |
| Weather | Daily minimum/maximum temperature, rainfall, solar radiation and humidity from establishment through day 60 | Acquired and linked for 17,855 candidates; gridded estimates, not station validation |
| Weather features | Calendar-window summaries; optional growing-degree exposure, heat exposure and dry spells | Basic means/rain totals built; rice-specific thresholds require source support and sensitivity checks |
| Water | Irrigation access/source and applications known by day 60 | Access fields acquired; actual application timing unresolved |
| Fertiliser | Verified nutrient rates in kg/ha and application dates through day 60 | Source fields acquired; units and timing incomplete |
| Soil | Observed texture; measured pH, organic carbon or nutrients if matched to the field | Texture acquired; measured chemistry absent |
| Validation groups | District, year and defensible repeated-field/survey-location grouping | Labels acquired; cross-year farm identity not established |
| Optional molecular block | Verified cultivar/allele-to-sequence mapping, variation across labelled yield observations | Not available; public reference structures alone do not supply this mapping |

NASA POWER can provide estimated daily meteorology, not field-measured weather. Cache requests by coordinate/date window, preserve raw responses and hashes, check missing values and units, and document its spatial resolution. Avoid treating nearby records sharing a meteorological grid as independent weather environments. Do not replace measured soil aluminium with pH or an unvalidated proxy. An external gridded soil product would be a separate, clearly labelled estimate requiring spatial matching and validation.

The archive provides a useful starting sample, not a guaranteed sufficient sample. Final usable counts depend on quality, timing and geographical coverage. Three source years offer limited temporal evaluation. Additional recent seasons would strengthen evidence for forecasting future conditions. No universal number of variables or rows guarantees reliability.

## Models and evaluation

1. Reconcile source filters, units, dates, repeated coordinates and predictor availability; freeze a documented cohort. Do not fabricate unknown input values as zeros.
2. Acquire and validate daily weather, then freeze the forecast cutoff. Actual harvest date, full-season totals, final yield components and retrospective stress ratings must not enter the predictor matrix.
3. Compare training-mean and defensible district/context baselines, regularised linear regression, Random Forest and gradient boosting. Fit all imputers, encoders and tuning inside training folds. Model complexity is chosen by validation, not by a diagram.
4. Evaluate a held-out later year and held-out districts separately, with nested tuning that respects those groups. Keep related/repeated observations together where identifiable. Reserve a final assessment before model selection; declare the split and sample counts first. With only three years, report the limits of temporal validation.
5. Run weather/planting versus added-management/soil ablations on the same cohort. Report MAE, RMSE, R squared, bias and errors by district/year; for risk report prevalence baseline, Brier score, calibration and discrimination. Check residual patterns, stability and transfer failures. These checks diagnose weaknesses; they do not prove absence of misspecification or causality.
6. Add uncertainty intervals only with a calibration design suitable for the grouped data, then display actual held-out results and limitations in the app. Claim savings only after a separate decision and economic evaluation.

The [source study](https://doi.org/10.1038/s41467-024-52448-6) motivates weather, planting and management variables and uses tree-based analysis. Our early forecast cutoff and validation design are separate choices: its whole-season predictors and reported performance cannot be reused as evidence of our forecasting skill.

Public protein sequences and predicted/experimental structures can support biological context. To test their incremental yield-prediction value, we need verified molecular differences linked to the varieties in the yield dataset. Repeating one rice reference embedding across farms adds no variety-specific signal. Protein and aluminium therefore remain optional supporting work until matched measurements exist.
