"""One fixed numerical-input forest and one baseline, with temporal evaluation."""
import json
import platform

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.data import ROOT, FEATURES, LAGS, TARGET, SOURCE_SHA, load_data, validate_inputs, digest

OUT = ROOT / "models/input_model"
PROTOCOL = ROOT / "docs/Method.md"
PARAMETERS = dict(n_estimators=300, max_depth=4, min_samples_leaf=10, random_state=42, n_jobs=2)


def scores(actual, predicted):
    return {"MAE (kg/ha)": float(mean_absolute_error(actual, predicted)),
            "RMSE (kg/ha)": float(np.sqrt(mean_squared_error(actual, predicted))),
            "R squared": float(r2_score(actual, predicted)),
            "Mean error (kg/ha)": float(np.mean(predicted-actual))}


def contract():
    return {"source_sha256": SOURCE_SHA, "features": FEATURES, "parameters": PARAMETERS,
            "code_sha256": {p.name: digest(p) for p in [ROOT / "src/data.py", ROOT / "src/model.py", PROTOCOL]},
            "versions": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__, "sklearn": sklearn.__version__}}


def build():
    """A new retrospective experiment; never modifies old results or receipts."""
    frame = load_data()
    stamp = contract()
    if (OUT / "report.json").exists():
        load_model()
        return json.loads((OUT / "report.json").read_text())
    train = frame.loc[frame.year <= 2004]
    forest = RandomForestRegressor(**PARAMETERS)
    reference = train[LAGS].mean(axis=1)
    forest.fit(train[FEATURES], train[TARGET]-reference)
    evaluated = frame.loc[frame.year.between(2006, 2017)].copy()
    evaluated["baseline"] = evaluated[LAGS].mean(axis=1)
    evaluated["prediction"] = np.maximum(0, evaluated.baseline + forest.predict(evaluated[FEATURES]))
    evaluated["period"] = np.where(evaluated.year <= 2011, "Earlier check: 2006-2011", "Later check: 2012-2017")
    rows = []
    for period, part in evaluated.groupby("period", sort=False):
        for label, column in [("Numerical Random Forest", "prediction"), ("Recent mean baseline", "baseline")]:
            rows.append({"Period": period, "Method": label, "Rows": len(part), **scores(part[TARGET], part[column])})
    report = {"contract": stamp, "training_rows": len(train), "training_years": [int(train.year.min()), 2004],
              "predictor_count": len(FEATURES), "scores": rows,
              "interpretation": "Retrospective comparison on previously examined years; no independent new test or operational damage validation."}
    OUT.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(OUT / "evaluation.csv", index=False, lineterminator="\n")
    bundle = {"forest": forest, "features": FEATURES, "contract": stamp,
              "minimum": train[FEATURES].min().to_dict(), "maximum": train[FEATURES].max().to_dict()}
    joblib.dump(bundle, OUT / "forest.joblib")
    report["artifact_sha256"] = {name: digest(OUT / name) for name in ["forest.joblib", "evaluation.csv"]}
    (OUT / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return report


def load_model():
    if not (OUT / "report.json").exists():
        raise ValueError("Build the model first: python app.py --train")
    report = json.loads((OUT / "report.json").read_text())
    if report["contract"] != contract():
        raise ValueError("Model inputs, code or environment changed. Review and version a new experiment.")
    for name, expected in report["artifact_sha256"].items():
        if digest(OUT / name) != expected:
            raise ValueError(f"Model evidence changed: {name}")
    return joblib.load(OUT / "forest.joblib"), report


def predict(values, bundle):
    frame = pd.DataFrame([values])[FEATURES]
    validate_inputs(frame)
    reference = float(frame[LAGS].mean(axis=1).iloc[0])
    estimate = max(0., reference+float(bundle["forest"].predict(frame)[0]))
    outside = [column for column in FEATURES if not bundle["minimum"][column] <= values[column] <= bundle["maximum"][column]]
    return {"estimate": estimate, "reference": reference, "change_percent": 100*(estimate/reference-1), "outside": outside}
