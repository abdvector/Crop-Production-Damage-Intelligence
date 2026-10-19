"""Declared 2018 low-yield-risk development comparison; no 2019 assessment reuse."""
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.rice_field_data import FIELD_DATA
from src.rice_field_cohort import geographic_masks
from src.rice_field_management import FOLDER as MANAGEMENT, _configuration
from src.rice_field_model import feature_matrix

FOLDER = FIELD_DATA / "risk_2018"


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def declare_risk_protocol():
    management = json.loads((MANAGEMENT / "protocol.json").read_text())
    summary = json.loads((MANAGEMENT / "summary.json").read_text())
    protocol = {"version": "risk-2018-matched-v1", "declared_on": "2026-10-19", "seed": 20261019,
        "cohort": "Same complete-report 2018 records and district/weather-purged splits as management comparison",
        "membership_sha256": summary["record_membership_sha256"], "management_protocol_sha256": _hash(MANAGEMENT / "protocol.json"),
        "feature_sha256": summary["feature_sha256"],
        "target": "Yield strictly below each fitting split's 20th percentile; linear quantile; never computed from validation yields",
        "quantile": .2, "blocks": management["blocks"], "input_configuration": management,
        "baselines": ["Global training prevalence", "State training prevalence with global fallback"],
        "classifiers": [{"name": "Logistic C=1", "kind": "logistic", "C": 1.0, "max_iter": 2000},
            {"name": "Random Forest leaf=50", "kind": "forest", "n_estimators": 200, "min_samples_leaf": 50, "max_features": .7},
            {"name": "Gradient boosting leaves=15", "kind": "boosting", "max_iter": 150, "max_leaf_nodes": 15,
             "min_samples_leaf": 30, "learning_rate": .05, "early_stopping": False}],
        "primary_metric": "Pooled cross-fitted Brier score; compare baselines on identical validation labels",
        "secondary_metrics": ["log loss", "mean within-fold ROC AUC", "mean within-fold average precision", "probability calibration"],
        "calibration": "Raw held-out probabilities; ten fixed equal-width bins, observed event rate versus mean probability",
        "no_hyperparameter_search": True, "no_resampling_or_class_weights": True, "no_validation_recalibration": True,
        "no_operational_decision_threshold_selected": True, "2019_used": False,
        "qualification": "Development comparison on an already studied year; not an independent final assessment"}
    FOLDER.mkdir(parents=True, exist_ok=True)
    path = FOLDER / "protocol.json"
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError("Existing risk declaration differs; use a new experiment version")
    _json(path, protocol)
    return protocol


def training_target(yields, quantile=.2):
    threshold = float(np.quantile(np.asarray(yields), quantile, method="linear"))
    return threshold, np.asarray(yields) < threshold


def risk_metrics(observed, probability):
    observed, probability = np.asarray(observed, dtype=int), np.asarray(probability, dtype=float)
    two_classes = len(np.unique(observed)) == 2
    return {"records": len(observed), "event_rate": float(observed.mean()), "mean_probability": float(probability.mean()),
        "probability_bias": float(probability.mean() - observed.mean()), "brier_score": float(brier_score_loss(observed, probability)),
        "log_loss": float(log_loss(observed, probability, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(observed, probability)) if two_classes else None,
        "average_precision": float(average_precision_score(observed, probability)) if two_classes else None}


def fit_risk(training, validation, labels, candidate, config):
    categorical = config["categorical_preprocessing"]
    transform = ColumnTransformer([
        ("numeric", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), config["numeric_features"]),
        ("categorical", OneHotEncoder(handle_unknown=categorical["unknown"], min_frequency=categorical["min_frequency"],
            max_categories=categorical["max_categories"], sparse_output=False), config["categorical_features"])])
    if candidate["kind"] == "logistic":
        estimator = LogisticRegression(C=candidate["C"], max_iter=candidate["max_iter"], random_state=config["seed"])
    elif candidate["kind"] == "forest":
        estimator = RandomForestClassifier(n_estimators=candidate["n_estimators"], min_samples_leaf=candidate["min_samples_leaf"],
            max_features=candidate["max_features"], random_state=config["seed"], n_jobs=2)
    else:
        estimator = HistGradientBoostingClassifier(max_iter=candidate["max_iter"], max_leaf_nodes=candidate["max_leaf_nodes"],
            min_samples_leaf=candidate["min_samples_leaf"], learning_rate=candidate["learning_rate"],
            early_stopping=candidate["early_stopping"], random_state=config["seed"])
    model = make_pipeline(transform, estimator)
    with threadpool_limits(limits=2):
        model.fit(feature_matrix(training, config), labels)
        probabilities = model.predict_proba(feature_matrix(validation, config))[:, 1]
    if not np.isfinite(probabilities).all() or not ((probabilities >= 0) & (probabilities <= 1)).all():
        raise ValueError("Invalid risk probabilities")
    return probabilities


def run_risk_comparison(progress=print):
    if (FOLDER / "summary.json").exists():
        raise ValueError("Risk comparison already completed; load the saved results")
    protocol = json.loads((FOLDER / "protocol.json").read_text())
    management = protocol["input_configuration"]
    original = json.loads((FIELD_DATA / "yield_label_trace.json").read_text())["preserved_result_hashes"]
    preserved = {**{f"model/{k}": v for k, v in original.items()},
                 "management_2018/metrics.csv": _hash(MANAGEMENT / "metrics.csv")}
    for name, value in preserved.items():
        if _hash(FIELD_DATA / name) != value:
            raise ValueError("Existing result hash no longer matches")
    if _hash(MANAGEMENT / "features_local.csv") != protocol["feature_sha256"]:
        raise ValueError("Management features changed after declaration")
    if _hash(MANAGEMENT / "protocol.json") != protocol["management_protocol_sha256"]:
        raise ValueError("Management protocol changed")
    data = pd.read_csv(FIELD_DATA / "cohort_local.csv", low_memory=False)
    data = data.loc[data.year.eq(2018)].merge(pd.read_csv(MANAGEMENT / "features_local.csv"), on="record_id", validate="one_to_one")
    data = data.loc[data.area_arithmetic_pass & data.complete_management].copy()
    splits = pd.read_csv(FIELD_DATA / "development_splits_local.csv")
    data = data.merge(splits[["record_id", "geographic_fold"]], on="record_id", validate="one_to_one")
    membership = hashlib.sha256("\n".join(sorted(data.record_id)).encode()).hexdigest()
    if membership != protocol["membership_sha256"] or not data.year.eq(2018).all():
        raise ValueError("Risk cohort does not match declared 2018 membership")
    predictions, folds, thresholds = [], [], []
    for fold in range(5):
        train, valid, purged = geographic_masks(data, fold)
        fitting, validation = data.loc[train], data.loc[valid]
        cutoff, labels = training_target(fitting.yield_kg_ha, protocol["quantile"])
        observed = validation.yield_kg_ha.lt(cutoff).to_numpy()
        if len(np.unique(labels)) != 2:
            raise ValueError("Classifier fitting requires both classes")
        prevalence = float(labels.mean())
        state_rates = pd.DataFrame({"state": fitting.state.to_numpy(), "event": labels}).groupby("state").event.mean()
        thresholds.append({"fold": fold, "fitting_records": len(fitting), "validation_records": len(validation),
            "purged_records": int(purged.sum()), "yield_threshold_kg_ha": cutoff,
            "training_event_rate": prevalence, "validation_event_rate": float(observed.mean())})
        for block in ["baseline"] + protocol["blocks"]:
            candidates = [{"name": n, "kind": "baseline"} for n in protocol["baselines"]] if block == "baseline" else protocol["classifiers"]
            config = _configuration(management, block)
            config["seed"] = protocol["seed"]
            for candidate in candidates:
                progress(f"Risk fold {fold}: {block}, {candidate['name']}")
                if candidate["name"] == protocol["baselines"][0]:
                    probability = np.full(len(validation), prevalence)
                elif candidate["name"] == protocol["baselines"][1]:
                    probability = validation.state.map(state_rates).fillna(prevalence).to_numpy()
                else:
                    probability = fit_risk(fitting, validation, labels, candidate, config)
                table = validation[["record_id", "year", "state", "district_group"]].copy()
                table["fold"], table["model"], table["block"] = fold, candidate["name"], block
                table["yield_threshold_kg_ha"] = cutoff
                table["observed_low_yield"], table["probability"] = observed.astype(int), probability
                predictions.append(table)
                folds.append({"fold": fold, "model": candidate["name"], "block": block, **risk_metrics(observed, probability)})
    rows, fold_table = pd.concat(predictions, ignore_index=True), pd.DataFrame(folds)
    rows.to_csv(FOLDER / "predictions_local.csv", index=False, lineterminator="\n")
    fold_table.to_csv(FOLDER / "fold_metrics.csv", index=False, lineterminator="\n")
    pd.DataFrame(thresholds).to_csv(FOLDER / "thresholds.csv", index=False, lineterminator="\n")
    aggregate, calibration = [], []
    for (model, block), group in rows.groupby(["model", "block"]):
        result = risk_metrics(group.observed_low_yield, group.probability)
        result.pop("roc_auc"); result.pop("average_precision")
        same = fold_table.loc[fold_table.model.eq(model) & fold_table.block.eq(block)]
        result["mean_fold_roc_auc"] = float(same.roc_auc.mean())
        result["mean_fold_average_precision"] = float(same.average_precision.mean())
        result["mean_fold_event_rate"] = float(same.event_rate.mean())
        bins = np.minimum((group.probability.to_numpy() * 10).astype(int), 9)
        error = 0.0
        for number in range(10):
            subset = group.loc[bins == number]
            if subset.empty:
                continue
            rate, predicted = float(subset.observed_low_yield.mean()), float(subset.probability.mean())
            error += len(subset) * abs(rate - predicted) / len(group)
            calibration.append({"model": model, "block": block, "bin": number, "lower": number / 10,
                "upper": (number + 1) / 10, "records": len(subset), "mean_probability": predicted, "observed_event_rate": rate})
        aggregate.append({"model": model, "block": block, **result, "equal_width_calibration_error": error})
    aggregate = pd.DataFrame(aggregate)
    aggregate.to_csv(FOLDER / "metrics.csv", index=False, lineterminator="\n")
    pd.DataFrame(calibration).to_csv(FOLDER / "calibration.csv", index=False, lineterminator="\n")
    changes = []
    baseline = aggregate.loc[aggregate.model.eq(protocol["baselines"][0]), "brier_score"].iloc[0]
    state_baseline = aggregate.loc[aggregate.model.eq(protocol["baselines"][1]), "brier_score"].iloc[0]
    for candidate in protocol["classifiers"]:
        model = candidate["name"]
        group = aggregate.loc[aggregate.model.eq(model)].set_index("block")
        for block in protocol["blocks"]:
            changes.append({"model": model, "block": block, "brier_gain_vs_global_prevalence": float(baseline - group.loc[block, "brier_score"]),
                "brier_skill_vs_global_prevalence": float(1 - group.loc[block, "brier_score"] / baseline),
                "brier_gain_vs_state_prevalence": float(state_baseline - group.loc[block, "brier_score"]),
                "brier_gain_vs_weather_planting": float(group.loc["weather_planting", "brier_score"] - group.loc[block, "brier_score"])})
    pd.DataFrame(changes).to_csv(FOLDER / "paired_changes.csv", index=False, lineterminator="\n")
    for name, value in preserved.items():
        if _hash(FIELD_DATA / name) != value:
            raise ValueError("Earlier assessment or regression results changed")
    summary = {"version": protocol["version"], "completed_on": "2026-10-19", "records": len(data),
        "district_groups": int(data.district_group.nunique()), "folds": 5, "models": 3, "blocks": 3,
        "threshold_min_kg_ha": min(t["yield_threshold_kg_ha"] for t in thresholds),
        "threshold_max_kg_ha": max(t["yield_threshold_kg_ha"] for t in thresholds),
        "risk_definition": "Yield below each training fold's 20th percentile; thresholds vary across folds",
        "protocol_sha256": _hash(FOLDER / "protocol.json"), "membership_sha256": membership,
        "preserved_result_hashes": preserved, "development_only": True, "2019_used": False,
        "probability_recalibration_fitted": False, "operational_threshold_selected": False,
        "limitations": ["Retrospective, one-year complete-report cohort", "Fold-specific risk thresholds, not one fixed absolute loss threshold",
            "No new independent-year assessment or calibrated deployment probabilities", "Low yield is not measured crop damage or causal loss",
            "No prediction intervals or risk-based economic decision evaluation"]}
    _json(FOLDER / "summary.json", summary)
    return summary


def load_risk_results():
    path = FOLDER / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text()), pd.read_csv(FOLDER / "metrics.csv"), pd.read_csv(FOLDER / "paired_changes.csv")
