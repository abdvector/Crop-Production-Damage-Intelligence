# Rice field cohort and declared validation

Prepared 13 October 2026, before fitting any new field-survey model. This protocol preserves the earlier trial benchmark as a separate experiment.

## Cohort

Start with all source records, retain source-row identifiers locally, and require a positive finite rice yield, valid day-60 dates, India-range coordinates and complete weather passing physical checks. Check GPS against the reported state using the downloaded [geoBoundaries India ADM1 dataset](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/). State names are matched after accent and punctuation normalisation; polygon holes and multipolygons are handled with Shapely. Points on the polygon boundary count as concordant.

Nineteen of 17,855 weather-eligible records fall outside their reported state polygon. They remain in the original data and local flags but are excluded from the primary cohort. The primary cohort has **17,836 records**: 6,183 in 2017, 7,432 in 2018 and 4,221 in 2019, across 92 state/district label combinations. State-boundary concordance does not verify a farm location. Boundaries are a third-party geographical screening source, not a survey-year official district register: metadata say 2011 but the downloaded administrative set includes later changes. These limitations matter for interpreting points near borders. The 19 discordant records should be investigated, not assigned repaired coordinates automatically; a later explicit sensitivity analysis may reinstate them.

There are 490 rows sharing a reduced signature of year, exact coordinates, establishment date, reported variety and yield; 246 are repetitions beyond the first signature occurrence. Unique survey-instance IDs and similar observed variables do not prove either independent farms or duplicate farms. All these rows remain in the primary cohort. Repeated GPS/year groups and district groups remain local for split checks. No cross-year coordinate pair repeats exactly, but this does not establish independent farms across years. Small coordinate changes can hide repeat visits.

Yields above the audit's 15,000 kg/ha review threshold are not silently deleted or winsorised. That threshold is a descriptive flag, not an established upper biological limit. Any later sensitivity analysis must be labelled and must not be chosen to improve assessment results.

## Management audit

Eighteen product/event/source summaries examine three urea and three DAP top-dressing events in each year. A positive amount with missing timing remains unknown. Applications after day 60 are future information and cannot enter early predictors. Missing timing and timing counts are published in `management_timing_audit.csv`; counts refer to application entries and can include multiple events from the same record.

The source's total N per-hectare fields generally agree with total N divided by plot acres multiplied by **0.4**, rather than the exact acre-to-hectare factor 0.40468564224. The difference is about 1.17% in the resulting rates. This is an arithmetic diagnostic, not confirmation of raw fertiliser-product units or their timing reference. Area conversion also does not reconcile for every record. We keep source labels unchanged and do not turn these full-season totals into early forecasts. A questionnaire/codebook check remains necessary before a fertiliser-rate ablation. Irrigation counts are whole-season reports without verified application dates and remain excluded.

## Initial predictor blocks

The initial core study may use weather summaries restricted to days 0–60, field establishment day-of-year, establishment method, reported variety categories and state/district context. Calendar year is a validation label, not a predictor. Coordinates, survey IDs, harvest dates, grain quantities, full-season weather/totals and retrospective stress reports are blocked as predictors. Category spelling is normalised without pretending that matching variety names verify cultivar identities. Rare-category handling and unseen-category encoding must be fitted on the training data only.

Survey soil texture and irrigation availability can form a separately labelled static-context sensitivity block after confirming what the questionnaire measures. These are reported categories, not measured soil chemistry or dated irrigation events. The study cannot yet claim that adding verified fertiliser or aluminium measurements improves prediction. Public protein reference structures do not establish matched molecular variation in these fields.

## Validation declared before model fitting

- Temporal development: fit 2017 and assess 2018 for model development. State coverage changes substantially, so this combines year transfer with location transfer.
- Geographic development: use 2017–2018 only. Sort district-group labels by SHA-256 and allocate them cyclically to five folds. A district label never appears in fitting and validation within a fold. This allocation does not use yield values or model performance.
- Weather overlap: within every geographic fold, remove fitting rows sharing any parameter's returned source-grid cell with held-out rows, across both development years. This is deliberately stringent and removes many fitting rows because the solar grid is coarse. It avoids interpreting common weather exposure as independent geographical validation. The remaining fitting counts range from 3,213 to 4,280 per fold; assessment counts range from 2,436 to 2,851. The purge is done per parameter, and split checks require zero retained cell overlap.
- Final temporal assessment: reserve all 4,221 eligible 2019 records until development choices are fixed. No fitting, encoding, imputation, threshold selection or model selection may use those records. Quality checks and split counts do not establish assessment accuracy. Test results must distinguish previously observed versus new states/districts.

The machine-readable `field_model_protocol.json` freezes eight regression candidates: global mean, state mean with global fallback, two Ridge penalties, two Random Forest minimum-leaf sizes and two gradient-boosting leaf counts. The selection objective gives equal weight to geographic and temporal development RMSE, each divided by its corresponding global-mean baseline RMSE. The feature allowlist, seed and training-only preprocessing are declared there. Report all development candidates, not only the winner. Risk candidate selection remains deferred and requires its own declaration before fitting. Model results and a frozen configuration must precede any main dashboard forecast claim.

Low-yield thresholds must use training labels only (a declared training 20th percentile for the first risk experiment). Report a training-prevalence baseline, Brier score, calibration and discrimination alongside regression MAE, RMSE, R squared and bias. Report both pooled and district/year summaries because a large Bihar sample can dominate aggregate performance. These are predictive association analyses, not causal damage estimates or proof of correct specification.

District strings are normalised labels, not fully verified official district identities. Historical renaming, spelling variants and survey revisions remain limits. Spatial overlap purging helps prevent shared exposures across a split, but does not solve all geographic dependence or farm identity uncertainty.

## Reproduction and privacy

`src/rice_field_cohort.py` contains source management diagnostics, state screening, cohort generation and geographic split masks. Use `prepare_cohort()` after local weather linkage. `audit_management()` accepts the three raw RData objects and writes only aggregate checks. Source boundary metadata and hashes identify the geographical input; the full boundary file, row-level cohort, flags and split assignments stay local. Published coverage/audits contain no exact field coordinates or personal identifiers. The temporary R reader is removed after inspection. `app.py` remains the sole application entry point.

No new field model has been trained in this milestone. The core cohort is prepared for an initial weather/planting comparison; the intended verified-management extension is still incomplete.

## Public questionnaire needed for management verification

The [source survey article](https://doi.org/10.1016/j.dib.2022.108625) identifies the public [CIMMYT repository](https://data.cimmyt.org/dataset.xhtml?persistentId=hdl:11529/10548656), with variable details, an ODK Build file and accompanying code. The repository API returned HTTP 403 from this environment on 13 October 2026. This is not evidence that the materials are private, and no questionnaire was acquired or verified.

If accessible in a normal browser, download the variable details/data dictionary and ODK survey form or Build file. Save them in the local source folder; the full original survey dataset and additional precise GPS are not needed for this check. The definitions we need are the raw fertiliser amount unit, plot-area unit/conversion, whether application days refer to field establishment or nursery seeding, and what irrigation availability means. A dictionary for 2018 may not establish unchanged definitions in 2017/2019. This check does not prevent the declared core weather/planting experiment from starting.

Coverage changes also limit temporal interpretation: 2018 has 4,048 records in states absent from 2017 and 4,825 in new district labels. The 2019 assessment has 727 records in a new state and 3,882 in district labels absent from the earlier years. Temporal test errors therefore include substantial geographic transfer, not simply another year at the same farms.
