"""Official DES Kharif rice acquisition and a development-only label audit.

The raw national report remains local. Post-2017 numeric outcomes are never
converted, summarized or written into development outputs by this module.
"""
import csv
import hashlib
import http.cookiejar
from html.parser import HTMLParser
import json
import math
import re
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/rice/des_kharif_2026"
OUT = ROOT / "data/processed/rice/seasonal_source"
REPORT = RAW / "rice_kharif_1997_2022_report.html"
FORM = "https://www.data.desagri.gov.in/website/apy-query-report-web"
ENDPOINT = "https://www.data.desagri.gov.in/report/crop/apy-query-report-show"
FIELDS = [("fltrstates[]", ""), ("fltrdistricts[]", "all"), ("fltrcrops[]", "1"),
          ("fltrseason[]", "K"), ("fltrstartyear", "1997"), ("fltrendyear", "2022"),
          ("fltrrptformat", "exl"), ("fltrcontribut", "all")]
STATES = {"Bihar", "Jharkhand", "Odisha", "Chhattisgarh", "West Bengal"}
DEVELOPMENT_END = 2017


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


class _ReportParser(HTMLParser):
    """Parse text cells of the named report table without executing HTML/scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "table" and (self.depth or attrs.get("id") == "apyreport"):
            self.depth += 1
        if self.depth == 1:
            if tag == "tr":
                self.row = []
            elif tag in ("th", "td") and self.row is not None:
                self.cell = {"tag": tag, "text": "", "attributes": attrs}

    def handle_data(self, text):
        if self.cell is not None:
            self.cell["text"] += text

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.cell["text"] = " ".join(self.cell["text"].split())
            self.row.append(self.cell)
            self.cell = None
        if tag == "tr" and self.depth == 1 and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "table" and self.depth:
            self.depth -= 1


def _read_report():
    parser = _ReportParser()
    parser.feed(REPORT.read_text(encoding="utf-8"))
    if len(parser.rows) < 3:
        raise ValueError("No complete named official report table")
    first, units = parser.rows[:2]
    if [c["text"] for c in first[:3]] != ["S.No.", "State", "District"]:
        raise ValueError("Unexpected geographic report schema")
    years = []
    for cell in first[3:]:
        match = re.fullmatch(r"(\d{4}) - (\d{4})", cell["text"])
        if not match or int(match[2]) != int(match[1]) + 1 or cell["attributes"].get("colspan") != "3":
            raise ValueError("Unexpected agricultural year header")
        years.append(int(match[1]))
    if years != list(range(1997, 2023)):
        raise ValueError("Report year span differs from the requested acquisition")
    expected = ["Area( Ha. )", "Production (Tonnes)", "Yield (Ton./Ha.)"] * len(years)
    if [c["text"] for c in units] != expected:
        raise ValueError("Official unit header changed; do not assume a conversion")
    width = 3 + 3 * len(years)
    for row in parser.rows[2:]:
        if len(row) != width or any(c["tag"] != "td" for c in row):
            raise ValueError("Unexpected report row width or nested totals")
    return years, parser.rows[2:]


def acquire_report():
    """Use the public form request with normal TLS checks; cache exact response bytes.

    No login, CAPTCHA bypass, certificate override or session-token persistence.
    Certificate-store issues must be resolved with a normally validated client.
    """
    if REPORT.exists():
        _read_report()
        return REPORT
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with opener.open(FORM, timeout=30) as response:
        form = response.read().decode("utf-8")
    tag = re.search(r'<input[^>]*id="hdnrltoken"[^>]*>', form)
    token = re.search(r'value="([^"]+)"', tag[0]) if tag else None
    if not token:
        raise ValueError("Public form token missing; no data request submitted")
    body = urllib.parse.urlencode(FIELDS + [("_token", token[1])]).encode("utf-8")
    request = urllib.request.Request(ENDPOINT, data=body,
                                    headers={"Referer": FORM, "X-Requested-With": "XMLHttpRequest",
                                             "Content-Type": "application/x-www-form-urlencoded"})
    with opener.open(request, timeout=50) as response:
        content = response.read()
    parser = _ReportParser()
    parser.feed(content.decode("utf-8"))
    if len(parser.rows) < 3:
        raise ValueError("Official request returned no report; response not cached as data")
    RAW.mkdir(parents=True, exist_ok=True)
    REPORT.write_bytes(content)
    _read_report()
    return REPORT


def _number(text):
    if text.strip().lower() in {"", "-", "--", "na", "n/a", "null"}:
        return None
    try:
        value = float(text.replace(",", ""))
    except ValueError as exc:
        raise ValueError("Unrecognized numeric cell in development years") from exc
    if not math.isfinite(value):
        raise ValueError("Nonfinite development value")
    return value


def inspect_source():
    """Audit metadata and <=2017 values only; do not train or open newer targets."""
    years, rows = _read_report()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "download_manifest.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8"))["sha256"] != _hash(REPORT):
            raise ValueError("Cached source differs from receipt; preserve it and version a new acquisition")
    manifest = {"retrieved_on": "2026-10-20", "publisher": "Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare, India",
                "form_url": FORM, "endpoint": ENDPOINT, "request_method": "POST",
                "request_fields": dict(FIELDS), "session_secrets_retained": False,
                "relative_file": REPORT.relative_to(ROOT).as_posix(), "bytes": REPORT.stat().st_size,
                "sha256": _hash(REPORT), "format": "Original HTML report returned to the website's Excel export; not a native XLSX workbook",
                "first_acquisition_transport": "Windows Invoke-WebRequest with normal system certificate validation; decoded response stored as UTF-8 without BOM. Python requests/certifi rejected the issuer chain; no TLS verification was disabled.",
                "scope_evidence": "Rice=1 and Kharif=K in the original public form request; response table does not repeat crop/season in each row.",
                "unit_evidence": "Every year header explicitly reports hectares, tonnes, tonnes per hectare.",
                "terms": "Public official report, with publisher attribution. No independent licence or historical release-vintage verification is asserted."}
    inventory, development, seen = [], [], set()
    state_counts = {}
    for row in rows:
        _, state, district = [c["text"] for c in row[:3]]
        key = (state, district)
        if not state or not district or key in seen:
            raise ValueError("Blank or duplicate geographic report row")
        seen.add(key)
        state_counts[state] = state_counts.get(state, 0) + 1
        in_scope = state in STATES
        inventory.append({"state_source": state, "district_source": district, "in_five_state_scope": in_scope,
                          "official_district_code_supplied": False, "historical_boundary_crosswalk_verified": False})
        if not in_scope:
            continue
        for j, year in enumerate(years):
            if year > DEVELOPMENT_END:
                # Deliberately skip all three newer numeric cells, including area/production.
                continue
            area, production, source_yield = [_number(c["text"]) for c in row[3 + j*3:6 + j*3]]
            complete = all(value is not None for value in (area, production, source_yield))
            positive = complete and area > 0 and production > 0 and source_yield > 0
            derived = 1000 * production / area if complete and area > 0 else None
            converted = 1000 * source_yield if source_yield is not None else None
            development.append({"state_source": state, "district_source": district,
                                "agricultural_start_year": year, "crop": "Rice", "season": "Kharif",
                                "area_ha": area, "production_tonnes": production,
                                "source_yield_tonnes_ha": source_yield, "yield_kg_ha": converted,
                                "yield_from_production_area_kg_ha": derived,
                                "absolute_rounding_difference_kg_ha": abs(converted-derived) if converted is not None and derived is not None else None,
                                "positive_complete_triplet": bool(positive),
                                "boundary_verified": False, "ready_for_training": False})
    development_counts = []
    for state in sorted(STATES):
        for year in years:
            allowed = year <= DEVELOPMENT_END
            selected = [r for r in development if r["state_source"] == state and r["agricultural_start_year"] == year]
            development_counts.append({"state_source": state, "agricultural_start_year": year,
                                       "district_rows_in_report": state_counts.get(state, 0),
                                       "value_access": "development audit" if allowed else "reserved; not inspected",
                                       "positive_complete_triplets": sum(r["positive_complete_triplet"] for r in selected) if allowed else None})
    for filename, records in [("district_inventory.csv", inventory), ("development_labels.csv", development),
                              ("state_year_coverage.csv", development_counts)]:
        if not records:
            raise ValueError("Empty expected source output")
        with (OUT / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    positive = [r for r in development if r["positive_complete_triplet"]]
    summary = {"audited_on": "2026-10-20", "original_official_report_obtained": True,
               "national_district_rows": len(rows), "header_years": years,
               "five_state_district_rows": {s: state_counts.get(s, 0) for s in sorted(STATES)},
               "development_end": DEVELOPMENT_END, "reserved_years": [y for y in years if y > DEVELOPMENT_END],
               "development_grid_rows": len(development), "positive_complete_development_triplets": len(positive),
               "missing_or_nonpositive_development_triplets": len(development)-len(positive),
               "development_max_rounding_difference_kg_ha": max(r["absolute_rounding_difference_kg_ha"] for r in positive),
               "newer_numeric_cells_inspected": False, "new_models_trained": False,
               "target_unit_conversion": "Official tonnes/ha multiplied by 1000 to kg/ha; source values also retained.",
               "boundary_ready": False, "weather_ready": False, "training_ready": False,
               "decision": "Official season-specific labels obtained. Next verify district identities and boundary history, reporting availability and issue-date crop calendar before aligned daily-weather acquisition or model fitting.",
               "limitations": ["Source rows supply names, not district IDs or boundary vintages.",
                               "A modern district name appearing across all year columns does not certify stable historical geography.",
                               "Blank/nonpositive triplets are retained with flags, not silently turned into zero yield.",
                               "Post-2017 values remain in the local raw report only and are skipped by development preparation.",
                               "This snapshot ends in 2022-23; it does not establish current-season forecasting or exact historical publication dates."]}
    _json(manifest_path, manifest)
    _json(OUT / "summary.json", summary)
    return summary
