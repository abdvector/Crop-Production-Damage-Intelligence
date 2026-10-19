"""Audit and prepare LCAS field observations without exposing source identifiers."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "rice"

FIELD_DATA = DATA / "india_field_survey"
SOURCE_OBJECTS = {"rice_2017": 2017, "data": 2018, "data1": 2019}


def _column(table, names):
    for name in names:
        if name in table:
            return table[name].reset_index(drop=True)
    return pd.Series(pd.NA, index=range(len(table)))


def _dates(values):
    text = values.astype("string").str.strip()
    iso = text.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    parsed.loc[iso] = pd.to_datetime(text.loc[iso], format="ISO8601", errors="coerce")
    parsed.loc[~iso] = pd.to_datetime(text.loc[~iso], format="mixed", dayfirst=True, errors="coerce")
    return parsed


def normalise_field_records(objects, cutoff_days=60):
    """Source rows stay distinct; quality flags do not silently remove observations."""
    output, inventory = [], []
    for name, year in SOURCE_OBJECTS.items():
        table = objects[name].reset_index(drop=True)
        frame = pd.DataFrame({"source_object": name, "source_row": np.arange(1, len(table) + 1), "year": year})
        frame["record_id"] = name + ":" + frame.source_row.astype(str)
        frame["crop"] = _column(table, ["crop"]).fillna("Rice" if name == "rice_2017" else "Unknown")
        frame["state"] = _column(table, ["state"]).astype("string").str.strip().replace(
            {"jharkhand": "Jharkhand", "Chattisgarh": "Chhattisgarh", "WestBengal": "West Bengal", "UttarPradesh": "Uttar Pradesh"})
        frame["district"] = _column(table, ["district"]).astype("string").str.strip()
        frame["season"] = _column(table, ["season"]).fillna("Unknown")
        frame["variety_label_source"] = _column(table, ["varName", "VarName"]).astype("string")
        frame["establishment_method"] = _column(table, ["CropEst", "cropEst"]).astype("string")
        frame["soil_texture_label"] = _column(table, ["soilTexture"]).astype("string")
        frame["establishment_date"] = _dates(_column(table, ["seedingSowingTransDate", "seedingSowingTransDate1"]))
        frame["harvest_date_audit_only"] = _dates(_column(table, ["harvestDate1", "harvestDate"]))
        frame["forecast_date"] = frame.establishment_date + pd.Timedelta(days=cutoff_days)
        frame["yield_kg_ha"] = pd.to_numeric(_column(table, ["L.tonPerHectare", "K.tonPerHectare"]), errors="coerce") * 1000
        frame["latitude_weather_link_only"] = pd.to_numeric(_column(table, ["O.largestPlotGPS.Latitude", "largestPlotGPS.Latitude"]), errors="coerce")
        frame["longitude_weather_link_only"] = pd.to_numeric(_column(table, ["O.largestPlotGPS.Longitude", "largestPlotGPS.Longitude"]), errors="coerce")
        frame["irrigation_availability_reported"] = _column(table, ["irrigAvail"])
        for cause in ["drought", "flood", "weed", "insect", "disease"]:
            frame[f"{cause}_severity_retrospective"] = _column(table, [cause + "Severity"]).astype("string").replace("", pd.NA)
        identity = _column(table, ["meta.instanceID"])
        frame["duplicate_source_identifier"] = identity.duplicated(keep=False) & identity.notna()
        frame["valid_rice_yield"] = frame.crop.astype("string").str.lower().eq("rice") & np.isfinite(frame.yield_kg_ha) & frame.yield_kg_ha.gt(0)
        frame["plausible_india_coordinates"] = frame.latitude_weather_link_only.between(6, 38) & frame.longitude_weather_link_only.between(68, 98)
        frame["valid_forecast_dates"] = (frame.establishment_date.dt.year.eq(year) & frame.harvest_date_audit_only.gt(frame.forecast_date)
                                        & (frame.harvest_date_audit_only - frame.establishment_date).dt.days.le(365))
        frame["duplicate_coordinate_season"] = frame.duplicated(["latitude_weather_link_only", "longitude_weather_link_only", "year"], keep=False)
        frame["yield_above_15000_review_flag"] = frame.yield_kg_ha.gt(15000)
        frame["candidate_for_daily_weather_link"] = frame.valid_rice_yield & frame.plausible_india_coordinates & frame.valid_forecast_dates & ~frame.duplicate_source_identifier
        inventory.append({"source_object": name, "source_year": year, "rows": len(table), "columns": len(table.columns),
                          "duplicate_source_identifiers": int(frame.duplicate_source_identifier.sum()),
                          "reported_variety_count": int(frame.variety_label_source.nunique())})
        output.append(frame)
    return pd.concat(output, ignore_index=True), inventory


def field_predictor_policy():
    return pd.DataFrame([
        ["yield_kg_ha", "Target only", "Published t/ha multiplied by 1000; moisture basis unresolved"],
        ["state, district, year", "Grouping and context", "Use grouped/time validation; do not claim independent farm panels"],
        ["establishment_date, method, variety label", "Candidate early inputs", "Dates are field sowing/transplanting; variety names are not verified molecular IDs"],
        ["soil_texture_label", "Candidate early input", "Survey category; not measured pH, nutrients or aluminium"],
        ["irrigation_availability_reported", "Conditional", "Confirm it reflects conditions known by issue date"],
        ["GPS coordinates", "Local linkage only", "Needed for weather; not published in aggregate audit"],
        ["basal fertiliser amounts", "2018 matched development experiment prepared", "Five product masses prepared with area/completeness checks; other-year definitions and nutrient composition remain unverified"],
        ["top-dressing amounts and appDays", "Conditional event inputs", "2018 form references field sowing/transplanting; include only verified dated applications by cutoff; missing timing stays unknown"],
        ["Tmax_avg, Tmin_avg, Rain_avg, rad_avg", "Blocked for early forecasts", "Published sowing-to-harvest weather; acquire daily data and truncate"],
        ["total_N_ha, total_p_ha, total_K_ha, irrigTimes", "Blocked as current early inputs", "Whole-season totals have unverified availability at the cutoff"],
        ["harvest date, crop duration, grain quantities", "Audit/target only", "Outcome-period information; never forecast predictors"],
        ["stress severity and lodging reports", "Possible separate outcomes", "Retrospective ordinal reports, not timed damage percentages or early predictors"],
        ["names, phones, government IDs, device IDs", "Excluded", "No modelling role; original source remains local"],
        ["protein embeddings and aluminium", "Unavailable in this survey", "No verified variety-specific alleles or measured field aluminium"],
    ], columns=["variable_or_block", "forecast_status", "reason"])


def save_field_audit(records, inventory, archive_path, cutoff_days=60):
    FIELD_DATA.mkdir(parents=True, exist_ok=True)
    curated = FIELD_DATA / "field_records_local.csv"
    records.to_csv(curated, index=False, date_format="%Y-%m-%d")
    profile_records = records.assign(valid_reported_yield=records.yield_kg_ha.where(records.valid_rice_yield))
    profile = profile_records.groupby(["year", "state"], dropna=False).agg(
        source_rows=("record_id", "size"), valid_yield_rows=("valid_rice_yield", "sum"),
        candidate_weather_rows=("candidate_for_daily_weather_link", "sum"),
        distinct_districts=("district", "nunique"), mean_reported_yield_kg_ha=("valid_reported_yield", "mean")).reset_index()
    profile.to_csv(FIELD_DATA / "year_state_coverage.csv", index=False)
    field_predictor_policy().to_csv(FIELD_DATA / "predictor_availability.csv", index=False)
    summary = {"audit_version": "lcas-source-audit-v1", "audited_on": "2026-10-13",
               "source_doi": "10.1038/s41467-024-52448-6", "archive_sha256": hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
               "curated_local_sha256": hashlib.sha256(curated.read_bytes()).hexdigest(), "objects": inventory,
               "raw_rows": len(records), "valid_rice_yield_rows": int(records.valid_rice_yield.sum()),
               "unique_district_labels": int(records[["state", "district"]].drop_duplicates().shape[0]),
               "candidate_weather_rows": int(records.candidate_for_daily_weather_link.sum()),
               "candidate_unique_coordinates": int(records.loc[records.candidate_for_daily_weather_link, ["latitude_weather_link_only", "longitude_weather_link_only"]].drop_duplicates().shape[0]),
               "missing_establishment_dates": int(records.establishment_date.isna().sum()),
               "missing_harvest_dates": int(records.harvest_date_audit_only.isna().sum()),
               "invalid_forecast_dates": int((~records.valid_forecast_dates).sum()),
               "invalid_coordinates": int((~records.plausible_india_coordinates).sum()),
               "duplicate_source_identifier_rows": int(records.duplicate_source_identifier.sum()),
               "duplicate_coordinate_season_rows": int(records.duplicate_coordinate_season.sum()),
               "yield_above_15000_review_rows": int(records.yield_above_15000_review_flag.sum()),
               "forecast_cutoff_days_after_field_establishment": cutoff_days,
               "severity_report_counts": {cause: int(records[f"{cause}_severity_retrospective"].notna().sum()) for cause in ["drought", "flood", "weed", "insect", "disease"]},
               "daily_weather_acquired": False, "new_model_trained": False,
               "forecast_ready": False, "privacy": "Raw identifiers and local field coordinates excluded from GitHub",
               "limitations": ["Source raw counts differ from paper analysis sample; published filters not reproduced",
                               "Full-season weather and management totals blocked at the issue date",
                               "Event amounts/units and missing application timing require validation",
                               "Yield moisture convention and crop-cut validation subset need confirmation",
                               "Ordinal stress reports are retrospective and absent in 2019",
                               "No soil pH/Al measurements or verified protein links"]}
    (FIELD_DATA / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def load_field_audit():
    path = FIELD_DATA / "audit_summary.json"
    if not path.exists():
        return None
    summary = json.loads(path.read_text(encoding="utf-8"))
    return summary, pd.read_csv(FIELD_DATA / "year_state_coverage.csv"), pd.read_csv(FIELD_DATA / "predictor_availability.csv")
