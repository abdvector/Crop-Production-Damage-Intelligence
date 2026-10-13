"""Read-only source-yield trace and unresolved review ledger; never repair by guessing."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.rice_field_data import FIELD_DATA

SOURCE_MAP = {"rice_2017": (2017, "L.tonPerHectare", "totalGrainYieldQUINTAL", None),
              "data": (2018, "L.tonPerHectare", "largestPlotYieldQUNITAL", "L.quintalPerAcre"),
              "data1": (2019, "K.tonPerHectare", "largestPlotYieldQUNITAL", "K.quintalPerAcre")}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trace_source_yields(objects, archive_path):
    """Accept publisher RData objects; no names, phone numbers or GPS are exported."""
    normalised = pd.read_csv(FIELD_DATA / "field_records_local.csv", low_memory=False).set_index("record_id")
    model_path = FIELD_DATA / "model"
    preserved = {name: _sha(model_path / name) for name in ["selection.json", "assessment_metrics.csv", "assessment_predictions_local.csv"]}
    rows, reviews = [], []
    for name, (year, target_column, quantity_column, per_acre_column) in SOURCE_MAP.items():
        source = objects[name].reset_index(drop=True)
        y = pd.to_numeric(source[target_column], errors="coerce")
        quantity = pd.to_numeric(source[quantity_column], errors="coerce")
        area = pd.to_numeric(source.cropLarestAreaAcre, errors="coerce")
        record_ids = name + ":" + pd.Series(np.arange(1, len(source) + 1)).astype(str)
        project_y = normalised.loc[record_ids, "yield_kg_ha"].to_numpy()
        exact_project_conversion = np.isclose(project_y, y.to_numpy() * 1000, rtol=0, atol=1e-8, equal_nan=True)
        if not exact_project_conversion.all():
            raise ValueError("Project labels disagree with publisher tonnes-to-kilograms conversion")
        source_formula = quantity / area * .25
        match = np.isclose(source_formula, y, rtol=.01, atol=.01)
        valid = y.notna() & quantity.notna() & area.gt(0)
        flagged = y.gt(15)
        result = {"source_object": name, "year": year, "source_rows": len(source), "target_column": target_column,
            "quantity_column": quantity_column, "quantity_scope_verified": False,
            "project_conversion_agreement_rows": int(exact_project_conversion.sum()),
            "source_quantity_area_comparison_rows": int(valid.sum()),
            "source_quantity_area_agreement_rows_1pct": int((valid & match).sum()),
            "stored_per_acre_to_tonnes_comparison_rows": 0, "stored_per_acre_to_tonnes_agreement_rows": 0,
            "stored_per_acre_agreement_with_one_decimal_rounding_rows": 0,
            "review_flag_rows": int(flagged.sum()), "review_flag_quantity_area_agreement_rows": int((flagged & valid & match).sum()),
            "max_source_tonnes_ha": float(y.max()),
            "interpretation": "Arithmetic consistency is not verification of observed units, quantity scope or farmer report"}
        if per_acre_column:
            per_acre = pd.to_numeric(source[per_acre_column], errors="coerce")
            result["stored_per_acre_to_tonnes_comparison_rows"] = int((per_acre.notna() & y.notna()).sum())
            result["stored_per_acre_to_tonnes_agreement_rows"] = int(np.isclose(per_acre * .25, y, rtol=0, atol=.0051).sum())
            result["stored_per_acre_agreement_with_one_decimal_rounding_rows"] = int(np.isclose(per_acre * .25, y, rtol=0, atol=.051).sum())
        rows.append(result)
        for index in source.index[flagged]:
            reviews.append({"record_id": record_ids.iloc[index], "source_object": name, "source_row": int(index + 1),
                "year": year, "source_target_tonnes_ha": float(y.iloc[index]), "project_target_kg_ha": float(y.iloc[index] * 1000),
                "reported_quantity_source_column": quantity_column, "reported_quantity_value": float(quantity.iloc[index]),
                "reported_plot_acres": float(area.iloc[index]), "source_formula_tonnes_ha": float(source_formula.iloc[index]),
                "formula_agreement_1pct": bool(match[index]), "review_status": "Unresolved; retain original label",
                "possible_issue": "Quantity-unit confusion needs verification" if quantity.iloc[index] >= 1000 else "Quantity/area/report needs verification",
                "confirmed_correction": False})
    trace = pd.DataFrame(rows)
    trace.to_csv(FIELD_DATA / "yield_trace_by_year.csv", index=False, lineterminator="\n")
    ledger = pd.DataFrame(reviews)
    ledger.to_csv(FIELD_DATA / "yield_review_local.csv", index=False, lineterminator="\n")
    summary = {"version": "source-yield-trace-v1", "audited_on": "2026-10-13", "archive_sha256": _sha(archive_path),
        "traced_source_rows": int(trace.source_rows.sum()), "project_conversion_agreement_rows": int(trace.project_conversion_agreement_rows.sum()),
        "review_records": len(ledger), "flagged_source_formula_agreement_records": int(ledger.formula_agreement_1pct.sum()),
        "flagged_quantity_at_least_1000_records": int(ledger.reported_quantity_value.ge(1000).sum()),
        "confirmed_corrections": 0, "existing_results_modified": False,
        "preserved_result_hashes": preserved, "raw_identifiers_exported": False,
        "questionnaire_status": "2018 documentation reviewed; yield-unit conflicts and year-specific limits documented" if (FIELD_DATA / "documentation_audit.json").exists() else "Public repository identified; documentation not acquired because access failed",
        "limitations": ["Named quintal fields do not prove actual units entered by respondents",
            "2017 quantity scope unresolved; candidate quantity/area formula mostly disagrees with published labels",
            "Two 2018 per-acre-derived values disagree even allowing one-decimal rounding; author edits or semantics unresolved",
            "2019 arithmetic consistency does not establish validity of extreme input quantities",
            "No automatic division by 100, winsorisation, source-row deletion or model reselection"]}
    for name, checksum in preserved.items():
        if _sha(model_path / name) != checksum:
            raise ValueError("Original assessment changed during source audit")
    (FIELD_DATA / "yield_label_trace.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def load_label_trace():
    path = FIELD_DATA / "yield_label_trace.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_documentation_audit():
    path = FIELD_DATA / "documentation_audit.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
