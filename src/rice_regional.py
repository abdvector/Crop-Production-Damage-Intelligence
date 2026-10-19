"""Annual district rice outlook: original administrative data, dated inputs and inference.

No executable launcher: the dashboard calls these functions. Historical boundaries and
annual (not season-specific) targets are intentional parts of the model contract.
"""
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/rice/icrisat_district"
WEATHER = RAW / "nasa_monthly"
OUT = ROOT / "data/processed/rice/regional_forecast"
MODEL = ROOT / "models/rice_regional.joblib"
STATES = ["Bihar", "Jharkhand", "Orissa", "Chhattisgarh", "West Bengal"]
PARAMETERS = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"]
CLIMATE = [f"{p}_{m:02d}" for p in PARAMETERS for m in [6, 7, 8]]
HISTORY = ["yield_lag2", "yield_lag3", "yield_lag4", "yield_lag5", "yield_lag6", "reference_yield", "history_trend"]
NUMERIC = HISTORY + ["year", "latitude", "longitude"]
CANDIDATES = ["Recent mean", "Last available yield", "Historical trend", "History Ridge", "Weather Ridge", "Weather forest", "Weather boosting"]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def source_table(name):
    d = json.loads((RAW / name).read_bytes())
    return pd.DataFrame(d["data"], columns=[h["header"] for h in d["headers"]])


def rice_source():
    f = source_table("area_production_yield.json")
    f = f.rename(columns={"Dist Code": "district_id", "Dist Name": "district", "State Name": "state",
                          "Year": "year", "LATITUDE": "latitude", "LONGITUDE": "longitude",
                          "RICE YIELD": "yield_kg_ha", "RICE AREA": "area_1000ha", "RICE PRODUCTION": "production_1000t"})
    columns = ["district_id", "district", "state", "year", "latitude", "longitude", "yield_kg_ha", "area_1000ha", "production_1000t"]
    f = f[columns].copy()
    for c in set(columns) - {"district", "state"}:
        f[c] = pd.to_numeric(f[c], errors="raise")
    if f.duplicated(["district_id", "year"]).any():
        raise ValueError("Duplicate district/year in original source")
    return f.sort_values(["district_id", "year"])


def acquire_source():
    """Fetch original provider data with resumable local caching, no mirror inputs."""
    RAW.mkdir(parents=True, exist_ok=True)
    sources = {
        "area_production_yield.json": "http://data.icrisat.org/dldAPI/apportioned/area-production-yield",
        "districts.json": "http://data.icrisat.org/dldAPI/apportioned/districts",
        "catalogue.json": "https://dataverse.icrisat.org/api/datasets/:persistentId/?persistentId=doi:10.21421/D2/XFB1BZ",
        "DLD_Apportioned_Documentation.pdf": "https://dataverse.icrisat.org/api/access/datafile/8864",
    }
    manifest = []
    for name, url in sources.items():
        path = RAW / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=40) as response:
                raw = response.read()
            if name.endswith(".json"):
                json.loads(raw)
            elif not raw.startswith(b"%PDF"):
                raise ValueError("Invalid source documentation")
            path.write_bytes(raw)
        manifest.append({"filename": name, "url": url, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    write_json(OUT / "source_manifest.json", {"retrieved_on": "2026-10-19", "doi": "10.21421/D2/XFB1BZ", "files": manifest,
               "transport": "The provider's DLD API serves HTTP; HTTPS requests timed out. Checksums identify retrieved bytes; no publisher checksum is available for API JSON.",
               "source_kind": "Government secondary administrative records compiled by ICRISAT and TCI. No survey PII or synthetic outcomes.",
               "terms": "ICRISAT Data Sharing Agreement; no CC BY claim. Research/educational use with attribution.",
               "agreement": "http://data.icrisat.org/document/ICRISAT-Data-Sharing-Agreement.html"})
    return rice_source()


def districts():
    """Scope selected using pre-development records only, never final-year performance."""
    f = rice_source()
    historical = f.loc[f.state.isin(STATES) & f.year.between(1981, 1997)]
    eligible = historical.groupby("district_id").agg(records=("yield_kg_ha", lambda v: (v > 0).sum()), area=("area_1000ha", "median"))
    ids = eligible.index[(eligible.records >= 14) & (eligible.area >= 10)]
    return f.loc[f.district_id.isin(ids)].drop_duplicates("district_id")[["district_id", "district", "state", "latitude", "longitude"]]


def weather_request(row):
    arguments = {"parameters": ",".join(PARAMETERS), "community": "AG", "latitude": row.latitude,
                 "longitude": row.longitude, "start": 1981, "end": 2017, "format": "JSON"}
    return "https://power.larc.nasa.gov/api/temporal/monthly/point?" + urllib.parse.urlencode(arguments)


def check_weather(d):
    expected = {f"{y}{m:02d}" for y in range(1981, 2018) for m in [6, 7, 8]}
    values = d["properties"]["parameter"]
    units = {"T2M_MAX": "C", "T2M_MIN": "C", "PRECTOTCORR": "mm/day", "RH2M": "%"}
    for p in PARAMETERS:
        if d["parameters"][p]["units"] != units[p]:
            raise ValueError(f"Unexpected NASA unit for {p}")
        if not expected.issubset(values[p]):
            raise ValueError("Missing required weather month")
        if any(not np.isfinite(values[p][k]) or values[p][k] <= -900 for k in expected):
            raise ValueError("NASA fill or nonfinite value in required months")
    return d


def acquire_weather():
    WEATHER.mkdir(parents=True, exist_ok=True)
    rows = list(districts().itertuples(index=False))

    def fetch(row):
        path = WEATHER / f"{row.district_id}.json"
        url = weather_request(row)
        if not path.exists():
            last = None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url, timeout=35) as response:
                        raw = response.read()
                    check_weather(json.loads(raw))
                    path.write_bytes(raw)
                    break
                except (OSError, ValueError, KeyError) as error:
                    last = error
            else:
                raise RuntimeError(f"District {row.district_id}: {last}")
        check_weather(json.loads(path.read_bytes()))
        return {"district_id": int(row.district_id), "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}

    manifest, failures = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = {pool.submit(fetch, r): r for r in rows}
        for future in as_completed(tasks):
            try:
                manifest.append(future.result())
            except Exception as error:
                failures.append(str(error))
            print(f"District weather {len(manifest) + len(failures)}/{len(rows)}; failures {len(failures)}", flush=True)
    write_json(OUT / "weather_manifest.json", {"files": sorted(manifest, key=lambda x: x["district_id"]), "failures": failures,
               "interpretation": "NASA POWER monthly reanalysis estimates at source district representative coordinates, not district area means or observations available in real time."})
    if failures:
        raise RuntimeError("Weather acquisition incomplete; resume before modelling")


def prepare():
    f = rice_source()
    f = f.loc[f.district_id.isin(districts().district_id)].copy()
    # -1 is the documented source missing sentinel. Zero/no harvested area has
    # no positive yield target. No upper-yield censoring or final-year pruning.
    valid = (f.yield_kg_ha > 0) & (f.area_1000ha > 0) & (f.production_1000t > 0)
    f.loc[~valid, "yield_kg_ha"] = np.nan
    records = []
    for district_id, g in f.groupby("district_id"):
        by_year = g.set_index("year")
        d = check_weather(json.loads((WEATHER / f"{district_id}.json").read_bytes()))
        for row in g.loc[g.year.between(1987, 2017)].to_dict("records"):
            y = row["year"]
            past = [by_year.at[y - lag, "yield_kg_ha"] if y - lag in by_year.index else np.nan for lag in range(2, 7)]
            if not np.isfinite(past).all() or not np.isfinite(row["yield_kg_ha"]):
                continue
            row.update(dict(zip(HISTORY[:5], past)))
            row["reference_yield"] = float(np.mean(past))
            row["history_trend"] = float(np.polyfit([-2, -3, -4, -5, -6], past, 1)[0])
            row["low_yield_threshold"] = .8 * row["reference_yield"]
            for p in PARAMETERS:
                for month in [6, 7, 8]:
                    row[f"{p}_{month:02d}"] = d["properties"]["parameter"][p][f"{y}{month:02d}"]
            records.append(row)
    table = pd.DataFrame(records).sort_values(["year", "district_id"]).reset_index(drop=True)
    if table.empty or table[NUMERIC + CLIMATE + ["yield_kg_ha"]].isna().any().any():
        raise ValueError("Incomplete modelling table")
    table["low_yield"] = table.yield_kg_ha < table.low_yield_threshold
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "district_years.csv", index=False)
    audit = {"original_records": len(rice_source()), "scope_districts": len(districts()), "model_records": len(table),
             "years": [int(table.year.min()), int(table.year.max())], "states": STATES,
             "target": "Annual district rice yield kg/ha; agricultural year Y means Y to Y+1. Not Kharif-only or farm yield.",
             "history_availability": "Use only Y-2 through Y-6; a conservative assumed two-year administrative reporting lag, not verified historical release vintages.",
             "weather_cutoff": "31 August of agricultural start year Y; June, July and August only.",
             "boundaries": "ICRISAT apportioned historical 1966 district units, not current district boundaries.",
             "units": {p: json.loads((WEATHER / f'{districts().iloc[0].district_id}.json').read_bytes())["parameters"][p]["units"] for p in PARAMETERS},
             "source_consistency_max_difference_kg_ha": float((f.yield_kg_ha - f.production_1000t / f.area_1000ha * 1000).abs().max())}
    write_json(OUT / "data_audit.json", audit)
    return table


def declare_protocol():
    protocol = {"research_question": "Can rainfall, temperature and humidity through August improve annual district rice yield and low-yield-risk outlooks over recent-history baselines in five eastern Indian states?",
                "scope": STATES, "scope_selection": "At least 14 positive yields during 1981-1997 and median rice area at least 10,000 ha during those years.",
                "training_start": 1987, "development_years": [1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005],
                "fit_end": 2004, "calibration_years": list(range(2006, 2012)), "assessment_years": list(range(2012, 2018)),
                "validation": "Expanding window; fit only years <= validation year minus 2. One-year embargo for assumed reporting delay.",
                "candidates": CANDIDATES, "selection": "Lowest pooled development MAE; fixed candidates; tie broken in listed order. Assessment and calibration never select or tune model.",
                "estimators": "Learn residual kg/ha relative to the historical reference. Ridge alpha=100; forest 300 trees, leaf=8, max_features=0.8; boosting 200 iterations, learning_rate=0.05, 7 leaves, min_leaf=15, l2=10, no early stopping. Median imputation/scaling and district/state encoding fit inside each training set. Predicted yields floored at zero.",
                "forecast": "31 August, annual rice kg/ha, historical 1966 district units. Inputs June-August monthly mean daily maximum/minimum temperature C, mean daily precipitation mm/day and RH percent; Y-2..Y-6 yields kg/ha; year and location.",
                "prohibited": "Same-year or Y-1 yields, target-year area/production, weather after August, outcome-derived district selection, random splits and retrospective label corrections.",
                "uncertainty": "Fixed selected estimator fitted through 2004; scaled signed residuals from 2006-2011; empirical 10th/90th quantiles give an approximate 80% interval. Dependence/nonstationarity mean no guaranteed coverage.",
                "risk": "Yield < 80% of district mean of Y-2..Y-6, probability from signed relative residual CDF with add-one smoothing. Test Brier versus development event prevalence.",
                "deployment": "Preserve fixed assessment estimator for reproducible historical inference. Do not present 2026 forecasts using old data or auto-refit on assessment.",
                "seed": 42}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "protocol.json"
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError("Existing protocol differs; create a separately identified study")
    write_json(path, protocol)
    return protocol


def estimator(name):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    columns = NUMERIC + (CLIMATE if name.startswith("Weather") else [])
    transform = ColumnTransformer([
        ("numeric", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), columns),
        ("geography", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["district_id", "state"]),
    ])
    if name.endswith("Ridge"):
        regressor = Ridge(alpha=100)
    elif name.endswith("forest"):
        regressor = RandomForestRegressor(n_estimators=300, min_samples_leaf=8, max_features=.8, random_state=42, n_jobs=2)
    elif name.endswith("boosting"):
        regressor = HistGradientBoostingRegressor(max_iter=200, learning_rate=.05, max_leaf_nodes=7,
                                                  min_samples_leaf=15, l2_regularization=10, early_stopping=False, random_state=42)
    else:
        raise ValueError("Unknown learned estimator")
    return make_pipeline(transform, regressor)


def fit_candidate(name, fitting):
    if name in CANDIDATES[:3]:
        return None
    model = estimator(name)
    model.fit(fitting, fitting.yield_kg_ha - fitting.reference_yield)
    return model


def point_prediction(name, model, inputs):
    if name == "Recent mean":
        y = inputs.reference_yield.to_numpy()
    elif name == "Last available yield":
        y = inputs.yield_lag2.to_numpy()
    elif name == "Historical trend":
        y = (inputs.reference_yield + 4 * inputs.history_trend).to_numpy()
    else:
        y = inputs.reference_yield.to_numpy() + model.predict(inputs)
    return np.maximum(0, y)


def regression_metrics(actual, predicted):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    return {"records": len(actual), "mae_kg_ha": float(mean_absolute_error(actual, predicted)),
            "rmse_kg_ha": float(np.sqrt(mean_squared_error(actual, predicted))), "r_squared": float(r2_score(actual, predicted)),
            "wape_percent": float(100 * np.sum(np.abs(np.asarray(actual) - predicted)) / np.sum(actual))}


def attach_distribution(inputs, predicted, residuals):
    reference = inputs.reference_yield.to_numpy()
    q10, q90 = np.quantile(residuals, [.1, .9])
    threshold = .8 * reference
    # Signed yield residual / reference; this shared calibration distribution
    # is a simple risk model whose calibration is measured on later years.
    relative_cutoff = (threshold - predicted) / reference
    probability = np.array([(1 + np.sum(residuals < v)) / (len(residuals) + 2) for v in relative_cutoff])
    return np.maximum(0, predicted + q10 * reference), np.maximum(0, predicted + q90 * reference), probability


def run_study():
    """Write selection before opening assessment; prevent accidental overwrite."""
    import joblib
    from sklearn.metrics import brier_score_loss, roc_auc_score
    protocol = declare_protocol()
    if (OUT / "summary.json").exists() or (OUT / "selection.json").exists():
        raise ValueError("Study already run. Preserve opened assessment; do not silently retrain or retune.")
    table = prepare()
    dev_predictions = []
    for year in protocol["development_years"]:
        fitting, validation = table.loc[table.year <= year - 2], table.loc[table.year.eq(year)]
        if fitting.empty or validation.empty:
            raise ValueError(f"Empty development split for {year}")
        for name in CANDIDATES:
            model = fit_candidate(name, fitting)
            p = point_prediction(name, model, validation)
            d = validation[["district_id", "year", "yield_kg_ha", "reference_yield", "low_yield"]].copy()
            d["prediction_kg_ha"], d["model"], d["fit_max_year"] = p, name, int(fitting.year.max())
            dev_predictions.append(d)
        print(f"Development year {year} complete", flush=True)
    dev = pd.concat(dev_predictions, ignore_index=True)
    metrics = pd.DataFrame([{ "model": name, **regression_metrics(g.yield_kg_ha, g.prediction_kg_ha)} for name, g in dev.groupby("model", sort=False)])
    metrics = metrics.sort_values("mae_kg_ha", kind="stable")
    selected = metrics.iloc[0].model
    metrics.to_csv(OUT / "development_metrics.csv", index=False)
    dev.to_csv(OUT / "development_predictions.csv", index=False)
    selection = {"selected_model": selected, "selection_criterion": "Pooled development MAE only", "protocol_sha256": hashlib.sha256((OUT / "protocol.json").read_bytes()).hexdigest(),
                 "table_sha256": hashlib.sha256((OUT / "district_years.csv").read_bytes()).hexdigest()}
    write_json(OUT / "selection.json", selection)
    fitting = table.loc[table.year <= protocol["fit_end"]]
    calibration = table.loc[table.year.isin(protocol["calibration_years"])]
    model = fit_candidate(selected, fitting)
    cal_prediction = point_prediction(selected, model, calibration)
    residuals = ((calibration.yield_kg_ha.to_numpy() - cal_prediction) / calibration.reference_yield.to_numpy())
    cal = calibration[["district_id", "year", "yield_kg_ha", "reference_yield"]].copy()
    cal["prediction_kg_ha"], cal["relative_residual"] = cal_prediction, residuals
    cal.to_csv(OUT / "calibration_residuals.csv", index=False)
    # Save fixed assessment estimator before loading assessment targets.
    bundle = {"model": model, "name": selected, "residuals": residuals, "fit_end": protocol["fit_end"],
              "district_ids": sorted(fitting.district_id.unique().tolist()),
              "input_bounds": {c: [float(fitting[c].min()), float(fitting[c].max())] for c in NUMERIC + CLIMATE if c != "year"},
              "sklearn_version": __import__("sklearn").__version__, "protocol_sha256": selection["protocol_sha256"]}
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL)
    assessment = table.loc[table.year.isin(protocol["assessment_years"])].copy()
    assessment["prediction_kg_ha"] = point_prediction(selected, model, assessment)
    assessment["lower_80_kg_ha"], assessment["upper_80_kg_ha"], assessment["low_yield_probability"] = attach_distribution(assessment, assessment.prediction_kg_ha.to_numpy(), residuals)
    assessment["covered_80"] = (assessment.yield_kg_ha >= assessment.lower_80_kg_ha) & (assessment.yield_kg_ha <= assessment.upper_80_kg_ha)
    # All baselines declared before assessment. No final-period fitted comparator.
    test_metrics = []
    for name in dict.fromkeys([selected] + CANDIDATES[:3]):
        p = point_prediction(name, model if name == selected else None, assessment)
        test_metrics.append({"model": name, **regression_metrics(assessment.yield_kg_ha, p)})
    test_metrics = pd.DataFrame(test_metrics)
    test_metrics.to_csv(OUT / "assessment_metrics.csv", index=False)
    assessment.to_csv(OUT / "assessment_predictions.csv", index=False)
    yearly = []
    for year, g in assessment.groupby("year"):
        yearly.append({"year": int(year), **regression_metrics(g.yield_kg_ha, g.prediction_kg_ha),
                       "coverage_80": float(g.covered_80.mean()), "brier_score": float(brier_score_loss(g.low_yield, g.low_yield_probability))})
    pd.DataFrame(yearly).to_csv(OUT / "assessment_year_metrics.csv", index=False)
    regional = []
    for state, g in assessment.groupby("state"):
        regional.append({"state": state, **regression_metrics(g.yield_kg_ha, g.prediction_kg_ha), "coverage_80": float(g.covered_80.mean())})
    pd.DataFrame(regional).to_csv(OUT / "assessment_state_metrics.csv", index=False)
    prevalence = float(table.loc[table.year.isin(protocol["development_years"]), "low_yield"].mean())
    brier = float(brier_score_loss(assessment.low_yield, assessment.low_yield_probability))
    baseline_brier = float(brier_score_loss(assessment.low_yield, np.full(len(assessment), prevalence)))
    bins = pd.cut(assessment.low_yield_probability, np.linspace(0, 1, 6), include_lowest=True)
    calibration_bins = assessment.groupby(bins, observed=False).agg(records=("low_yield", "size"), mean_probability=("low_yield_probability", "mean"), observed_frequency=("low_yield", "mean"))
    calibration_bins.to_csv(OUT / "risk_calibration.csv")
    summary = {**selection, "fit_records": len(fitting), "fit_end": protocol["fit_end"], "calibration_records": len(calibration), "assessment_records": len(assessment),
               "assessment_districts": int(assessment.district_id.nunique()), "assessment_years": protocol["assessment_years"],
               "regression": test_metrics.iloc[0].to_dict(), "interval_coverage_80": float(assessment.covered_80.mean()),
               "mean_interval_width_kg_ha": float((assessment.upper_80_kg_ha - assessment.lower_80_kg_ha).mean()),
               "risk_brier": brier, "prevalence_brier": baseline_brier, "development_prevalence": prevalence,
               "assessment_low_yield_rate": float(assessment.low_yield.mean()),
               "risk_auc": float(roc_auc_score(assessment.low_yield, assessment.low_yield_probability)),
               "risk_beats_prevalence": brier < baseline_brier,
               "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
               "status": "Historical retrospective regional outlook. Not a current-season forecast, farm prediction or causal damage estimate."}
    write_json(OUT / "summary.json", summary)
    return summary


def load_study():
    if not (OUT / "summary.json").exists():
        return None
    return json.loads((OUT / "summary.json").read_text())


def forecast(inputs, bundle=None):
    """Strict single/batch inference; targets and acreage are never required."""
    if bundle is None:
        import joblib
        summary = load_study()
        if summary is None or hashlib.sha256(MODEL.read_bytes()).hexdigest() != summary["model_sha256"]:
            raise ValueError("Forecast artifact missing or checksum differs")
        bundle = joblib.load(MODEL)  # Load only this project's local, verified artifact.
    f = inputs.copy()
    uses_weather = bundle["name"].startswith("Weather")
    required = ["district_id", "year"] + HISTORY[:5] + (CLIMATE if uses_weather else [])
    if set(required) - set(f.columns):
        raise ValueError("Missing inputs: " + ", ".join(sorted(set(required) - set(f.columns))))
    numeric_inputs = [c for c in NUMERIC + CLIMATE + ["district_id"] if c in f]
    for c in numeric_inputs:
        f[c] = pd.to_numeric(f[c], errors="raise")
    if not np.isfinite(f[numeric_inputs]).all().all():
        raise ValueError("All numerical inputs must be finite")
    if not f.district_id.isin(bundle["district_ids"]).all():
        raise ValueError("District outside the trained historical boundary scope")
    if not (f.year.between(2012, 2017) & f.year.mod(1).eq(0)).all():
        raise ValueError("This frozen model supports historical replay for 2012-2017. Current seasons require updated data and revalidation.")
    # Inference uses checked-in derived metadata, so no raw API cache or network
    # is needed on a fresh checkout. No contemporary boundary inference occurs.
    known = pd.read_csv(OUT / "district_years.csv").drop_duplicates("district_id").set_index("district_id")
    for _, r in f.iterrows():
        d = known.loc[r.district_id]
        for c in ["state", "latitude", "longitude"]:
            if c in f and (r[c] != d[c] if c == "state" else not np.isclose(r[c], d[c])):
                raise ValueError("State/coordinates must match the source historical district")
    for c in ["state", "latitude", "longitude"]:
        f[c] = f.district_id.map(known[c])
    if (f[HISTORY[:5]] <= 0).any().any():
        raise ValueError("Historical yields must be positive kg/ha")
    past = f[HISTORY[:5]].to_numpy()
    if "reference_yield" in f and not np.allclose(f.reference_yield, past.mean(axis=1)):
        raise ValueError("Reference must equal the mean of Y-2 through Y-6")
    expected_slope = (past * np.array([2, 1, 0, -1, -2])).sum(axis=1) / 10
    if "history_trend" in f and not np.allclose(f.history_trend, expected_slope):
        raise ValueError("History trend does not match the supplied yields")
    f["reference_yield"] = past.mean(axis=1)
    f["history_trend"] = expected_slope
    for m in [6, 7, 8]:
        if all(f"{p}_{m:02d}" in f for p in PARAMETERS) and ((f[f"T2M_MIN_{m:02d}"] > f[f"T2M_MAX_{m:02d}"]) | ~f[f"RH2M_{m:02d}"].between(0, 100) | (f[f"PRECTOTCORR_{m:02d}"] < 0)).any():
            raise ValueError("Invalid temperature, rainfall or humidity")
    p = point_prediction(bundle["name"], bundle["model"], f)
    lower, upper, risk = attach_distribution(f, p, bundle["residuals"])
    flags = []
    for _, r in f.iterrows():
        outside = [c for c, (lo, hi) in bundle["input_bounds"].items() if c in r and (uses_weather or c not in CLIMATE) and not lo <= r[c] <= hi]
        flags.append(", ".join(outside))
    return pd.DataFrame({"predicted_yield_kg_ha": p, "lower_80_kg_ha": lower, "upper_80_kg_ha": upper,
                         "reference_yield_kg_ha": f.reference_yield.to_numpy(), "low_yield_threshold_kg_ha": .8 * f.reference_yield.to_numpy(),
                         "low_yield_probability": risk, "outside_training_range": flags}, index=inputs.index)
