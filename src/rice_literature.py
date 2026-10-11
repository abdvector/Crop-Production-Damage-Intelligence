"""Declared rice-literature adaptations: compact PLS and centred reaction norms."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.rice_baseline import DATA
from src.rice_context import REGRESSION as PREVIOUS, RISK, context_designs, context_prediction, prepare_context, save_environment_rankings
from src.rice_reliability import location_stability
from src.rice_validation import INPUTS, run_nested_benchmark

VERSION = "literature-compact-reaction-v1"
COMPACT = ["lit_mean_min_temperature_c", "lit_mean_temperature_c", "lit_mean_diurnal_range_c",
           "lit_mean_radiation_mj_m2_day", "lit_total_rain_mm", "lit_mean_vpd_approx_kpa"]
REGRESSION = (PREVIOUS
              + [{"name": f"Compact environment PLS components={n}", "kind": "compact_pls", "components": n,
                  "genetics": False} for n in [1, 2]]
              + [{"name": f"Compact environment Ridge alpha={a}", "kind": "compact_ridge", "alpha": a,
                  "genetics": False} for a in [1, 100]]
              + [{"name": f"Balanced environment + genome PLS components={n}", "kind": "balanced_pls",
                  "components": n, "genetics": True} for n in [1, 2]]
              + [{"name": f"Centred {'reaction norm' if interaction else 'genomic residual'} alpha={a}",
                  "kind": "centred", "alpha": a, "reaction": interaction, "genetics": True}
                 for interaction in [False, True] for a in [100, 1000]])


def prepare_literature(cutoff_days=60):
    frame, windows = prepare_context(cutoff_days)
    weather = pd.read_csv(DATA / "daily_weather.csv", parse_dates=["date"])
    rows = []
    for window in windows.itertuples(index=False):
        days = weather.loc[weather.environment_id.eq(window.environment_id) &
                           weather.date.between(window.seeding_date, window.forecast_date)]
        low, high = days.temperature_min_c, days.temperature_max_c
        saturation_low = 0.6108 * np.exp(17.27 * low / (low + 237.3))
        saturation_high = 0.6108 * np.exp(17.27 * high / (high + 237.3))
        vpd = ((saturation_low + saturation_high) / 2 * (1 - days.relative_humidity_percent / 100)).clip(lower=0)
        rows.append({"environment_id": window.environment_id,
                     "lit_mean_min_temperature_c": float(low.mean()),
                     "lit_mean_temperature_c": float(days.temperature_mean_c.mean()),
                     "lit_mean_diurnal_range_c": float((high - low).mean()),
                     "lit_mean_radiation_mj_m2_day": float(days.solar_radiation_mj_m2_day.mean()),
                     "lit_total_rain_mm": float(days.precipitation_mm_day.sum()),
                     "lit_mean_vpd_approx_kpa": float(vpd.mean())})
    return frame.merge(pd.DataFrame(rows), on="environment_id", validate="many_to_one"), windows


def literature_designs(training, testing, context, markers):
    # Preserve every previous candidate's original feature representation.
    original = [c for c in context if not c.startswith("lit_")]
    designs = context_designs(training, testing, original, markers)
    unique = training.drop_duplicates("environment_id")
    impute = SimpleImputer(strategy="median", keep_empty_features=True).fit(unique[COMPACT])
    scale = StandardScaler().fit(impute.transform(unique[COMPACT]))
    unique_values = scale.transform(impute.transform(unique[COMPACT]))
    ct, cv = scale.transform(impute.transform(training[COMPACT])), scale.transform(impute.transform(testing[COMPACT]))
    designs["compact"] = (ct, cv)
    pca = PCA(n_components=2, svd_solver="full").fit(unique_values)
    et, ev = pca.transform(ct), pca.transform(cv)
    gt, gv = designs["genomic_kernel"]
    designs["reaction"] = (np.c_[gt, (gt[:, :, None] * et[:, None, :]).reshape(len(gt), -1)],
                           np.c_[gv, (gv[:, :, None] * ev[:, None, :]).reshape(len(gv), -1)])
    designs["balanced"] = (np.c_[ct / np.sqrt(ct.shape[1]), gt / np.sqrt(gt.shape[1])],
                           np.c_[cv / np.sqrt(cv.shape[1]), gv / np.sqrt(gv.shape[1])])
    return designs


def _environment_prediction(candidate, training, designs):
    xt, xv = designs["compact"]
    first = ~training.environment_id.duplicated().to_numpy()
    targets = training.groupby("environment_id").yield_kg_ha.mean().reindex(training.loc[first, "environment_id"])
    if candidate["kind"] == "compact_ridge":
        estimator = Ridge(alpha=candidate["alpha"])
    else:
        estimator = PLSRegression(n_components=candidate.get("components", 1), scale=False)
    return np.asarray(estimator.fit(xt[first], targets).predict(xv)).reshape(-1)


def literature_prediction(candidate, training, testing, designs, context):
    kind = candidate["kind"]
    if kind in ["compact_pls", "compact_ridge"]:
        return _environment_prediction(candidate, training, designs)
    if kind == "balanced_pls":
        xt, xv = designs["balanced"]
        return np.asarray(PLSRegression(n_components=candidate["components"], scale=False)
                          .fit(xt, training.yield_kg_ha).predict(xv)).reshape(-1)
    if kind == "centred":
        base = _environment_prediction({"kind": "compact_pls", "components": 1}, training, designs)
        xt, xv = designs["reaction" if candidate["reaction"] else "genomic_kernel"]
        deviation = training.yield_kg_ha - training.groupby("environment_id").yield_kg_ha.transform("mean")
        counts = training.groupby("environment_id").environment_id.transform("size").to_numpy()
        weights = 1 / counts
        weights /= weights.mean()
        adjustment = Ridge(alpha=candidate["alpha"], fit_intercept=False).fit(xt, deviation, sample_weight=weights).predict(xv)
        return base + adjustment
    return context_prediction(candidate, training, testing, designs, context)


def _code_hashes():
    folder = Path(__file__).resolve().parent
    return {name: hashlib.sha256((folder / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            for name in ["rice_baseline.py", "rice_context.py", "rice_validation.py", "rice_reliability.py", "rice_literature.py"]}


def run_literature_benchmark(cutoff_days=60, progress=None):
    options = {"version": VERSION, "folder": "literature", "prepare": prepare_literature,
               "feature_prefixes": ("agro_", "plant_", "lit_"), "designs": literature_designs,
               "predict": literature_prediction, "regression": REGRESSION, "risk": RISK,
               "weather_name": "Literature environment selection", "full_name": "Literature full selection",
               "genetic_control": True, "summary": {"genetic_PC_count": None,
               "genetic_representation": "Full training-centred genomic relationship; optional two-environment-PC products",
               "protocol": "docs/Rice_Literature_Protocol.md", "new_candidates": 10, "previous_candidates": 13,
               "VPD_status": "Derived approximate proxy from daily temperatures and mean RH; not measured VPD",
               "risk_status": "Unchanged context risk grid; new compact features are not used for risk"}}
    metrics, predictions, folds, summary = run_nested_benchmark(cutoff_days, progress, experiment=options)
    frame, _ = prepare_literature(cutoff_days)
    directory = DATA / "literature" / f"day_{cutoff_days}"
    save_environment_rankings(predictions, directory)
    location_stability(predictions).to_csv(directory / "location_stability.csv", index=False)
    frame[["environment_id", *COMPACT]].drop_duplicates("environment_id").to_csv(directory / "compact_features.csv", index=False)
    pd.DataFrame({"feature": COMPACT, "unit": ["C", "C", "C", "MJ/m2/day", "mm", "kPa"],
                  "source": "daily_weather.csv", "window": f"Seeding day through day {cutoff_days}, inclusive"}).to_csv(
        directory / "compact_feature_catalogue.csv", index=False)
    summary.update(weather_feature_count=29, planting_feature_count=8, compact_feature_count=6,
                   code_sha256=_code_hashes())
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return metrics, predictions, folds, summary


def load_literature_results(cutoff_days=60):
    directory = DATA / "literature" / f"day_{cutoff_days}"
    path = directory / "summary.json"
    if not path.exists():
        return None
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("version") != VERSION or summary.get("code_sha256") != _code_hashes():
        return None
    for name in INPUTS:
        if not (DATA / name).exists() or hashlib.sha256((DATA / name).read_bytes()).hexdigest() != summary["source_sha256"].get(name):
            return None
    return pd.read_csv(directory / "metrics.csv"), pd.read_csv(directory / "held_out_predictions.csv"), pd.read_csv(directory / "location_metrics.csv"), summary
