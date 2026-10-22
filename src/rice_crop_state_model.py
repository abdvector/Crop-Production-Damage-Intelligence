"""Fixed, retrospective feature-block comparison; no model selection or UI changes."""
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

from src.rice_crop_state import ROOT, CODE, YEAR, OUT as DATA, check_import
from src.rice_foundation import LAGS, WEATHER

OUT = ROOT / "data/processed/rice/crop_state_model"
PROTOCOL = ROOT / "docs/Crop_State_Comparison_Protocol.md"
TARGET = "yield_kg_ha"
REFERENCE = "history_reference_yield_kg_ha"
NDVI = [f"ndvi_{m:02d}" for m in (6, 7, 8)]
CROP = NDVI + [f"soil_moisture_{m:02d}" for m in (6, 7, 8)]
FLAGS = [name+"_missing" for name in NDVI]
METHODS = ("Recent mean", "History forest", "History/weather forest", "History/weather/crop-state forest")
PARAMETERS = dict(n_estimators=300, max_depth=4, min_samples_leaf=10, random_state=42,
                  n_jobs=2, max_features=1., bootstrap=True, criterion="squared_error")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")


def csv(name, frame):
    frame.to_csv(OUT / (name+".csv"), index=False, lineterminator="\n")


def scores(frame):
    actual, prediction = frame.actual_yield_kg_ha.to_numpy(), frame.predicted_yield_kg_ha.to_numpy()
    error = prediction-actual
    return {"records": len(frame), "mae_kg_ha": float(abs(error).mean()),
            "rmse_kg_ha": float(np.sqrt(np.square(error).mean())), "bias_kg_ha": float(error.mean()),
            "r_squared": float(1-np.square(error).sum()/np.square(actual-actual.mean()).sum()),
            "wape_percent": float(100*abs(error).sum()/abs(actual).sum())}


def load():
    check_import()
    frame = pd.read_csv(DATA / "prepared_inputs.csv", dtype={CODE: str})
    source = pd.read_csv(ROOT / "data/processed/rice/odisha_seasonal/prepared_inputs.csv", dtype={CODE: str})
    source = source.loc[source[YEAR].between(2004, 2017)]
    keys = [CODE, YEAR]
    original = source.set_index(keys).sort_index()
    current = frame.set_index(keys).sort_index()
    if len(frame) != 420 or frame.duplicated(keys).any() or not current.index.equals(original.index):
        raise ValueError("Fixed input cohort changed")
    if not np.array_equal(current[TARGET].to_numpy(), original[TARGET].to_numpy()):
        raise ValueError("Outcome labels changed during join")
    numeric = LAGS + WEATHER + [YEAR, TARGET, REFERENCE] + CROP[3:]
    if not np.isfinite(frame[numeric].to_numpy()).all() or (frame[TARGET] < 0).any():
        raise ValueError("Invalid required inputs")
    if not np.allclose(frame[LAGS].mean(axis=1), frame[REFERENCE]):
        raise ValueError("Historical reference arithmetic changed")
    if not np.array_equal(current[LAGS].to_numpy(), original[LAGS].to_numpy()):
        raise ValueError("Lag inputs changed")
    for name in NDVI:
        frame[name+"_missing"] = frame[name].isna().astype(int)
    return frame.sort_values([YEAR, CODE]).reset_index(drop=True)


def forecast(method, train, future):
    if train[YEAR].max() > future[YEAR].min()-2 or set(train[CODE]) != set(future[CODE]):
        raise ValueError("Invalid fitting cutoff or district cohort")
    numeric = LAGS + [YEAR]
    if method in METHODS[2:]:
        numeric += WEATHER
    if method == METHODS[3]:
        numeric += CROP + FLAGS
    if train[numeric].isna().all().any():
        raise ValueError("An entire fitting predictor is missing; acquisition review required")
    diagnostic = {"method": method, YEAR: int(future[YEAR].iloc[0]), "training_rows": len(train),
                  "training_end_year": int(train[YEAR].max()), "numeric_columns": len(numeric)}
    if method == METHODS[0]:
        return future[REFERENCE].to_numpy(), diagnostic, []
    transform = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median"), numeric),
        ("district", OneHotEncoder(drop="first", handle_unknown="error", sparse_output=False), [CODE])])
    model = Pipeline([("inputs", transform), ("model", RandomForestRegressor(**PARAMETERS))])
    x = numeric + [CODE]
    with threadpool_limits(limits=2):
        model.fit(train[x], train[TARGET]-train[REFERENCE])
        # Removing Y explicitly makes it impossible for inference to read it.
        prediction = np.maximum(future[REFERENCE].to_numpy()+model.predict(future[x]), 0)
        fitted = np.maximum(train[REFERENCE].to_numpy()+model.predict(train[x]), 0)
    if not np.isfinite(prediction).all():
        raise ValueError("Nonfinite predictions")
    diagnostic["fitting_mae_kg_ha"] = float(abs(fitted-train[TARGET]).mean())
    diagnostic["outside_training_range_observed_cells"] = int(((future[numeric] < train[numeric].min()) |
                                                               (future[numeric] > train[numeric].max())).sum().sum())
    medians = model.named_steps["inputs"].named_transformers_["numeric"].statistics_
    imputation = [{"method": method, YEAR: diagnostic[YEAR], "predictor": name,
                   "training_missing_rows": int(train[name].isna().sum()),
                   "forecast_missing_rows": int(future[name].isna().sum()),
                   "training_median": float(value)} for name, value in zip(numeric, medians)]
    return prediction, diagnostic, imputation


def plots(frame, predictions, yearly, overall):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    labels = ["Recent mean", "History", "History + weather", "History + weather + crop state"]
    axes[0].barh(labels, overall.set_index("method").loc[list(METHODS)].mae_kg_ha,
                 color=["#aec9e5", "#769ec6", "#4479aa", "#174b7d"])
    axes[0].set_xlabel("MAE (kg/ha); lower is better")
    available = 100*frame[NDVI].notna().mean()
    axes[1].bar(["June", "July", "August"], available, color="#4479aa")
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("NDVI available after quality rule (%)")
    fig.suptitle("Odisha crop-state extension: accuracy and input availability")
    fig.savefig(OUT / "figures/accuracy_and_coverage.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    for method in METHODS:
        part = yearly.loc[yearly.method.eq(method)]
        ax.plot(part[YEAR], part.mae_kg_ha, marker="o", label=method)
    ax.set(xlabel="Agricultural start year", ylabel="MAE (kg/ha)", title="Annual errors: same 30 districts per method")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "figures/yearly_errors.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
    part = predictions.loc[predictions.method.eq(METHODS[3])]
    axes[0].scatter(part.actual_yield_kg_ha, part.predicted_yield_kg_ha, s=14, alpha=.6, color="#245d92")
    limits = [0, float(max(part.actual_yield_kg_ha.max(), part.predicted_yield_kg_ha.max()))]
    axes[0].plot(limits, limits, color="black", linewidth=1)
    axes[0].set(xlabel="Actual yield (kg/ha)", ylabel="Predicted yield (kg/ha)", title="Full forest: 180 saved forecasts")
    axes[1].scatter(part.predicted_yield_kg_ha, part.predicted_yield_kg_ha-part.actual_yield_kg_ha,
                    s=14, alpha=.6, color="#245d92")
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set(xlabel="Predicted yield (kg/ha)", ylabel="Prediction minus actual (kg/ha)", title="Forecast errors")
    fig.savefig(OUT / "figures/forecast_errors.png", dpi=180)
    plt.close(fig)


def run():
    frame = load()
    pins = [Path(__file__), PROTOCOL, DATA / "prepared_inputs.csv", DATA / "import_audit.json",
            DATA / "export_plan.json", ROOT / "src/rice_crop_state.py", ROOT / "src/rice_foundation.py",
            ROOT / "data/processed/rice/odisha_seasonal/prepared_inputs.csv"]
    manifest = {"version": 1, "methods": list(METHODS), "forest_parameters": PARAMETERS,
                "evaluation_years": list(range(2012, 2018)), "timing": "fit through Y-2; issue August 31",
                "input_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in pins},
                "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                "pandas": pd.__version__, "scikit_learn": sklearn.__version__}}
    OUT.mkdir(parents=True, exist_ok=True)
    completed = OUT / "completed.json"
    if completed.exists():
        receipt = json.loads(completed.read_text(encoding="utf-8"))
        if receipt["manifest"] != manifest:
            raise ValueError("Completed experiment inputs/code changed; declare a separate version")
        for name, expected in receipt["output_sha256"].items():
            if sha(OUT / name) != expected:
                raise ValueError("Saved experiment output changed: "+name)
        return json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    write_json(OUT / "run_manifest.json", manifest)
    (OUT / "figures").mkdir(exist_ok=True)
    rows, diagnostics, medians = [], [], []
    for year in range(2012, 2018):
        train = frame.loc[frame[YEAR] <= year-2].copy()
        future = frame.loc[frame[YEAR].eq(year)].copy()
        if len(future) != 30 or len(train) != 30*(year-2005):
            raise ValueError("Incomplete fitting/evaluation year cohort")
        for method in METHODS:
            prediction, info, imputation = forecast(method, train, future)
            part = future[[CODE, "district_source", YEAR, TARGET, REFERENCE]].copy()
            part = part.rename(columns={TARGET: "actual_yield_kg_ha", REFERENCE: "reference_yield_kg_ha"})
            part["predicted_yield_kg_ha"] = prediction
            part["method"] = method
            part["training_end_year"] = info["training_end_year"]
            rows.append(part)
            diagnostics.append(info)
            medians.extend(imputation)
        print(f"Crop-state comparison: {year}, four methods, training through {year-2}", flush=True)
    predictions = pd.concat(rows, ignore_index=True)
    overall = pd.DataFrame([{"method": name, **scores(g)} for name, g in predictions.groupby("method")])
    yearly = pd.DataFrame([{"method": name, YEAR: int(year), **scores(g)}
                           for (name, year), g in predictions.groupby(["method", YEAR])])
    district = pd.DataFrame([{"method": name, CODE: code, **scores(g)}
                             for (name, code), g in predictions.groupby(["method", CODE])])
    wide = yearly.pivot(index=YEAR, columns="method", values="mae_kg_ha")
    changes, uncertainty = [], []
    rng = np.random.default_rng(42)
    indices = rng.integers(0, 6, size=(10000, 6))
    for reference in (METHODS[0], METHODS[2]):
        delta = wide[reference]-wide[METHODS[3]]
        changes.extend({YEAR: int(y), "reference": reference, "mae_reduction_kg_ha": float(v)} for y, v in delta.items())
        lo, hi = np.quantile(delta.to_numpy()[indices].mean(axis=1), [.025, .975])
        uncertainty.append({"reference": reference, "mean_mae_reduction_kg_ha": float(delta.mean()),
                            "year_bootstrap_95_low": float(lo), "year_bootstrap_95_high": float(hi),
                            "assessment_years": 6, "status": "exploratory; six years; serial dependence not ruled out"})
    csv("predictions", predictions)
    csv("overall_metrics", overall)
    csv("yearly_metrics", yearly)
    csv("district_metrics", district)
    csv("fitting_diagnostics", pd.DataFrame(diagnostics))
    csv("imputation_audit", pd.DataFrame(medians))
    csv("paired_year_changes", pd.DataFrame(changes))
    csv("augmentation_uncertainty", pd.DataFrame(uncertainty))
    csv("ndvi_availability_by_year", frame.groupby(YEAR)[NDVI].count().reset_index())
    plots(frame, predictions, yearly, overall)
    summary = {"status": "completed_exploratory_comparison", "input_rows": 420, "assessment_rows_per_method": 180,
               "metrics": overall.to_dict("records"), "augmentation": uncertainty,
               "new_independent_test": False, "operational_forecast": False,
               "ndvi_available_rows": {k: int(v) for k, v in frame[NDVI].notna().sum().items()}}
    write_json(OUT / "summary.json", summary)
    outputs = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in OUT.rglob("*") if p.is_file() and p != completed}
    write_json(completed, {"manifest": manifest, "output_sha256": outputs})
    return summary
