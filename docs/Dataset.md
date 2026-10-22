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
| Solar radiation (3 X) | `ALLSKY_SFC_SW_DWN_06`, `_07`, `_08` | Mean daily solar radiation, kWh/m2/day |
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
