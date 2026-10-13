"""Declared regression experiment with development-only selection and 2019 assessment."""
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.rice_field_cohort import geographic_masks
from src.rice_field_data import FIELD_DATA

RESULTS = FIELD_DATA / "model"
PROTOCOL = FIELD_DATA / "field_model_protocol.json"


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def metrics(y, prediction):
    return {"records": len(y), "mae_kg_ha": float(mean_absolute_error(y, prediction)),
            "rmse_kg_ha": float(np.sqrt(mean_squared_error(y, prediction))),
            "r_squared": float(r2_score(y, prediction)) if len(y) > 1 else None,
            "bias_kg_ha": float(np.mean(np.asarray(prediction) - np.asarray(y)))}


def feature_matrix(records, protocol):
    numeric, categorical = protocol["numeric_features"], protocol["categorical_features"]
    if set(numeric + categorical) & {"year", "yield_kg_ha", "record_id", "harvest_date_audit_only"}:
        raise ValueError("Outcome, identifier or year in predictor allowlist")
    result = records[numeric + categorical].copy()
    for column in categorical:
        result[column] = result[column].fillna("unknown").astype(str)
    return result


def fit_predict(training, assessment, candidate, protocol):
    y = training[protocol["target"]].to_numpy()
    if candidate["kind"] == "mean":
        return np.full(len(assessment), y.mean())
    if candidate["kind"] == "state_mean":
        state_means = training.groupby("state")[protocol["target"]].mean()
        return assessment.state.map(state_means).fillna(y.mean()).to_numpy()
    categorical = protocol["categorical_preprocessing"]
    transform = ColumnTransformer([
        ("numeric", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), protocol["numeric_features"]),
        ("categorical", OneHotEncoder(handle_unknown=categorical["unknown"], min_frequency=categorical["min_frequency"],
                                      max_categories=categorical["max_categories"], sparse_output=False), protocol["categorical_features"]),
    ])
    if candidate["kind"] == "ridge":
        estimator = Ridge(alpha=candidate["alpha"], solver="lsqr")
    elif candidate["kind"] == "forest":
        estimator = RandomForestRegressor(n_estimators=candidate["n_estimators"], min_samples_leaf=candidate["min_samples_leaf"],
            max_features=candidate["max_features"], n_jobs=2, random_state=protocol["seed"])
    elif candidate["kind"] == "boosting":
        estimator = HistGradientBoostingRegressor(max_leaf_nodes=candidate["max_leaf_nodes"],
            min_samples_leaf=candidate["min_samples_leaf"], max_iter=candidate["max_iter"],
            learning_rate=candidate["learning_rate"], early_stopping=candidate["early_stopping"], random_state=protocol["seed"])
    else:
        raise ValueError("Unknown declared model")
    model = make_pipeline(transform, estimator)
    with threadpool_limits(limits=2):
        model.fit(feature_matrix(training, protocol), y)
        prediction = model.predict(feature_matrix(assessment, protocol))
    if not np.isfinite(prediction).all():
        raise ValueError("Nonfinite predictions")
    return prediction


def _prediction_rows(assessment, prediction, candidate, stage, fold):
    result = assessment[["record_id", "year", "state", "district_group"]].copy()
    result["observed_yield_kg_ha"] = assessment.yield_kg_ha.to_numpy()
    result["predicted_yield_kg_ha"] = prediction
    result["model"] = candidate["name"]
    result["stage"], result["fold"] = stage, fold
    return result


def _group_report(predictions, columns):
    output = []
    for keys, frame in predictions.groupby(columns, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        output.append({**dict(zip(columns, keys)), **metrics(frame.observed_yield_kg_ha, frame.predicted_yield_kg_ha)})
    return pd.DataFrame(output)


def _paired_stability(assessment, selected_name, seed):
    """Descriptive district bootstrap, not a calibrated prediction interval."""
    selected = assessment.loc[assessment.model.eq(selected_name)].set_index("record_id")
    baseline = assessment.loc[assessment.model.eq("Global training mean")].set_index("record_id")
    aligned = selected.join(baseline.predicted_yield_kg_ha.rename("baseline"), validate="one_to_one")
    aligned["selected_sse"] = (aligned.predicted_yield_kg_ha - aligned.observed_yield_kg_ha) ** 2
    aligned["baseline_sse"] = (aligned.baseline - aligned.observed_yield_kg_ha) ** 2
    groups = aligned.groupby("district_group").agg(n=("observed_yield_kg_ha", "size"),
        selected_sse=("selected_sse", "sum"), baseline_sse=("baseline_sse", "sum"))
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(groups), size=(2000, len(groups)))
    n = groups.n.to_numpy()[sampled].sum(axis=1)
    improvement = np.sqrt(groups.baseline_sse.to_numpy()[sampled].sum(axis=1) / n) - np.sqrt(groups.selected_sse.to_numpy()[sampled].sum(axis=1) / n)
    return {"district_groups": len(groups), "bootstrap_repeats": 2000,
            "rmse_gain_kg_ha_percentile_95_interval": np.quantile(improvement, [.025, .975]).tolist(),
            "fraction_resamples_with_positive_gain": float((improvement > 0).mean()),
            "qualification": "Descriptive district resampling; districts are not established independent or exchangeable units"}


def run_field_benchmark(progress=print):
    if (RESULTS / "assessment_metrics.csv").exists():
        raise ValueError("Assessment already completed; load the saved results. Do not reselect after viewing 2019.")
    if (RESULTS / "selection.json").exists():
        raise ValueError("A selection checkpoint exists; inspect it before restarting an interrupted assessment.")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    cohort_audit = json.loads((FIELD_DATA / "cohort_audit.json").read_text(encoding="utf-8"))
    for filename, key in [("cohort_local.csv", "cohort_sha256"), ("development_splits_local.csv", "splits_sha256")]:
        if _hash(FIELD_DATA / filename) != cohort_audit[key]:
            raise ValueError("Cohort or split hash changed after declaration")
    cohort = pd.read_csv(FIELD_DATA / "cohort_local.csv", low_memory=False)
    if not cohort.record_id.is_unique:
        raise ValueError("Duplicate record keys")
    split_file = pd.read_csv(FIELD_DATA / "development_splits_local.csv")
    development = cohort.loc[cohort.year.isin(protocol["development"]["geographic_years"])].merge(
        split_file[["record_id", "geographic_fold"]], on="record_id", validate="one_to_one")
    if development.year.eq(protocol["assessment"]["year"]).any() or len(development) != len(split_file):
        raise ValueError("Invalid development membership")
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows, folds = [], []
    split_plan = []
    for fold in range(protocol["development"]["geographic_folds"]):
        fitting, validation, purged = geographic_masks(development, fold)
        split_plan.append(("geographic", fold, development.loc[fitting], development.loc[validation], int(purged.sum())))
    split_plan.append(("temporal", 0,
        development.loc[development.year.eq(protocol["development"]["temporal_fit_year"])],
        development.loc[development.year.eq(protocol["development"]["temporal_validation_year"])], 0))
    for stage, fold, training, validation, purged in split_plan:
        for candidate in protocol["regression_candidates"]:
            progress(f"Development {stage} fold {fold}: {candidate['name']}")
            prediction = fit_predict(training, validation, candidate, protocol)
            rows.append(_prediction_rows(validation, prediction, candidate, stage, fold))
            folds.append({"stage": stage, "fold": fold, "model": candidate["name"], "fitting_records": len(training),
                          "purged_records": purged, **metrics(validation.yield_kg_ha, prediction)})
    predictions = pd.concat(rows, ignore_index=True)
    predictions.to_csv(RESULTS / "development_predictions_local.csv", index=False, lineterminator="\n")
    pd.DataFrame(folds).to_csv(RESULTS / "development_fold_metrics.csv", index=False, lineterminator="\n")
    aggregate = _group_report(predictions, ["stage", "model"])
    aggregate.to_csv(RESULTS / "development_metrics.csv", index=False, lineterminator="\n")
    score = aggregate.pivot(index="model", columns="stage", values="rmse_kg_ha")
    baseline = score.loc["Global training mean"]
    ranking = []
    for candidate in protocol["regression_candidates"]:
        name = candidate["name"]
        ranking.append({"model": name, "selection_objective": float(.5 * score.loc[name, "geographic"] / baseline.geographic
            + .5 * score.loc[name, "temporal"] / baseline.temporal)})
    ranking = pd.DataFrame(ranking).sort_values("selection_objective", kind="stable")
    ranking.to_csv(RESULTS / "development_selection.csv", index=False, lineterminator="\n")
    selected_name = ranking.iloc[0].model
    selected = next(c for c in protocol["regression_candidates"] if c["name"] == selected_name)
    selection = {"selected_candidate": selected, "selection_objective": float(ranking.iloc[0].selection_objective),
        "protocol_sha256": _hash(PROTOCOL), "cohort_sha256": cohort_audit["cohort_sha256"],
        "development_years": [2017, 2018], "assessment_used_for_selection": False}
    _json(RESULTS / "selection.json", selection)
    progress(f"Selection saved before assessment: {selected_name}")
    # Only now evaluate the selected configuration and prespecified mean baselines on 2019.
    assessment = cohort.loc[cohort.year.eq(protocol["assessment"]["year"])].copy()
    assessment["seen_state"] = assessment.state.isin(development.state)
    assessment["seen_district"] = assessment.district_group.isin(development.district_group)
    final_candidates = [c for c in protocol["regression_candidates"] if c["kind"] in ("mean", "state_mean") or c["name"] == selected_name]
    final_rows = []
    for candidate in final_candidates:
        progress(f"2019 assessment: {candidate['name']}")
        prediction = fit_predict(development, assessment, candidate, protocol)
        table = _prediction_rows(assessment, prediction, candidate, "assessment_2019", 0)
        table["seen_state"], table["seen_district"] = assessment.seen_state.to_numpy(), assessment.seen_district.to_numpy()
        final_rows.append(table)
    final = pd.concat(final_rows, ignore_index=True)
    final.to_csv(RESULTS / "assessment_predictions_local.csv", index=False, lineterminator="\n")
    _group_report(final, ["model"]).to_csv(RESULTS / "assessment_metrics.csv", index=False, lineterminator="\n")
    _group_report(final, ["model", "state"]).to_csv(RESULTS / "assessment_state_metrics.csv", index=False, lineterminator="\n")
    district_report = _group_report(final, ["model", "district_group"])
    district_report.to_csv(RESULTS / "assessment_district_metrics.csv", index=False, lineterminator="\n")
    macro = district_report.groupby("model")[['mae_kg_ha', 'rmse_kg_ha']].mean().add_prefix("macro_district_").reset_index()
    macro.to_csv(RESULTS / "assessment_macro_metrics.csv", index=False, lineterminator="\n")
    _group_report(final, ["model", "seen_state", "seen_district"]).to_csv(RESULTS / "assessment_transfer_metrics.csv", index=False, lineterminator="\n")
    summary = {"version": protocol["version"], "selected_model": selected_name, "development_records": len(development),
        "assessment_records": len(assessment), "assessment_year": protocol["assessment"]["year"],
        "assessment_unseen_state_records": int((~assessment.seen_state).sum()),
        "assessment_unseen_district_records": int((~assessment.seen_district).sum()),
        "numeric_predictors": protocol["numeric_features"], "categorical_predictors": protocol["categorical_features"],
        "new_model_trained": True, "risk_model_trained": False, "prospective_validation": False,
        "protocol_sha256": _hash(PROTOCOL), "cohort_sha256": cohort_audit["cohort_sha256"],
        "selection_sha256": _hash(RESULTS / "selection.json"), "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__, "numpy_version": np.__version__, "pandas_version": pd.__version__,
        "paired_district_stability": _paired_stability(final, selected_name, protocol["seed"]),
        "limitations": ["Retrospective backtest with farmer-reported yield; moisture convention unresolved",
            "2019 combines year transfer with new states/districts", "No verified management-rate, aluminium or molecular predictors",
            "Repeated signatures retained; farm independence not established", "No calibrated prediction intervals or new field risk model",
            "Single final assessment; future changes cannot reuse 2019 as an untouched test"]}
    _json(RESULTS / "summary.json", summary)
    progress("Field regression assessment complete")
    return summary


def load_field_results():
    summary = RESULTS / "summary.json"
    if not summary.exists():
        return None
    return json.loads(summary.read_text(encoding="utf-8")), pd.read_csv(RESULTS / "assessment_metrics.csv"), pd.read_csv(RESULTS / "development_selection.csv")


def audit_assessment_labels():
    """Diagnostic using a previously declared source flag; no refitting or selection."""
    cohort = pd.read_csv(FIELD_DATA / "cohort_local.csv", low_memory=False)
    predictions = pd.read_csv(RESULTS / "assessment_predictions_local.csv")
    predictions = predictions.merge(cohort[["record_id", "yield_above_15000_review_flag"]], on="record_id", validate="many_to_one")
    diagnostic, influence = [], []
    for name, frame in predictions.groupby("model"):
        unflagged = frame.loc[~frame.yield_above_15000_review_flag]
        diagnostic.append({"model": name, "analysis": "Previously flagged yield records omitted; diagnostic only, predictions unchanged",
                           **metrics(unflagged.observed_yield_kg_ha, unflagged.predicted_yield_kg_ha)})
        squared = (frame.observed_yield_kg_ha - frame.predicted_yield_kg_ha) ** 2
        influence.append({"model": name, "flagged_records": int(frame.yield_above_15000_review_flag.sum()),
            "flagged_fraction_of_squared_error": float(squared[frame.yield_above_15000_review_flag].sum() / squared.sum())})
    pd.DataFrame(diagnostic).to_csv(RESULTS / "assessment_label_sensitivity.csv", index=False, lineterminator="\n")
    pd.DataFrame(influence).to_csv(RESULTS / "assessment_label_influence.csv", index=False, lineterminator="\n")
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    summary["assessment_label_audit"] = {"preexisting_review_threshold_kg_ha": 15000,
        "flagged_assessment_records": int(cohort.loc[cohort.year.eq(2019), "yield_above_15000_review_flag"].sum()),
        "maximum_source_yield_kg_ha": float(cohort.loc[cohort.year.eq(2019), "yield_kg_ha"].max()),
        "diagnostic_refitting": False, "assessment_selection_changed": False,
        "qualification": "Threshold was a source audit flag, not a validated biological exclusion; sensitivity is not a new untouched test"}
    _json(RESULTS / "summary.json", summary)
    return summary["assessment_label_audit"]
