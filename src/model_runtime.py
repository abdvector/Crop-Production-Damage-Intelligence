"""Verify deployment compatibility without changing the training receipt or fit."""
import json
import platform

import joblib
import numpy as np
import pandas as pd

from src.data import FEATURES, LAGS, load_data, digest
from src.model import OUT, contract


def load_model():
    """Keep scientific checks strict; verify Python portability by prediction replay."""
    report = json.loads((OUT / "report.json").read_text())
    saved = report["contract"]
    current = contract()
    # Python patch/minor versions can differ between the training PC and Cloud.
    # All scientific source hashes and numerical package versions remain exact.
    differences = [key for key in saved if key != "versions" and saved[key] != current.get(key)]
    if differences:
        raise ValueError("Model verification failed: changed " + ", ".join(differences) + ".")
    for name, expected in saved["versions"].items():
        if name != "python" and current["versions"].get(name) != expected:
            raise ValueError(f"Model requires {name} {expected}; installed {current['versions'].get(name)}. Install requirements.txt.")
    if platform.python_version_tuple()[0] != saved["versions"]["python"].split(".")[0]:
        raise ValueError("Deployment requires the same Python major version as training.")
    for name, expected in report["artifact_sha256"].items():
        if digest(OUT / name) != expected:
            raise ValueError(f"Model evidence changed: {name}")
    data = load_data()
    bundle = joblib.load(OUT / "forest.joblib")
    if bundle["contract"] != saved or bundle["features"] != FEATURES:
        raise ValueError("Saved model does not match its training receipt.")
    evaluation = pd.read_csv(OUT / "evaluation.csv", float_precision="round_trip")
    expected = data.loc[data.year.between(2006, 2017)]
    if len(evaluation) != len(expected) or not np.array_equal(
        evaluation[["district_id", "year"]].to_numpy(), expected[["district_id", "year"]].to_numpy()
    ):
        raise ValueError("Saved assessment records do not match the verified source.")
    reference = expected[LAGS].mean(axis=1).to_numpy()
    replay = np.maximum(0, reference + bundle["forest"].predict(expected[FEATURES]))
    if not np.allclose(replay, evaluation.prediction, rtol=1e-12, atol=1e-8):
        raise ValueError("Saved predictions could not be reproduced in this deployment runtime.")
    return bundle, report
