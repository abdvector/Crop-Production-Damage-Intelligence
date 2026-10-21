# Rice Yield Outlook

Birla Institute of Technology, Mesra
Department of Quantitative Economics and Data Science
Guide: Dr. Manish Kumar Pandey

A research app for predicting rice yield per hectare and comparing forecasts with recorded harvests. The presentation interface uses four sidebar pages, state/district selectors and vertical results tables.

**Start with [the presentation guide](docs/Project_Guide.md).** It explains the question, data, models, results and what you can honestly claim.

## Run

From the project folder, run `python app.py` with the project environment active, or `.\.venv\Scripts\python.exe app.py` in PowerShell. `app.py` is the sole launcher. Restart it after edits because file watching is disabled. Dependencies in `requirements.txt` pin the verified environment, recorded with Python 3.13.5; the saved model uses scikit-learn 1.9.1.

## Use the app

1. Choose a **State**, **Coverage**, **District** and agricultural start year.
2. **Forecast** shows the estimate in a vertical table. Reveal the recorded outcome when ready.
3. **Model results** lets you select accuracy, model comparison, uncertainty, low-yield flags or yearly/district results.
4. **Data & methods** explains inputs and evaluation. **Presentation guide** gives a short speaking outline.

Kharif coverage is available for Odisha. All five states remain selectable through the separate annual study. These are historical replays, not live current-season forecasts.

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
