"""Frozen Odisha study preparation; no training or reserved outcome access."""
import hashlib
import json
import math
import subprocess
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/rice/odisha_seasonal"
RAW = ROOT / "data/raw/rice/odisha_seasonal_weather"
GEO = ROOT / "data/processed/rice/seasonal_geography"
LABELS = ROOT / "data/processed/rice/seasonal_source/development_labels.csv"
DOCUMENT = ROOT / "docs/Rice_Odisha_Seasonal_Protocol.md"
AMENDMENT = ROOT / "docs/Rice_Odisha_Timing_Amendment.md"
ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/regional"
PARAMETERS = {"T2M_MAX": "C", "T2M_MIN": "C", "PRECTOTCORR": "mm/day",
              "RH2M": "%", "ALLSKY_SFC_SW_DWN": "MJ/m^2/day"}
RESOLUTION = {p: ((1., 1.) if p == "ALLSKY_SFC_SW_DWN" else (.625, .5)) for p in PARAMETERS}
BLOCKS = [(year, year) for year in range(1998, 2023)]  # Regional endpoint permits at most 366 days.
TILES = [(80.5, 17., 84.5, 20.5), (84.5, 17., 88., 20.5),
         (80.5, 20.5, 84.5, 23.5), (84.5, 20.5, 88., 23.5)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != payload:
        pending = path.with_suffix(path.suffix + ".pending")
        pending.write_text(payload, encoding="utf-8", newline="\n")
        for attempt in range(4):
            try:
                pending.replace(path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(.1 * (attempt + 1))


def freeze_protocol():
    """Reject changed design/input pins, including on acquisition-only reruns."""
    inputs = [DOCUMENT, AMENDMENT, LABELS, GEO / "district_crosswalk.csv", GEO / "reference_geometries.geojson"]
    declaration = {
        "version": 2, "declared_date": "2026-10-20", "state": "Odisha", "crop": "Rice", "season": "Kharif",
        "target_unit": "kg/ha", "issue_month_day": "08-31", "observation_start": "06-01",
        "observation_end": "08-24", "years": [1998, 2022], "history_lags": [2, 3, 4, 5, 6],
        "development_validation_years": list(range(2009, 2013)), "calibration_years": [2014, 2015, 2016],
        "timing_gap_target_years": [2013, 2017],
        "assessment_years_reserved": list(range(2018, 2023)), "rolling_training_end": "Y-2",
        "spatial_assumption": "fixed 2011 reference; annual equivalence not certified",
        "spatial_weighting": "whole-district spherical equal-area cell intersection; not crop-area weights",
        "daily_parameters_units": PARAMETERS, "weather_predictor_count": 19,
        "input_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in inputs},
    }
    path = OUT / "protocol.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != declaration:
        raise ValueError("Frozen Odisha protocol or pinned inputs changed; declare a new study version")
    write_json(path, declaration)
    return declaration


def districts():
    features = json.loads((GEO / "reference_geometries.geojson").read_text(encoding="utf-8"))["features"]
    crosswalk = pd.read_csv(GEO / "district_crosswalk.csv", dtype=str)
    crosswalk = crosswalk.loc[crosswalk.state_source.eq("Odisha")]
    lookup = {f["properties"]["district_code_census2011"]: f for f in features
              if f["properties"]["state_code_census2011"] == "21"}
    if len(crosswalk) != 30 or len(lookup) != 30:
        raise ValueError("Expected exactly 30 Odisha source rows and reference polygons")
    result = []
    for row in crosswalk.to_dict("records"):
        code = row["district_code_census2011_reference"]
        if code not in lookup:
            raise ValueError(f"Unmapped Odisha source district: {row['district_source']}")
        polygon = shape(lookup[code]["geometry"])
        if not polygon.is_valid or polygon.is_empty:
            raise ValueError("Invalid source polygon; no silent repair")
        result.append({"district_source": row["district_source"], "district_code_census2011": code,
                       "district_census2011": lookup[code]["properties"]["district_census2011"], "polygon": polygon})
    if len({r["district_code_census2011"] for r in result}) != 30:
        raise ValueError("Duplicate Census reference assignment")
    return sorted(result, key=lambda r: r["district_code_census2011"])


def request_plan():
    jobs = []
    for start, end in BLOCKS:
        for tile_id, (west, south, east, north) in enumerate(TILES):
            for parameter in PARAMETERS:
                args = {"parameters": parameter, "community": "AG", "latitude-min": south,
                        "latitude-max": north, "longitude-min": west, "longitude-max": east,
                        "start": f"{start}0601", "end": f"{end}0824", "format": "JSON", "time-standard": "LST"}
                jobs.append({"filename": f"{start}_{end}_{tile_id}_{parameter}.json", "parameter": parameter,
                             "start_year": start, "end_year": end, "tile": tile_id,
                             "url": ENDPOINT + "?" + urllib.parse.urlencode(args), "arguments": args})
    return jobs


def validate_response(payload, job):
    header = payload["header"]
    for key in ("start", "end"):
        if str(header[key]) != job["arguments"][key]:
            raise ValueError("NASA response dates do not match requested dates")
    p = job["parameter"]
    if header.get("time_standard") != "LST" or payload["parameters"][p]["units"] != PARAMETERS[p]:
        raise ValueError("Unexpected weather units or time standard")
    expected = set(pd.date_range(str(header["start"]), str(header["end"])).strftime("%Y%m%d"))
    features = payload.get("features", [])
    if not features:
        raise ValueError("Empty regional grid")
    coordinates = []
    for f in features:
        x, y = f["geometry"]["coordinates"][:2]
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Nonfinite grid coordinates")
        coordinates.append((x, y))
        if set(f["properties"]["parameter"][p]) != expected:
            raise ValueError("Incomplete daily date keys")
    if len(set(coordinates)) != len(coordinates):
        raise ValueError("Duplicate grid coordinates in one response")
    dx, dy = RESOLUTION[p]
    for axis, spacing in ((0, dx), (1, dy)):
        unique = sorted({c[axis] for c in coordinates})
        if len(unique) < 2 or not np.allclose(np.diff(unique), spacing, atol=1e-8):
            raise ValueError(f"Unexpected native grid spacing for {p}")
    return payload


def _fetch(job, previous):
    path = RAW / job["filename"]
    receipt = previous.get(job["filename"])
    if path.exists() and receipt is not None and digest(path) != receipt["sha256"]:
        raise ValueError(f"Cached weather changed: {path.name}")
    if not path.exists():
        # Windows system trust, normal certificate validation; no TLS bypass.
        escaped_url = job["url"].replace("'", "''")
        pending = path.with_suffix(".download")
        escaped_path = str(pending).replace("'", "''")
        command = f"$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri '{escaped_url}' -OutFile '{escaped_path}' -TimeoutSec 150"
        for attempt in range(3):
            try:
                process = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                         capture_output=True, text=True, timeout=180)
            except subprocess.TimeoutExpired:
                if pending.exists():
                    pending.unlink()
                if attempt == 2:
                    raise
                continue
            if process.returncode == 0:
                try:
                    validate_response(json.loads(pending.read_bytes()), job)
                    pending.replace(path)
                finally:
                    if pending.exists():
                        pending.unlink()
                break
            if pending.exists():
                pending.unlink()  # Exact incomplete response inside this module's cache only.
            if attempt == 2:
                raise RuntimeError(f"Weather download failed: {job['filename']}: {process.stderr[-500:]}")
            if "366" in process.stderr or "(422)" in process.stderr or "(400)" in process.stderr:
                raise RuntimeError(f"NASA rejected request arguments: {job['filename']}: {process.stderr[-500:]}")
            time.sleep(3 * (attempt + 1))
    if receipt is not None and digest(path) != receipt["sha256"]:
        raise ValueError(f"Downloaded response differs from pinned receipt: {path.name}; review source revisions explicitly")
    payload = validate_response(json.loads(path.read_bytes()), job)
    return {**{k: job[k] for k in ("filename", "parameter", "start_year", "end_year", "tile", "url")},
            "sha256": digest(path), "bytes": path.stat().st_size, "header": payload["header"],
            "units": payload["parameters"][job["parameter"]]["units"], "grid_points": len(payload["features"])}


def acquire_weather(workers=2):
    freeze_protocol()
    RAW.mkdir(parents=True, exist_ok=True)
    path = OUT / "weather_manifest.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"files": []}
    previous = {r["filename"]: r for r in previous["files"]}
    receipts, failures = dict(previous), []
    jobs = request_plan()
    if not set(receipts).issubset({job["filename"] for job in jobs}):
        raise ValueError("Weather receipt contains requests outside the frozen acquisition plan")
    completed = 0
    with ThreadPoolExecutor(max_workers=min(max(int(workers), 1), 2)) as pool:
        futures = {pool.submit(_fetch, job, previous): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                receipt = future.result()
                receipts[receipt["filename"]] = receipt
            except Exception as error:
                receipts.pop(job["filename"], None)
                failures.append({"filename": job["filename"], "error": str(error)})
            write_json(path, {"protocol_sha256": digest(OUT / "protocol.json"), "planned_requests": len(jobs),
                              "completed_requests": len(receipts), "failures": failures,
                              "files": [receipts[k] for k in sorted(receipts)]})
            completed += 1
            if completed % 5 == 0 or completed == len(jobs):
                print(f"Odisha weather: {completed}/{len(jobs)}, failures {len(failures)}", flush=True)
    if failures:
        raise RuntimeError("Some weather requests failed; successful receipts retained, rerun to resume")
    return {"completed_requests": len(receipts), "bytes": sum(r["bytes"] for r in receipts.values())}


def equal_area(geometry):
    """Spherical cylindrical equal-area projection; areas in square kilometres."""
    return transform(lambda x, y, z=None: (6371.0088 * np.deg2rad(x), 6371.0088 * np.sin(np.deg2rad(y))), geometry)


def grid_weights(coordinates, parameter, district_rows):
    dx, dy = RESOLUTION[parameter]
    cells = {c: box(c[0]-dx/2, c[1]-dy/2, c[0]+dx/2, c[1]+dy/2) for c in coordinates}
    weights, evidence = {}, []
    union = unary_union(list(cells.values()))
    for district in district_rows:
        polygon = district["polygon"]
        projected_polygon = equal_area(polygon)
        area = projected_polygon.area
        uncovered = equal_area(polygon.difference(union)).area / area
        if uncovered > 1e-8:
            raise ValueError(f"Weather grid does not cover {district['district_source']}: {uncovered}")
        w = {}
        for coordinate, cell in cells.items():
            intersection = projected_polygon.intersection(equal_area(cell))
            if intersection.is_empty:
                continue
            intersection_area = intersection.area
            if intersection_area <= 1e-10:
                continue
            w[coordinate] = intersection_area / area
        if not math.isclose(sum(w.values()), 1., rel_tol=1e-7, abs_tol=1e-7):
            raise ValueError("Overlapping or incomplete grid footprints")
        weights[district["district_code_census2011"]] = w
        for (longitude, latitude), weight in sorted(w.items()):
            evidence.append({k: v for k, v in district.items() if k != "polygon"} |
                            {"parameter": parameter, "longitude": longitude, "latitude": latitude,
                             "cell_width_degrees": dx, "cell_height_degrees": dy, "weight": weight,
                             "district_area_spherical_km2": area, "uncovered_fraction": uncovered})
    return weights, evidence


def _longest_dry(values):
    best = run = 0
    for value in values:
        run = run + 1 if value < 1 else 0
        best = max(best, run)
    return best


def prepare_weather():
    """Build predictors only; newer target values are never read."""
    freeze_protocol()
    manifest = json.loads((OUT / "weather_manifest.json").read_text(encoding="utf-8"))
    receipts = {r["filename"]: r for r in manifest["files"]}
    jobs = request_plan()
    if len(receipts) != len(jobs) or manifest["failures"]:
        raise ValueError("Complete weather acquisition required")
    district_rows = districts()
    daily_rows, weight_rows, grid_signatures, weight_cache = [], [], {}, {}
    for start, end in BLOCKS:
        # Keep only the declared per-year observation dates, before any aggregation.
        dates = [d for year in range(start, end+1) for d in pd.date_range(f"{year}-06-01", f"{year}-08-24")]
        keys = [d.strftime("%Y%m%d") for d in dates]
        output = {(d["district_code_census2011"], date): {} for d in district_rows for date in dates}
        for parameter in PARAMETERS:
            samples = {}
            for job in jobs:
                if job["start_year"] != start or job["parameter"] != parameter:
                    continue
                path = RAW / job["filename"]
                if digest(path) != receipts[path.name]["sha256"]:
                    raise ValueError(f"Weather cache checksum mismatch: {path.name}")
                payload = validate_response(json.loads(path.read_bytes()), job)
                fill = float(payload["header"]["fill_value"])
                for f in payload["features"]:
                    coordinate = tuple(f["geometry"]["coordinates"][:2])
                    series = f["properties"]["parameter"][parameter]
                    values = np.array([series[k] for k in keys], dtype=float)
                    values[values == fill] = np.nan
                    if coordinate in samples and not np.array_equal(samples[coordinate], values, equal_nan=True):
                        raise ValueError("Conflicting weather values in overlapping request tiles")
                    samples[coordinate] = values
            signature = sorted(samples)
            if parameter in grid_signatures and grid_signatures[parameter] != signature:
                raise ValueError("Weather grid changed between time blocks")
            if parameter not in grid_signatures:
                weights, evidence = grid_weights(signature, parameter, district_rows)
                weight_rows.extend(evidence)
                grid_signatures[parameter] = signature
                weight_cache[parameter] = weights
            weights = weight_cache[parameter]
            for district in district_rows:
                code = district["district_code_census2011"]
                result = np.zeros(len(keys))
                for coordinate, weight in weights[code].items():
                    values = samples[coordinate]
                    lower, upper = {"T2M_MAX": (-50, 65), "T2M_MIN": (-60, 55), "PRECTOTCORR": (0, 2000),
                                    "RH2M": (0, 100), "ALLSKY_SFC_SW_DWN": (0, 60)}[parameter]
                    if not np.isfinite(values).all() or (values < lower).any() or (values > upper).any():
                        raise ValueError(f"Missing or physically invalid contributing weather: {parameter}, {coordinate}")
                    result += weight * values
                for date, value in zip(dates, result):
                    output[(code, date)][parameter] = float(value)
        for (code, date), values in output.items():
            if values["T2M_MIN"] > values["T2M_MAX"]:
                raise ValueError("Daily Tmin exceeds Tmax")
            daily_rows.append({"district_code_census2011": code, "date": date.strftime("%Y-%m-%d"), **values})
        print(f"Prepared Odisha daily weather: {start}–{end}", flush=True)
    daily = pd.DataFrame(daily_rows).sort_values(["district_code_census2011", "date"])
    daily["year"] = pd.to_datetime(daily.date).dt.year
    daily["month"] = pd.to_datetime(daily.date).dt.month
    feature_rows = []
    for (code, year), group in daily.groupby(["district_code_census2011", "year"]):
        if len(group) != 85:
            raise ValueError("Expected 85 pre-cutoff days per district-year")
        row = {"district_code_census2011": code, "agricultural_start_year": int(year),
               "weather_start": f"{year}-06-01", "weather_end": f"{year}-08-24", "issue_date": f"{year}-08-31"}
        for month, month_group in group.groupby("month"):
            for parameter in PARAMETERS:
                name = f"{parameter}_{month:02d}"
                row[name] = float(month_group[parameter].sum() if parameter == "PRECTOTCORR" else month_group[parameter].mean())
        rain = group.PRECTOTCORR.to_numpy()
        row.update(longest_dry_spell_days=_longest_dry(rain), wet_days=int((rain >= 1).sum()),
                   max_five_day_rain_mm=float(pd.Series(rain).rolling(5).sum().max()),
                   tmax_p95_c=float(np.quantile(group.T2M_MAX, .95)))
        feature_rows.append(row)
    features = pd.DataFrame(feature_rows)
    labels = pd.read_csv(LABELS)
    labels = labels.loc[labels.state_source.eq("Odisha") & labels.agricultural_start_year.between(1998, 2017)]
    if len(labels) != 600 or not labels.positive_complete_triplet.all():
        raise ValueError("Unexpected Odisha development labels; revisit source audit")
    metadata = pd.DataFrame([{k: v for k, v in d.items() if k != "polygon"} for d in district_rows])
    table = features.merge(metadata, on="district_code_census2011", validate="many_to_one")
    table = table.merge(labels[["district_source", "agricultural_start_year", "yield_kg_ha"]],
                        on=["district_source", "agricultural_start_year"], how="left", validate="one_to_one")
    lookup = table.set_index(["district_code_census2011", "agricultural_start_year"]).yield_kg_ha.to_dict()
    for lag in range(2, 7):
        table[f"yield_lag{lag}"] = [lookup.get((code, year-lag), np.nan)
                                   for code, year in zip(table.district_code_census2011, table.agricultural_start_year)]
    history = table[[f"yield_lag{i}" for i in range(2, 7)]]
    table["history_reference_yield_kg_ha"] = history.mean(axis=1, skipna=False)
    table["history_trend_kg_ha_per_year"] = history.mul([2, 1, 0, -1, -2]).sum(axis=1, skipna=False) / 10
    table["target_access"] = np.where(table.agricultural_start_year <= 2017, "development", "reserved; not read")
    table["history_complete_from_open_labels"] = history.notna().all(axis=1)
    protocol = freeze_protocol()
    roles = {year: "selection validation" for year in protocol["development_validation_years"]}
    roles.update({year: "interval calibration" for year in protocol["calibration_years"]})
    roles.update({year: "timing gap; may enter later fitting" for year in protocol["timing_gap_target_years"]})
    roles.update({year: "reserved sequential assessment" for year in protocol["assessment_years_reserved"]})
    table["evaluation_role"] = [roles.get(year, "history only" if year < 2004 else "initial fitting pool")
                                for year in table.agricultural_start_year]
    table["geography_assumption"] = "fixed 2011 reference; not annual boundary certification"
    if table.loc[table.agricultural_start_year >= 2018, "yield_kg_ha"].notna().any():
        raise ValueError("Reserved target leak")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, frame in (("daily_weather.csv", daily.drop(columns=["year", "month"])),
                        ("grid_weights.csv", pd.DataFrame(weight_rows)), ("prepared_inputs.csv", table)):
        frame.to_csv(OUT / name, index=False, lineterminator="\n")
    summary = {"state": "Odisha", "districts": 30, "weather_years": [1998, 2022],
               "daily_records": len(daily), "days_per_district_year": 85, "weather_district_years": len(table),
               "development_labels": len(labels), "development_model_rows_with_history": int((table.target_access.eq("development") & table.history_complete_from_open_labels).sum()),
               "weather_predictors": 19, "reserved_target_values_read": 0, "new_model_fitted": False,
               "selection_validation_years": protocol["development_validation_years"],
               "calibration_years": protocol["calibration_years"], "reserved_assessment_years": protocol["assessment_years_reserved"],
               "grid_cells_by_parameter": {p: len(c) for p, c in grid_signatures.items()},
               "spatial_assumption": "fixed 2011 polygons; annual boundary equivalence unverified",
               "weighting": "whole-district area, not rice-area weights", "issue_date": "31 August",
               "weather_window": "1 June–24 August", "next_step": "frozen development comparison; keep 2018–2022 outcomes reserved"}
    write_json(OUT / "summary.json", summary)
    files = [OUT / name for name in ("protocol_v1.json", "protocol.json", "weather_manifest.json", "daily_weather.csv", "grid_weights.csv", "prepared_inputs.csv", "summary.json")]
    write_json(OUT / "verification.json", {"protocol_document_sha256": digest(DOCUMENT),
               "output_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in files},
               "checks": ["30 unique district identities", "native coordinate spacing checked per parameter and time block",
                          "all selected dates complete; no missing-cell renormalization", "polygon coverage and weight sums checked",
                          "physical ranges and Tmin/Tmax consistency checked", "reserved targets absent from prepared inputs"]})
    return summary
