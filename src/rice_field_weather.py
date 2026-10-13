"""Cached NASA POWER regional downloads and cutoff-safe field weather features."""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from src.rice_field_data import FIELD_DATA

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/raw/rice/nayak_2024_lcas_weather"
ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/regional"
PARAMETERS = {"T2M_MAX": "C", "T2M_MIN": "C", "PRECTOTCORR": "mm/day",
              "ALLSKY_SFC_SW_DWN": "MJ/m^2/day", "RH2M": "%"}


def load_fields():
    records = pd.read_csv(FIELD_DATA / "field_records_local.csv",
                          parse_dates=["establishment_date", "forecast_date"])
    return records.loc[records.candidate_for_daily_weather_link].copy()


def request_plan(records):
    """Four-degree core tiles plus a half-degree border for nearest grid linkage."""
    records = records.copy()
    records["lat_tile"] = np.floor(records.latitude_weather_link_only / 4).astype(int) * 4
    records["lon_tile"] = np.floor(records.longitude_weather_link_only / 4).astype(int) * 4
    jobs = []
    for (year, lat, lon), group in records.groupby(["year", "lat_tile", "lon_tile"]):
        for parameter in PARAMETERS:
            arguments = {"parameters": parameter, "community": "AG", "latitude-min": int(lat) - .5,
                         "latitude-max": int(lat) + 4.5, "longitude-min": int(lon) - .5,
                         "longitude-max": int(lon) + 4.5, "start": group.establishment_date.min().strftime("%Y%m%d"),
                         "end": group.forecast_date.max().strftime("%Y%m%d"), "format": "JSON", "time-standard": "LST"}
            jobs.append({"year": int(year), "lat_tile": int(lat), "lon_tile": int(lon), "parameter": parameter,
                         "arguments": arguments, "filename": f"{year}_{lat}_{lon}_{parameter}.json"})
    return records, jobs


def validate_response(payload, job):
    header = payload["header"]
    if header["start"] != job["arguments"]["start"] or header["end"] != job["arguments"]["end"]:
        raise ValueError("Response dates do not match request")
    if header.get("time_standard") != "LST":
        raise ValueError("Unexpected daily time standard")
    parameter = job["parameter"]
    if payload["parameters"][parameter]["units"] != PARAMETERS[parameter]:
        raise ValueError(f"Unexpected unit for {parameter}: {payload['parameters'][parameter]['units']}")
    if not payload.get("features"):
        raise ValueError("No weather grid features returned")
    dates = set(pd.date_range(header["start"], header["end"]).strftime("%Y%m%d"))
    for feature in payload["features"]:
        if set(feature["properties"]["parameter"][parameter]) != dates:
            raise ValueError("Incomplete daily date keys")
    return payload


def fetch_job(job):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / job["filename"]
    url = ENDPOINT + "?" + urllib.parse.urlencode(job["arguments"])
    if path.exists():
        validate_response(json.loads(path.read_bytes()), job)
    else:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=50) as response:
                    raw = response.read()
                validate_response(json.loads(raw), job)
                path.write_bytes(raw)
                break
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt == 2:
                    raise RuntimeError(f"{job['filename']}: {error}") from error
                time.sleep(3 * (attempt + 1))
    return {**{key: job[key] for key in ("year", "lat_tile", "lon_tile", "parameter", "filename")},
            "url": url, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def download_weather(workers=2):
    """Resumable, bounded acquisition; errors leave successful cache entries intact."""
    _, jobs = request_plan(load_fields())
    manifest, failures = [], []
    with ThreadPoolExecutor(max_workers=min(max(workers, 1), 2)) as pool:
        futures = {pool.submit(fetch_job, job): job for job in jobs}
        for future in as_completed(futures):
            try:
                manifest.append(future.result())
            except Exception as error:
                failures.append({"filename": futures[future]["filename"], "error": str(error)})
            completed = len(manifest) + len(failures)
            if completed % 10 == 0 or completed == len(jobs):
                print(f"Weather requests: {completed}/{len(jobs)}; failures: {len(failures)}", flush=True)
    report = {"endpoint": ENDPOINT, "time_standard": "LST", "parameters_expected_units": PARAMETERS,
              "planned_requests": len(jobs), "successful_requests": len(manifest), "failures": failures,
              "files": sorted(manifest, key=lambda entry: entry["filename"])}
    (FIELD_DATA / "weather_source_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if failures:
        raise RuntimeError(f"{len(failures)} weather requests failed; inspect manifest and resume")
    return report


def _series(feature, payload, parameter):
    values = pd.Series(feature["properties"]["parameter"][parameter], dtype=float)
    values.index = pd.to_datetime(values.index, format="%Y%m%d")
    return values.replace(payload["header"]["fill_value"], np.nan).sort_index()


def build_weather_features():
    """Never replace missing weather with simulator values or partial-window totals."""
    records, jobs = request_plan(load_fields())
    catalogue = {(j["year"], j["lat_tile"], j["lon_tile"], j["parameter"]): j for j in jobs}
    output, links = [], []
    for (year, lat, lon), group in records.groupby(["year", "lat_tile", "lon_tile"]):
        matrices, grids = {}, {}
        for parameter in PARAMETERS:
            job = catalogue[(year, lat, lon, parameter)]
            payload = validate_response(json.loads((CACHE / job["filename"]).read_bytes()), job)
            grids[parameter] = np.array([f["geometry"]["coordinates"][:2] for f in payload["features"]])
            matrices[parameter] = [_series(f, payload, parameter) for f in payload["features"]]
        for row in group.itertuples():
            dates = pd.date_range(row.establishment_date, row.forecast_date)
            if len(dates) != 61:
                raise ValueError("Expected inclusive day 0 through day 60")
            frame = pd.DataFrame(index=dates)
            link = {"record_id": row.record_id, "year": int(year)}
            for parameter, grid in grids.items():
                # Local tangent-plane distance approximation; parameter grids remain separate.
                delta = grid - [row.longitude_weather_link_only, row.latitude_weather_link_only]
                delta[:, 0] *= np.cos(np.deg2rad(row.latitude_weather_link_only))
                nearest = int(np.argmin((delta ** 2).sum(axis=1)))
                distance = float(np.sqrt((delta[nearest] ** 2).sum()) * 111.2)
                link[f"{parameter}_grid_lon"], link[f"{parameter}_grid_lat"] = grid[nearest].tolist()
                link[f"{parameter}_distance_km"] = distance
                frame[parameter] = matrices[parameter][nearest].reindex(dates)
            complete = bool(frame.notna().all().all())
            physical = bool((frame.T2M_MIN <= frame.T2M_MAX).all() and frame.PRECTOTCORR.ge(0).all()
                            and frame.ALLSKY_SFC_SW_DWN.ge(0).all() and frame.RH2M.between(0, 100).all()
                            and frame.T2M_MIN.between(-90, 65).all() and frame.T2M_MAX.between(-90, 65).all())
            result = {"record_id": row.record_id, "year": int(year), "state": row.state,
                      "first_weather_date": dates.min().strftime("%Y-%m-%d"), "last_weather_date": dates.max().strftime("%Y-%m-%d"),
                      "expected_days": len(dates), "complete_weather": complete, "physical_checks_pass": physical,
                      "missing_parameter_days": int(frame.isna().sum().sum())}
            for label, start, end in [("all", 0, 60), ("d0_14", 0, 14), ("d15_29", 15, 29), ("d30_44", 30, 44), ("d45_60", 45, 60)]:
                window = frame.iloc[start:end + 1]
                for parameter in PARAMETERS:
                    result[f"{parameter}_{label}_mean"] = float(window[parameter].mean()) if window[parameter].notna().all() else np.nan
                result[f"rain_{label}_total_mm"] = float(window.PRECTOTCORR.sum()) if window.PRECTOTCORR.notna().all() else np.nan
            output.append(result)
            links.append(link)
    features, linkage = pd.DataFrame(output), pd.DataFrame(links)
    features.to_csv(FIELD_DATA / "weather_features_local.csv", index=False, lineterminator="\n")
    linkage.to_csv(FIELD_DATA / "weather_linkage_local.csv", index=False, lineterminator="\n")
    coverage = features.groupby(["year", "state"]).agg(linked_records=("record_id", "size"),
        complete_records=("complete_weather", "sum"), physical_check_pass_records=("physical_checks_pass", "sum")).reset_index()
    coverage.to_csv(FIELD_DATA / "weather_coverage.csv", index=False, lineterminator="\n")
    summary = {"linked_records": len(features), "complete_records": int(features.complete_weather.sum()),
               "physical_check_pass_records": int(features.physical_checks_pass.sum()),
               "missing_parameter_days": int(features.missing_parameter_days.sum()), "cutoff_day": 60,
               "inclusive_days": 61, "time_standard": "LST", "new_model_trained": False,
               "linkage_method": "Nearest returned source grid per parameter; no station measurements",
               "distance_km_quantiles": {p: {str(q): float(linkage[f"{p}_distance_km"].quantile(q)) for q in [.5, .95, 1]} for p in PARAMETERS},
               "limitations": ["Source field GPS not verified", "Weather grid resolution does not equal field precision",
                               "No management-unit verification or new trained model", "Calendar windows are not observed phenological stages"]}
    (FIELD_DATA / "weather_audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    source_audit_path = FIELD_DATA / "audit_summary.json"
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    source_audit["daily_weather_acquired"] = summary["complete_records"] == len(records)
    source_audit["weather_linked_records"] = len(features)
    source_audit["forecast_ready"] = False
    source_audit_path.write_text(json.dumps(source_audit, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def load_weather_audit():
    path = FIELD_DATA / "weather_audit.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
