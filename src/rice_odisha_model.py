"""Declared temporal comparison and gated assessment for Odisha Kharif rice."""
import json
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.rice_odisha_seasonal import ROOT, OUT as DATA, PARAMETERS, digest, freeze_protocol, write_json

OUT = DATA / "model"
YEAR = "agricultural_start_year"
CODE = "district_code_census2011"
TARGET = "yield_kg_ha"
REFERENCE = "history_reference_yield_kg_ha"
TREND = "history_trend_kg_ha_per_year"
LAGS = [f"yield_lag{i}" for i in range(2, 7)]
HISTORY = LAGS + [REFERENCE, TREND, YEAR]
WEATHER = [f"{p}_{month:02d}" for month in (6, 7, 8) for p in PARAMETERS] + [
    "longest_dry_spell_days", "wet_days", "max_five_day_rain_mm", "tmax_p95_c"]
NOTE = ROOT / "docs/Rice_Odisha_Model_Implementation.md"


def candidates():
    rows = [{"id": name, "algorithm": "baseline", "weather": False, "parameters": {}}
            for name in ("Recent mean", "Last available yield", "Historical trend")]
    for weather in (False, True):
        for alpha in (1, 10, 100):
            rows.append({"id": f"{'Weather' if weather else 'History'} Ridge alpha {alpha}",
                         "algorithm": "ridge", "weather": weather, "parameters": {"alpha": alpha}})
    for depth in (4, 8):
        rows.append({"id": f"Weather Random Forest depth {depth}", "algorithm": "forest", "weather": True,
                     "parameters": {"n_estimators": 300, "min_samples_leaf": 10, "max_depth": depth,
                                    "random_state": 42, "n_jobs": 2}})
    for penalty in (1, 10):
        rows.append({"id": f"Weather histogram boosting L2 {penalty}", "algorithm": "boosting", "weather": True,
                     "parameters": {"learning_rate": .05, "max_iter": 150, "max_leaf_nodes": 7,
                                    "min_samples_leaf": 15, "l2_regularization": penalty,
                                    "random_state": 42, "early_stopping": False}})
    return rows


def _csv(name, frame):
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / name, index=False, lineterminator="\n")


def _read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def verify_inputs():
    protocol = freeze_protocol()
    receipt = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    for name, value in receipt["output_sha256"].items():
        if digest(ROOT / name) != value:
            raise ValueError(f"Prepared input changed: {name}")
    if max(protocol["development_validation_years"])+2 > min(protocol["calibration_years"]):
        raise ValueError("Selection labels would be unavailable for calibration")
    if max(protocol["calibration_years"])+2 > min(protocol["assessment_years_reserved"]):
        raise ValueError("Calibration labels would be unavailable for first assessment")
    return protocol


def execution_manifest():
    return {"protocol": verify_inputs(), "candidates": candidates(),
            "input_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in
                             [DATA / "prepared_inputs.csv", DATA / "protocol.json", NOTE, Path(__file__)]},
            "versions": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__, "scikit_learn": sklearn.__version__}}


def load_development():
    frame = pd.read_csv(DATA / "prepared_inputs.csv", dtype={CODE: str})
    if frame.loc[frame[YEAR] >= 2018, TARGET].notna().any():
        raise ValueError("Reserved labels appeared in original preparation")
    frame = frame.loc[frame[YEAR].between(2004, 2017)].copy()
    if len(frame) != 420 or not np.isfinite(frame[HISTORY + WEATHER + [TARGET]].to_numpy()).all():
        raise ValueError("Development requires the same 420 complete rows for every candidate")
    if frame.duplicated([CODE, YEAR]).any() or (frame[REFERENCE] <= 0).any() or (frame[TARGET] < 0).any():
        raise ValueError("Invalid development key or yield reference")
    return frame


def estimator(candidate, district_codes):
    numeric = HISTORY + (WEATHER if candidate["weather"] else [])
    transform = ColumnTransformer([
        ("numeric", StandardScaler() if candidate["algorithm"] == "ridge" else "passthrough", numeric),
        ("district", OneHotEncoder(categories=[sorted(district_codes)], handle_unknown="error", sparse_output=False), [CODE]),
    ], remainder="drop", sparse_threshold=0)
    algorithm = {"ridge": Ridge, "forest": RandomForestRegressor, "boosting": HistGradientBoostingRegressor}[candidate["algorithm"]]
    return Pipeline([("inputs", transform), ("model", algorithm(**candidate["parameters"]))])


def predict(candidate, train, future, district_codes):
    if train.empty or future.empty or train[YEAR].max() > future[YEAR].min()-2:
        raise ValueError("Training must end at least two start-years before forecasting")
    required = HISTORY + (WEATHER if candidate["weather"] else [])
    if not np.isfinite(future[required].to_numpy()).all():
        raise ValueError("Incomplete inference predictors")
    reference = future[REFERENCE].to_numpy()
    if candidate["algorithm"] == "baseline":
        result = {"Recent mean": reference, "Last available yield": future.yield_lag2.to_numpy(),
                  "Historical trend": reference + 4*future[TREND].to_numpy()}[candidate["id"]]
    else:
        model = estimator(candidate, district_codes)
        # Only the explicit X whitelist enters preprocessing. Future target/area/production never enter it.
        x_columns = required + [CODE]
        with threadpool_limits(limits=2):
            model.fit(train[x_columns], train[TARGET]-train[REFERENCE])
            result = reference + model.predict(future[x_columns])
    result = np.maximum(np.asarray(result, dtype=float), 0)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite prediction")
    return result


def rolling_predictions(frame, years, configurations):
    rows = []
    codes = sorted(frame[CODE].unique())
    for year in years:
        train = frame.loc[frame[YEAR].between(2004, year-2)]
        future = frame.loc[frame[YEAR].eq(year)].sort_values(CODE)
        if future.empty:
            continue
        for candidate in configurations:
            values = predict(candidate, train, future, codes)
            for record, value in zip(future.to_dict("records"), values):
                rows.append({CODE: record[CODE], "district_source": record["district_source"], YEAR: int(year),
                             "candidate": candidate["id"], "actual_yield_kg_ha": record[TARGET],
                             "predicted_yield_kg_ha": float(value), "reference_yield_kg_ha": record[REFERENCE],
                             "low_yield_threshold_kg_ha": .8*record[REFERENCE],
                             "training_end_year": int(train[YEAR].max()), "training_rows": len(train)})
        print(f"Odisha comparison year {year}: {len(future)} forecasts per candidate, {len(train)} fitting rows", flush=True)
    return pd.DataFrame(rows)


def metrics(frame):
    actual = frame.actual_yield_kg_ha.to_numpy()
    predicted = frame.predicted_yield_kg_ha.to_numpy()
    error = predicted-actual
    denominator = float(np.square(actual-actual.mean()).sum())
    low = actual < frame.low_yield_threshold_kg_ha.to_numpy()
    flag = predicted < frame.low_yield_threshold_kg_ha.to_numpy()
    tp, fp, fn, tn = [int(v) for v in ((low & flag).sum(), (~low & flag).sum(), (low & ~flag).sum(), (~low & ~flag).sum())]
    return {"records": len(frame), "mae_kg_ha": float(np.abs(error).mean()),
            "rmse_kg_ha": float(np.sqrt(np.square(error).mean())), "bias_kg_ha": float(error.mean()),
            "r_squared": 1-float(np.square(error).sum())/denominator if denominator > 0 else None,
            "wape": float(np.abs(error).sum()/np.abs(actual).sum()) if np.abs(actual).sum() > 0 else None,
            "low_yield_count": int(low.sum()), "flagged_count": int(flag.sum()),
            "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
            "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
            "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            "both_outcome_classes_present": bool(low.any() and (~low).any())}


def comparison_tables(predictions):
    annual = pd.DataFrame([{YEAR: int(year), "candidate": name, **metrics(group)}
                           for (year, name), group in predictions.groupby([YEAR, "candidate"])])
    order = {c["id"]: i for i, c in enumerate(candidates())}
    overall = []
    for name, group in predictions.groupby("candidate"):
        years = annual.loc[annual.candidate.eq(name)]
        overall.append({"candidate": name, "candidate_order": order[name],
                        "equal_year_mae_kg_ha": float(years.mae_kg_ha.mean()),
                        "equal_year_rmse_kg_ha": float(years.rmse_kg_ha.mean()), **metrics(group)})
    ranked = pd.DataFrame(overall).sort_values(["equal_year_mae_kg_ha", "equal_year_rmse_kg_ha", "candidate_order"])
    return ranked, annual


def verify_selection():
    selected = _read("selection.json")
    if selected["execution_manifest"] != execution_manifest():
        raise ValueError("Frozen model code, inputs, configuration or runtime changed after selection")
    for name, value in selected["development_output_sha256"].items():
        if digest(OUT / name) != value:
            raise ValueError(f"Frozen development result changed: {name}")
    return selected


def run_development():
    if (OUT / "selection.json").exists():
        return verify_selection()
    if (OUT / "assessment_source_labels.csv").exists():
        raise ValueError("Assessment has been opened; do not rerun model selection")
    manifest = execution_manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT / "execution_manifest.json"
    if receipt.exists() and _read(receipt.name) != manifest:
        raise ValueError("Declared execution changed; preserve and version the earlier run")
    write_json(receipt, manifest)
    frame = load_development()
    configs = candidates()
    development = rolling_predictions(frame, manifest["protocol"]["development_validation_years"], configs)
    ranked, annual = comparison_tables(development)
    choice = next(c for c in configs if c["id"] == ranked.iloc[0].candidate)
    calibration = rolling_predictions(frame, manifest["protocol"]["calibration_years"], [choice])
    scores = np.abs(calibration.actual_yield_kg_ha-calibration.predicted_yield_kg_ha)/calibration.reference_yield_kg_ha
    rank = min(len(scores), math.ceil((len(scores)+1)*.8))
    q = float(np.sort(scores)[rank-1])
    calibration["lower_80_kg_ha"] = np.maximum(0, calibration.predicted_yield_kg_ha-q*calibration.reference_yield_kg_ha)
    calibration["upper_80_kg_ha"] = calibration.predicted_yield_kg_ha+q*calibration.reference_yield_kg_ha
    for name, table in (("development_predictions.csv", development), ("development_metrics.csv", ranked),
                        ("development_year_metrics.csv", annual), ("calibration_predictions.csv", calibration)):
        _csv(name, table)
    history_id = ranked.loc[ranked.candidate.str.startswith("History Ridge")].iloc[0].candidate
    weather_id = ranked.loc[ranked.candidate.str.startswith("Weather Ridge")].iloc[0].candidate
    result = {"execution_manifest": manifest, "selected_candidate": choice, "history_ridge_control": history_id,
              "weather_ridge_control": weather_id, "interval_relative_half_width": q, "calibration_records": len(scores),
              "calibration_order_statistic_rank": rank, "latest_calibration_target_year": int(calibration[YEAR].max()),
              "assessment_outcomes_opened": False,
              "development_output_sha256": {name: digest(OUT / name) for name in
                    ["execution_manifest.json", "development_predictions.csv", "development_metrics.csv",
                     "development_year_metrics.csv", "calibration_predictions.csv"]}}
    write_json(OUT / "selection.json", result)
    return result


def unlock_assessment_labels(selection):
    from src.rice_seasonal_data import REPORT, _read_report, _number

    # This is the only function allowed to open the reserved numeric report.
    if selection != verify_selection():
        raise ValueError("Selection must be verified before source access")
    receipt = json.loads((DATA.parent / "seasonal_source/download_manifest.json").read_text(encoding="utf-8"))
    if digest(REPORT) != receipt["sha256"]:
        raise ValueError("Original official seasonal report changed")
    years, rows = _read_report()
    wanted = set(selection["execution_manifest"]["protocol"]["assessment_years_reserved"])
    records = []
    for row in rows:
        if row[1]["text"] != "Odisha":
            continue
        district = row[2]["text"]
        for j, year in enumerate(years):
            if year not in wanted:
                continue
            area, production, source_yield = [_number(c["text"]) for c in row[3+j*3:6+j*3]]
            reason, converted, difference = "", None, None
            if any(v is None for v in (area, production, source_yield)):
                reason = "missing official area, production or yield"
            elif area <= 0 or production < 0 or source_yield < 0:
                reason = "nonpositive area or negative production/yield"
            else:
                converted = source_yield*1000
                difference = abs(converted-1000*production/area)
                if difference > 5.01:
                    reason = "yield and production/area exceed declared rounding tolerance"
            records.append({"district_source": district, YEAR: year, "area_ha_audit_only": area,
                            "production_tonnes_audit_only": production, "source_yield_tonnes_ha": source_yield,
                            TARGET: converted, "rounding_difference_kg_ha": difference,
                            "valid_target": not reason, "exclusion_reason": reason})
    labels = pd.DataFrame(records)
    if len(labels) != 150 or labels.duplicated(["district_source", YEAR]).any():
        raise ValueError("Expected exactly 30 unique Odisha districts by five assessment years")
    _csv("assessment_source_labels.csv", labels)
    return labels, digest(REPORT)


def assessment_frame(labels):
    frame = pd.read_csv(DATA / "prepared_inputs.csv", dtype={CODE: str})
    names = set(frame.district_source.unique())
    if names != set(labels.district_source.unique()):
        raise ValueError("Assessment names differ from the reviewed district scope")
    source = labels.set_index(["district_source", YEAR])
    for index in frame.index[frame[YEAR] >= 2018]:
        key = (frame.at[index, "district_source"], frame.at[index, YEAR])
        record = source.loc[key]
        frame.at[index, TARGET] = record[TARGET] if record.valid_target else np.nan
        frame.at[index, "target_access"] = "assessment opened after frozen selection/calibration"
    lookup = frame.set_index([CODE, YEAR])[TARGET].to_dict()
    for lag in range(2, 7):
        frame[f"yield_lag{lag}"] = [lookup.get((code, year-lag), np.nan) for code, year in zip(frame[CODE], frame[YEAR])]
    history = frame[LAGS]
    frame[REFERENCE] = history.mean(axis=1, skipna=False)
    frame[TREND] = history.mul([2, 1, 0, -1, -2]).sum(axis=1, skipna=False)/10
    frame["history_complete_from_open_labels"] = history.notna().all(axis=1)
    frame["eligible_for_model"] = (np.isfinite(frame[HISTORY+WEATHER+[TARGET]].to_numpy()).all(axis=1)
                                   & frame[REFERENCE].gt(0) & frame[TARGET].ge(0) & frame[YEAR].ge(2004))
    missing = frame.loc[frame[YEAR].ge(2018) & ~frame.eligible_for_model, [CODE, "district_source", YEAR]].copy()
    if not missing.empty:
        reasons = labels.set_index(["district_source", YEAR]).exclusion_reason.to_dict()
        missing["exclusion_reason"] = [reasons.get((r.district_source, getattr(r, YEAR)), "") or "incomplete history or weather"
                                        for r in missing.itertuples()]
    else:
        missing["exclusion_reason"] = pd.Series(dtype=str)
    _csv("assessment_exclusions.csv", missing)
    _csv("assessment_inputs.csv", frame)
    return frame.loc[frame.eligible_for_model].copy()


def paired_year_bootstrap(predictions, model_id, reference_id):
    pivot = predictions.assign(absolute_error=lambda d: abs(d.predicted_yield_kg_ha-d.actual_yield_kg_ha)).pivot(
        index=[CODE, YEAR], columns="candidate", values="absolute_error")
    differences = (pivot[reference_id]-pivot[model_id]).groupby(level=YEAR).mean().to_numpy()
    if len(differences) < 2:
        return {"model": model_id, "reference": reference_id, "years": len(differences), "improvement_kg_ha": None,
                "lower_95_kg_ha": None, "upper_95_kg_ha": None}
    samples = np.random.default_rng(42).choice(differences, (2000, len(differences)), replace=True).mean(axis=1)
    return {"model": model_id, "reference": reference_id, "years": len(differences),
            "improvement_kg_ha": float(differences.mean()), "lower_95_kg_ha": float(np.quantile(samples, .025)),
            "upper_95_kg_ha": float(np.quantile(samples, .975))}


def run_assessment():
    selection = verify_selection()
    if (OUT / "assessment_manifest.json").exists():
        completed = _read("assessment_manifest.json")
        for name, value in completed["output_sha256"].items():
            if digest(OUT / name) != value:
                raise ValueError(f"Completed assessment result changed: {name}")
        return _read("summary.json")
    labels, source_hash = unlock_assessment_labels(selection)
    frame = assessment_frame(labels)
    years = selection["execution_manifest"]["protocol"]["assessment_years_reserved"]
    assessment = rolling_predictions(frame, years, candidates())
    if assessment.empty:
        raise ValueError("No eligible assessment outcomes; inspect source labels/exclusions, do not fabricate results")
    ranked, annual = comparison_tables(assessment)
    selected_id = selection["selected_candidate"]["id"]
    selected = assessment.loc[assessment.candidate.eq(selected_id)].copy()
    half_width = selection["interval_relative_half_width"]*selected.reference_yield_kg_ha
    selected["lower_80_kg_ha"] = np.maximum(0, selected.predicted_yield_kg_ha-half_width)
    selected["upper_80_kg_ha"] = selected.predicted_yield_kg_ha+half_width
    selected["interval_covers"] = selected.actual_yield_kg_ha.between(selected.lower_80_kg_ha, selected.upper_80_kg_ha)
    selected["predicted_low_yield"] = selected.predicted_yield_kg_ha < selected.low_yield_threshold_kg_ha
    district = pd.DataFrame([{CODE: code, "district_source": group.district_source.iloc[0], **metrics(group)}
                              for code, group in selected.groupby(CODE)])
    interval_years = pd.DataFrame([{YEAR: int(year), "records": len(group), "coverage_80": float(group.interval_covers.mean()),
                                   "width_kg_ha": float((group.upper_80_kg_ha-group.lower_80_kg_ha).mean())}
                                  for year, group in selected.groupby(YEAR)])
    pairs = [paired_year_bootstrap(assessment, selected_id, reference) for reference in ("Recent mean", "Last available yield")]
    pairs.append(paired_year_bootstrap(assessment, selection["weather_ridge_control"], selection["history_ridge_control"]))
    selected_metrics = next(r for r in ranked.to_dict("records") if r["candidate"] == selected_id)
    selected_metrics = {key: None if pd.isna(value) else value for key, value in selected_metrics.items()}
    summary = {"selected_candidate": selection["selected_candidate"], "assessment_records": len(selected),
               "assessment_years": sorted(int(v) for v in selected[YEAR].unique()), "configurations_reported": len(ranked),
               "selected_metrics": selected_metrics, "interval_coverage_80": float(selected.interval_covers.mean()),
               "mean_interval_width_kg_ha": float((selected.upper_80_kg_ha-selected.lower_80_kg_ha).mean()),
               "calibration_records": selection["calibration_records"], "paired_year_comparisons": pairs,
               "assessment_labels_valid": int(labels.valid_target.sum()), "assessment_labels_excluded": int((~labels.valid_target).sum()),
               "forecast_rows_excluded": int((pd.read_csv(OUT / "assessment_exclusions.csv")).shape[0]),
               "assessment_outcomes_opened": True, "selection_changed_after_assessment": False,
               "latest_fitting_year": int(selected.training_end_year.max()),
               "scope": "sequential historical Kharif replay; fixed 2011 district geography assumed; not live forecasts",
               "weather_incremental_evidence": "Use the frozen paired Ridge control comparison; a weather tree versus a history baseline also changes algorithm",
               "no_causal_damage_or_financial_savings_claim": True}
    outputs = {"assessment_predictions.csv": assessment, "selected_assessment_predictions.csv": selected,
               "assessment_metrics.csv": ranked, "assessment_year_metrics.csv": annual,
               "selected_district_metrics.csv": district, "interval_year_metrics.csv": interval_years}
    for name, table in outputs.items():
        _csv(name, table)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "paired_year_comparisons.json", pairs)
    names = list(outputs) + ["assessment_source_labels.csv", "assessment_inputs.csv", "assessment_exclusions.csv",
                             "summary.json", "paired_year_comparisons.json", "selection.json"]
    write_json(OUT / "assessment_manifest.json", {"source_report_sha256": source_hash,
               "frozen_selection_sha256": digest(OUT / "selection.json"),
               "output_sha256": {name: digest(OUT / name) for name in names},
               "method": "Selection and calibration verified before source unlock; all forecasts trained through Y-2"})
    return summary
