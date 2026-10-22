# Crop-state extension: acquisition and declared comparison

Declared 22 October 2026, before obtaining the new district vegetation/soil table. Status: export prepared; Earth Engine execution and import are pending. This does not replace any completed study or establish improved accuracy.

Acquisition correction, version 2: the first cloud task failed with a zero-band `Image.unmask` error. A calendar regression check reproduced the empty August selection: on the MODIS 16-day schedule, August-starting composites do not finish by 24 August. Grouping by start month was incorrect for this cutoff. Version 2 groups composites by their nominal exclusive completion date (start +16 days), retaining the latest late-July composite completed during August. This changes the vegetation month definition; it does not extend the observation cutoff. The replacement also uses literal date intervals, isolates each year's construction, preserves named bands using fully masked seeds, and checks all 42 year/month source counts before creating tasks. Seeds are excluded from reported observation counts and contribute no valid values. Four replacement tasks/files end in `_v2`; old failed tasks must not be restarted. Cloud completion of version 2 remains unverified.

Acquisition correction, version 3: the 2004–2007 v2 task failed at district map index 24 because `Dictionary.set` received a null value. Version 3 encodes absent NDVI/soil means as **−9999** with separate 0/1 validity flags. Null/absent reduction sums become zero only for area/count bookkeeping, not as fabricated predictor observations. Import converts −9999 to missing, checks the flags and still rejects absent soil observations. A cloud preflight now computes the affected district's full 2004 row before creating four `_v3` tasks. This is a targeted computation check, not validation of every exported record. Version 3 cloud completion remains pending.

## Closest prior work

De Clercq and Mahdi (2024), *Feasibility of machine learning-based rice yield prediction in India at the district level using climate reanalysis and remote sensing data*, Agricultural Systems 220, 104099. [Publication](https://doi.org/10.1016/j.agsy.2024.104099), [open preprint and methods](https://arxiv.org/html/2403.07967v1).

This is a close precedent for our broad district rice-yield question. The preprint describes 247 districts, 19 algorithms, climate/soil/vegetation predictors and chronological evaluation in 2019–2020. It reports best R squared around 0.82. Its monthly features span May–November. That performance is not evidence of equivalent accuracy using only information through August. We have not reproduced those results or recovered a usable author data repository; the preprint's statement that data/code are on GitHub is not a verified download.

Our extension is an adaptation: ask whether early crop-state information improves an existing chronological forecast. We do not claim to invent district rice-yield forecasting. Low-yield forecasting is also distinct from measuring actual disease, aluminium injury or causal crop damage.

## Data we will acquire

One row per Census-reference district and agricultural start year: 30 Odisha districts × 2004–2017 = **420 rows**. Existing official DES Kharif yield remains Y, in kg/ha. The one-to-one join uses `district_code_census2011` and `agricultural_start_year`; names are descriptive. No new yield labels are needed.

Six new predictors:

| Predictor | Meaning | Spatial/temporal definition |
| --- | --- | --- |
| `ndvi_06`, `ndvi_07`, `ndvi_08` | Green vegetation activity, unitless | Quality-filtered MODIS vegetation over prior mapped cropland; composites completing in the named month, through August 24 |
| `soil_moisture_06`, `soil_moisture_07`, `soil_moisture_08` | Modelled surface-soil water volume fraction, m³/m³, 0–7 cm | Whole-district ERA5-Land daily averages; June, July and August 1–24 |

Sources: [MOD13Q1.061](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1), [MCD12Q1.061](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1), [ERA5-Land daily aggregates](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR). A small public Open-Meteo request was also tested successfully for surface soil moisture; that single-location access check is not a district dataset or a training result.

To keep acquisition manageable, vegetation uses land-cover classes 12 (cropland) and 14 (cropland/natural mosaics) from Y−2. This is **a mixed-cropland proxy, not a rice-specific mask**. Its advantage is excluding much nonagricultural vegetation without a separate rice-map upload. It includes other crops and natural vegetation in mosaics; neither NDVI nor coarse soil water measures rice stress directly. A rice-specific mask would require a separate validated extension. We do not substitute a 2020 rice mask into earlier forecast years.

Use the existing exact 2011 reference polygons, without simplification. Their equivalence to every year's administrative boundaries remains an assumption. Pixel-area weighted district summaries use each product's native projection/resolution; the 500 m land-cover mask is sampled on the 250 m NDVI grid. The coarse soil grid is not upsampled and called a field measurement.

## Timing and quality rules

- Forecast issue date stays 31 August. Soil observations stop on 24 August inclusive. No September–November information is permitted.
- MODIS 16-day composites must have their entire nominal support ending before 25 August. August composites starting too late are excluded even if their timestamp precedes the forecast.
- NDVI uses `SummaryQA == 0`, raw range −2000 to 10000 and scale 0.0001. Monthly values average valid composites per pixel, then area-weight across mapped cropland. This is a composite-completion-month summary, not an exact daily calendar-month average: an August value can contain late-July observations. For a month interval [start,end), select source starts in [start−16 days,end−16 days). Using an exclusive upper bound conservatively excludes composites ending exactly at the next boundary. Valid area and average valid-observation count are exported separately.
- An NDVI month with less than 25% valid mapped-cropland area becomes missing. No district-years are silently removed. Later fitting must impute from training data only and retain missingness indicators. If an entire training column is missing, stop and review the acquisition rather than fit it.
- Soil summaries require all 30, 31 and 24 daily images respectively, finite volume fractions in [0,1], and at least 50% district spatial coverage. Export coverage and day counts as audit fields, not predictors.
- These are revised historical archives. A seven-day observation buffer and Y−2 map do not prove that the same versions were available on each historical issue date. This remains a retrospective experiment, not a vintage-certified operational backtest.

## Planned comparison after import

Use the same 420-row cohort, chronological annual refits through Y−2 and evaluation years 2012–2017. These outcomes have already been examined, so report an exploratory comparison, not a new independent test.

Keep one fixed Random Forest configuration: 300 trees, maximum depth 4, minimum leaf size 10, seed 42. Compare recent five-available-year mean, history-only forest, history/weather forest, and history/weather/crop-state forest. The three forest blocks share fitting records and settings; add no target-year area or production. Retain district identity and the existing five lagged yields/year. Fit departures from the historical mean and add the mean back. No new hyperparameter search or switching to a test-set winner.

Report MAE, RMSE, R squared, bias, error by year/district and paired annual error changes. A six-year sample provides weak uncertainty evidence; no reliable damage-alert claim follows from yield accuracy alone. This comparison has **not yet been implemented or run** because the crop-state inputs are not acquired. Existing models and UI remain unchanged.

## Your setup and download steps

1. Open [Earth Engine registration](https://earthengine.google.com/noncommercial/). Sign in with your own Google account, create/select a Cloud project and follow the current noncommercial research eligibility/verification steps. [Official access instructions](https://developers.google.com/earth-engine/guides/access). Do not choose a paid plan just to follow this project.
2. Open the [Code Editor](https://code.earthengine.google.com/) and select that registered project. Registration/project activation must finish before exports can run.
3. The local command `python app.py --prepare-crop-state-export` creates `data/processed/rice/crop_state/Earth_Engine_Export.js`. It already embeds all 30 district polygons: no boundary upload, asset path, author email or private dataset is required.
4. Copy the entire regenerated JavaScript into the Code Editor, replacing the old code, and click **Run**. Wait for the Console's source-date checks and district computation check. In **Tasks**, start the four named `Odisha_Crop_State_..._v3` table exports to your Drive. Allow processing to finish. Inspect any cloud error before assuming success. The cloud script is locally syntax-checked but version 3 has not been executed in an authenticated Earth Engine session.
5. Download the four CSVs from Drive into `data/raw/rice/crop_state/`, retaining their `Odisha_Crop_State_..._v3.csv` names. Expected counts: 120, 120, 90 and 90 rows. Do not export/open reserved yield outcomes.
6. Run `python app.py --check-crop-state-import`. It checks cohort keys, date/map metadata, ranges, coverage and the one-to-one join, then writes a separate prepared input table and audit. This checks file contents, not the authenticity of a user's cloud execution. Retain the Code Editor script and completed task records for provenance review before modelling.

The generator performs no cloud actions and needs no password. The import command fails if files are missing; it does not invent values or start model training. Original datasets/results are preserved. NASA/USGS MODIS and Copernicus/ECMWF attribution must accompany any resulting data or figures.
