"""Aggregate local predictor linkage audit; no training, downloads or row exports."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.rice_baseline import ROOT, DATA, prepare_data
from src.rice_regional import CLIMATE, HISTORY, WEATHER, check_weather, rice_source

OUT = DATA / "predictor_audit"
REGIONAL = DATA / "regional_forecast"
FIELD = DATA / "india_field_survey"


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _coverage(dataset, frame, block, columns, availability, qualification):
    present = [c for c in columns if c in frame]
    complete = frame[present].notna().all(axis=1) if len(present) == len(columns) else pd.Series(False, index=frame.index)
    return {"dataset": dataset, "predictor_block": block, "requested_columns": len(columns),
            "present_columns": len(present), "records": len(frame), "complete_records": int(complete.sum()),
            "coverage_percent": round(100 * complete.mean(), 2), "availability": availability,
            "qualification": qualification, "columns": ";".join(columns)}


def run_audit():
    """Recompute aggregate checks from existing local caches; preserve model outputs."""
    protected = [ROOT / "models/rice_regional.joblib"]
    protected += [p for folder in [REGIONAL, FIELD / "model", FIELD / "management_2018",
                                  DATA / "protein_experiment/day_60"]
                  for p in folder.glob("*") if p.is_file()]
    before = {p.relative_to(ROOT).as_posix(): _hash(p) for p in protected}
    source_receipts = _json(REGIONAL / "source_manifest.json")["files"]
    for receipt in source_receipts:
        path = ROOT / "data/raw/rice/icrisat_district" / receipt["filename"]
        if _hash(path) != receipt["sha256"]:
            raise ValueError(f"Administrative cache checksum changed: {receipt['filename']}")
    weather_receipts = _json(REGIONAL / "weather_manifest.json")["files"]
    for receipt in weather_receipts:
        if _hash(WEATHER / f"{receipt['district_id']}.json") != receipt["sha256"]:
            raise ValueError(f"Weather cache checksum changed: {receipt['district_id']}")
    source = rice_source()
    regional = pd.read_csv(REGIONAL / "district_years.csv")
    field = pd.read_csv(FIELD / "cohort_local.csv", low_memory=False)
    management = pd.read_csv(FIELD / "management_2018/features_local.csv")
    field_protocol = _json(FIELD / "field_model_protocol.json")
    products = _json(FIELD / "management_2018/feature_audit.json")["product_features"]
    trials, windows = prepare_data(60)
    coding = pd.read_csv(DATA / "molecular_linkage_audit/measured_variant_dosages.csv")
    for name, frame, key in [("district", regional, ["district_id", "year"]),
                             ("field", field, ["record_id"]), ("management", management, ["record_id"]),
                             ("trial", trials, ["genotype_id", "environment_id"])]:
        if frame.duplicated(key).any():
            raise ValueError(f"Duplicate {name} modelling keys")
    lookup = source.set_index(["district_id", "year"])
    target = lookup.yield_kg_ha.reindex(pd.MultiIndex.from_arrays([regional.district_id, regional.year]))
    if not np.allclose(target, regional.yield_kg_ha):
        raise ValueError("Regional labels no longer match the original administrative source")
    for lag in range(2, 7):
        keys = pd.MultiIndex.from_arrays([regional.district_id, regional.year - lag])
        expected = lookup.yield_kg_ha.reindex(keys).to_numpy()
        if not np.allclose(expected, regional[f"yield_lag{lag}"]):
            raise ValueError(f"Incorrect district-year lag {lag}")
    if not np.allclose(regional[HISTORY[:5]].mean(axis=1), regional.reference_yield):
        raise ValueError("Reference yields disagree with the five available lags")
    for district, group in regional.groupby("district_id"):
        weather = check_weather(_json(WEATHER / f"{int(district)}.json"))
        values = weather["properties"]["parameter"]
        for column in CLIMATE:
            parameter, month = column.rsplit("_", 1)
            expected = [values[parameter][f"{int(year)}{month}"] for year in group.year]
            if not np.allclose(expected, group[column]):
                raise ValueError(f"Regional weather mismatch: {district}/{column}")
    dates = field[["establishment_date", "forecast_date", "last_weather_date", "harvest_date_audit_only"]].apply(pd.to_datetime)
    if not (dates.forecast_date.lt(dates.harvest_date_audit_only).all()
            and dates.last_weather_date.eq(dates.forecast_date).all()
            and (dates.forecast_date - dates.establishment_date).dt.days.eq(60).all()
            and field.expected_days.eq(61).all()):
        raise ValueError("Field date-window checks changed")
    joined = field.merge(management, on="record_id", validate="one_to_one", how="inner")
    matched = joined.loc[joined.area_arithmetic_pass & joined.complete_management].copy()
    if not matched.year.eq(2018).all() or not np.isfinite(matched[products]).all().all():
        raise ValueError("Invalid matched 2018 product block")
    molecular = trials.merge(coding, on="genotype_id", validate="many_to_one", how="left")
    snps = [c for c in trials if c.startswith("snp_")]
    coded = list(coding.columns.drop("genotype_id"))
    core = field_protocol["numeric_features"] + field_protocol["categorical_features"]
    blocks = [
        _coverage("Regional annual", regional, "Yield history", HISTORY, "Assumed historical reporting lag",
                  "Y-2..Y-6 matched to exact source district/year; release vintages unverified."),
        _coverage("Regional annual", regional, "June-August point weather", CLIMATE, "Retrospective date-truncated archive",
                  "Representative source points; monthly release dates unverified; not a crop-area mean."),
        _coverage("Regional annual", regional, "Soil chemistry", ["soil_ph", "soil_organic_carbon", "soil_clay_percent"], "Not linked",
                  "No compatible district/year measurements in the current modelling table."),
        _coverage("Regional annual", regional, "Irrigation and fertilizer", ["rice_irrigated_share", "nitrogen_kg_ha"], "Not linked",
                  "Farm survey values cannot populate historical district-year rows."),
        _coverage("Regional annual", regional, "Canopy and soil water", ["lai_preissue", "soil_moisture_preissue"], "Not linked",
                  "Additional sources require dated crop-area aggregation and geography matching."),
        _coverage("Regional annual", regional, "Molecular and aluminium", ["cultivar_adoption", "verified_allele", "measured_aluminium"], "Not linked",
                  "No cultivar/adoption link or measured district aluminium exposure."),
        _coverage("Indian field", field, "Declared weather and planting context", core, "Retrospective day-60 reconstruction",
                  "Weather extends to issue day; publication vintages not established."),
        _coverage("Indian field", field, "Reported soil texture and irrigation access",
                  ["soil_texture_label_normalised", "irrigation_availability_reported_normalised"], "Conditional early context",
                  "Nonmissing categories do not establish laboratory soil values or dated irrigation quantities."),
        _coverage("Indian field", field, "Laboratory soil and aluminium", ["soil_ph", "exchangeable_aluminium", "soil_nitrogen"], "Not linked",
                  "No field-specific laboratory measurements in the current cohort."),
        _coverage("Indian field", field, "Cultivar proteins", ["verified_cultivar_protein"], "Not linked",
                  "Reported variety text is not a verified molecular accession."),
        _coverage("Matched 2018 field", matched, "Timed fertilizer product masses", products, "Dated retrospective reconstruction",
                  "2018 form only; product kg/ha, not nutrient kg/ha; area/completeness-selected population."),
        _coverage("Rice trial", trials, "Measured genetic markers", snps, "Genotype linked",
                  "107 genotypes repeated across 15 environments; not independent weather samples."),
        _coverage("Rice trial", molecular, "Protein-altering SNP dosages", coded, "Genotype linked reference annotations",
                  "Deterministic representation of measured SNPs; six structure sites tested without a reliable yield benefit."),
        _coverage("Rice trial", trials, "Soil and timed management", ["soil_ph", "measured_aluminium", "nitrogen_kg_ha", "irrigation_mm"], "Not linked",
                  "Other studies cannot supply measurements for these trial environments."),
    ]
    field_2018 = field.loc[field.year.eq(2018)]
    summary = {
        "audited_on": "2026-10-20", "scope": "Existing local predictor-target linkage; no fitting, acquisition or label repair.",
        "regional": {"records": len(regional), "districts": regional.district_id.nunique(),
                     "years": [int(regional.year.min()), int(regional.year.max())],
                     "year_count": regional.year.nunique(), "complete_history_weather_records": int(regional[HISTORY+CLIMATE].notna().all(axis=1).sum()),
                     "missing_district_years_inside_observed_span": int(regional.district_id.nunique() * regional.year.nunique() - len(regional)),
                     "target": "Annual agricultural-year rice kg/ha, all seasons; historical 1966 district units.",
                     "supported_use": "Historical annual-yield replay; conditional reporting-delay assumptions.",
                     "live_or_season_specific_ready": False,
                     "flagged_coordinate_count": len(_json(REGIONAL / "coordinate_screen.json")["flagged"])},
        "field": {"records": len(field), "records_by_year": {str(k): int(v) for k,v in field.groupby("year").size().items()},
                  "district_label_groups": field.district_group.nunique(), "same_day_weather_records": int(dates.forecast_date.eq(dates.last_weather_date).sum()),
                  "yield_review_flags_by_year": {str(k): int(v) for k,v in field.groupby("year").yield_above_15000_review_flag.sum().items()},
                  "matched_2018_management_records": len(matched), "matched_2018_districts": matched.district_group.nunique(),
                  "management_retention_percent_of_eligible_2018": round(100 * len(matched) / len(field_2018), 2),
                  "excluded_eligible_2018_for_area_or_management": len(field_2018)-len(matched),
                  "independent_verified_management_years": 1,
                  "label_status": "Year-specific unit/scope conflicts unresolved; 2019 assessment already opened."},
        "trial": {"records": len(trials), "genotypes": trials.genotype_id.nunique(),
                  "environments": trials.environment_id.nunique(), "locations": trials.location_group.nunique(),
                  "protein_coding_dosage_complete_records": int(molecular[coded].notna().all(axis=1).sum()),
                  "soil_aluminium_management_complete_records": 0},
        "decision": "Keep the annual district prototype as the main existing deliverable. For a stronger pre-harvest study, acquire season-specific official rice yields and stable district geography before additional model training. Preserve field and molecular results as separate supporting studies.",
        "first_data_priority": "Official district x agricultural year x crop x season rice labels, definitions/units, stable geography/crosswalk and release information; preserve post-2017 outcomes unopened until a new protocol is fixed.",
        "timing_gap": "Weather-date truncation is verified; actual publication availability and historical reanalysis vintages are not. Current NASA guidance reports typical 2-3 day meteorology and 5-7 day solar latency. A future daily-data protocol should leave at least seven days as a planning buffer and verify actual availability; this does not certify monthly products or historical vintages.",
        "new_training_performed": False, "private_record_exported": False,
    }
    files = [REGIONAL / "district_years.csv", FIELD / "cohort_local.csv", FIELD / "management_2018/features_local.csv",
             FIELD / "field_model_protocol.json", FIELD / "management_2018/feature_audit.json",
             FIELD / "yield_label_trace.json", FIELD / "documentation_audit.json",
             DATA / "trial_metadata.csv", DATA / "yield_observations_audited.csv", DATA / "daily_weather.csv",
             DATA / "genotype_marker_calls.csv", DATA / "molecular_linkage_audit/measured_variant_dosages.csv",
             ROOT / "data/raw/rice/icrisat_district/area_production_yield.json"]
    checks = {"district_key_uniqueness": True, "regional_targets_match_source": True,
              "administrative_cache_files_matching_download_receipts": len(source_receipts),
              "weather_cache_files_matching_download_receipts": len(weather_receipts),
              "all_five_lags_match_district_and_year": True, "reference_mean_recomputed": True,
              "all_twelve_weather_columns_match_raw_caches": True, "field_and_management_keys_unique": True,
              "field_day60_windows_precede_harvest": True, "matched_management_is_2018_and_finite": True,
              "protected_file_count": len(before),
              "source_sha256": {p.relative_to(ROOT).as_posix(): _hash(p) for p in files},
              "protected_sha256": before}
    if any(_hash(ROOT / path) != value for path, value in before.items()):
        raise RuntimeError("Existing research/model output changed during read-only audit")
    checks["all_existing_model_and_result_bytes_preserved"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(blocks).to_csv(OUT / "coverage.csv", index=False, lineterminator="\n")
    for name, result in [("summary.json", summary), ("checks.json", checks)]:
        (OUT / name).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary
