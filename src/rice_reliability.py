"""Location-level stability, transfer diagnostics and separate split intervals."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.rice_baseline import DATA
from src.rice_context import REGRESSION, RISK, context_designs, context_prediction, load_context_results, prepare_context
from src.rice_validation import INPUTS, _inner_selection, _metrics

VERSION = "location-reliability-v1"
SEED = 20261011
REPEATS = 10000


def location_stability(predictions):
    regression = predictions.loc[predictions.predicted_yield_kg_ha.notna()].copy()
    regression["absolute_error"] = (regression.predicted_yield_kg_ha - regression.observed_yield_kg_ha).abs()
    regression["squared_error"] = regression.absolute_error ** 2
    errors = regression.groupby(["model", "held_out_location"])[["absolute_error", "squared_error"]].mean()
    baseline = errors.loc["Training mean"].sort_index()
    samples = np.random.default_rng(SEED).integers(0, len(baseline), size=(REPEATS, len(baseline)))
    rows = []
    for model in errors.index.get_level_values("model").unique():
        values = errors.loc[model].reindex(baseline.index)
        if values.isna().any().any():
            raise ValueError("All compared models must cover the same locations.")
        base_mae, base_mse = baseline.absolute_error.to_numpy(), baseline.squared_error.to_numpy()
        model_mae, model_mse = values.absolute_error.to_numpy(), values.squared_error.to_numpy()
        for metric, improvement, draws in [
            ("MAE", base_mae.mean() - model_mae.mean(), (base_mae[samples] - model_mae[samples]).mean(axis=1)),
            ("RMSE", np.sqrt(base_mse.mean()) - np.sqrt(model_mse.mean()),
             np.sqrt(base_mse[samples].mean(axis=1)) - np.sqrt(model_mse[samples].mean(axis=1)))]:
            lower, upper = np.quantile(draws, [0.025, 0.975])
            rows.append({"model": model, "metric": metric, "equal_location_improvement_kg_ha": float(improvement),
                         "bootstrap_95_lower_kg_ha": float(lower), "bootstrap_95_upper_kg_ha": float(upper),
                         "locations_improved": int((values["absolute_error" if metric == "MAE" else "squared_error"]
                                                    < baseline["absolute_error" if metric == "MAE" else "squared_error"]).sum()),
                         "locations": len(baseline), "bootstrap_repeats": REPEATS})
    return pd.DataFrame(rows)


def transfer_diagnostics(frame):
    context = [c for c in frame if c.startswith(("agro_", "plant_"))]
    rows = []
    for location in sorted(frame.location_group.unique()):
        training = frame.loc[frame.location_group.ne(location)].drop_duplicates("environment_id")
        testing = frame.loc[frame.location_group.eq(location)].drop_duplicates("environment_id")
        numeric = training[context].select_dtypes(include="number").columns.tolist()
        categorical = [c for c in context if c not in numeric]
        impute = SimpleImputer(strategy="median", keep_empty_features=True).fit(training[numeric])
        scale = StandardScaler().fit(impute.transform(training[numeric]))
        xt, xv = scale.transform(impute.transform(training[numeric])), scale.transform(impute.transform(testing[numeric]))
        encoding = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(training[categorical])
        train_values = np.c_[xt, encoding.transform(training[categorical])]
        test_values = np.c_[xv, encoding.transform(testing[categorical])]
        distances = pairwise_distances(test_values, train_values) / np.sqrt(train_values.shape[1])
        within = pairwise_distances(train_values) / np.sqrt(train_values.shape[1])
        np.fill_diagonal(within, np.inf)
        reference = float(within.min(axis=1).max())
        for i, record in enumerate(testing.itertuples(index=False)):
            nearest = int(distances[i].argmin())
            current = testing.iloc[i]
            outside = [c for c in numeric if pd.notna(current[c]) and
                       (current[c] < training[c].min() or current[c] > training[c].max())]
            unknown = [c for c in categorical if current[c] not in set(training[c])]
            differences = np.abs(xv[i] - xt[nearest])
            strongest = np.argsort(-differences)[:3]
            rows.append({"held_out_location": location, "environment_id": record.environment_id,
                         "nearest_training_environment": training.iloc[nearest].environment_id,
                         "context_distance": float(distances[i, nearest]), "training_neighbour_max_distance": reference,
                         "beyond_training_neighbour_distance": bool(distances[i, nearest] > reference),
                         "numeric_inputs_outside_training_range": "; ".join(outside),
                         "unseen_categories": "; ".join(unknown),
                         "largest_neighbour_differences": "; ".join(f"{numeric[j]} ({differences[j]:.2f} scaled units)" for j in strongest)})
    return pd.DataFrame(rows)


def interval_radius(scores, coverage):
    """Finite-sample order statistic, including the mandatory infinite endpoint."""
    if not 0 < coverage < 1 or len(scores) == 0:
        raise ValueError("Coverage must be between zero and one, with calibration scores present.")
    rank = math.ceil((len(scores) + 1) * coverage)
    return (float(np.sort(scores)[rank - 1]) if rank <= len(scores) else np.inf), rank


def interval_split(frame):
    groups = np.array(sorted(frame.location_group.unique()))
    if len(groups) != 12:
        raise ValueError("This declared interval protocol requires the original twelve locations.")
    shuffled = np.random.default_rng(SEED).permutation(groups)
    return pd.DataFrame({"location_group": shuffled, "role": ["fit"] * 6 + ["calibration"] * 4 + ["assessment"] * 2})


def split_intervals(frame):
    membership = interval_split(frame)
    sets = {role: frame.loc[frame.location_group.isin(membership.loc[membership.role.eq(role), "location_group"])].copy()
            for role in ["fit", "calibration", "assessment"]}
    fitting, calibration, assessment = sets["fit"], sets["calibration"], sets["assessment"]
    context = [c for c in frame if c.startswith(("agro_", "plant_"))]
    markers = [c for c in frame if c.startswith("snp_")]
    _, best, _, scores = _inner_selection(fitting, context, markers, REGRESSION, RISK,
                                        context_designs, context_prediction)
    targets = pd.concat([calibration, assessment], ignore_index=True)
    designs = context_designs(fitting, targets, context, markers)
    intervals, calibration_rows, metrics = [], [], []
    for model, candidate in [("Split context/full-SNP selection", best), ("Split training mean", REGRESSION[0])]:
        predicted = context_prediction(candidate, fitting, targets, designs, context)
        n = len(calibration)
        residuals = pd.DataFrame({"location_group": calibration.location_group.to_numpy(),
                                  "absolute_error": np.abs(calibration.yield_kg_ha.to_numpy() - predicted[:n])})
        group_scores = residuals.groupby("location_group").absolute_error.max()
        for location, score in group_scores.items():
            calibration_rows.append({"model": model, "location_group": location, "maximum_absolute_error_kg_ha": float(score)})
        actual, pred = assessment.yield_kg_ha.to_numpy(), predicted[n:]
        for coverage in [0.8, 0.9]:
            radius, rank = interval_radius(group_scores.to_numpy(), coverage)
            lower, upper = np.maximum(0, pred - radius), pred + radius
            covered = (actual >= lower) & (actual <= upper)
            records = assessment[["source_csv_row", "genotype_id", "environment_id", "location_group"]].copy()
            records["model"], records["target_coverage"] = model, coverage
            records["observed_yield_kg_ha"], records["predicted_yield_kg_ha"] = actual, pred
            records["lower_kg_ha"], records["upper_kg_ha"], records["covered"] = lower, upper, covered
            intervals.extend(records.to_dict("records"))
            group_coverage = pd.DataFrame({"location": assessment.location_group.to_numpy(), "covered": covered}).groupby("location").covered.all()
            metrics.append({"model": model, "selected_candidate": candidate["name"], "target_coverage": coverage,
                            "calibration_locations": len(group_scores), "calibration_rank": rank,
                            "finite_interval": bool(np.isfinite(radius)),
                            "radius_kg_ha": float(radius) if np.isfinite(radius) else None,
                            "mean_width_kg_ha": float((upper - lower).mean()) if np.isfinite(radius) else None,
                            "assessment_records": len(assessment), "assessment_locations": len(group_coverage),
                            "row_coverage": float(covered.mean()), "whole_location_coverage": float(group_coverage.mean()),
                            **_metrics(actual, pred)})
    tuning = pd.DataFrame([{"candidate": c["name"], "inner_mean_location_MSE": scores[c["name"]],
                            "selected": c == best} for c in REGRESSION])
    return membership, pd.DataFrame(calibration_rows), pd.DataFrame(intervals), pd.DataFrame(metrics), tuning


def _hashes(cutoff_days):
    root = Path(__file__).resolve().parents[1]
    paths = [DATA / name for name in INPUTS]
    paths += [DATA / "context" / f"day_{cutoff_days}" / name for name in ["held_out_predictions.csv", "summary.json"]]
    paths += [root / "src" / name for name in ["rice_baseline.py", "rice_validation.py", "rice_context.py", "rice_reliability.py"]]
    # Git may convert Python line endings on Windows; hash canonical source text.
    return {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8") if path.suffix == ".py" else path.read_bytes()).hexdigest()
        for path in paths}


def run_reliability(cutoff_days=60, progress=None):
    results = load_context_results(cutoff_days)
    if results is None:
        raise ValueError("Run the planting/full-SNP benchmark first for this forecast date.")
    if progress:
        progress("Comparing errors across whole locations")
    frame, _ = prepare_context(cutoff_days)
    stability = location_stability(results[1])
    transfer = transfer_diagnostics(frame)
    if progress:
        progress("Fitting the separate six-location interval experiment")
    split, scores, intervals, metrics, tuning = split_intervals(frame)
    directory = DATA / "reliability" / f"day_{cutoff_days}"
    directory.mkdir(parents=True, exist_ok=True)
    tables = {"location_stability": stability, "environment_transfer": transfer, "interval_split": split,
              "calibration_scores": scores, "interval_predictions": intervals, "interval_metrics": metrics,
              "interval_candidate_scores": tuning}
    for name, table in tables.items():
        table.to_csv(directory / f"{name}.csv", index=False)
    summary = {"version": VERSION, "cutoff_days": cutoff_days, "seed": SEED, "bootstrap_repeats": REPEATS,
               "source_and_code_sha256": _hashes(cutoff_days), "fit_locations": 6, "calibration_locations": 4,
               "assessment_locations": 2, "interval_score": "Maximum absolute residual per calibration location",
               "coverage_condition": "Exchangeability of whole location datasets; not established for these trials",
               "assessment_status": "Previously inspected development data; not an independent external test",
               "prediction_scope": "Separate split model; intervals must not be attached to nested outer predictions"}
    summary["output_sha256"] = {name: hashlib.sha256((directory / f"{name}.csv").read_bytes()).hexdigest() for name in tables}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return tables, summary


def load_reliability(cutoff_days=60):
    directory = DATA / "reliability" / f"day_{cutoff_days}"
    path = directory / "summary.json"
    if not path.exists():
        return None
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("version") != VERSION or summary.get("cutoff_days") != cutoff_days:
        return None
    try:
        if summary["source_and_code_sha256"] != _hashes(cutoff_days):
            return None
        tables = {}
        for name, expected in summary["output_sha256"].items():
            output = directory / f"{name}.csv"
            if hashlib.sha256(output.read_bytes()).hexdigest() != expected:
                return None
            tables[name] = pd.read_csv(output)
    except (OSError, KeyError):
        return None
    return tables, summary
