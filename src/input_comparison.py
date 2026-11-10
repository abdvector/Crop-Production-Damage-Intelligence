"""Fixed annual rice comparison: change inputs, keep target and estimator fixed."""
import json

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from src.data import FEATURES, LAGS, ROOT, SOURCE_SHA, TARGET, WEATHER, load_data
from src.model import PARAMETERS, scores

REPORT = ROOT / "models/input_comparison/report.json"
INPUTS = {"Weather only": WEATHER, "Past yields only": LAGS, "Past yields + weather": FEATURES}
PERIODS = {"Earlier check: 2006-2011": (2006, 2011), "Later check: 2012-2017": (2012, 2017)}


def compare():
    frame = load_data()
    training = frame.loc[frame.year.le(2004)]
    assessment = frame.loc[frame.year.between(2006, 2017)]
    results = []
    for method, columns in INPUTS.items():
        model = RandomForestRegressor(**PARAMETERS).fit(training[columns], training[TARGET])
        estimated = model.predict(assessment[columns])
        for period, (start, end) in PERIODS.items():
            mask = assessment.year.between(start, end)
            results.append({"Period": period, "Inputs": method, "Rows": int(mask.sum()),
                            **scores(assessment.loc[mask, TARGET], estimated[np.asarray(mask)])})
    return {"source_sha256": SOURCE_SHA, "training_rows": len(training), "training_years": [1987, 2004],
            "parameters": PARAMETERS, "features": INPUTS, "target": TARGET, "scores": results}


def write_report():
    report = compare()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    return report
