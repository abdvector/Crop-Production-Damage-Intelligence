"""2018-only timed product-mass features and matched-cohort development ablations."""
import hashlib
import json

import numpy as np
import pandas as pd

from src.rice_field_data import FIELD_DATA

FOLDER = FIELD_DATA / "management_2018"
PRODUCTS = ["Urea", "DAP", "MoP", "SSP", "ZnSO4"]
AREA_FACTOR = .40468564224


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def known_amount(amount, selection, product):
    """Recorded zero is accepted only with an explicit compatible product selection."""
    amount = pd.to_numeric(amount, errors="coerce")
    labels = selection.fillna("").astype(str).str.strip()
    selected = labels.str.split().map(lambda values: product in values)
    explicit_none = labels.str.lower().eq("none")
    known_selection = labels.ne("")
    compatible = (amount.gt(0) & selected) | (amount.eq(0) & known_selection & ~selected)
    compatible &= ~(amount.gt(0) & explicit_none)
    return amount.where(compatible & amount.ge(0))


def timed_amount(amount, days, selection, product, cutoff=60):
    """Known future events contribute zero; ambiguous quantities/times stay missing."""
    clean = known_amount(amount, selection, product)
    days = pd.to_numeric(days, errors="coerce")
    result = clean.where(clean.eq(0) | days.between(0, cutoff))
    # Event-day values alone establish that this event cannot contribute by cutoff.
    result.loc[days.gt(cutoff)] = 0.0
    return result


def prepare_management(source):
    source = source.reset_index(drop=True)
    frame = pd.DataFrame({"record_id": "data:" + pd.Series(np.arange(1, len(source) + 1)).astype(str)})
    area = pd.to_numeric(source.cropLarestAreaAcre, errors="coerce")
    local = pd.to_numeric(source.cropLargestArea, errors="coerce")
    conversion = pd.to_numeric(source.acreConv, errors="coerce")
    frame["area_arithmetic_pass"] = np.isfinite(area) & np.isfinite(local) & np.isfinite(conversion) & area.gt(0) & conversion.gt(0) & np.isclose(area, local / conversion, rtol=.01, atol=.001)
    hectare = area * AREA_FACTOR
    event_audit = []
    selectors = {1: "F.firstTopDressFert", 2: "F.secondTopDressFert", 3: "F.thirdTopDressFert"}
    for product in PRODUCTS:
        basal = known_amount(source[f"basal{product}"], source["F.basalFerts"], product)
        components = [basal]
        for number in range(1, 4):
            amount = pd.to_numeric(source[f"{number}td{product}"], errors="coerce")
            days = pd.to_numeric(source[f"{number}appDays{product}"], errors="coerce")
            value = timed_amount(amount, days, source[selectors[number]], product)
            components.append(value)
            event_audit.append({"product": product, "event": number, "source_rows": len(source),
                "positive_amount_rows": int(amount.gt(0).sum()), "positive_missing_day_rows": int((amount.gt(0) & days.isna()).sum()),
                "positive_after_cutoff_rows": int((amount.gt(0) & days.gt(60)).sum()), "ambiguous_event_rows": int(value.isna().sum())})
        frame[f"{product}_basal_product_kg_ha"] = basal / hectare
        frame[f"{product}_through_day60_product_kg_ha"] = pd.concat(components, axis=1).sum(axis=1, min_count=4) / hectare
    features = [c for c in frame if c.endswith("_kg_ha")]
    frame["complete_management"] = np.isfinite(frame[features]).all(axis=1) & frame[features].ge(0).all(axis=1)
    FOLDER.mkdir(parents=True, exist_ok=True)
    frame.to_csv(FOLDER / "features_local.csv", index=False, lineterminator="\n")
    pd.DataFrame(event_audit).to_csv(FOLDER / "event_audit.csv", index=False, lineterminator="\n")
    summary = {"prepared_on": "2026-10-19", "year": 2018, "source_object": "data", "source_rows": len(source),
        "product_features": features, "products": PRODUCTS, "hectares_per_acre": AREA_FACTOR, "cutoff_day": 60,
        "area_arithmetic_pass_rows": int(frame.area_arithmetic_pass.sum()),
        "complete_management_rows": int(frame.complete_management.sum()),
        "complete_and_area_pass_rows": int((frame.complete_management & frame.area_arithmetic_pass).sum()),
        "zero_policy": "Zero accepted only with an explicit compatible product-selection response; blank selections stay unknown",
        "missing_policy": "No inferred dates, no partial cumulative sums; complete-case primary comparison",
        "source_features_sha256": _hash(FOLDER / "features_local.csv"),
        "limitations": ["2018 form only; no inheritance to 2017/2019", "Product mass, not nutrient mass",
                        "Retrospective event reconstruction and report-completeness selection", "No validation of actual dose entries against farm records"]}
    _write_json(FOLDER / "feature_audit.json", summary)
    return summary


def declare_experiment():
    """Freeze configuration before fitting; fail if an existing declaration would change."""
    original = json.loads((FIELD_DATA / "field_model_protocol.json").read_text())
    audit = json.loads((FOLDER / "feature_audit.json").read_text())
    protocol = {"version": "management-2018-matched-v1", "declared_on": "2026-10-19", "seed": 20261019,
        "year": 2018, "target": "yield_kg_ha", "core_numeric": original["numeric_features"],
        "core_categorical": original["categorical_features"], "product_numeric": audit["product_features"],
        "static_categorical": ["soil_texture_label_normalised", "irrigation_availability_reported_normalised"],
        "categorical_preprocessing": original["categorical_preprocessing"],
        "models": [c for c in original["regression_candidates"] if c["name"] in
                   ["Ridge alpha=1000", "Random Forest leaf=50", "Gradient boosting leaves=15"]],
        "blocks": ["weather_planting", "plus_static_context", "plus_static_and_timed_products"],
        "cohort": "2018 primary cohort, positive/consistent area and complete declared management features; matched for all blocks",
        "folds": "Existing district fold assignments; remove fitting rows sharing any source weather cell with validation",
        "primary_comparisons": "Paired product/static additions within each fixed model on identical records/splits; no winner-based final claim",
        "status": "Development sensitivity after earlier development results; no new untouched assessment",
        "model_search": False, "2019_used": False, "feature_sha256": audit["source_features_sha256"]}
    path = FOLDER / "protocol.json"
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError("Existing declaration differs; version a new experiment")
    _write_json(path, protocol)
    return protocol


def _configuration(protocol, block):
    result = {"seed": protocol["seed"], "target": protocol["target"],
              "numeric_features": list(protocol["core_numeric"]), "categorical_features": list(protocol["core_categorical"]),
              "categorical_preprocessing": protocol["categorical_preprocessing"]}
    if block != "weather_planting":
        result["categorical_features"] += protocol["static_categorical"]
    if block == "plus_static_and_timed_products":
        result["numeric_features"] += protocol["product_numeric"]
    return result


def run_management_comparison(progress=print):
    from src.rice_field_cohort import geographic_masks
    from src.rice_field_model import fit_predict, metrics
    if (FOLDER / "summary.json").exists():
        raise ValueError("Development comparison already exists; load saved results instead of rerunning")
    protocol = json.loads((FOLDER / "protocol.json").read_text())
    source_trace = json.loads((FIELD_DATA / "yield_label_trace.json").read_text())
    preserved = source_trace["preserved_result_hashes"]
    for name, checksum in preserved.items():
        if _hash(FIELD_DATA / "model" / name) != checksum:
            raise ValueError("Earlier assessment no longer matches its preserved hash")
    if _hash(FOLDER / "features_local.csv") != protocol["feature_sha256"]:
        raise ValueError("Features changed after declaration")
    cohort = pd.read_csv(FIELD_DATA / "cohort_local.csv", low_memory=False)
    cohort = cohort.loc[cohort.year.eq(2018)].copy()
    features = pd.read_csv(FOLDER / "features_local.csv")
    joined = cohort.merge(features, on="record_id", validate="one_to_one")
    eligible = joined.area_arithmetic_pass & joined.complete_management
    data = joined.loc[eligible].copy()
    splits = pd.read_csv(FIELD_DATA / "development_splits_local.csv")
    data = data.merge(splits[["record_id", "geographic_fold"]], on="record_id", validate="one_to_one")
    if not data.year.eq(2018).all() or not data.record_id.is_unique:
        raise ValueError("Invalid matched-cohort membership")
    baseline_candidates = [{"name": "Global training mean", "kind": "mean"}, {"name": "State training mean", "kind": "state_mean"}]
    predictions, fold_rows, split_rows = [], [], []
    for fold in range(5):
        train, valid, purged = geographic_masks(data, fold)
        training, validation = data.loc[train], data.loc[valid]
        if len(training) < 100 or len(validation) < 100:
            raise ValueError("Insufficient rows after spatial purge")
        split_rows.append({"fold": fold, "fitting_records": len(training), "validation_records": len(validation), "purged_records": int(purged.sum())})
        for block in ["baseline"] + protocol["blocks"]:
            candidates = baseline_candidates if block == "baseline" else protocol["models"]
            config = _configuration(protocol, block)
            for candidate in candidates:
                progress(f"2018 fold {fold}: {block}, {candidate['name']}")
                estimate = fit_predict(training, validation, candidate, config)
                table = validation[["record_id", "year", "state", "district_group"]].copy()
                table["model"], table["block"], table["fold"] = candidate["name"], block, fold
                table["observed_yield_kg_ha"], table["predicted_yield_kg_ha"] = validation.yield_kg_ha.to_numpy(), estimate
                predictions.append(table)
                fold_rows.append({"fold": fold, "model": candidate["name"], "block": block, **metrics(validation.yield_kg_ha, estimate)})
    rows = pd.concat(predictions, ignore_index=True)
    rows.to_csv(FOLDER / "predictions_local.csv", index=False, lineterminator="\n")
    pd.DataFrame(fold_rows).to_csv(FOLDER / "fold_metrics.csv", index=False, lineterminator="\n")
    pd.DataFrame(split_rows).to_csv(FOLDER / "split_counts.csv", index=False, lineterminator="\n")
    aggregates = [{"model": model, "block": block, **metrics(g.observed_yield_kg_ha, g.predicted_yield_kg_ha)}
                  for (model, block), g in rows.groupby(["model", "block"])]
    aggregate = pd.DataFrame(aggregates)
    aggregate.to_csv(FOLDER / "metrics.csv", index=False, lineterminator="\n")
    changes = []
    for model in [c["name"] for c in protocol["models"]]:
        group = aggregate.loc[aggregate.model.eq(model)].set_index("block")
        for first, second, label in [("weather_planting", "plus_static_context", "static_context_added"),
            ("plus_static_context", "plus_static_and_timed_products", "timed_products_added"),
            ("weather_planting", "plus_static_and_timed_products", "all_context_added")]:
            changes.append({"model": model, "comparison": label, "rmse_gain_kg_ha": float(group.loc[first,"rmse_kg_ha"] - group.loc[second,"rmse_kg_ha"]),
                "mae_gain_kg_ha": float(group.loc[first,"mae_kg_ha"] - group.loc[second,"mae_kg_ha"]),
                "rmse_improvement_percent": float(100 * (1 - group.loc[second,"rmse_kg_ha"] / group.loc[first,"rmse_kg_ha"]))})
    pd.DataFrame(changes).to_csv(FOLDER / "paired_changes.csv", index=False, lineterminator="\n")
    data.groupby("state").agg(records=("record_id","size"),districts=("district_group","nunique")).reset_index().to_csv(FOLDER / "coverage.csv",index=False,lineterminator="\n")
    summary = {"version": protocol["version"], "completed_on": "2026-10-19", "eligible_primary_2018_records": len(cohort),
        "matched_records": len(data), "excluded_area_or_incomplete_records": int((~eligible).sum()),
        "district_groups": int(data.district_group.nunique()), "folds":5, "fixed_models":3, "blocks":3,
        "protocol_sha256":_hash(FOLDER / "protocol.json"), "feature_sha256":protocol["feature_sha256"],
        "record_membership_sha256":hashlib.sha256("\n".join(sorted(data.record_id)).encode()).hexdigest(),
        "development_only":True, "2019_used":False, "original_assessment_modified":False,
        "preserved_original_result_hashes":preserved, "source_archive_sha256":source_trace["archive_sha256"],
        "limitations":["Complete-report cohort is not representative of all farms", "One survey year; no temporal assessment",
            "Static access and doses reconstructed from a retrospective survey", "Product mass not verified nutrient rates",
            "District and weather-cell purging does not prove farm independence", "No causal impact or savings claim"]}
    for name, checksum in preserved.items():
        if _hash(FIELD_DATA / "model" / name) != checksum:
            raise ValueError("Original assessment changed during management experiment")
    _write_json(FOLDER / "summary.json",summary)
    return summary


def load_management_results():
    path = FOLDER / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text()), pd.read_csv(FOLDER / "metrics.csv"), pd.read_csv(FOLDER / "paired_changes.csv")


def summarise_management_diagnostics():
    """Describe already saved paired predictions without refitting or selecting models."""
    from src.rice_field_model import metrics
    rows = pd.read_csv(FOLDER / "predictions_local.csv")
    states = []
    for (model, block, state), group in rows.groupby(["model", "block", "state"]):
        states.append({"model":model, "block":block, "state":state,
                       **metrics(group.observed_yield_kg_ha, group.predicted_yield_kg_ha)})
    pd.DataFrame(states).to_csv(FOLDER / "state_metrics.csv",index=False,lineterminator="\n")
    folds = pd.read_csv(FOLDER / "fold_metrics.csv")
    paired = []
    for model, group in rows.loc[rows.block.ne("baseline")].groupby("model"):
        wide = group.pivot(index="record_id",columns="block",values="predicted_yield_kg_ha")
        truth = group.drop_duplicates("record_id").set_index("record_id")[["district_group","observed_yield_kg_ha"]]
        wide = wide.join(truth,validate="one_to_one")
        for block in ["weather_planting","plus_static_context","plus_static_and_timed_products"]:
            wide[block+"_sse"]=(wide[block]-wide.observed_yield_kg_ha)**2
        districts=wide.groupby("district_group").agg(n=("observed_yield_kg_ha","size"),
            core=("weather_planting_sse","sum"),static=("plus_static_context_sse","sum"),augmented=("plus_static_and_timed_products_sse","sum"))
        rng=np.random.default_rng(20261019)
        sampled=rng.integers(0,len(districts),size=(2000,len(districts)))
        n=districts.n.to_numpy()[sampled].sum(axis=1)
        for first,second,label in [("core","augmented","all_context_added"),("static","augmented","timed_products_added")]:
            gain=np.sqrt(districts[first].to_numpy()[sampled].sum(axis=1)/n)-np.sqrt(districts[second].to_numpy()[sampled].sum(axis=1)/n)
            fold_table=folds.loc[folds.model.eq(model)].pivot(index="fold",columns="block",values="rmse_kg_ha")
            first_block="weather_planting" if first=="core" else "plus_static_context"
            paired.append({"model":model,"comparison":label,"districts":len(districts),
                "folds_with_lower_rmse":int((fold_table.plus_static_and_timed_products<fold_table[first_block]).sum()),
                "district_bootstrap_gain_low_kg_ha":float(np.quantile(gain,.025)),
                "district_bootstrap_gain_high_kg_ha":float(np.quantile(gain,.975)),
                "qualification":"Descriptive paired district resampling; independence/exchangeability not established"})
    pd.DataFrame(paired).to_csv(FOLDER / "paired_stability.csv",index=False,lineterminator="\n")
