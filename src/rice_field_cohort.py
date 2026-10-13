"""Audit geographical concordance and declare field-study cohorts before fitting."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import covers, make_valid, points, prepare
from shapely.geometry import shape

from src.rice_field_data import FIELD_DATA
from src.rice_field_weather import PARAMETERS

ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = ROOT / "data/raw/rice/india_boundaries"


def canonical_label(value):
    if pd.isna(value):
        return "unknown"
    ascii_text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip() or "unknown"


def audit_management(objects):
    """Publish aggregate timing and arithmetic checks; never infer unknown timing."""
    timing, units = [], []
    for name in ("rice_2017", "data", "data1"):
        table = objects[name]
        def number(column):
            return pd.to_numeric(table[column], errors="coerce")
        for product in ("Urea", "DAP"):
            for event in range(1, 4):
                prefix = "X" if name == "rice_2017" else ""
                amount = number(f"{prefix}{event}td{product}")
                day = number(f"{prefix}{event}appDays{product}")
                positive = amount.gt(0)
                timing.append({"source_object": name, "product": product, "application_number": event,
                    "rows": len(table), "positive_amount_rows": int(positive.sum()),
                    "positive_missing_timing_rows": int((positive & day.isna()).sum()),
                    "positive_after_day60_rows": int((positive & day.gt(60)).sum()),
                    "positive_by_day60_rows": int((positive & day.between(0, 60)).sum()),
                    "positive_negative_timing_rows": int((positive & day.lt(0)).sum())})
        area = number("cropLarestAreaAcre")
        total, rate = number("total_N"), number("total_N_ha")
        units.append({"source_object": name, "rows": len(table),
            "area_conversion_agreement_rows": int(np.isclose(area, number("cropLargestArea") / number("acreConv"), rtol=.01, atol=.001).sum()),
            "N_rate_using_0_4_ha_per_acre_agreement_rows": int(np.isclose(total / (area * .4), rate, rtol=.001, atol=.001).sum()),
            "N_rate_using_exact_ha_per_acre_agreement_rows": int(np.isclose(total / (area * .40468564224), rate, rtol=.001, atol=.001).sum()),
            "status": "Arithmetic diagnostic only; raw product units, day reference and questionnaire still need confirmation"})
    pd.DataFrame(timing).to_csv(FIELD_DATA / "management_timing_audit.csv", index=False, lineterminator="\n")
    pd.DataFrame(units).to_csv(FIELD_DATA / "management_unit_audit.csv", index=False, lineterminator="\n")
    return pd.DataFrame(timing), pd.DataFrame(units)


def state_concordance(records):
    boundaries = json.loads((BOUNDARIES / "IND_ADM1.geojson").read_bytes())
    polygons = {}
    for feature in boundaries["features"]:
        geometry = shape(feature["geometry"])
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        prepare(geometry)
        polygons[canonical_label(feature["properties"]["shapeName"])] = geometry
    result = pd.Series(False, index=records.index)
    available = pd.Series(False, index=records.index)
    for state, group in records.groupby("state"):
        key = canonical_label(state)
        if key in polygons:
            available.loc[group.index] = True
            locations = points(group.longitude_weather_link_only.to_numpy(), group.latitude_weather_link_only.to_numpy())
            result.loc[group.index] = covers(polygons[key], locations)
    return result, available


def geographic_masks(development, fold):
    """Hold out districts and remove any fitting row sharing a source weather cell."""
    validation = development.geographic_fold.eq(fold)
    purged = pd.Series(False, index=development.index)
    for parameter in PARAMETERS:
        columns = [f"{parameter}_grid_lon", f"{parameter}_grid_lat"]
        cells = pd.MultiIndex.from_frame(development[columns])
        held_out_cells = pd.MultiIndex.from_frame(development.loc[validation, columns]).unique()
        purged |= pd.Series(cells.isin(held_out_cells), index=development.index)
    training = ~validation & ~purged
    return training, validation, ~validation & purged


def prepare_cohort():
    records = pd.read_csv(FIELD_DATA / "field_records_local.csv", parse_dates=["establishment_date", "forecast_date"])
    weather = pd.read_csv(FIELD_DATA / "weather_features_local.csv")
    links = pd.read_csv(FIELD_DATA / "weather_linkage_local.csv")
    if not records.record_id.is_unique or not weather.record_id.is_unique or not links.record_id.is_unique:
        raise ValueError("Record IDs must be unique for one-to-one linkage")
    records["inside_reported_state"], records["state_boundary_available"] = state_concordance(records)
    signature = ["year", "latitude_weather_link_only", "longitude_weather_link_only", "establishment_date",
                 "variety_label_source", "yield_kg_ha"]
    records["repeated_reduced_signature"] = records.duplicated(signature, keep=False)
    records["district_group"] = records.state.map(canonical_label) + ":" + records.district.map(canonical_label)
    records["coordinate_year_group"] = pd.util.hash_pandas_object(records[["year", "latitude_weather_link_only", "longitude_weather_link_only"]], index=False).astype(str)
    flags = records[["record_id", "year", "state", "inside_reported_state", "state_boundary_available",
                     "repeated_reduced_signature", "coordinate_year_group", "district_group"]].copy()
    linked = records.merge(weather.drop(columns=["year", "state"]), on="record_id", how="left", validate="one_to_one")
    linked = linked.merge(links.drop(columns="year"), on="record_id", how="left", validate="one_to_one")
    eligible_weather = linked.complete_weather.eq(True) & linked.physical_checks_pass.eq(True)
    base = linked.candidate_for_daily_weather_link & eligible_weather
    primary = base & linked.inside_reported_state & linked.state_boundary_available & ~linked.district_group.str.endswith(":unknown")
    flags["eligible_weather_before_geography"] = base
    flags["eligible_primary_cohort"] = primary
    flags.to_csv(FIELD_DATA / "geography_flags_local.csv", index=False, lineterminator="\n")
    cohort = linked.loc[primary].copy()
    cohort["temporal_role"] = cohort.year.map({2017: "development_fit", 2018: "development_validation", 2019: "locked_temporal_assessment"})
    cohort["establishment_day_of_year"] = cohort.establishment_date.dt.dayofyear
    for column in ("variety_label_source", "establishment_method", "soil_texture_label", "irrigation_availability_reported"):
        cohort[column + "_normalised"] = cohort[column].map(canonical_label)
    cohort.to_csv(FIELD_DATA / "cohort_local.csv", index=False, date_format="%Y-%m-%d", lineterminator="\n")
    # Split district labels without yield-based balancing; purge shared weather cells at fitting time.
    development = cohort.loc[cohort.year.lt(2019)].copy()
    groups = sorted(development.district_group.unique(), key=lambda s: hashlib.sha256(s.encode()).hexdigest())
    assignment = {group: i % 5 for i, group in enumerate(groups)}
    development["geographic_fold"] = development.district_group.map(assignment)
    development[["record_id", "year", "district_group", "coordinate_year_group", "geographic_fold"]].to_csv(
        FIELD_DATA / "development_splits_local.csv", index=False, lineterminator="\n")
    split_counts = []
    for fold in range(5):
        fitting, validation, purged = geographic_masks(development, fold)
        split_counts.append({"fold": fold, "fitting_records": int(fitting.sum()), "validation_records": int(validation.sum()),
            "purged_weather_overlap_records": int(purged.sum()), "held_out_districts": int(development.loc[validation, "district_group"].nunique())})
    pd.DataFrame(split_counts).to_csv(FIELD_DATA / "development_split_counts.csv", index=False, lineterminator="\n")
    coverage = cohort.groupby(["year", "state", "temporal_role"]).agg(records=("record_id", "size"),
        districts=("district_group", "nunique"), repeated_signature_rows=("repeated_reduced_signature", "sum")).reset_index()
    coverage.to_csv(FIELD_DATA / "cohort_coverage.csv", index=False, lineterminator="\n")
    geography = flags.groupby(["year", "state"]).agg(source_rows=("record_id", "size"),
        state_concordant_rows=("inside_reported_state", "sum"), primary_rows=("eligible_primary_cohort", "sum")).reset_index()
    geography.to_csv(FIELD_DATA / "geography_audit.csv", index=False, lineterminator="\n")
    summary = {"version": "field-cohort-v1", "prepared_on": "2026-10-13", "raw_records": len(records),
        "weather_eligible_records": int(base.sum()), "primary_records": len(cohort),
        "state_discordant_raw_records": int((~records.inside_reported_state).sum()),
        "state_discordant_weather_eligible_records": int((base & ~linked.inside_reported_state).sum()),
        "repeated_reduced_signature_rows": int(records.repeated_reduced_signature.sum()),
        "repeated_reduced_signature_extra_rows": int(records.duplicated(signature).sum()),
        "primary_repeated_signature_rows": int(cohort.repeated_reduced_signature.sum()),
        "primary_district_groups": int(cohort.district_group.nunique()),
        "primary_year_counts": {str(int(y)): int(n) for y, n in cohort.year.value_counts().sort_index().items()},
        "development_geographic_fold_counts": {str(int(f)): int(n) for f, n in development.geographic_fold.value_counts().sort_index().items()},
        "purged_geographic_splits": split_counts,
        "new_model_trained": False, "core_cohort_prepared": True, "management_rates_verified": False,
        "cohort_sha256": hashlib.sha256((FIELD_DATA / "cohort_local.csv").read_bytes()).hexdigest(),
        "splits_sha256": hashlib.sha256((FIELD_DATA / "development_splits_local.csv").read_bytes()).hexdigest(),
        "boundary_sha256": hashlib.sha256((BOUNDARIES / "IND_ADM1.geojson").read_bytes()).hexdigest(),
        "limitations": ["Boundary concordance is not field GPS verification; source boundaries are not historical district maps",
            "Repeated signatures retained; not sufficient proof of duplicate farms", "Cross-year farm identity not established",
            "Only three years and changing state coverage", "Fertiliser and irrigation event rates blocked until questionnaire verification",
            "Reported yield moisture convention unresolved"]}
    (FIELD_DATA / "cohort_audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def load_cohort_audit():
    path = FIELD_DATA / "cohort_audit.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
