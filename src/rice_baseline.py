"""Reproducible pre-harvest benchmarks on the audited rice trial data."""

from pathlib import Path
import json
import hashlib

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, brier_score_loss
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rice"
ALPHA = 100.0


def prepare_data(cutoff_days=60):
    """Cutoff is inclusive: day 60 uses days 0..60 after recorded seeding."""
    if not 30 <= cutoff_days <= 90:
        raise ValueError("Choose a cutoff between 30 and 90 days after seeding.")
    yields = pd.read_csv(DATA / "yield_observations_audited.csv")
    yields = yields.loc[yields.eligible_after_key_audit].copy()
    if yields.duplicated(["genotype_id", "environment_id"]).any():
        raise ValueError("Ambiguous genotype/environment targets remain.")
    trials = pd.read_csv(DATA / "trial_metadata.csv")
    weather = pd.read_csv(DATA / "daily_weather.csv", parse_dates=["date"])
    features, windows = [], []
    for row in trials.itertuples(index=False):
        start = pd.Timestamp(row.seeding_date)
        end = start + pd.Timedelta(days=cutoff_days)
        if end >= pd.Timestamp(row.harvest_date_observed):
            raise ValueError(f"Cutoff is not pre-harvest for {row.environment_id}.")
        days = weather.loc[(weather.environment_id == row.environment_id)
                           & weather.date.between(start, end)].sort_values("date")
        expected = pd.date_range(start, end)
        if not days.date.reset_index(drop=True).equals(pd.Series(expected)):
            raise ValueError(f"Incomplete or duplicated weather window: {row.environment_id}")
        weather_cols = [c for c in days if c not in ["date", "environment_id", "weather_source", "time_standard"]]
        if days[weather_cols].isna().any().any():
            raise ValueError("Missing weather values require an explicit treatment.")
        values = {"environment_id": row.environment_id}
        # Monthly-sized windows use only observed days before the issue date.
        for label, chunk in [("early", days.iloc[:30]), ("recent", days.iloc[30:])]:
            for name in weather_cols:
                values[f"weather_{label}_{name}"] = float(chunk[name].sum() if name == "precipitation_mm_day" else chunk[name].mean())
        features.append(values)
        windows.append({"environment_id": row.environment_id, "seeding_date": start.date().isoformat(),
                        "forecast_date": end.date().isoformat(), "last_weather_date": days.date.max().date().isoformat(),
                        "weather_days": len(days), "harvest_date": row.harvest_date_observed})
    markers = pd.read_csv(DATA / "genotype_marker_calls.csv").set_index("genotype_id")
    metadata = pd.read_csv(DATA / "marker_metadata.csv").set_index("rs#")
    encoded = pd.DataFrame(index=markers.index)
    encoded_columns = {}
    for name in markers:
        alleles = str(metadata.loc[name, "alleles"]).split("/")
        if len(alleles) != 2 or not markers[name].isin(alleles).all():
            raise ValueError(f"Unsupported allele coding for {name}")
        # Arbitrary documented allele orientation, not a resistance score.
        encoded_columns["snp_" + name] = (markers[name] != alleles[0]).astype(float)
    encoded = pd.DataFrame(encoded_columns, index=markers.index).reset_index()
    frame = yields.merge(pd.DataFrame(features), on="environment_id", validate="many_to_one")
    frame = frame.merge(encoded, on="genotype_id", validate="many_to_one")
    if len(frame) != len(yields) or frame.isna().filter(regex="^(weather_|snp_)").any().any():
        raise ValueError("Predictor linkage failed.")
    frame["location_group"] = frame.country + " / " + frame.location
    return frame, pd.DataFrame(windows)


def run_benchmark(cutoff_days=60):
    frame, windows = prepare_data(cutoff_days)
    weather = [c for c in frame if c.startswith("weather_")]
    genetics = [c for c in frame if c.startswith("snp_")]
    sets = {"Training mean": [], "Weather Ridge": weather,
            "Genetics Ridge": genetics, "Weather + genetics Ridge": weather + genetics}
    target = frame.yield_kg_ha.to_numpy()
    output, fold_metrics = [], []
    splitter = LeaveOneGroupOut()
    for train, test in splitter.split(frame, groups=frame.location_group):
        training, testing = frame.iloc[train], frame.iloc[test]
        threshold = float(np.quantile(target[train], 0.2))
        risk_train = (target[train] < threshold).astype(int)
        risk_actual = (target[test] < threshold).astype(int)
        fold = testing.location_group.iloc[0]
        for name, columns in sets.items():
            if columns:
                model = make_pipeline(StandardScaler(), Ridge(alpha=ALPHA))
                model.fit(training[columns], target[train])
                prediction = model.predict(testing[columns])
            else:
                model = DummyRegressor(strategy="mean").fit(np.zeros((len(train), 1)), target[train])
                prediction = model.predict(np.zeros((len(test), 1)))
            for idx, value in zip(test, prediction):
                record = frame.loc[idx, ["source_csv_row", "genotype_id", "environment_id", "country", "location", "year", "season"]].to_dict()
                record.update(model=name, held_out_location=fold, observed_yield_kg_ha=float(target[idx]), predicted_yield_kg_ha=float(value))
                output.append(record)
            fold_metrics.append({"model": name, "held_out_location": fold, "train_records": len(train),
                                 "test_records": len(test), "MAE_kg_ha": float(mean_absolute_error(target[test], prediction)),
                                 "RMSE_kg_ha": float(np.sqrt(mean_squared_error(target[test], prediction))),
                                 "bias_kg_ha": float(np.mean(prediction - target[test]))})
        classifier = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000, random_state=42))
        classifier.fit(training[weather + genetics], risk_train)
        probability = classifier.predict_proba(testing[weather + genetics])[:, 1]
        prevalence = float(risk_train.mean())
        for idx, prob, actual in zip(test, probability, risk_actual):
            # Risk rows have their own task labels; regression metrics exclude them.
            output.append({"source_csv_row": int(frame.loc[idx, "source_csv_row"]),
                           "genotype_id": int(frame.loc[idx, "genotype_id"]),
                           "environment_id": frame.loc[idx, "environment_id"], "model": "Low-yield risk",
                           "held_out_location": fold, "low_yield_threshold_kg_ha": threshold,
                           "observed_low_yield": int(actual), "predicted_low_yield_probability": float(prob),
                           "training_prevalence_probability": prevalence})
    predictions = pd.DataFrame(output)
    metrics = []
    for name in sets:
        d = predictions.loc[predictions.model == name]
        actual, predicted = d.observed_yield_kg_ha, d.predicted_yield_kg_ha
        metrics.append({"model": name, "MAE_kg_ha": float(mean_absolute_error(actual, predicted)),
                        "RMSE_kg_ha": float(np.sqrt(mean_squared_error(actual, predicted))),
                        "R2": float(r2_score(actual, predicted)), "bias_kg_ha": float((predicted - actual).mean())})
    risk = predictions.loc[predictions.model == "Low-yield risk"]
    summary = {"cutoff_days_after_seeding_inclusive": cutoff_days, "records": len(frame),
               "genotypes": int(frame.genotype_id.nunique()), "environments": int(frame.environment_id.nunique()),
               "held_out_locations": int(frame.location_group.nunique()), "weather_feature_count": len(weather),
               "marker_feature_count": len(genetics), "ridge_alpha_fixed_not_tuned": ALPHA,
               "validation": "Leave one entire country/location group out; other locations may contain the same genotypes",
               "low_yield_definition": "Yield below the 20th percentile of each fold's training targets; fold-specific risk definition",
               "risk_Brier": float(brier_score_loss(risk.observed_low_yield, risk.predicted_low_yield_probability)),
               "prevalence_Brier": float(brier_score_loss(risk.observed_low_yield, risk.training_prevalence_probability)),
               "limits": ["Published adjusted targets, not independent farm harvest validation",
                          "Only 12 locations and 15 environments; year/geography confounding",
                          "Source SNP filtering preceded our validation; not raw unfiltered genomic validation",
                          "Gridded weather estimates; no measured trial soil/Al or verified protein embeddings",
                          "Risk probabilities uncalibrated externally; no monetary or causal damage estimate",
                          "No guarantee of unseen-genotype transfer; no prediction intervals"]}
    directory = DATA / "baseline" / f"day_{cutoff_days}"
    directory.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(directory / "held_out_predictions.csv", index=False)
    pd.DataFrame(metrics).to_csv(directory / "metrics.csv", index=False)
    pd.DataFrame(fold_metrics).to_csv(directory / "location_metrics.csv", index=False)
    windows.to_csv(directory / "forecast_windows.csv", index=False)
    summary["source_sha256"] = {}
    for name in ["yield_observations_audited.csv", "daily_weather.csv", "genotype_marker_calls.csv", "marker_metadata.csv", "trial_metadata.csv"]:
        summary["source_sha256"][name] = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return pd.DataFrame(metrics), predictions, pd.DataFrame(fold_metrics), summary


def load_results(cutoff_days=60):
    directory = DATA / "baseline" / f"day_{cutoff_days}"
    if not (directory / "summary.json").exists():
        return None
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    for name, expected in summary["source_sha256"].items():
        source = DATA / name
        if not source.exists() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            return None
    return (pd.read_csv(directory / "metrics.csv"), pd.read_csv(directory / "held_out_predictions.csv"),
            pd.read_csv(directory / "location_metrics.csv"), summary)
