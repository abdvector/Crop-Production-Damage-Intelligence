# Rice Yield Outlook

Birla Institute of Technology, Mesra
Department of Quantitative Economics and Data Science
Guide: Dr. Manish Kumar Pandey

A research app for exploring rice yield per hectare, public study data and saved forecasts. Three sidebar sections use interactive charts, state/district selectors and vertical results tables. The interface has a white main area, light-blue navigation and black text; presentation notes and institutional headings are kept out of the user workflow.

**Current phase: revised nested comparison completed, with negative findings.** Read the [revised statistical review and results](docs/Revised_Modelling_Results.md) and [declared comparison protocol](docs/Revised_Modelling_Protocol.md). The new 2012–2017 nested procedure has MAE 780.2 kg/ha versus 684.3 for recent mean; it is not operationally cleared. Existing forecasts below are preserved legacy results, not replaced or newly validated models. The 2018–2022 assessment has already been seen and cannot be reused as independent confirmation for revised models.

Run `python app.py --audit-data` to reproduce the development-only audit and figures without training a model. **Data explorer** offers four interactive graph views for each available state, with district highlighting, year-range filtering and weather-variable controls. Detailed audit tables and static PNG/SVG figures remain under `data/processed/rice/foundation/`.

Run `python app.py --compare-models` for the revised comparison; completed reruns verify receipts without refitting. Results and three diagnostic figures are under `data/processed/rice/revised_modelling/`. Model-specific checks distinguish numerical validity from predictive adequacy; no claim that all assumptions passed is made.

The [crop-state extension and download guide](docs/Crop_State_Extension.md) identifies closely matching published work. **The four v3 exports are now imported and the fixed comparison is complete.** All 420 district-years join correctly; soil moisture is complete, while quality-filtered NDVI is available for 375 June, 62 July and 29 August rows. Vegetation is a mixed-cropland proxy, not a rice-only measurement. In the exploratory 2012–2017 comparison, adding crop state does not improve the history/weather forest: MAE 798.8 versus 796.6 kg/ha; recent mean is 684.3. Existing dashboard forecasts are preserved. See [the results and limitations](docs/Crop_State_Results.md) and [fixed comparison protocol](docs/Crop_State_Comparison_Protocol.md).

Run `python app.py --compare-crop-state-models` to reproduce/verify the separate experiment; completed reruns verify receipts without refitting. `--prepare-crop-state-export` regenerates the authenticated Earth Engine acquisition script, and `--check-crop-state-import` checks the four downloaded v3 CSVs. Original CSVs are retained under `data/raw/rice/crop_state/`; joined inputs/audit are under `data/processed/rice/crop_state/`; comparison results and figures are under `data/processed/rice/crop_state_model/`.

## Run

From the project folder, run `python app.py` with the project environment active, or `.\.venv\Scripts\python.exe app.py` in PowerShell. `app.py` is the sole launcher. Restart it after edits because file watching is disabled. Dependencies in `requirements.txt` pin the verified environment, recorded with Python 3.13.5; the saved model uses scikit-learn 1.9.1.

## Use the app

1. Choose a **State**, **Study** and **District**. Odisha offers the revised Kharif study and two saved forecast studies; other states offer the annual study.
2. **Yield explorer** overlays actual and forecast yield lines across the saved years. The top-right **Show forecast** toggle controls the dashed forecast line; the vertical guide marks the harvest year selected for the table. The recorded-harvest toggle controls actual values in the graph/table/export. Historical model inputs remain available in a collapsed section.
3. **Data explorer** shows yield trends, district distributions, weather patterns and data coverage. Change the year range and district; hover over charts for values. **Show forecast** overlays the primary method's saved predictions when they fall within the displayed range. Seasonal graphs use the 1998–2017 development observations; annual graphs use the separately prepared annual cohort.
4. **Model evaluation** provides a sidebar result selector for accuracy, method comparison, yearly errors, low-yield detection, uncertainty and error patterns. Choose state, district or full-study scope. All seven annual methods now have saved district-level predictions, so these filters also apply to the annual model comparison.

All interactions explore saved records; they do not retrain models or create live forecasts. The revised interval experiment is explicitly separate from the adaptive selection procedure. Detailed methods and source definitions are available in collapsed sections. The local presentation guide remains in `docs/Project_Guide.md` rather than appearing in the app.

Kharif coverage is available for Odisha. All five states remain selectable through the separate annual study. These are historical replays, not live current-season forecasts.

The annual **Method** dropdown includes History Ridge, Weather Ridge, Weather Random Forest, Weather Gradient Boosting and three historical baselines for all 50 study districts. The added learned comparators use the original fixed settings and fitting cutoff (2004) on the same 2012–2017 assessment records. They are retrospective comparisons, not new independent validation; History Ridge remains the original selected model. Only it retains the original saved prediction intervals. Reproduce/verify this extension with `python app.py --compare-annual-models`; outputs and receipts are under `data/processed/rice/regional_comparison/`. See the [declared annual comparison extension](docs/Annual_Model_Comparison.md).

## The two studies

| | Main seasonal study | Additional annual study |
| --- | --- | --- |
| Coverage | 30 Odisha districts | 50 historical districts across Bihar, Chhattisgarh, Jharkhand, Odisha and West Bengal |
| Target | Kharif rice yield, kg/ha | Annual rice yield, kg/ha |
| Yield source | Official DES | ICRISAT District Level Database |
| Weather | NASA daily weather; 19 summaries | NASA monthly weather; 12 variables |
| Later-year assessment | 2018-2022; 150 records | 2012-2017; 300 records |
| Selected configuration | History Ridge, alpha 10 | History Ridge |
| MAE | 516.8 kg/ha | 450.0 kg/ha |

Both selected configurations use yield history. Weather candidates were tested but did not win development selection. Current-year production and area are never predictors. The studies use different targets, periods and geographic units; their errors are not a head-to-head comparison.

## Main findings

The Odisha study compares **13 configurations**: three historical baselines, six Ridge configurations, two Random Forest configurations and two histogram gradient-boosting configurations. Earlier-year selection and interval calibration precede later-year assessment.

The selected Ridge has MAE **516.8 kg/ha**, versus **577.7** for recent mean. Random Forest depth 4 achieves **405.3 kg/ha** as a secondary finding; it was not promoted after seeing assessment. Baseline gains remain uncertain across years. Low-yield detection is weak and uncertainty intervals are wide. This is a completed research prototype with mixed findings, not a high-precision operational service.

Protein and aluminium work is supporting research. Neither is an input to the district forecasts. See [the full Kharif results](docs/Rice_Odisha_Model_Results.md).

## Code and data

- `app.py`: sole launcher.
- `src/rice_dashboard.py` and `src/dashboard.css`: the presentation interface.
- `src/rice_regional.py`: annual data, modelling and inference.
- `src/rice_seasonal_data.py`: official Kharif source parsing.
- `src/rice_geography.py`: district reference geography checks.
- `src/rice_odisha_seasonal.py`: daily weather and history preparation.
- `src/rice_odisha_model.py`: frozen model comparison, calibration and assessment.
- `data/` and `models/`: all datasets, recorded results, receipts and model artifacts are preserved. Some raw/private caches are intentionally ignored by Git.
- `docs/`: current guide, results, methods and original protocols. Earlier documentation is in `docs/research_notes/`.
- `Presentation_Figures/`, `Research Papers/` and the literature matrix: preserved supporting materials. Earlier wheat illustrations describe the initial proposal, not the implemented rice pipeline.

The current source reproduces the two district studies. Retired exploratory runners and duplicate dashboards were removed; their datasets and recorded findings remain. See [the cleanup record](docs/Codebase_Cleanup.md). Local mentor materials remain local and ignored.

## Sources and method records

[Official DES](https://www.data.desagri.gov.in/website/apy-query-report-web) · [ICRISAT DLD](https://doi.org/10.21421/D2/XFB1BZ) · [NASA POWER](https://power.larc.nasa.gov/)

[Original seasonal protocol](docs/Rice_Odisha_Seasonal_Protocol.md) · [Timing amendment](docs/Rice_Odisha_Timing_Amendment.md) · [Implementation rules](docs/Rice_Odisha_Model_Implementation.md) · [Annual report](docs/Rice_Regional_Forecast.md)

Map attribution: DataMeet Community Maps Project, [CC BY 2.5 India](https://creativecommons.org/licenses/by/2.5/in/). Fixed 2011 boundaries and historical publication availability remain assumptions. The annual source uses historical 1966-apportioned units.

ICRISAT data attribution: Swamikannu et al. (2021), District Level Data and Dashboard for Agriculture and Allied-sectors in India. ICRISAT bears no responsibility or liability for these analyses or interpretations. Source terms are the ICRISAT Data Sharing Agreement; no CC BY claim is made for those data.
