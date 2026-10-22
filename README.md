# Rice yield from predictor inputs

Enter five past rice yields and June-August weather values to estimate **annual rice yield in kg/ha**. A state/district/year selector can load real historical examples; area names are not predictors. All values can be edited before estimating.

This is a historical research model, not a validated farm forecast or crop-damage service. The interface reports measured error beside the estimate. Numerical inputs do not establish transferability to any location or a causal effect of changing weather.

## Run

Use Python 3.13 and the pinned dependencies in `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe app.py
```

To build or verify the model and evaluation artifacts:

```powershell
.\.venv\Scripts\python.exe app.py --train
```

The checked-in model is the exact fit used in evaluation. Completed builds verify hashes and environment rather than silently retraining changed code.

## The project in four parts

| File | Responsibility |
| --- | --- |
| `app.py` | Sole launcher |
| `src/data.py` | Load and validate the prepared data; define predictor names and units |
| `src/model.py` | Fit one Random Forest, evaluate against one baseline, predict from numerical X |
| `src/interface.py` | Editable input form, four data graphs, results |

`src/dashboard.css` holds the white-and-blue interface style. There are three pages: **Estimate yield**, **Explore data**, and **Model and results**. The estimate appears in a vertical table. No model-selection menu is needed.

**Explore data** includes an India map with year and measure selectors, state and district filters, a year range and an option to focus on a selected state. Hover over a district marker for its observed value; click a marker to filter the plots below and double-click to clear it. The map uses representative source coordinates rather than reconstructed historical district polygons. Only the five study states have observations. Outlines are simplified 2011 state boundaries derived from the retained DataMeet source; their provenance and licence are embedded in `data/india_states.geojson`. The map loads locally without a map-service token.

## Data and model

- **Y:** annual rice yield, kg/ha, all seasons combined.
- **17 X variables:** yields Y-2 through Y-6, and maximum/minimum temperature, rainfall (mm/day) and relative humidity for June, July and August.
- **Sources:** ICRISAT District Level Database administrative yields and NASA POWER monthly reanalysis at district representative coordinates.
- **Coverage:** 1,490 complete district-year records, 1987-2017; 50 historical districts across Bihar, Chhattisgarh, Jharkhand, Odisha and West Bengal.
- **Model:** fixed Random Forest, 300 trees, depth 4, minimum leaf size 10. It estimates a departure from the five-past-yield mean.
- **Baseline:** mean of those same five yields.
- **Excluded from X:** state, district, coordinates, year, current acreage, current production, actual target yield, protein and aluminium.

The model is fitted through 2004 and evaluated separately on 2006-2011 and 2012-2017. Those years have been seen in earlier studies, so this is a **retrospective comparison**, not a new independent test. Results are in `models/input_model/report.json` and the app. Read [the full method](docs/Method.md) for validation, reporting-delay assumptions and limits.

Later-period results (300 district-year records, 2012-2017):

| Method | MAE (kg/ha) | RMSE (kg/ha) | R squared |
| --- | ---: | ---: | ---: |
| Numerical Random Forest | 414.5 | 535.7 | 0.376 |
| Five-past-yield mean | 461.0 | 584.1 | 0.258 |

The forest has lower error in this comparison, but this does not establish high precision, independent confirmation or reliable damage prediction.

## What was simplified

For the separate seasonal research dataset, open **`data/rice_yield_master.csv`**: one Odisha Kharif table with 570 district-year records, yield as the label and 30 candidate predictors, including soil moisture and NDVI. See [column meanings, joins and missingness](docs/Dataset.md). This file does not replace the active annual model's input or mix the two targets.

A small [LAI acquisition check](docs/Dataset.md#lai-acquisition-feasibility-check-22-october-2026) confirms direct access to two MODIS composites and a prior-year paddy mask. Its files remain separate under `data/raw/rice/lai_feasibility/`; they are not a complete training dataset or inputs to the current model.

A [broader seasonal coverage audit](docs/Dataset.md#broader-seasonal-lai-coverage-audit) checks six districts across all five states in 2004, 2013 and 2022. It preserves 390 district/date checks from 65 available composites, with one catalogue gap. This is acquisition evidence, not new yield-model results; the underlying arrays and reproducible audit source are stored together in one archive.

Earlier annual, seasonal, satellite and statistical experiments are preserved in [one archive](archive/README.md), including their original code, protocols and model. Their datasets and saved results remain in `data/`. They are not loaded as competing application workflows. The active app uses only `data/processed/rice/regional_forecast/district_years.csv` and `models/input_model/`.

Papers, diagrams, the literature matrix and local mentor materials are preserved. Some earlier wheat diagrams describe the original proposal, not the current rice model. Local mentor materials are excluded from Git.

## Attribution

[ICRISAT DLD](https://doi.org/10.21421/D2/XFB1BZ): Swamikannu et al. (2021), District Level Data and Dashboard for Agriculture and Allied-sectors in India. ICRISAT bears no responsibility for these analyses. Data are subject to its Data Sharing Agreement; no CC BY claim is made. [NASA POWER](https://power.larc.nasa.gov/) provides reanalysis inputs. Earlier retained maps use DataMeet Community Maps, CC BY 2.5 India.
