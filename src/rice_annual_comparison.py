"""Materialize the declared annual comparator forecasts without changing the study."""
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from src import rice_regional as annual
from src.rice_foundation import sha

OUT = annual.OUT.parent / "regional_comparison"
PROTOCOL = annual.ROOT / "docs/Annual_Model_Comparison.md"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")


def run():
    source = annual.OUT
    selection = json.loads((source / "selection.json").read_text())
    summary = json.loads((source / "summary.json").read_text())
    protocol = json.loads((source / "protocol.json").read_text())
    if sha(source / "district_years.csv") != selection["table_sha256"] or sha(source / "protocol.json") != selection["protocol_sha256"]:
        raise ValueError("Original annual inputs no longer match frozen selection")
    if sha(annual.MODEL) != summary["model_sha256"]:
        raise ValueError("Original selected artifact changed")
    if protocol["fit_end"] != 2004 or protocol["assessment_years"] != list(range(2012, 2018)) or protocol["candidates"] != annual.CANDIDATES:
        raise ValueError("Unexpected annual study contract")
    protected = [p for p in source.iterdir() if p.is_file()] + [annual.MODEL, Path(annual.__file__)]
    paths = protected + [Path(__file__), PROTOCOL]
    hashes = {str(p.relative_to(annual.ROOT)).replace('\\', '/'): sha(p) for p in paths}
    declaration = {"input_sha256": hashes, "selected_model": selection["selected_model"],
                   "fit_end": 2004, "assessment_years": protocol["assessment_years"], "candidates": annual.CANDIDATES,
                   "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                                "scikit_learn": sklearn.__version__},
                   "status": "retrospective fixed-settings comparators; original selection preserved"}
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT / "run_manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != declaration:
        raise ValueError("Declared comparator run changed; version rather than overwrite")
    if (OUT / "completed.json").exists():
        receipt = json.loads((OUT / "completed.json").read_text())
        for name, value in receipt.items():
            if sha(OUT / name) != value:
                raise ValueError(f"Completed comparator result changed: {name}")
        return json.loads((OUT / "verification.json").read_text())
    write_json(manifest, declaration)
    # Match original numeric district IDs and source row order before encoding.
    table = pd.read_csv(source / "district_years.csv")
    original = pd.read_csv(source / "assessment_predictions.csv")
    fitting = table.loc[table.year <= 2004].copy()
    future = table.loc[table.year.isin(protocol["assessment_years"])].copy()
    keys = ["district_id", "year"]
    if len(future) != 300 or future.duplicated(keys).any() or fitting.year.max() != 2004:
        raise ValueError("Invalid fitting/evaluation cohort")
    numeric = annual.NUMERIC + annual.CLIMATE
    if not np.isfinite(fitting[numeric+["yield_kg_ha"]]).all().all() or not np.isfinite(future[numeric]).all().all():
        raise ValueError("Nonfinite comparison inputs")
    if not future[keys].reset_index(drop=True).equals(original[keys].reset_index(drop=True)):
        raise ValueError("Original assessment order/cohort differs")
    if not np.allclose(future.yield_kg_ha, original.yield_kg_ha, rtol=0, atol=1e-7):
        raise ValueError("Assessment target mismatch")
    bundle = joblib.load(annual.MODEL)
    if bundle["name"] != selection["selected_model"] or bundle["fit_end"] != 2004:
        raise ValueError("Saved estimator metadata differs")
    old_scores = pd.read_csv(source / "assessment_metrics.csv").set_index("model")
    outputs, scores, reproduced = [], [], []
    inputs = future[numeric+["district_id", "state"]].copy()
    for name in annual.CANDIDATES:
        with threadpool_limits(limits=2):
            model = bundle["model"] if name == selection["selected_model"] else annual.fit_candidate(name, fitting)
            predicted = annual.point_prediction(name, model, inputs)
        if not np.isfinite(predicted).all() or (predicted < 0).any():
            raise ValueError("Invalid comparator predictions")
        values = annual.regression_metrics(future.yield_kg_ha, predicted)
        if name in old_scores.index:
            for metric in ("mae_kg_ha", "rmse_kg_ha", "r_squared", "wape_percent"):
                if not np.isclose(values[metric], old_scores.at[name, metric], rtol=0, atol=1e-7):
                    raise ValueError(f"Original score failed to reproduce: {name}, {metric}")
            reproduced.append(name)
        if name == selection["selected_model"] and not np.allclose(predicted, original.prediction_kg_ha, rtol=0, atol=1e-7):
            raise ValueError("Original selected predictions failed to reproduce")
        row = future[["district_id", "district", "state", "year", "yield_kg_ha", "reference_yield", "low_yield_threshold"]].copy()
        row["model"], row["prediction_kg_ha"], row["fit_max_year"] = name, predicted, 2004
        row["lower_80_kg_ha"], row["upper_80_kg_ha"] = np.nan, np.nan
        if name == selection["selected_model"]:
            for bound in ("lower_80_kg_ha", "upper_80_kg_ha"):
                row[bound] = original[bound].to_numpy()
        outputs.append(row)
        scores.append({"model": name, **values})
        print(f"Saved annual comparator: {name}", flush=True)
    predictions = pd.concat(outputs, ignore_index=True)
    if len(predictions) != 2100 or predictions.duplicated(["model"]+keys).any():
        raise ValueError("Invalid seven-method forecast cohort")
    predictions.to_csv(OUT / "all_method_predictions.csv", index=False, lineterminator="\n")
    pd.DataFrame(scores).to_csv(OUT / "all_method_metrics.csv", index=False, lineterminator="\n")
    if any(sha(annual.ROOT / name) != value for name, value in hashes.items()):
        raise ValueError("Original study or declaration changed during fitting")
    verification = {"methods": len(annual.CANDIDATES), "records_per_method": 300, "total_records": len(predictions),
                    "states": sorted(future.state.unique().tolist()), "districts": int(future.district_id.nunique()),
                    "original_score_models_reproduced": reproduced, "selected_predictions_reproduced": True,
                    "original_files_unchanged": True, "original_selection_preserved": True,
                    "intervals_only_for_original_selected_model": True,
                    "new_retrospective_comparators": [n for n in annual.CANDIDATES if n not in old_scores.index]}
    write_json(OUT / "verification.json", verification)
    write_json(OUT / "completed.json", {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "completed.json"})
    return verification
