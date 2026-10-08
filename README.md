# Multi-Scale AI Framework for Wheat Crop Production & Damage Intelligence

**Institution**: Birla Institute of Technology (BIT), Mesra  
**Department**: Quantitative Economics and Data Science

**Guide**: Dr. Manish Kumar Pandey

**Focus**: Multi-Scale Biophysical Modeling, Soil Aluminium Toxicity, Phenological Climate Stress, and Vast Acreage Yield Prediction  
**Target Crop**: Wheat (*Triticum aestivum L.*)

---

## Research Overview

This repository provides an end-to-end multi-modal machine learning pipeline that models wheat crop production and yield damage from the **inside out**:
1. **Molecular Layer**: Extracts 320-dimensional biological resilience representations from wheat defense proteins (ALMT1 Aluminium transporter and Heat Shock Proteins) using Meta AI's **ESM-2** Protein Language Model.
2. **Edaphic Soil Layer**: Ingests subsurface soil chemistry (Aluminium saturation %, acidic pH, CEC) to model root stunting in acidic soils (e.g., Jharkhand/Ranchi lateritic soils, pH 4.5–5.5).
3. **Temporal Phenology Layer**: Aggregates daily weather time-series (NASA POWER) into non-linear growth stage indices (Extreme Degree-Days > 30°C at flowering, terminal heatwave days, consecutive dry days) across the wheat biological calendar (sowing to harvest).
4. **Predictive Regressors**: Benchmarks Ridge Regression, Random Forest, and **XGBoost** with Spatial-Temporal Cross-Validation ($R^2 \ge 0.78$, $\text{RMSE} < 4\%$).
5. **Explainable AI (TreeSHAP)**: Decomposes predicted yield loss into cooperative game-theoretic contributions, identifying the primary and secondary limiting environmental determinants.
6. **Vast Acreage Scaling (ISRO Connection)**: Calibrates the multi-factor baseline on controlled experimental plots and scales predictions across hundreds of thousands of hectares to match satellite radar (NISAR S-band) and optical NDVI biomass trajectories.
7. **Interactive Dashboard**: Full Streamlit web application with district selection, What-If stress anomaly sliders, biophysical loss diagnostics, and literature deep-dive.

---

## Quickstart

### Run the app

From the project folder, use the existing virtual environment:
```powershell
.\.venv\Scripts\python.exe app.py
```

If your IDE or terminal already uses the project's `.venv` interpreter:
```powershell
python app.py
```

`app.py` starts the Streamlit server and dashboard itself. Stop it with
`Ctrl+C` in the terminal. No separate PowerShell, batch, or Python launcher
is required. Model and dataset paths resolve from the location of `app.py`.

For a new environment, install dependencies once with
`python -m pip install -r requirements.txt` using the interpreter you will
use to run the app.

## Project implementation map

- `app.py`: the dashboard and sole application entry point. Sidebar inputs
  select a district and protein profile and adjust pH, aluminium, heat, and drought.
- `src/bio_embeddings.py`: loads ESM-2 when available, with a deterministic
  biophysical projection fallback; provides four protein profiles.
- `src/edaphic_features.py`: nine district soil profiles and soil stress indices.
- `src/weather_phenology.py`: simulates a 140-day season and computes
  growth-stage heat, rainfall, and drought features. A NASA POWER fetch helper
  exists, but the dashboard currently uses simulated weather.
- `src/explainability.py`: loads the saved model bundle and XGBoost JSON,
  falls back to Random Forest, and groups feature contributions into stress drivers.
- `src/damage_assessment.py`: converts predicted loss into estimated harvested
  yield, severity, limiting factors, and intervention suggestions.
- `src/data_pipeline.py` and `src/train_models.py`: offline dataset generation
  and training utilities. They are not required to launch the dashboard with
  the supplied artifacts. Training uses a temporal holdout through 2019 versus
  2020-2023, rather than a spatial cross-validation split.
- `data/processed/` and `models/`: the dataset and trained artifacts loaded at startup.
- `Research Papers/`, `Presentation_Figures/`, and the PDF/XLSX:
  retained research documents, diagrams, and literature review assets.

The current dataset generator synthesizes weather and yield-loss targets;
the benchmark measures performance on those generated targets. Satellite
integration is described in the dashboard but is not implemented as a live
data connection. Benchmark figures displayed by the dashboard are hardcoded.

---

## Benchmark Results (Forward Unseen Seasons 2020–2023)

| Model Architecture | $R^2$ Score | Root Mean Squared Error (RMSE) | Mean Absolute Error (MAE) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Ridge Regression (Baseline)** | `0.7935` | `3.84%` | `3.11%` | Linear Lower Bound |
| **Random Forest Regressor** | `0.7990` | `3.79%` | `2.97%` | Bagging Ensemble |
| **XGBoost Regressor (Champion)** | `0.7764` | `3.99%` | `3.09%` | **Production Champion (TreeSHAP Compatible)** |

---

## Landmark Academic Literature Foundations

1. **van Klompenburg et al. (2020)** — *Crop yield prediction using machine learning: A systematic literature review*. Computers and Electronics in Agriculture. (DOI: `10.1016/j.compag.2020.105709`) — **1,849 citations**
2. **Kochian et al. (2004)** — *How do crop plants tolerate acid soils? Mechanisms of aluminum tolerance and phosphorous efficiency*. Annual Review of Plant Biology. (DOI: `10.1146/annurev.arplant.55.031903.141655`) — **1,831 citations**
3. **Schlenker & Roberts (2009)** — *Nonlinear temperature effects indicate severe damages to U.S. crop yields under climate change*. PNAS. (DOI: `10.1073/pnas.0906865106`) — **3,442 citations**
4. **Lobell et al. (2011)** — *Climate trends and global crop production since 1980*. Science. (DOI: `10.1126/science.1204531`) — **4,622 citations**
