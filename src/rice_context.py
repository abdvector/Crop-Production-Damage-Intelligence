"""Pre-harvest planting context and full-SNP relationship benchmarks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.rice_baseline import DATA, prepare_data
from src.rice_validation import run_nested_benchmark

VERSION = "planting-full-snp-v1"
REGRESSION = ([{"name": "Training mean", "kind": "mean", "genetics": False}]
              + [{"name": f"Context Ridge alpha={a}", "kind": "ridge", "alpha": a, "genetics": False} for a in [100, 10000]]
              + [{"name": f"Context kernel alpha={a}", "kind": "environment", "alpha": a, "genetics": False} for a in [1, 100]]
              + [{"name": f"Full-SNP genomic kernel alpha={a}", "kind": "genomic", "alpha": a, "genetics": True} for a in [1, 100]]
              + [{"name": f"Context + genomic kernel weight={g} alpha={a}", "kind": "additive", "alpha": a,
                  "weight": g, "genetics": True} for g in [0.1, 1] for a in [1, 100]]
              + [{"name": f"Context forest leaf={n}", "kind": "forest", "leaf": n, "genetics": False} for n in [2, 4]])
RISK = ([{"name": "Training prevalence", "kind": "prevalence", "genetics": False}]
        + [{"name": f"{'Context + full SNPs' if g else 'Context'} logistic C={c}", "kind": "logistic",
            "genetics": g, "C": c} for g in [False, True] for c in [0.001, 0.01]])


def _longest_spell(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def prepare_context(cutoff_days=60):
    frame, windows = prepare_data(cutoff_days)
    weather = pd.read_csv(DATA / "daily_weather.csv", parse_dates=["date"])
    rows = []
    for trial in pd.read_csv(DATA / "trial_metadata.csv").itertuples(index=False):
        start = pd.Timestamp(trial.seeding_date)
        issue = start + pd.Timedelta(days=cutoff_days)
        established = pd.Timestamp(trial.establishment_date)
        completed = established <= issue
        days = weather.loc[weather.environment_id.eq(trial.environment_id) & weather.date.between(start, issue)].sort_values("date")
        columns = [c for c in days if c not in ["date", "environment_id", "weather_source", "time_standard"]]
        angle = 2 * np.pi * (start.dayofyear - 1) / (366 if start.is_leap_year else 365)
        features = {"environment_id": trial.environment_id, "plant_seeding_sin": np.sin(angle),
                    "plant_seeding_cos": np.cos(angle), "plant_established_by_issue": int(completed),
                    "plant_delay_observed_days": float((established - start).days) if completed else np.nan,
                    "plant_field_days_observed": max(0, (issue - established).days + 1) if completed else 0,
                    "plant_method": str(trial.establishment_method) if completed else "Not yet observed",
                    "plant_season": str(trial.season),
                    "plant_spacing_layout_source": f"{trial.row_spacing_source}x{trial.hill_spacing_source}" if completed else "Not yet observed"}
        # Three fixed 15-day summaries; all indexes end at or before the issue date.
        for label, chunk in [("first15", days.iloc[:15]), ("previous15", days.iloc[-30:-15]), ("last15", days.iloc[-15:])]:
            for name in columns:
                features[f"agro_{label}_{name}"] = float(chunk[name].sum() if name == "precipitation_mm_day" else chunk[name].mean())
        rain, tmax, tmin = days.precipitation_mm_day, days.temperature_max_c, days.temperature_min_c
        features.update(agro_total_rain_mm=float(rain.sum()),
                        agro_total_radiation_mj_m2=float(days.solar_radiation_mj_m2_day.sum()),
                        agro_days_tmax_above35=int(tmax.gt(35).sum()),
                        agro_days_tmin_above25=int(tmin.gt(25).sum()),
                        agro_tmax_exceedance35_c_days=float((tmax - 35).clip(lower=0).sum()),
                        agro_longest_rain_below1_mm_spell_days=_longest_spell(rain.lt(1)))
        field = days.loc[days.date.ge(established)] if completed else days.iloc[:0]
        features["agro_field_rain_mm"] = float(field.precipitation_mm_day.sum())
        features["agro_field_mean_temperature_c"] = float(field.temperature_mean_c.mean()) if len(field) else np.nan
        rows.append(features)
    contextual = pd.DataFrame(rows)
    return frame.merge(contextual, on="environment_id", validate="many_to_one"), windows


def _basis(gram, cross):
    """Exact positive-eigenspace factor, retaining the full training kernel span."""
    values, vectors = np.linalg.eigh((gram + gram.T) / 2)
    keep = values > 1e-10
    if not keep.any():
        return np.zeros((len(cross), 1))
    return cross @ (vectors[:, keep] / np.sqrt(values[keep]))


def context_designs(training, testing, context, markers):
    unique_env = training.drop_duplicates("environment_id")
    numeric = unique_env[context].select_dtypes(include="number").columns.tolist()
    categorical = [c for c in context if c not in numeric]
    impute = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True).fit(unique_env[numeric])
    scale = StandardScaler().fit(impute.transform(unique_env[numeric]))
    encoding = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(unique_env[categorical])
    def environment_values(rows):
        return np.c_[scale.transform(impute.transform(rows[numeric])), encoding.transform(rows[categorical])]
    unique_values = environment_values(unique_env)
    xt, xv = environment_values(training), environment_values(testing)
    gamma = 1 / unique_values.shape[1]
    env_gram = rbf_kernel(unique_values, gamma=gamma)
    env_train = _basis(env_gram, rbf_kernel(xt, unique_values, gamma=gamma))
    env_test = _basis(env_gram, rbf_kernel(xv, unique_values, gamma=gamma))
    # Source marker calls are homozygous; 0/1 indicators become 0/2 allele counts.
    unique_gen = training.drop_duplicates("genotype_id")
    dosage = unique_gen[markers].to_numpy(dtype=float) * 2
    frequency = dosage.mean(axis=0) / 2
    centred = dosage - 2 * frequency
    denominator = float(np.sum(2 * frequency * (1 - frequency)))
    if denominator <= 0:
        raise ValueError("Training genotypes have no polymorphic SNPs.")
    genomic_gram = centred @ centred.T / denominator
    normaliser = float(np.diag(genomic_gram).mean())
    genomic_gram /= normaliser
    # Compute each genotype once, then link its kernel coordinates to trial rows.
    union = pd.concat([unique_gen, testing.drop_duplicates("genotype_id")]).drop_duplicates("genotype_id")
    cross = (union[markers].to_numpy(dtype=float) * 2 - 2 * frequency) @ centred.T / (denominator * normaliser)
    features = pd.DataFrame(_basis(genomic_gram, cross), index=union.genotype_id)
    gt = features.reindex(training.genotype_id).to_numpy()
    gv = features.reindex(testing.genotype_id).to_numpy()
    return {"weather": (xt, xv), "genetic": (np.c_[xt, gt], np.c_[xv, gv]),
            "environment_kernel": (env_train, env_test), "genomic_kernel": (gt, gv)}


def context_prediction(candidate, training, testing, designs, context):
    kind = candidate["kind"]
    if kind == "mean":
        return np.full(len(testing), training.yield_kg_ha.mean())
    if kind == "forest":
        xt, xv = designs["weather"]
        first = ~training.environment_id.duplicated().to_numpy()
        environment_targets = training.groupby("environment_id").yield_kg_ha.mean().reindex(training.loc[first, "environment_id"])
        forest = RandomForestRegressor(n_estimators=128, min_samples_leaf=candidate["leaf"], random_state=42, n_jobs=1)
        return forest.fit(xt[first], environment_targets).predict(xv)
    if kind == "additive":
        et, ev = designs["environment_kernel"]
        gt, gv = designs["genomic_kernel"]
        xt, xv = np.c_[et, np.sqrt(candidate["weight"]) * gt], np.c_[ev, np.sqrt(candidate["weight"]) * gv]
    else:
        key = {"ridge": "weather", "environment": "environment_kernel", "genomic": "genomic_kernel"}[kind]
        xt, xv = designs[key]
    return Ridge(alpha=candidate["alpha"]).fit(xt, training.yield_kg_ha).predict(xv)


def save_environment_rankings(predictions, directory):
    """Within-trial ranking separates genotype discrimination from site mean shifts."""
    regressions = predictions.loc[predictions.predicted_yield_kg_ha.notna()]
    rows = []
    for (model, environment), records in regressions.groupby(["model", "environment_id"]):
        actual, predicted = records.observed_yield_kg_ha, records.predicted_yield_kg_ha
        defined = actual.std(ddof=0) > 1e-8 and predicted.std(ddof=0) > 1e-8
        rows.append({"model": model, "environment_id": environment, "test_records": len(records),
                     "within_environment_Pearson_r": float(actual.corr(predicted)) if defined else np.nan,
                     "ranking_defined": bool(defined)})
    rankings = pd.DataFrame(rows)
    rankings.to_csv(directory / "environment_ranking.csv", index=False)
    return rankings


def run_context_benchmark(cutoff_days=60, progress=None):
    options = {"version": VERSION, "folder": "context", "prepare": prepare_context,
               "feature_prefixes": ("agro_", "plant_"), "designs": context_designs,
               "predict": context_prediction, "regression": REGRESSION, "risk": RISK,
               "weather_name": "Context selection", "full_name": "Context + full-SNP selection",
               "genetic_control": True, "summary": {"genetic_PC_count": None,
               "genetic_representation": "Full positive-eigenspace factor of training-centred, normalised genomic relationship",
               "density_status": "Spacing units and plants per hill unresolved; no physical density inferred"}}
    metrics, predictions, folds, summary = run_nested_benchmark(cutoff_days, progress, experiment=options)
    frame, _ = prepare_context(cutoff_days)
    columns = [c for c in frame if c.startswith(("agro_", "plant_"))]
    summary.update(environment_feature_count=len(columns), weather_feature_count=sum(c.startswith("agro_") for c in columns),
                   planting_feature_count=sum(c.startswith("plant_") for c in columns),
                   context_implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    directory = DATA / "context" / f"day_{cutoff_days}"
    save_environment_rankings(predictions, directory)
    frame[["environment_id", *columns]].drop_duplicates("environment_id").to_csv(directory / "environment_features.csv", index=False)
    units = {"temperature_mean_c": "C", "temperature_min_c": "C", "temperature_max_c": "C",
             "precipitation_mm_day": "mm summed over window", "relative_humidity_percent": "%",
             "solar_radiation_mj_m2_day": "MJ/m2/day mean", "wind_speed_2m_m_s": "m/s mean"}
    catalogue = []
    for column in columns:
        unit = next((value for suffix, value in units.items() if column.endswith(suffix)), None)
        if unit is None:
            unit = "source category" if column in ["plant_method", "plant_season", "plant_spacing_layout_source"] else "C-days" if "exceedance" in column else "days" if "days" in column or "spell" in column else "mm" if column.endswith("_mm") else "MJ/m2" if "radiation" in column else "C" if "temperature_c" in column else "dimensionless"
        catalogue.append({"feature": column, "source": "trial_metadata.csv" if column.startswith("plant_") else "daily_weather.csv",
                          "unit": unit, "availability": "Known or observed by forecast date",
                          "missing_count_environments": int(frame.drop_duplicates("environment_id")[column].isna().sum())})
    pd.DataFrame(catalogue).to_csv(directory / "feature_catalogue.csv", index=False)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return metrics, predictions, folds, summary


def load_context_results(cutoff_days=60):
    directory = DATA / "context" / f"day_{cutoff_days}"
    if not (directory / "summary.json").exists():
        return None
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    if summary.get("version") != VERSION:
        return None
    for name, expected in summary["source_sha256"].items():
        if not (DATA / name).exists() or hashlib.sha256((DATA / name).read_bytes()).hexdigest() != expected:
            return None
    return pd.read_csv(directory / "metrics.csv"), pd.read_csv(directory / "held_out_predictions.csv"), pd.read_csv(directory / "location_metrics.csv"), summary
