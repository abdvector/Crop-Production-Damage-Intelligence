"""Nested location validation for a fixed, conservative rice model search."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from src.rice_baseline import DATA, prepare_data

VERSION = "nested-location-v1"
INPUTS = ["yield_observations_audited.csv", "daily_weather.csv", "genotype_marker_calls.csv",
          "marker_metadata.csv", "trial_metadata.csv"]
REGRESSION = ([{"name": "Training mean", "kind": "mean", "genetics": False}]
              + [{"name": f"Weather Ridge alpha={a}", "kind": "ridge", "alpha": a, "genetics": False}
                 for a in [100, 1000, 10000]]
              + [{"name": f"Weather + genetic PCs Ridge alpha={a}", "kind": "ridge", "alpha": a, "genetics": True}
                 for a in [100, 1000, 10000]]
              + [{"name": f"Weather x genetic PCs Ridge alpha={a}", "kind": "ridge", "alpha": a,
                  "genetics": True, "interactions": True} for a in [1000, 10000]]
              + [{"name": f"Environment forest leaf={n}", "kind": "forest", "leaf": n, "genetics": False}
                 for n in [2, 4]])
RISK = ([{"name": "Training prevalence", "kind": "prevalence", "genetics": False}]
        + [{"name": f"{'Weather + genetic PCs' if g else 'Weather'} logistic C={c}",
            "kind": "logistic", "C": c, "genetics": g} for g in [False, True] for c in [0.001, 0.01]])


def _designs(training, testing, weather, markers):
    """All fitted state comes from training; no validation/test target is read."""
    unique_weather = training.drop_duplicates("environment_id")
    weather_scale = StandardScaler().fit(unique_weather[weather])
    wt = weather_scale.transform(training[weather])
    wv = weather_scale.transform(testing[weather])
    unique_genetics = training.drop_duplicates("genotype_id")
    marker_scale = StandardScaler().fit(unique_genetics[markers])
    pca = PCA(n_components=5, svd_solver="randomized", random_state=42)
    pca.fit(marker_scale.transform(unique_genetics[markers]))
    gt = pca.transform(marker_scale.transform(training[markers]))
    gv = pca.transform(marker_scale.transform(testing[markers]))
    genetic_scale = StandardScaler().fit(pca.transform(marker_scale.transform(unique_genetics[markers])))
    gt, gv = genetic_scale.transform(gt), genetic_scale.transform(gv)
    designs = {}
    for name, xt, xv in [("weather", wt, wv), ("genetic", np.c_[wt, gt], np.c_[wv, gv]),
                         ("interaction", np.c_[wt, gt, (wt[:, :, None] * gt[:, None, :]).reshape(len(wt), -1)],
                          np.c_[wv, gv, (wv[:, :, None] * gv[:, None, :]).reshape(len(wv), -1)])]:
        scale = StandardScaler().fit(xt)
        designs[name] = (scale.transform(xt), scale.transform(xv))
    return designs


def _key(candidate):
    return "interaction" if candidate.get("interactions") else "genetic" if candidate["genetics"] else "weather"


def _regression(candidate, training, testing, designs, weather):
    if candidate["kind"] == "mean":
        return np.full(len(testing), training.yield_kg_ha.mean())
    if candidate["kind"] == "forest":
        # One fitting observation per actual environment, irrespective of plot count.
        environments = training.groupby("environment_id", sort=True)
        x = environments[weather].first()
        y = environments.yield_kg_ha.mean().reindex(x.index)
        estimator = RandomForestRegressor(n_estimators=128, min_samples_leaf=candidate["leaf"],
                                          random_state=42, n_jobs=1)
        return estimator.fit(x, y).predict(testing[weather])
    xt, xv = designs[_key(candidate)]
    return Ridge(alpha=candidate["alpha"]).fit(xt, training.yield_kg_ha).predict(xv)


def _risk(candidate, training, testing, designs):
    threshold = float(training.yield_kg_ha.quantile(0.2))
    labels = training.yield_kg_ha.lt(threshold).astype(int).to_numpy()
    if candidate["kind"] == "prevalence" or len(np.unique(labels)) < 2:
        return np.full(len(testing), labels.mean()), threshold
    xt, xv = designs[_key(candidate)]
    estimator = LogisticRegression(C=candidate["C"], max_iter=2000, random_state=42)
    return estimator.fit(xt, labels).predict_proba(xv)[:, 1], threshold


def _inner_selection(training, weather, markers, regression_candidates=None, risk_candidates=None,
                     design_builder=_designs, regression_predictor=_regression, risk_predictor=_risk):
    regression_candidates = REGRESSION if regression_candidates is None else regression_candidates
    risk_candidates = RISK if risk_candidates is None else risk_candidates
    scores = {c["name"]: [] for c in regression_candidates + risk_candidates}
    for group in sorted(training.location_group.unique()):
        fit = training.loc[training.location_group.ne(group)]
        validate = training.loc[training.location_group.eq(group)]
        assert set(fit.location_group).isdisjoint(validate.location_group)
        designs = design_builder(fit, validate, weather, markers)
        for candidate in regression_candidates:
            pred = regression_predictor(candidate, fit, validate, designs, weather)
            scores[candidate["name"]].append(float(mean_squared_error(validate.yield_kg_ha, pred)))
        for candidate in risk_candidates:
            prob, threshold = risk_predictor(candidate, fit, validate, designs)
            scores[candidate["name"]].append(float(brier_score_loss(validate.yield_kg_ha.lt(threshold), prob)))
    averages = {name: float(np.mean(values)) for name, values in scores.items()}
    weather_best = min([c for c in regression_candidates if not c["genetics"]], key=lambda c: averages[c["name"]])
    full_best = min(regression_candidates, key=lambda c: averages[c["name"]])
    risk_best = min(risk_candidates, key=lambda c: averages[c["name"]])
    return weather_best, full_best, risk_best, averages


def _metrics(actual, predicted):
    return {"MAE_kg_ha": float(mean_absolute_error(actual, predicted)),
            "RMSE_kg_ha": float(np.sqrt(mean_squared_error(actual, predicted))),
            "R2": float(r2_score(actual, predicted)), "bias_kg_ha": float(np.mean(predicted - actual)),
            "Pearson_r": float(np.corrcoef(actual, predicted)[0, 1]) if np.std(actual) > 1e-8 and np.std(predicted) > 1e-8 else np.nan}


def run_nested_benchmark(cutoff_days=60, progress=None, experiment=None):
    options = experiment or {}
    frame, windows = options.get("prepare", prepare_data)(cutoff_days)
    weather = [c for c in frame if c.startswith(options.get("feature_prefixes", ("weather_",)))]
    markers = [c for c in frame if c.startswith("snp_")]
    candidates = options.get("regression", REGRESSION)
    risks_candidates = options.get("risk", RISK)
    design_builder = options.get("designs", _designs)
    regression_predictor = options.get("predict", _regression)
    weather_name = options.get("weather_name", "Nested weather selection")
    full_name = options.get("full_name", "Nested weather + genetics selection")
    predictions, folds, tuning, diagnostics = [], [], [], []
    groups = sorted(frame.location_group.unique())
    for number, group in enumerate(groups, 1):
        if progress:
            progress(number, len(groups), group)
        training = frame.loc[frame.location_group.ne(group)]
        testing = frame.loc[frame.location_group.eq(group)]
        assert set(training.location_group).isdisjoint(testing.location_group)
        weather_best, full_best, risk_best, averages = _inner_selection(
            training, weather, markers, candidates, risks_candidates, design_builder, regression_predictor)
        designs = design_builder(training, testing, weather, markers)
        for candidate in candidates + risks_candidates:
            tuning.append({"held_out_location": group, "candidate": candidate["name"],
                           "task": "regression" if candidate in candidates else "risk",
                           "inner_mean_location_score": averages[candidate["name"]],
                           "selected_weather": candidate == weather_best,
                           "selected_full": candidate == full_best, "selected_risk": candidate == risk_best,
                           "inner_location_count": training.location_group.nunique()})
        procedures = [("Training mean", candidates[0]), (weather_name, weather_best), (full_name, full_best)]
        if options.get("genetic_control"):
            genetic_best = min([c for c in candidates if c["kind"] in ["mean", "genomic"]], key=lambda c: averages[c["name"]])
            procedures.append(("Full-SNP genomic control", genetic_best))
        for name, candidate in procedures:
            pred = regression_predictor(candidate, training, testing, designs, weather)
            records = testing[["source_csv_row", "genotype_id", "environment_id", "country", "location", "year", "season"]].copy()
            records["model"], records["held_out_location"], records["selected_candidate"] = name, group, candidate["name"]
            records["observed_yield_kg_ha"] = testing.yield_kg_ha
            records["predicted_yield_kg_ha"] = pred
            predictions.extend(records.to_dict("records"))
            folds.append({"model": name, "held_out_location": group, "selected_candidate": candidate["name"],
                          "train_records": len(training), "test_records": len(testing),
                          **_metrics(testing.yield_kg_ha.to_numpy(), pred)})
        prob, threshold = _risk(risk_best, training, testing, designs)
        prevalence = float(training.yield_kg_ha.lt(threshold).mean())
        risk_rows = testing[["source_csv_row", "genotype_id", "environment_id"]].copy()
        risk_rows["model"], risk_rows["held_out_location"] = "Nested low-yield risk", group
        risk_rows["selected_candidate"] = risk_best["name"]
        risk_rows["low_yield_threshold_kg_ha"] = threshold
        risk_rows["observed_low_yield"] = testing.yield_kg_ha.lt(threshold).astype(int)
        risk_rows["predicted_low_yield_probability"] = prob
        risk_rows["training_prevalence_probability"] = prevalence
        predictions.extend(risk_rows.to_dict("records"))
        numeric = training[weather].select_dtypes(include="number").columns
        outside = (testing[numeric] < training[numeric].min()) | (testing[numeric] > training[numeric].max())
        diagnostics.append({"held_out_location": group, "test_records": len(testing),
                            "weather_features_outside_training_range": int(outside.any().sum()),
                            "fraction_records_outside_weather_range": float(outside.any(axis=1).mean()),
                            "risk_candidate": risk_best["name"],
                            "risk_Brier": float(brier_score_loss(risk_rows.observed_low_yield, prob)),
                            "prevalence_Brier": float(brier_score_loss(risk_rows.observed_low_yield, np.full(len(testing), prevalence)))})
    predictions, folds = pd.DataFrame(predictions), pd.DataFrame(folds)
    metrics = []
    for name in folds.model.unique():
        rows = predictions.loc[predictions.model.eq(name)]
        per_location = folds.loc[folds.model.eq(name)]
        metrics.append({"model": name, **_metrics(rows.observed_yield_kg_ha.to_numpy(), rows.predicted_yield_kg_ha.to_numpy()),
                        "equal_location_RMSE_kg_ha": float(np.sqrt(np.mean(per_location.RMSE_kg_ha ** 2)))})
    risks = predictions.loc[predictions.model.eq("Nested low-yield risk")]
    summary = {"version": options.get("version", VERSION), "cutoff_days_after_seeding_inclusive": cutoff_days,
               "records": len(frame), "genotypes": int(frame.genotype_id.nunique()),
               "environments": int(frame.environment_id.nunique()), "held_out_locations": len(groups),
               "weather_feature_count": len(weather), "marker_feature_count": len(markers), "genetic_PC_count": 5,
               "selection": "Inner leave-one-location-out; equal-location MSE/Brier; fixed candidate grid",
               "regression_candidates": candidates, "risk_candidates": risks_candidates,
               "low_yield_definition": "Yield below the 20th percentile of each training split; fold-specific thresholds",
               "risk_Brier": float(brier_score_loss(risks.observed_low_yield, risks.predicted_low_yield_probability)),
               "prevalence_Brier": float(brier_score_loss(risks.observed_low_yield, risks.training_prevalence_probability)),
               "source_sha256": {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest() for name in INPUTS},
               "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "software_versions": {"sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
               "limits": ["Development dataset already inspected; no independent external test",
                          "Only 12 locations and 15 weather environments; location/year confounding",
                          "Published adjusted yield targets and source-prefiltered SNPs",
                          "Repeated genotypes may occur in training and testing at different locations",
                          "No linked soil/Al or verified variety-specific protein inputs",
                          "Low-yield probabilities not externally calibrated; no causal damage or monetary estimate"]}
    summary.update(options.get("summary", {}))
    directory = DATA / options.get("folder", "nested") / f"day_{cutoff_days}"
    directory.mkdir(parents=True, exist_ok=True)
    metric_table = pd.DataFrame(metrics).rename(columns={"Pearson_r": "pooled_Pearson_r"})
    metric_table.to_csv(directory / "metrics.csv", index=False)
    predictions.to_csv(directory / "held_out_predictions.csv", index=False)
    folds.to_csv(directory / "location_metrics.csv", index=False)
    pd.DataFrame(tuning).to_csv(directory / "inner_selection_scores.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(directory / "location_diagnostics.csv", index=False)
    windows.to_csv(directory / "forecast_windows.csv", index=False)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return metric_table, predictions, folds, summary


def load_nested_results(cutoff_days=60):
    directory = DATA / "nested" / f"day_{cutoff_days}"
    if not (directory / "summary.json").exists():
        return None
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    if summary.get("version") != VERSION:
        return None
    for name, expected in summary["source_sha256"].items():
        path = DATA / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return None
    return (pd.read_csv(directory / "metrics.csv"), pd.read_csv(directory / "held_out_predictions.csv"),
            pd.read_csv(directory / "location_metrics.csv"), summary)
