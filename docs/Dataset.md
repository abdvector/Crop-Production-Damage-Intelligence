# Consolidated Odisha rice dataset

Open `data/rice_yield_master.csv` for one table of compatible observations. One row represents one Odisha district and agricultural start year, for Kharif rice. The file has 570 rows, 30 districts, years 2004-2022 and 36 columns: one label, 30 candidate predictors and five identifying columns. The original datasets are preserved. The active annual model has not been retrained or switched to this seasonal file.

## Columns

| Role | Columns | Meaning / units |
| --- | --- | --- |
| Label Y | `yield_kg_ha` | Observed official DES Kharif rice yield, kg/ha |
| Identifiers, not X | `state`, `season`, `district_code_census2011`, `year`, `district` | Fixed Census 2011 district reference, agricultural start year and readable labels |
| Past yields (5 X) | `yield_lag2` through `yield_lag6` | District yield at Y-2 through Y-6, kg/ha; Y-1 excluded under the original reporting-delay assumption |
| Maximum temperature (3 X) | `T2M_MAX_06`, `_07`, `_08` | Mean daily maximum temperature, C |
| Minimum temperature (3 X) | `T2M_MIN_06`, `_07`, `_08` | Mean daily minimum temperature, C |
| Rainfall (3 X) | `PRECTOTCORR_06`, `_07`, `_08` | Period rainfall total, mm; these seasonal units differ from the active annual model's mm/day |
| Humidity (3 X) | `RH2M_06`, `_07`, `_08` | Mean relative humidity, percent |
| Solar radiation (3 X) | `ALLSKY_SFC_SW_DWN_06`, `_07`, `_08` | Mean daily solar radiation, MJ/m2/day, as recorded in the NASA POWER source receipts |
| Weather extremes (4 X) | `longest_dry_spell_days`, `wet_days`, `max_five_day_rain_mm`, `tmax_p95_c` | Longest run with rain below 1 mm/day; number of days with rain at least 1 mm; largest five-day rain total (mm); 95th percentile daily maximum temperature (C) |
| Vegetation (3 X) | `ndvi_06`, `_07`, `_08` | Quality-filtered MODIS NDVI, dimensionless, mixed-cropland proxy; not a rice-only measurement |
| Soil moisture (3 X) | `soil_moisture_06`, `_07`, `_08` | ERA5-Land volumetric moisture, top 0-7 cm, m3/m3; whole-district average |

Suffixes 06, 07 and 08 denote June, July and August. Weather and soil observations end on August 24; August therefore covers August 1-24. Historical issue date was August 31, with an assumed seven-day observation delay. This is archive data, not verified real-time vintage data. NDVI uses composites grouped by completion date, so the August feature can include observations from late July. NASA weather uses district-area weighting on a fixed boundary reference.

## Missing data

Blank cells mean unavailable or rejected by the original quality checks. They do not mean zero. No values were imputed during consolidation.

| Candidate predictor | Observed rows | Missing rows |
| --- | ---: | ---: |
| Each past-yield and weather variable | 570 | 0 |
| Each soil-moisture month | 420 | 150 |
| June NDVI | 375 | 195 |
| July NDVI | 62 | 508 |
| August NDVI | 29 | 541 |

Only five rows have all 30 predictors observed. Do not apply unrestricted `dropna()` to train on all columns. The 24 history/weather predictors have complete coverage across 570 rows. Soil moisture covers 2004-2017. NDVI coverage remains sparse even within that period. Predictor inclusion and any fitting-only imputation must be evaluated separately using chronological splits. These years have already been explored and do not constitute a new independent test.

## Join and verification

The base is `data/processed/rice/odisha_seasonal/model/assessment_inputs.csv` (750 district-year rows, 1998-2022). Keep 2004-2022, which supplies 570 rows with all five historical yields and 19 weather summaries. Earlier years are omitted because the required yield-history inputs are incomplete.

Left-join the six `ndvi_*` and `soil_moisture_*` columns from `data/processed/rice/crop_state/prepared_inputs.csv`, using **district_code_census2011 + agricultural_start_year**, with one-to-one validation. All 420 crop-state records match exactly; the remaining 150 base records are 2018-2022 and have no crop-state match. Never match by row position or district name alone.

Checks performed: source checksums, unique keys on both sides, exact join counts, unchanged yield/history/weather on the 420 overlapping records, finite base predictors and labels, CSV round-trip comparisons, preserved blanks and unchanged original files. Label, year and district identity are not candidate numerical X columns. Annual ICRISAT observations were excluded because their seasonal target and historical district definitions differ. No protein, aluminium, irrigation, fertilizer or soil chemistry measurements were invented or added.

Source SHA256:

```
assessment_inputs.csv
fc183e5cbedd94f1deda912fe286d51a878decf91830d5c93144365f83c9f4df

crop_state/prepared_inputs.csv
1f0ab40b3ba91716ccb96caca672f6feb920859554185dee886a7e8b8d5302ed
```

Consolidated CSV SHA256: `828e3775d198fb0e6d39f2b1884ec5c8b0f5ed8915a5e17f7769121e2ec3d159`.

To reconstruct, read the base and crop-state inputs with district codes as strings, filter the base to 2004-2022, select the five lags, 19 weather columns, label and keys, and perform the one-to-one left join described above. Rename `agricultural_start_year` to `year` and `district_source` to `district`, add `state=Odisha` and `season=Kharif`, then sort by district code and year. Exclude derived reference/trend, predictions, current acreage/production and modelling-role columns. Preserve floating-point precision and write missing values as empty CSV fields.

Sources: [Official DES area/production/yield records](https://www.data.desagri.gov.in/website/apy-query-report-web), [NASA POWER](https://power.larc.nasa.gov/), [MODIS vegetation indices](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1), [MODIS land cover](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1), [ERA5-Land](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR). Detailed source receipts remain with the original files. The cloud export was user-executed; consolidation verifies the downloaded records and their consistency, not independent cloud execution.

## LAI acquisition feasibility check, 22 October 2026

A small satellite-data check is stored in `data/raw/rice/lai_feasibility/`. These files are separate from the master CSV and the active annual model. They do not constitute a completed multi-year dataset, model comparison or replication of a paper.

Downloaded directly without a paid account or Earth Engine export:

- APRA500 paddy extent for **2008**, from [the authors' Zenodo record](https://doi.org/10.5281/zenodo.5557022), CC BY 4.0. The publisher's MD5 was verified. This is an annual paddy mask, not a Kharif-only mask or a map of all upland rice.
- Combined Terra+Aqua **MCD15A2H Collection 6.1**, LAI and quality layers, tile h25v06, for **5-12 August 2010** and **8-15 October 2010**. Accessed through the [Microsoft Planetary Computer MODIS catalogue](https://planetarycomputer.microsoft.com/dataset/group/modis). NASA's [product catalogue](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MCD15A2H) describes the 500 m, eight-day product. This is a newer collection than the paper's Collection 6.

Both Bargarh (Census code 370) and Sambalpur (372) are fully within the sample tile and match the existing district geography. The 2008 mask is a Y-2 paddy extent proxy for the 2010 observations. Its historical operational availability is not established by this retrospective download.

| District | 2008 mapped paddy pixels on LAI grid | Strictly clear, valid LAI coverage in August | Strictly clear, valid LAI coverage in October |
| --- | ---: | ---: | ---: |
| Bargarh | 3,844 | 1.1% | 96.3% |
| Sambalpur | 1,002 | 4.1% | 92.9% |

Procedure: project the existing fixed-2011 district polygons into the native MODIS sinusoidal grid, clip LAI and QC using pixel-centre inclusion, and reproject the paddy map with nearest-neighbour resampling onto that exact grid. Preserve valid non-rice zero values and explicitly use source/destination no-data code 3 for the rice map. Verify that direct warp and a virtual warped raster produce identical mask arrays. The mask has binary values 0/1; mapped paddy uses value 1. Pixel counts are raster-proxy counts, not ground-verified rice acreage.

The strict quality rule requires raw LAI <=100, MODLAND bit 0 = 0, SCF bits 5-7 <=1, dead-detector bit 2 = 0 and cloud-state bits 3-4 = 0. Scale LAI by 0.1 to m2/m2. The report also retains main-algorithm counts before the strict cloud filter, so the effect of filtering is visible. Do not interpret an average from 1% clear coverage as a reliable district estimate or relax the rule after seeing yield accuracy.

`sample_check.json` contains counts, quality settings, source hashes and limitations; `source_item.json` preserves the two catalogue items. No temporary signed access URLs are required for subsequent inspection. Rasterio 1.5.2 was used in a temporary dependency folder, which was removed after checking.

**Finding:** direct access and spatial matching are feasible. This sample demonstrates strong seasonal variation in strict cloud-free coverage, not complete coverage across districts or years. A larger seasonal coverage audit, an explicit prediction date, an assessment of paddy-mask representativeness and a declared evaluation protocol are still required before training. October observations cannot be used for an August forecast. The choice of these two pilot districts does not restrict the eventual geographic scope to Odisha.

## Broader seasonal LAI coverage audit

The bounded follow-up checks **six fixed districts across all five study states**: Bargarh and Sambalpur (Odisha), Patna (Bihar), Ranchi (Jharkhand), Durg (Chhattisgarh) and Puruliya (West Bengal). Years **2004, 2013 and 2022** sample the earlier, middle and later parts of the seasonal data period. This is a purposive feasibility sample, chosen for complete coverage within tile h25v06. It is not a representative assessment of India or a complete training dataset.

The plan was written before extraction. No yield file was read, and the same quality definition was applied throughout. All complete eight-day intervals starting on or after June 1 and finishing by December 1 were sought. Of **66 expected composites**, **65** were available in the Planetary Computer catalogue and successfully checked, producing **390 district/date records**. The expected **16 October 2022** combined-product composite was absent from that catalogue. The audit's `coverage_audit_incomplete` status records this source-series gap; it does not indicate remaining download failures. No source value was fabricated or interpolated.

Paddy masks come from APRA500 for Y-2: **2002, 2011 and 2020**. Publisher checksums were verified. The district geometry is the same fixed Census 2011 reference. Coverage denominators include all mapped paddy pixels inside the district geometry, including pixels with missing LAI; they are not restricted to pixels where LAI is already observed. Zero remains a valid non-rice value, and no-data code 3 is explicit during mask resampling. Archives hold the scaled-input precursors: original LAI bytes, QC bytes and Boolean mapped-paddy masks on the native grid.

For this descriptive check, a composite passes when **at least 50% of mapped paddy pixels** have strictly clear, main-algorithm LAI. This fixed screen was not selected using yield accuracy and does not establish that 50% coverage represents the entire crop. Diagnostic averages from lower coverage are explicitly labelled and are not admitted to the master dataset as model features.

| Data completed by | Expected district/date records | Records checked | Records passing the 50% screen | Median passing composites per district/year |
| --- | ---: | ---: | ---: | ---: |
| August 24, for the assumed August 31 issue | 180 | 180 | 35 | 2 |
| October 24, for the assumed October 31 issue | 324 | 318 | 102 | 5 |
| November 30 | 396 | 390 | 169 | 8.5 |

The rows are cumulative. An August or October issue includes only composites that have fully completed by its observation cutoff, not images merely timestamped before it.

Across the checked district/date records, median strict clear-sky coverage is **3.9% in July**, **11.1% in August** and **87.5% in October**. However, main-algorithm retrieval coverage before imposing the additional clear-sky requirement has monthly medians of approximately **96-99%**. These are different quality definitions: many retrieved values are not strictly clear-sky values. The result supports investigating later-season LAI under the declared conservative screen. It does not prove that all monsoon retrievals are unusable or authorize relaxing quality rules to improve yield scores. Any alternative quality policy needs product-based justification and its own declared comparison.

Files are grouped into two locations:

- `data/processed/rice/lai_coverage/`: the predeclared plan, per-composite coverage, cutoff summary and audit receipt.
- `data/raw/rice/lai_coverage/`: three paddy maps, unsigned source catalogue metadata, and **one ZIP** containing verified raster windows, entry hashes and the audit source code for reproduction. Raster windows were downloaded through range reads instead of retaining every full Asia/MODIS raster. Temporary loose caches and raster packages were removed after verification.

The provider's per-file signing endpoint rate-limited the initial execution. A transport-only revision reused a single public container token and resumed completed windows. Both source revisions and their hashes are retained; scientific scope, pixel rules and thresholds did not change. No temporary signed URLs were saved. All 390 coverage records were independently recalculated from the archived arrays and checked against the CSV, alongside source, plan and output hashes.

**Decision supported:** LAI access and seasonal extraction are feasible across this five-state sample, with stronger strict clear-sky coverage later in the season. Before a modelling experiment, obtain the full intended district/year series, choose an issue date, and verify rice-mask representativeness and yield-boundary compatibility. Availability of a Census 2011 polygon outside Odisha does not itself establish compatibility with the active annual model's historical apportioned districts. Existing targets have already been examined, so reuse would remain retrospective. This audit has not changed the app, trained model, master CSV or any accuracy claims.

## Matched later-season LAI dataset

The follow-up table is `data/processed/rice/lai_seasonal/matched_yield_lai.csv`: **570 rows, 30 Odisha districts, 2004-2022**. Every original master column and row is retained unchanged. The join is one-to-one on Census 2011 district code and agricultural start year. Odisha is used here because its seasonal yield/history/weather table already shares this district reference. This does not establish a valid join to the five-state annual model's historical districts. The fixed reference is not independent annual boundary certification.

The declared estimation date is **October 31**, admitting only whole eight-day composites completed by **October 24**, with an assumed seven-day delay. Depending on local cropping dates, this can be near or after harvest; it is not a verified early or universally pre-harvest forecast. Archive reprocessing and historical product availability prevent an operational-vintage claim.

Five candidate variables, `lai_06` through `lai_10`, measure paddy-masked LAI in m2/m2. For each district/composite, valid pixel counts and raw LAI sums are combined across **all intersecting tiles** before applying the same 50% strict-coverage screen. This avoids treating a district's partial tile as its full area. Admitted composite means are averaged within their completion month, using the last included observation day (`exclusive end - 1 day`) to assign that month. Monthly means can therefore summarize different numbers of observations. Each month has admitted/expected composite counts as **diagnostics**, not automatically model predictors. The resulting table has 51 columns: the original 36, five LAI summaries and ten counts.

| LAI feature | Observed district/year rows | Missing rows |
| --- | ---: | ---: |
| June | 478 | 92 |
| July | 50 | 520 |
| August | 43 | 527 |
| September | 514 | 56 |
| October, observations through October 24 | 563 | 7 |

Only **12 rows** have all five monthly LAI variables observed. Missing values remain blank in the data; there is no raw-data interpolation or zero filling. Sparse monsoon coverage and variable within-month sampling remain material limitations even though October coverage is substantially better.

Acquisition checked **1,364 available tile/date products** across four tiles, yielding **10,260 district/composite records**. There were no remaining download failures. Of 1,368 expected tile/date products, the October 16, 2022 composite is absent from the catalogue for all four tiles. Those 30 district/date observations remain unavailable. Duplicate processing versions for September 22, 2021 were resolved using the latest production timestamp in the product ID, without consulting yield outcomes; all catalogue metadata and the plan revision are retained. This is explicitly a reprocessed archive selection, not the data available on the historical issue date.

Files in `data/processed/rice/lai_seasonal/`:

- `plan.json`: acquisition scope, quality rules, dates and checksums, declared before extraction and outcome matching.
- `composites.csv`: every expected district/date, including missing catalogue observations and failed quality screens.
- `features.csv`: district/year monthly LAI and observation counts.
- `matched_yield_lai.csv`: the complete left join to the existing seasonal master.
- `audit.json` and `verification.json`: source/output hashes and independent checks.
- `comparison_protocol.json`, `comparison_predictions.csv` and `comparison_report.json`: the separate fixed experiment below.

All new raw materials are packaged in **`data/raw/rice/lai_seasonal/sources.zip`**. It retains 57 source files: downloaded paddy maps, publisher checksums, unsigned catalogue metadata, mapped-paddy counts, yearly archives of original LAI/QC bytes at paddy pixels, and preparation/comparison/verification source code. Existing pilot/audit masks are reused through recorded original paths. Every packaged file was checked byte-for-byte before loose copies were removed; no observations were discarded. Temporary raster packages and download caches are removed after verification.

To reproduce, extract `sources.zip` into its containing folder, then extract `preparation_source.zip` into a temporary `.lai-dataset-work/` folder at project root. `build.py` recreates the acquisition and join, `compare.py` runs the declared comparison, and `verify.py` independently recomputes outputs. Use the pinned project environment plus Rasterio 1.5.2 in `.lai-dataset-work/runtime`; the builder records library versions and hashes. The initial declaration is already saved, so run `compare.py` without `--declare`. The verifier also reads the packed archive directly without unpacking it. Building requires public network access; verification uses retained data. The active app does not import these preparation scripts or require Rasterio.

Independent verification recomputed all **1,364 tile/date arrays**, all **10,260 district/composite checks**, all monthly features and every matched row. It used an alternative quality-bit expression, checked source/output hashes, confirmed every original master value was unchanged, and loaded the active annual model successfully. Source parameter metadata also confirmed solar radiation is **MJ/m2/day**; the earlier kWh/m2/day wording in this guide was corrected without changing stored values.

## Fixed LAI comparison

One fixed **Gradient Boosting Regressor** is compared with and without LAI. Both predict the deviation from the five-past-yield mean and add that reference back. Parameters: 200 trees, learning rate 0.03, depth 2, minimum leaf size 10, squared-error loss and seed 42. The reference method is the same five-past-yield mean. This is an adaptation of the rice LAI/boosting idea, not a replication of the paper's dataset, tuning or reported accuracy.

Training uses **2004-2011 (240 rows)**. Year 2012 is an excluded gap, so the first 2013 prediction respects the assumed Y-2 availability of training yields. Both fitted models are then frozen for **2013-2017** and **2018-2022**, 150 rows each. There is no hyperparameter search or automatic deployment based on these scores. Gaussian predictor/residual assumptions are not requirements of these prediction trees. Neither model provides regression coefficient significance tests or causal effects.

The environmental input set is the five historical yields plus 19 June-August weather summaries. The added set contains five monthly LAI means. Current production/acreage, target yield, year, district identity, NDVI, soil moisture, observation-count diagnostics, protein and aluminium are excluded. Missing LAI is handled by medians and missingness indicators fitted **only on the 2004-2011 training rows**; a wholly missing training column would be excluded. Raw data is never overwritten by imputed values.

| Period | Method | MAE, kg/ha | RMSE, kg/ha | Predictive R squared |
| --- | --- | ---: | ---: | ---: |
| 2013-2017 | Past-yield mean | 659.5 | 809.3 | -0.474 |
| 2013-2017 | History/weather GBR | 586.9 | 726.9 | -0.189 |
| 2013-2017 | History/weather/LAI GBR | 585.0 | 729.6 | -0.198 |
| 2018-2022 | Past-yield mean | 577.7 | 682.0 | -0.213 |
| 2018-2022 | History/weather GBR | 506.8 | 597.0 | 0.071 |
| 2018-2022 | History/weather/LAI GBR | 515.5 | 612.1 | 0.023 |

**Finding:** this fixed comparison does not demonstrate a useful LAI improvement. Against the identical environmental model, adding LAI lowers earlier MAE by 1.8 kg/ha but increases later MAE by 8.7 kg/ha. A paired bootstrap resampling the five assessment years gives 95% intervals for MAE improvement of **-22.4 to 26.1** and **-28.6 to 11.2 kg/ha**, respectively. With only five year clusters these are coarse retrospective uncertainty estimates. LAI-model later bias is -370.9 kg/ha, showing substantial underprediction. Negative earlier R squared and low positive later R squared do not support a strong forecast claim.

These outcomes do not prove LAI is intrinsically unhelpful: monthly aggregation, conservative quality filtering, annual paddy masks, sparse monsoon observations, the small training sample and changes over time all limit this particular experiment. Missingness can itself reflect cloud/coverage patterns. Adding later-season LAI to weather ending in August also changes information timing, so it does not isolate a causal vegetation contribution. No further tuning was performed after seeing these scores.

The assessment years have been examined in prior project work; this is not new independent validation. Metrics must not be compared directly with the active **annual**, five-state model or paper scores on different targets, geography and splits. The active app model, its results and the original master remain unchanged. This dataset and experiment are available for review; no reliable damage alerts or operational forecasting capability have been established.
