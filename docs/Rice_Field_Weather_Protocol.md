# Field-survey daily weather linkage

## Source and acquisition

The weather source is the [NASA POWER daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), requested with the agriculture community and Local Solar Time (LST). It returns gridded estimates, not measurements from each farm. We request maximum/minimum temperature, corrected precipitation, surface shortwave radiation and relative humidity. Returned units must match C, mm/day, MJ/m²/day and percent respectively.

Four-degree core tiles with half-degree borders cover the survey coordinates. Requests use each tile/year's earliest establishment and latest forecast date. The request plan contains 25 tile-year groups and 125 single-parameter regional requests, using at most two workers. Cached successful responses are validated and reused on resumption. Responses retain the API header, parameter definitions and source-grid coordinates; the published manifest records exact request URLs and raw-file SHA-256 hashes. Raw caches remain local to limit repository size.

NASA describes meteorological and solar products with different spatial resolutions in its [API tutorial](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/). The linkage therefore chooses the nearest returned grid separately for each parameter, using longitude distances adjusted by latitude. Approximate distances are recorded for review. Grid geometry is read from the response rather than invented by rounding farm coordinates. Borders provide neighbouring cells near tile edges. Sampling tests compare tile neighbours and returned grids; actual field GPS accuracy remains unresolved.

## Forecast cutoff and features

For each eligible survey record, the predictor series includes establishment day through day 60, exactly 61 dates. Regional caches may contain later dates needed by other fields, but each field is reindexed to its own forecast window before aggregation. Harvest date and full-season weather averages are not used to produce these features.

Features contain means for the five parameters and total rainfall for the full window and calendar subwindows 0–14, 15–29, 30–44 and 45–60. These are calendar windows, not claims about observed flowering or other biological stages. This step does not introduce a rice heat-damage threshold, growing-degree base temperature or causal damage curve. Such transformations require a separate literature-backed specification before modelling.

NASA fill values become missing values. Missing dates or values are not replaced with simulated weather. A window with missing values has a missing mean/total rather than a falsely low partial total. Checks require minimum temperature no greater than maximum, nonnegative rainfall/radiation, humidity between 0 and 100 percent, and broad temperature bounds. Passing these checks does not validate gridded weather against local stations.

Local `weather_features_local.csv` contains record-level predictor summaries. Local `weather_linkage_local.csv` records matched source grids and approximate field-to-grid distances. Aggregate `weather_coverage.csv`, `weather_audit.json` and `weather_source_manifest.json` are published. No personal identifiers or exact field coordinates are added to GitHub.

## Reproduction

After obtaining the publisher archive and creating `field_records_local.csv`, import `download_weather` and `build_weather_features` from `src.rice_field_weather`. Call `download_weather()` followed by `build_weather_features()`. These are processing functions, not another application launcher; `app.py` remains the application entry point. A failed request produces an explicit error and resumable cache, not a simulated fallback. No extra package or temporary download script is required.

## What this establishes

On 13 October 2026, all 125 requests completed successfully. All 17,855 candidate records have complete 61-day windows, zero missing parameter-days and passing basic physical checks. The median approximate distance to the matched meteorological grid centre is 23.6 km (maximum 42.4 km); for solar radiation it is 43.6 km (maximum 76.1 km). These are distances to grid centres, not errors or station distances.

Checks reconciled every field's first/last weather date with its establishment/forecast dates, verified all 125 raw-file hashes, and compared source values and nearest-grid selection for 125 sampled records across all tile-year groups. A missing-value sentinel check passed. The Streamlit dashboard rendered without exceptions and showed the weather status. These are processing checks, not independent weather or model validation.

Completion establishes dated weather availability and auditable feature construction. It does not establish forecasting skill, independent farm identities, correct field GPS, verified management units, or an absence of model misspecification. Cohort checks and a declared district/year validation design remain necessary before training the new field model. The existing trial benchmark is preserved.
