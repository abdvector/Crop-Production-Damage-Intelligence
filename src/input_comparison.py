"""Fixed direct-yield and historical-mean adjustment comparisons."""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from src.data import FEATURES, LAGS, ROOT, SOURCE_SHA, TARGET, WEATHER, digest, load_data
from src.model import OUT, PARAMETERS, scores
from src.model_runtime import load_model

REPORT = ROOT / "models/input_comparison/report.json"
INPUTS = {"Weather only": WEATHER, "Past yields only": LAGS, "Past yields + weather": FEATURES}
PERIODS = {"Earlier check: 2006-2011": (2006, 2011), "Later check: 2012-2017": (2012, 2017)}
RF_HISTORY = "Random Forest: past yields only"
RF_WEATHER = "Random Forest: past yields + weather (app)"
OLS_HISTORY = "OLS: past yields only"
OLS_WEATHER = "OLS: past yields + weather"
LAST_YIELD = "Last available yield (Y-2)"


def score_periods(assessment, estimates, label):
    rows = []
    for period, (start, end) in PERIODS.items():
        mask = assessment.year.between(start, end)
        rows.append({"Period": period, **label, "Rows": int(mask.sum()),
                     **scores(assessment.loc[mask, TARGET], estimates[np.asarray(mask)])})
    return rows


def compare_adjustments(training, assessment):
    # Verify the deployed fit and its exact assessment predictions before using them.
    _, receipt = load_model()
    saved = pd.read_csv(OUT / "evaluation.csv", float_precision="round_trip")
    keys = ["district_id", "year"]
    pd.testing.assert_frame_equal(saved[keys].reset_index(drop=True), assessment[keys].reset_index(drop=True))
    np.testing.assert_allclose(saved[TARGET], assessment[TARGET], rtol=0, atol=1e-9)
    reference = assessment[LAGS].mean(axis=1).to_numpy()
    residual = training[TARGET] - training[LAGS].mean(axis=1)
    predictions = {}
    for name, estimator, columns in [
        (RF_HISTORY, RandomForestRegressor(**PARAMETERS), LAGS),
        (OLS_HISTORY, LinearRegression(), LAGS),
        (OLS_WEATHER, LinearRegression(), FEATURES),
    ]:
        estimator.fit(training[columns], residual)
        predictions[name] = np.maximum(0, reference + estimator.predict(assessment[columns]))
    predictions[RF_WEATHER] = saved.prediction.to_numpy()
    rows = []
    for name in (RF_HISTORY, RF_WEATHER, OLS_HISTORY, OLS_WEATHER):
        rows.extend(score_periods(assessment, predictions[name], {"Method": name}))
    baselines = score_periods(assessment, assessment[LAGS[0]].to_numpy(), {"Method": LAST_YIELD})
    actual = assessment[TARGET].to_numpy()
    yearly = pd.DataFrame({"year": assessment.year.to_numpy(),
                           "Random Forest": abs(actual - predictions[RF_HISTORY]) - abs(actual - predictions[RF_WEATHER]),
                           "OLS": abs(actual - predictions[OLS_HISTORY]) - abs(actual - predictions[OLS_WEATHER])})
    return {"target": "Observed yield minus the mean of five past yields",
            "app_evaluation_sha256": receipt["artifact_sha256"]["evaluation.csv"],
            "scores": rows, "additional_baselines": baselines,
            "weather_mae_gain_by_year_kg_ha": yearly.groupby("year", as_index=False).mean().to_dict("records")}


def compare():
    frame = load_data()
    training = frame.loc[frame.year.le(2004)]
    assessment = frame.loc[frame.year.between(2006, 2017)]
    results = []
    for method, columns in INPUTS.items():
        model = RandomForestRegressor(**PARAMETERS).fit(training[columns], training[TARGET])
        estimated = model.predict(assessment[columns])
        results.extend(score_periods(assessment, estimated, {"Inputs": method}))
    return {"source_sha256": SOURCE_SHA, "training_rows": len(training), "training_years": [1987, 2004],
            "parameters": PARAMETERS, "features": INPUTS, "target": TARGET, "scores": results,
            "code_sha256": digest(ROOT / "src/input_comparison.py"),
            "adjustment_comparison": compare_adjustments(training, assessment)}


def write_report():
    report = compare()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    return report
