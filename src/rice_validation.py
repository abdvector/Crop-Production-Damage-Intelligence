"""Declared, nested chronological comparison and model-appropriate diagnostics."""
import json
import math
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.rice_foundation import ROOT, SOURCE, OUT as FOUNDATION, CODE, YEAR, TARGET, LAGS, WEATHER, sha, validate
from src.rice_odisha_model import metrics

OUT = ROOT / "data/processed/rice/revised_modelling"
PROTOCOL = ROOT / "docs/Revised_Modelling_Protocol.md"
REFERENCE = "history_reference_yield_kg_ha"
TREND = "history_trend_kg_ha_per_year"
OUTER = list(range(2012, 2018))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")


def csv(name, frame):
    frame.to_csv(OUT / (name+".csv"), index=False, lineterminator="\n")


def configurations():
    result = [{"id": n, "family": "baseline", "weather": False, "parameters": {}}
              for n in ("Recent mean", "Last available yield", "Historical trend")]
    for weather in (False, True):
        prefix = "Weather" if weather else "History"
        for alpha in (1, 10, 100):
            result.append({"id": f"{prefix} Ridge alpha {alpha}", "family": "Ridge", "weather": weather,
                           "parameters": {"alpha": alpha}})
        for depth in (4, 8):
            result.append({"id": f"{prefix} Forest depth {depth}", "family": "Forest", "weather": weather,
                           "parameters": {"n_estimators": 300, "max_depth": depth, "min_samples_leaf": 10,
                                          "random_state": 42, "n_jobs": 2}})
        for penalty in (1, 10):
            result.append({"id": f"{prefix} Boosting L2 {penalty}", "family": "Boosting", "weather": weather,
                           "parameters": {"learning_rate": .05, "max_iter": 150, "max_leaf_nodes": 7,
                                          "min_samples_leaf": 15, "l2_regularization": penalty,
                                          "random_state": 42, "early_stopping": False}})
    return result


def columns(candidate, timing="full", redundant=False):
    names = LAGS + [YEAR]
    if candidate["weather"]:
        names += WEATHER if timing == "full" else [n for n in WEATHER if n.endswith(("_06", "_07"))]
    if redundant:
        names += [REFERENCE, TREND]
    return names


def fit_predict(candidate, train, future, codes, timing="full", redundant=False):
    if train.empty or future.empty or train[YEAR].max() > future[YEAR].min()-2:
        raise ValueError("Invalid chronological fitting cutoff")
    numeric = columns(candidate, timing, redundant)
    for part in (train, future):
        if not np.isfinite(part[numeric+[REFERENCE]].to_numpy()).all() or (part[REFERENCE] <= 0).any():
            raise ValueError("Invalid prediction inputs")
        if not set(part[CODE]).issubset(codes):
            raise ValueError("Unknown district")
    if not np.isfinite(train[TARGET]).all() or (train[TARGET] < 0).any():
        raise ValueError("Invalid fitting targets")
    # Future target deliberately not required or used: safe inference without Y.
    reference = future[REFERENCE].to_numpy()
    diagnostic = {"training_end_year": int(train[YEAR].max()), "training_rows": len(train)}
    if candidate["family"] == "baseline":
        values = {"Recent mean": reference, "Last available yield": future.yield_lag2.to_numpy(),
                  "Historical trend": reference+4*future[TREND].to_numpy()}[candidate["id"]]
        return np.maximum(values, 0), diagnostic
    array = train[numeric].to_numpy()
    spread = array.std(axis=0)
    if (spread == 0).any():
        raise ValueError("Constant numeric predictor needs explicit review")
    scaled = (array-array.mean(axis=0))/spread
    singular = np.linalg.svd(scaled, compute_uv=False)
    diagnostic.update({"numeric_rank": int(np.linalg.matrix_rank(scaled)), "numeric_columns": len(numeric),
                       "numeric_condition_number": float(singular[0]/max(singular[-1], 1e-12))})
    transform = ColumnTransformer([
        ("numeric", StandardScaler() if candidate["family"] == "Ridge" else "passthrough", numeric),
        ("district", OneHotEncoder(categories=[sorted(codes)], drop="first", handle_unknown="error", sparse_output=False), [CODE])])
    algorithm = {"Ridge": Ridge, "Forest": RandomForestRegressor, "Boosting": HistGradientBoostingRegressor}[candidate["family"]]
    model = Pipeline([("inputs", transform), ("model", algorithm(**candidate["parameters"]))])
    x = numeric + [CODE]
    with threadpool_limits(limits=2):
        model.fit(train[x], train[TARGET]-train[REFERENCE])
        predicted = np.maximum(reference+model.predict(future[x]), 0)
        fitting = np.maximum(train[REFERENCE]+model.predict(train[x]), 0)
    if not np.isfinite(predicted).all():
        raise ValueError("Nonfinite model prediction")
    diagnostic["fitting_mae_kg_ha"] = float(abs(fitting-train[TARGET]).mean())
    diagnostic["outside_training_range_cells"] = int(((future[numeric] < train[numeric].min()) |
                                                       (future[numeric] > train[numeric].max())).sum().sum())
    return predicted, diagnostic


def records(future, predicted, label, diagnostic):
    result = future[[CODE, "district_source", YEAR]].copy()
    result["candidate"] = label
    result["actual_yield_kg_ha"] = future[TARGET].to_numpy()
    result["predicted_yield_kg_ha"] = predicted
    result["reference_yield_kg_ha"] = future[REFERENCE].to_numpy()
    result["low_yield_threshold_kg_ha"] = .8*future[REFERENCE].to_numpy()
    for key, value in diagnostic.items():
        result[key] = value
    return result


def choose(predictions, candidates, years):
    scores = []
    for order, c in enumerate(candidates):
        part = predictions.loc[predictions.candidate.eq(c["id"]) & predictions[YEAR].isin(years)]
        if len(part) != 30*len(years):
            raise ValueError("Inner cohort mismatch")
        yearly = [metrics(g) for _, g in part.groupby(YEAR)]
        scores.append((np.mean([m["mae_kg_ha"] for m in yearly]),
                       np.mean([m["rmse_kg_ha"] for m in yearly]), order, c))
    return min(scores, key=lambda x: x[:3])[3]


def cached_predictions(frame, configs, codes, timing):
    rows, diagnostics = [], []
    for year in range(2008, 2018):
        train = frame.loc[frame[YEAR].between(2004, year-2)]
        future = frame.loc[frame[YEAR].eq(year)].sort_values(CODE)
        for c in configs:
            values, info = fit_predict(c, train, future, codes, timing)
            rows.append(records(future, values, c["id"], info))
            diagnostics.append({YEAR: year, "candidate": c["id"], "timing": timing, **info})
        print(f"{timing}: year {year}, 17 configurations, training through {year-2}", flush=True)
    return pd.concat(rows, ignore_index=True), pd.DataFrame(diagnostics)


def nested(predictions, configs, timing):
    rows, decisions = [], []
    for year in OUTER:
        inner = list(range(2008, year-1))
        groups = {"Nested selection": configs}
        groups.update({n: [c] for n in ("Recent mean", "Last available yield", "Historical trend") for c in configs if c["id"] == n})
        for family in ("Ridge", "Forest", "Boosting"):
            for weather in (False, True):
                groups[f"{'Weather' if weather else 'History'} {family}"] = [c for c in configs if c["family"] == family and c["weather"] == weather]
        for strategy, options in groups.items():
            selected = choose(predictions, options, inner)
            part = predictions.loc[predictions[YEAR].eq(year) & predictions.candidate.eq(selected["id"])].copy()
            part["selected_configuration"] = selected["id"]
            part["candidate"] = strategy
            rows.append(part)
            decisions.append({YEAR: year, "strategy": strategy, "selected_configuration": selected["id"],
                              "inner_first_year": min(inner), "inner_last_year": max(inner), "timing": timing})
    return pd.concat(rows, ignore_index=True), pd.DataFrame(decisions)


def score_tables(predictions):
    overall = pd.DataFrame([{"strategy": name, **metrics(g)} for name, g in predictions.groupby("candidate")])
    yearly = pd.DataFrame([{"strategy": name, YEAR: int(year), **metrics(g)}
                           for (name, year), g in predictions.groupby(["candidate", YEAR])])
    overall["equal_year_mae_kg_ha"] = overall.strategy.map(yearly.groupby("strategy").mae_kg_ha.mean())
    return overall, yearly


def paired_comparisons(predictions):
    pivot = predictions.assign(ae=lambda d: abs(d.predicted_yield_kg_ha-d.actual_yield_kg_ha)).groupby(
        [YEAR, "candidate"]).ae.mean().unstack()
    contrasts = [("Nested selection", n) for n in ("Recent mean", "Last available yield", "Historical trend")]
    contrasts += [(f"Weather {n}", f"History {n}") for n in ("Ridge", "Forest", "Boosting")]
    rows, years = [], []
    for model, reference in contrasts:
        difference = (pivot[reference]-pivot[model]).to_numpy()
        rng = np.random.default_rng(42)
        boot = rng.choice(difference, (2000, len(difference)), replace=True).mean(axis=1)
        rows.append({"model": model, "reference": reference, "mean_mae_improvement_kg_ha": float(difference.mean()),
                     "lower_95_exploratory": float(np.quantile(boot, .025)), "upper_95_exploratory": float(np.quantile(boot, .975)),
                     "years_improved": int((difference > 0).sum()), "years": len(difference)})
        for year, value in zip(pivot.index, difference):
            years.append({YEAR: int(year), "model": model, "reference": reference, "mae_improvement_kg_ha": value})
    csv("paired_year_differences", pd.DataFrame(years))
    return pd.DataFrame(rows)


def diagnose(predictions):
    weights = pd.read_csv(FOUNDATION / "spatial_diagnostic_weights.csv", index_col=0)
    weights.index = weights.index.astype(str)
    rows, spatial, bands = [], [], []
    for name, part in predictions.groupby("candidate"):
        part = part.copy()
        part["error"] = part.predicted_yield_kg_ha-part.actual_yield_kg_ha
        annual = part.groupby(YEAR).error.mean().to_numpy()
        bootstrap = np.random.default_rng(42).choice(annual, (2000, len(annual)), replace=True).mean(axis=1)
        previous = part[[CODE, YEAR, "error"]].assign(**{YEAR: lambda d: d[YEAR]+1})
        adjacent = part.merge(previous, on=[CODE, YEAR], suffixes=("", "_previous"), validate="one_to_one")
        rows.append({"strategy": name, "bias_kg_ha": float(part.error.mean()),
                     "bias_lower_95_exploratory": float(np.quantile(bootstrap, .025)),
                     "bias_upper_95_exploratory": float(np.quantile(bootstrap, .975)),
                     "lag1_error_correlation": float(adjacent.error.corr(adjacent.error_previous)),
                     "absolute_error_vs_prediction_spearman": float(stats.spearmanr(abs(part.error), part.predicted_yield_kg_ha).statistic),
                     "error_skewness_descriptive": float(stats.skew(part.error)),
                     "inference_status": "descriptive; short dependent panel, no iid assumption-pass claim"})
        quartile = pd.qcut(part.predicted_yield_kg_ha, 4, labels=False, duplicates="drop")
        for band, group in part.groupby(quartile):
            bands.append({"strategy": name, "prediction_quartile": int(band)+1, "records": len(group),
                          "bias_kg_ha": float(group.error.mean()), "mae_kg_ha": float(abs(group.error).mean())})
        for year, group in part.groupby(YEAR):
            group = group.set_index(CODE).reindex(weights.index)
            z = group.error.to_numpy(); z = z-z.mean()
            spatial.append({"strategy": name, YEAR: int(year), "moran_I_descriptive":
                            float(len(z)/weights.to_numpy().sum()*(z @ weights.to_numpy() @ z)/(z @ z))})
    csv("error_diagnostics", pd.DataFrame(rows))
    csv("spatial_error_diagnostics", pd.DataFrame(spatial))
    csv("error_by_prediction_quartile", pd.DataFrame(bands))
    district = pd.DataFrame([{"strategy": name, CODE: code, "district": g.district_source.iloc[0], **metrics(g)}
                             for (name, code), g in predictions.groupby(["candidate", CODE])])
    csv("district_metrics", district)


def sensitivities(frame, configs, decisions, primary, codes):
    rows = []
    lookup = {c["id"]: c for c in configs}
    for year in OUTER:
        selected = decisions.loc[decisions[YEAR].eq(year) & decisions.strategy.eq("Nested selection"), "selected_configuration"].iloc[0]
        candidate = lookup[selected]
        train = frame.loc[frame[YEAR].between(2004, year-2)]
        future = frame.loc[frame[YEAR].eq(year)].sort_values(CODE)
        influential = train.assign(deviation=lambda d: abs(d[TARGET]-d[REFERENCE])).groupby(YEAR).deviation.mean().idxmax()
        for label, subset, redundant in [("Redundant history representation", train, True),
                                          ("Remove unusual training year", train.loc[train[YEAR].ne(influential)], False)]:
            values, info = fit_predict(candidate, subset, future, codes, redundant=redundant)
            info["selected_configuration"] = selected
            info["training_year_removed"] = int(influential) if not redundant else None
            rows.append(records(future, values, label, info))
    combined = pd.concat(rows, ignore_index=True)
    csv("sensitivity_predictions", combined)
    base = primary.loc[primary.candidate.eq("Nested selection")]
    compare = []
    for name, part in combined.groupby("candidate"):
        paired = part.merge(base[[CODE, YEAR, "predicted_yield_kg_ha"]], on=[CODE, YEAR], suffixes=("", "_primary"), validate="one_to_one")
        compare.append({"sensitivity": name, **metrics(part), "mean_abs_prediction_change_kg_ha":
                        float(abs(paired.predicted_yield_kg_ha-paired.predicted_yield_kg_ha_primary).mean())})
    csv("sensitivity_metrics", pd.DataFrame(compare))


def interval_branch(cached, decisions):
    name = decisions.loc[decisions[YEAR].eq(2012) & decisions.strategy.eq("Nested selection"), "selected_configuration"].iloc[0]
    calibration = cached.loc[cached.candidate.eq(name) & cached[YEAR].between(2012, 2014)].copy()
    scores = abs(calibration.predicted_yield_kg_ha-calibration.actual_yield_kg_ha)/calibration.reference_yield_kg_ha
    q = float(np.sort(scores)[math.ceil((len(scores)+1)*.8)-1])
    test = cached.loc[cached.candidate.eq(name) & cached[YEAR].isin([2016, 2017])].copy()
    test["lower_80_kg_ha"] = np.maximum(test.predicted_yield_kg_ha-q*test.reference_yield_kg_ha, 0)
    test["upper_80_kg_ha"] = test.predicted_yield_kg_ha+q*test.reference_yield_kg_ha
    actual = test.actual_yield_kg_ha
    width = test.upper_80_kg_ha-test.lower_80_kg_ha
    test["covered"] = actual.between(test.lower_80_kg_ha, test.upper_80_kg_ha)
    test["interval_score_80"] = width+10*np.maximum(test.lower_80_kg_ha-actual, 0)+10*np.maximum(actual-test.upper_80_kg_ha, 0)
    csv("interval_calibration", calibration)
    csv("interval_evaluation", test)
    csv("interval_by_year", pd.DataFrame([{YEAR: int(year), "coverage": float(g.covered.mean()),
          "width_kg_ha": float((g.upper_80_kg_ha-g.lower_80_kg_ha).mean()), "interval_score_80": float(g.interval_score_80.mean())}
          for year, g in test.groupby(YEAR)]))
    return {"configuration_frozen_in_2012": name, "selection_labels": "2008–2010", "calibration_years": [2012, 2013, 2014],
            "evaluation_years": [2016, 2017], "calibration_records": len(calibration), "evaluation_records": len(test),
            "relative_half_width": q, "coverage_80": float(test.covered.mean()), "mean_width_kg_ha": float(width.mean()),
            "mean_interval_score_80": float(test.interval_score_80.mean()), "status": "separate exploratory fixed-configuration branch; no coverage guarantee"}


def figures(predictions, yearly, pairs):
    folder = OUT / "figures"; folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "svg.hashsalt": "rice-revised-v1", "axes.spines.top": False, "axes.spines.right": False})
    def save(fig, name):
        fig.savefig(folder / (name+".png"), dpi=180, bbox_inches="tight")
        fig.savefig(folder / (name+".svg"), bbox_inches="tight", metadata={"Date": None})
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5))
    for name in ("Nested selection", "Recent mean", "Last available yield", "Historical trend"):
        g = yearly.loc[yearly.strategy.eq(name)]
        ax.plot(g[YEAR], g.mae_kg_ha, marker="o", label=name)
    ax.set(xlabel="Agricultural start year", ylabel="MAE (kg/ha)", title="Chronological outer-fold errors: exploratory development study")
    ax.legend(frameon=False); save(fig, "01_yearly_errors")
    fig, ax = plt.subplots(figsize=(10, 5))
    weather = pairs.loc[pairs.model.str.startswith("Weather")].reset_index(drop=True)
    for i, row in weather.iterrows():
        ax.plot([row.lower_95_exploratory, row.upper_95_exploratory], [i, i], color="#225b96", linewidth=2)
        ax.plot(row.mean_mae_improvement_kg_ha, i, "o", color="#123d70")
    ax.axvline(0, color="black", linewidth=.8)
    ax.set(yticks=range(len(weather)), yticklabels=weather.model, xlabel="History MAE minus weather MAE (kg/ha); positive favours weather",
           title="Matched weather comparisons; exploratory year-bootstrap 95% intervals")
    save(fig, "02_weather_comparison")
    part = predictions.loc[predictions.candidate.eq("Nested selection")].copy()
    error = part.predicted_yield_kg_ha-part.actual_yield_kg_ha
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    axes[0, 0].scatter(part.actual_yield_kg_ha, part.predicted_yield_kg_ha, s=14, color="#225b96", alpha=.6)
    limit = max(part.actual_yield_kg_ha.max(), part.predicted_yield_kg_ha.max())
    axes[0, 0].plot([0, limit], [0, limit], color="black", linewidth=.8)
    axes[0, 0].set(xlabel="Observed yield (kg/ha)", ylabel="Predicted yield (kg/ha)", title="Forecast versus harvest")
    axes[0, 1].scatter(part.predicted_yield_kg_ha, error, s=14, color="#225b96", alpha=.6)
    axes[0, 1].axhline(0, color="black", linewidth=.8)
    axes[0, 1].set(xlabel="Predicted yield (kg/ha)", ylabel="Predicted minus observed (kg/ha)", title="Bias and functional form")
    axes[1, 0].scatter(part.predicted_yield_kg_ha, abs(error), s=14, color="#225b96", alpha=.6)
    axes[1, 0].set(xlabel="Predicted yield (kg/ha)", ylabel="Absolute error (kg/ha)", title="Changing error size")
    stats.probplot(error, plot=axes[1, 1]); axes[1, 1].set_title("Q–Q shape: descriptive, not an eligibility test")
    fig.suptitle("Nested selection: out-of-time error diagnostics, 2012–2017")
    save(fig, "03_error_diagnostics")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [Path(__file__), PROTOCOL, FOUNDATION / "audit.json", SOURCE / "prepared_inputs.csv",
             FOUNDATION / "spatial_diagnostic_weights.csv", ROOT / "src/rice_foundation.py", ROOT / "src/rice_odisha_model.py"]
    declaration = {"input_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths},
                   "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                                "scipy": scipy.__version__, "sklearn": sklearn.__version__},
                   "configurations": configurations(), "outer_years": OUTER,
                   "label": "exploratory nested redevelopment; no independent confirmation"}
    if (OUT / "run_manifest.json").exists():
        previous = json.loads((OUT / "run_manifest.json").read_text())
        if previous != declaration:
            raise ValueError("Frozen run changed: version rather than overwrite the completed study")
    else:
        write_json(OUT / "run_manifest.json", declaration)
    if (OUT / "completed.json").exists():
        receipt = json.loads((OUT / "completed.json").read_text())
        for key, value in receipt.items():
            if sha(OUT / key) != value:
                raise ValueError(f"Completed output changed: {key}")
        return json.loads((OUT / "summary.json").read_text())
    audit = json.loads((FOUNDATION / "audit.json").read_text())
    for section, base in (("input_sha256", ROOT), ("output_sha256", FOUNDATION)):
        if any(sha(base / key) != value for key, value in audit[section].items()):
            raise ValueError("Foundation receipt changed")
    dev = validate(pd.read_csv(SOURCE / "prepared_inputs.csv", dtype={CODE: str}))
    frame = dev.loc[dev[YEAR] >= 2004].copy()
    codes, configs = sorted(frame[CODE].unique()), configurations()
    cached, fitting = cached_predictions(frame, configs, codes, "full")
    primary, decisions = nested(cached, configs, "full")
    csv("configuration_predictions", cached); csv("fitting_diagnostics", fitting)
    csv("nested_predictions", primary); csv("nested_decisions", decisions)
    overall, yearly = score_tables(primary)
    csv("metrics", overall); csv("year_metrics", yearly)
    paired = paired_comparisons(primary); csv("paired_comparisons", paired)
    diagnose(primary)
    sensitivities(frame, configs, decisions, primary, codes)
    early, _ = cached_predictions(frame, configs, codes, "june_july")
    timing, timing_decisions = nested(early, configs, "june_july")
    csv("timing_configuration_predictions", early); csv("timing_nested_predictions", timing)
    csv("timing_decisions", timing_decisions); csv("timing_metrics", score_tables(timing)[0])
    interval = interval_branch(cached, decisions)
    figures(primary, yearly, paired)
    selected = overall.loc[overall.strategy.eq("Nested selection")].iloc[0].to_dict()
    summary = {"status": "completed exploratory nested comparison; not operationally cleared", "configurations": len(configs),
               "outer_years": OUTER, "outer_records_per_strategy": 180, "primary": selected,
               "interval_branch": interval, "assumptions_status": "data and chronology enforced; error adequacy measured, not universally passed",
               "assessment_2018_2022_read": False, "deployment_model_replaced": False}
    # JSON-safe undefined metrics are unavailable, not fabricated zero values.
    summary["primary"] = {k: None if pd.isna(v) else v for k, v in selected.items()}
    for path in OUT.rglob('*'):
        if path.suffix == '.svg':
            path.write_bytes(b'\n'.join(line.rstrip() for line in path.read_bytes().splitlines())+b'\n')
    write_json(OUT / "summary.json", summary)
    if any(sha(ROOT / key) != value for key, value in declaration["input_sha256"].items()):
        raise ValueError("Inputs changed during fitting")
    outputs = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in sorted(OUT.rglob('*'))
               if p.is_file() and p.name != 'completed.json'}
    write_json(OUT / "completed.json", outputs)
    return summary
