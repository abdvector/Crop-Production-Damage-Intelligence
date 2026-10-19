# Predictor linkage and next-data decision

Audited 20 October 2026 from the current local data. No models were trained, labels repaired, source coordinates changed or old results replaced. The audit recomputes key joins, source yields, five historical lags, all twelve regional weather columns and matched management counts. Only aggregate findings are published; survey records and exact field coordinates remain local.

Subsequent acquisition update: the [official Kharif rice source has now been obtained](Rice_Official_Kharif_Source.md). The audit below preserves the pre-acquisition findings; the new report records actual downloaded scope, units and remaining geographic/timing gaps.

## Decision

**Keep the annual district rice prototype as the main existing deliverable. Obtain better aligned target and geography data before another training cycle.** It has the strongest existing temporal structure: 1,490 district-years across 50 historical districts, 1987–2017. Its modest forecasting performance remains as previously reported.

For a stronger pre-harvest study, the next target should be **Kharif rice yield in kg/ha for a district and agricultural year**, with a declared issue date such as 31 August. The first acquisition priority is official season-specific labels, their units and district definitions. This is a proposed new study, not a relabelling of the existing annual model. Keep the current five-state interest: Bihar, Jharkhand, Odisha, Chhattisgarh and West Bengal. If comparable coverage is limited, narrow the scope based on data availability and boundary quality before examining prediction scores.

The original annual target combines rice seasons, so June–August weather cannot be assumed to describe every component. The 2018 farm study has richer management inputs but does not currently offer an independently verified multi-year replacement. Proteins and aluminium remain separate supporting research rather than mandatory predictors for this district task.

## What genuinely links

| Dataset | Linked evidence | Main limitation |
| --- | --- | --- |
| Annual districts | 1,490 labels; five exact source-matched yield lags and twelve monthly weather values on every row | Annual/all-season target; historical 1966 districts; archive ends in 2017; release vintages unverified |
| Farm survey | 17,836 weather-eligible records in 2017–2019, across 92 district-label groups; reported soil texture and irrigation access | Yields have year-specific scope/unit issues; the 2019 assessment is already opened; texture categories are not measured soil chemistry |
| Matched 2018 farm management | 4,801 records in 45 district groups with ten timed product-mass fields and area arithmetic checks | Only one documented management year; complete-report selection; product mass rather than nutrient mass |
| Rice trials | 1,046 eligible yields, 107 genotypes, 882 measured markers, 15 environments and 12 locations | Adjusted labels; very few independent environments; no matched soil chemistry or detailed management |
| Trial molecular extension | All 1,046 eligible yields link to 89 protein-altering SNP dosage columns; six sites have tested reference geometry | Existing controlled experiment found no reliable added prediction value; no full cultivar proteins or district adoption linkage |

The field cohort contains 6,183 records in 2017, 7,432 in 2018 and 4,221 in 2019. The matched management experiment retains **64.60%** of the eligible 2018 cohort, omitting 2,631 records for area or management completeness. Its results cannot be presented as performance for every surveyed farm. Thirteen 2019 yields retain review flags; no replacement values have been established.

Published aggregate outputs include [block coverage](../data/processed/rice/predictor_audit/coverage.csv), [summary](../data/processed/rice/predictor_audit/summary.json) and [integrity checks and hashes](../data/processed/rice/predictor_audit/checks.json). A complete-record count measures file completeness, not measurement validity, causality or publication availability. District, field and trial observations remain separate cohorts.

The four administrative source files and 50 weather caches match their recorded download checksums. This verifies preserved bytes, not independent measurement accuracy. The full 50-district by 31-year grid has 60 absent combinations; they remain absent rather than becoming invented targets or zero yields.

## Forecast dates need publication dates

Current field and trial weather windows include days 0–60 and end on their stated issue date; the regional weather block includes August in a 31 August outlook. The date truncation is correct for retrospective observations, but does not establish that the data product existed at that time.

[NASA POWER's official FAQ](https://power.larc.nasa.gov/docs/faqs/data/) reports typical delays of 2–3 days for meteorology and 5–7 days for solar data. Actual availability depends on service status; historical revisions and monthly publication timing need separate evidence. Accordingly, the existing results are retrospective archive-based studies, not verified operational real-time backtests. The selected regional estimator uses history rather than weather, but its historical yield release delay is also assumed rather than verified.

For a new daily-weather experiment, propose a seven-day planning buffer: a 31 August issue uses observations ending no later than 24 August. This is an explicit modelling choice, not a certified availability guarantee. Record retrieval time, product version and release evidence. Do not silently shift dates on the saved old predictions. Monthly August products must not be assumed available on 31 August merely because their timestamp says August.

## Variables for the next district study

| Role | Requested fields | Rule |
| --- | --- | --- |
| Target Y | Rice yield kg/ha, crop, Kharif season, agricultural year | Verify whether published or derived; if needed, 1,000 x production tonnes / area hectares, only for matching positive harvested-area definitions |
| Join and grouping keys | Stable district ID, state, boundary vintage, agricultural year, crop, season | Names alone do not establish geographic identity; a split district needs a documented crosswalk or separate treatment |
| Core X: historical yield | Prior released season-specific rice yields; training-only trend/reference | Use only values demonstrably available by issue date, or an explicit conservative delay assumption |
| Core X: weather | Daily maximum/minimum temperature, rainfall, relative humidity and solar radiation | Aggregate only pre-issue observations with a publication buffer; derive temperature/rain summaries within training protocol |
| Optional crop-state X | Pre-issue leaf area index or vegetation index; soil water estimate | Require quality flags, product version, rice-area aggregation and valid acquisition dates |
| Optional management X | Rice irrigated share/access or dated irrigation; verified fertilizer rates | Match crop, geography, units and time; whole-season realized quantities are not early inputs |
| Optional static X | Soil texture, pH, organic carbon, elevation | Treat maps as contextual estimates, not yearly field measurements; document spatial support and vintage |
| Not currently justified | District protein scores, cultivar tolerance scores, measured aluminium exposure | Need actual cultivar/adoption or exposure linkage; cannot borrow values from unrelated trials |

The district-level [De Clercq and Mahdi study](https://arxiv.org/abs/2403.07967) motivates season alignment and climate/crop-state predictors, including soil water and leaf area index. It does not prove that adding every available variable improves this project, prescribe a universal minimum sample size or justify copying its reported accuracy. Each optional block needs a matched-cohort ablation; geography effects are not substitutes for measured chemistry.

## Download order and exact export request

1. **Official yield/area/production labels and metadata first.** Request Rice, Kharif, all available years, all districts in the five states, with agricultural-year definitions and units. Aim for roughly 20 years where compatible data exist; this is a planning preference, not a guaranteed sample-size requirement. Preserve the full export before choosing a cohort. Collect boundary definitions and district-code changes alongside it. Older annual ICRISAT rows cannot simply be appended to modern season-specific rows.
2. **Inspect structure without opening new assessment outcomes.** Read documentation, header/ID/year coverage and geography. Keep post-2017 target values out of model/feature selection. Freeze split years, boundary decisions, issue-date rules, baselines and the small model list before accessing their scores. A new source is not automatically independent if it republishes the old target records.
3. **Acquire aligned daily weather after geography is fixed.** The existing source-point coordinates include four review flags, and no rice-area district aggregation is verified. New daily features require a defensible spatial definition; avoid bulk weather downloads for incorrect boundaries.
4. **Add one optional input block at a time.** Crop-state/soil-water information is a reasonable candidate after the core joins pass. Management and soil are optional until matching measurements can be established. More downloaded files are not a substitute for this linkage.

The [DES APY query form](https://www.data.desagri.gov.in/website/apy-query-report-web) is indexed with state, district, crop, season and year selectors. Direct opening timed out during this audit, so no export or year coverage is claimed as verified. The official [district/season crop statistics catalogue](https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0) is another discovery route. Neither source has been newly downloaded in this audit. If export access needs browser interaction, a manual download is appropriate; preserve accompanying units and metadata. No restricted data or email is necessary just to begin this acquisition attempt.

## Training gate and validation

More training is deferred until target units/season, district identity, pre-issue availability and missingness are audited and a new protocol is saved. Compare recent yield baselines, Ridge, Random Forest and gradient boosting on identical records with forward-year validation. Reserve genuinely new assessment years. Report MAE, RMSE, baseline-relative skill, per-year/district performance and interval coverage. Do not call explained associations causal damage effects or imply diagnostics prove a model has no misspecification.

No existing test set becomes untouched again. If revised experiments use the opened 2012–2017 district years, 2019 survey or existing rice trials, label those comparisons development evidence. Damage prediction needs a defined observed damage target; a yield shortfall remains a separate proxy.

## Reproduce the local audit

Using the project environment in a project-root Python session:

```python
from src.rice_predictor_audit import run_audit
run_audit()
```

This imported function uses local administrative/weather caches and ignored survey files. It performs no network access or fitting and exports no survey rows or exact field coordinates. A fresh clone without those local sources can inspect the committed aggregate audit, but cannot reverify every source join until the corresponding caches are restored. `app.py` remains the only application entry point.
