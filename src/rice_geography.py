"""Dated Census identity/geometry checks, with explicit territorial-change flags.

Reads district metadata only, never the raw seasonal report or numeric yields.
No current LGD codes, historical polygons or automatic boundary repairs are invented.
"""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import shapefile
from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/rice/seasonal_geography"
OUT = ROOT / "data/processed/rice/seasonal_geography"
INVENTORY = ROOT / "data/processed/rice/seasonal_source/district_inventory.csv"
CENSUS_URL = "https://censusindia.gov.in/nada/index.php/catalog/6191"
STATE_CODES = {"Bihar": "10", "West Bengal": "19", "Jharkhand": "20", "Odisha": "21", "Chhattisgarh": "22"}
ALIASES = {
    "Bihar": {"Purbi champaran": "Purba Champaran"},
    "Chhattisgarh": {"Dantewada": "Dakshin Bastar Dantewada", "Kanker": "Uttar Bastar Kanker",
                     "Kabirdham": "Kabeerdham", "Korea": "Koriya"},
    "Jharkhand": {"East singhbum": "Purbi Singhbhum", "West singhbhum": "Pashchimi Singhbhum",
                  "Koderma": "Kodarma", "Sahebganj": "Sahibganj"},
    "Odisha": {"Boudh": "Baudh", "Deogarh": "Debagarh", "Nabarangpur": "Nabarangapur", "Sonepur": "Subarnapur"},
    "West Bengal": {"24 paraganas north": "North Twenty Four Parganas", "24 paraganas south": "South Twenty Four Parganas",
                    "Coochbehar": "Koch Bihar", "Darjeeling": "Darjiling", "Dinajpur dakshin": "Dakshin Dinajpur",
                    "Dinajpur uttar": "Uttar Dinajpur", "Hooghly": "Hugli", "Howrah": "Haora", "Purulia": "Puruliya",
                    "Medinipur east": "Purba Medinipur", "Medinipur west": "Paschim Medinipur"},
}


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {"separators": (",", ":")} if path.suffix == ".geojson" else {"indent": 2}
    text = json.dumps(value, allow_nan=False, **options) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def _csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.casefold())


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def census_roster():
    parser = _TableParser()
    parser.feed((RAW / "census_2011_pca_catalogue.html").read_text(encoding="utf-8"))
    rows, state, state_code = [], "", ""
    for row in parser.rows:
        if len(row) != 3:
            continue
        if row[2] == "State":
            state, state_code = row[0], row[1].zfill(2)
        elif row[2] == "District":
            if not state_code or not re.fullmatch(r"\d{3}", row[1]):
                raise ValueError("Unrecognized official district roster hierarchy")
            rows.append({"state_census2011": state, "state_code_census2011": state_code,
                         "district_census2011": row[0], "district_code_census2011": row[1], "source_url": CENSUS_URL})
    codes = [r["district_code_census2011"] for r in rows]
    if len(rows) != 640 or len(set(codes)) != 640 or set(map(int, codes)) != set(range(1, 641)):
        raise ValueError("Official Census roster is not the complete unique 640-district register")
    return rows


def _reference_geometries(roster):
    reference = {r["district_code_census2011"]: r for r in roster}
    projection = (RAW / "2011_Dist.prj").read_text(encoding="utf-8")
    if 'GCS_WGS_1984' not in projection or 'UNIT["Degree"' not in projection:
        raise ValueError("Unexpected map CRS; do not treat projected coordinates as longitude/latitude")
    reader = shapefile.Reader(str(RAW / "2011_Dist"))
    features, audits, excluded, seen = [], [], [], set()
    for record in reader.iterShapeRecords():
        attrs = record.record.as_dict()
        code = str(attrs["censuscode"]).zfill(3)
        if code == "000":
            if attrs["DISTRICT"] != "Data Not Available":
                raise ValueError("Unexpected non-Census geometry")
            excluded.append(attrs)
            continue
        if code not in reference or code in seen:
            raise ValueError("Duplicate or unregistered global Census geometry identifier")
        seen.add(code)
        state_code = str(attrs["ST_CEN_CD"]).zfill(2)
        if state_code != reference[code]["state_code_census2011"]:
            raise ValueError("Geometry identifier belongs to the wrong official state")
        if state_code not in STATE_CODES.values():
            continue
        geometry = shape(record.shape.__geo_interface__)
        valid = bool(not geometry.is_empty and geometry.is_valid and geometry.geom_type in {"Polygon", "MultiPolygon"})
        point = geometry.representative_point() if valid else None
        if valid and not geometry.covers(point):
            raise ValueError("Reference representative point is outside its polygon")
        entry = reference[code]
        audit = {**entry, "geometry_name": attrs["DISTRICT"], "geometry_state_name": attrs["ST_NM"],
                 "map_global_code_field": "censuscode", "map_state_local_district_code_not_used": attrs["DT_CEN_CD"],
                 "source_name_same_after_case_punctuation": _norm(attrs["DISTRICT"]) == _norm(entry["district_census2011"]),
                 "valid_original_geometry": valid, "geometry_modified": False,
                 "reference_point_longitude": point.x if point else None, "reference_point_latitude": point.y if point else None,
                 "point_role": "2011 reference polygon interior diagnostic; not a crop-weighted weather location",
                 "all_year_boundary_verified": False}
        audits.append(audit)
        features.append({"type": "Feature", "properties": {"district_code_census2011": code,
                         "state_code_census2011": state_code, "district_census2011": entry["district_census2011"],
                         "source": "DataMeet Census_2011 derived map; CC BY 2.5 India", "valid_original_geometry": valid},
                         "geometry": mapping(geometry)})
    if seen != set(reference) or len(audits) != 129:
        raise ValueError("Incomplete reference geometry/code coverage")
    return features, audits, excluded


def run_geography_audit():
    """Create a metadata-only crosswalk; never open numeric label files or fit models."""
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "source_manifest.json"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (RAW / "datameet_commit.txt").read_text().strip() != prior["geometry_commit"]:
            raise ValueError("Pinned geometry commit changed; preserve and version a new acquisition")
        if any(_hash(ROOT / item["relative_path"]) != item["sha256"] for item in prior["files"]):
            raise ValueError("Cached geographic source bytes changed; do not silently overwrite their receipt")
    roster = census_roster()
    features, geometry_audit, excluded = _reference_geometries(roster)
    reference = {(r["state_code_census2011"], _norm(r["district_census2011"])): r for r in roster}
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        source = [r for r in csv.DictReader(handle) if r["in_five_state_scope"] == "True"]
    events = json.loads((OUT / "change_events.json").read_text(encoding="utf-8"))["events"]
    children = {(e["state"], _norm(n)): e for e in events for n in e["children"]}
    aliases = {state: {_norm(k): v for k,v in names.items()} for state,names in ALIASES.items()}
    spatial = {r["district_code_census2011"]: r for r in geometry_audit}

    def direct(state, name):
        text = aliases.get(state, {}).get(_norm(name), name)
        return reference.get((STATE_CODES[state], _norm(text)))

    def ancestor_codes(state, name, visited=()):
        key = (state, _norm(name))
        if key in visited:
            raise ValueError("Cycle in documented territorial change graph")
        event = children.get(key)
        if event and event["year"] > 2011:
            if event.get("parent_verified", True) is False:
                return set()
            return set().union(*(ancestor_codes(state, parent, (*visited,key)) for parent in event["parents"])) if event["parents"] else set()
        match = direct(state, name)
        return {match["district_code_census2011"]} if match else set()

    crosswalk, year_flags = [], []
    assigned = set()
    for row in source:
        state, name = row["state_source"], row["district_source"]
        key = (state, _norm(name))
        created = children.get(key)
        changed_unit = created is not None and created["year"] > 2011
        match = None if changed_unit else direct(state, name)
        if match:
            code = match["district_code_census2011"]
            if code in assigned:
                raise ValueError("Two source rows were assigned the same direct district identity")
            assigned.add(code)
            alias = _norm(name) in aliases.get(state, {})
            status = "reviewed_alias_to_2011_reference" if alias else "exact_case_punctuation_2011_reference"
        else:
            code, alias = "", False
            status = "post2011_territorial_unit_not_same_geometry" if changed_unit else "unresolved_identity"
        related = sorted(ancestor_codes(state, name)) if changed_unit else []
        relevant = [e for e in events if e["state"] == state and _norm(name) in {_norm(n) for n in e["children"]+e["parents"]}]
        valid_geometry = bool(code and spatial[code]["valid_original_geometry"])
        crosswalk.append({"state_source": state, "district_source": name, "state_code_census2011": STATE_CODES[state],
                          "match_status": status, "district_code_census2011_reference": code,
                          "district_name_census2011_reference": match["district_census2011"] if match else "",
                          "alias_is_explicit_review_rule": alias, "des_alias_confirmation_obtained": False,
                          "alias_qualification": "Reviewed translation/spelling candidate; no fuzzy match or source-issued code crosswalk" if alias else "",
                          "current_lgd_code": "", "lgd_code_inferred": False,
                          "related_2011_ancestor_codes_not_identity": ";".join(related),
                          "source_is_multi_parent_change": bool(created and len(created["parents"])>1),
                          "reviewed_change_years": ";".join(map(str,sorted({e["year"] for e in relevant}))),
                          "original_2011_geometry_valid": valid_geometry,
                          "all_year_boundary_verified": False, "ready_for_weather_linkage": False,
                          "evidence_urls": ";".join(dict.fromkeys([CENSUS_URL]+[e["source"] for e in relevant]))})
        for year in range(1997, 2023):
            flags = []
            if not match:
                flags.append("No same-unit Census2011 reference geometry")
            if year < 2011:
                flags.append("Pre2011 territorial equivalence not established")
            if created:
                if year < created["year"]:
                    flags.append("Before documented district creation; any historical recast needs source proof")
                elif year == created["year"]:
                    flags.append("Territorial transition year; do not assume a whole-year boundary")
            if any(year >= e["year"] and e["year"] > 2011 and _norm(name) in {_norm(p) for p in e["parents"]} for e in relevant):
                flags.append("2011 parent territory changed by documented split")
            if not valid_geometry:
                flags.append("Valid same-unit reference polygon unavailable")
            flags.append("Full history and source reporting geography remain unverified")
            year_flags.append({"state_source": state, "district_source": name, "agricultural_start_year": year,
                               "reserved_numeric_outcomes_not_read": year>=2018,
                               "boundary_verified": False, "ready_for_weather_linkage": False,
                               "screening_flags": "; ".join(flags)})
    if len(source) != 147 or any(r["match_status"] == "unresolved_identity" for r in crosswalk):
        raise ValueError("Source roster changed or lacks an explicit documented identity disposition")
    _csv(OUT / "official_census2011_districts.csv", roster)
    _csv(OUT / "district_crosswalk.csv", crosswalk)
    _csv(OUT / "reference_geometry_audit.csv", geometry_audit)
    _csv(OUT / "district_year_flags.csv", year_flags)
    _json(OUT / "reference_geometries.geojson", {"type": "FeatureCollection",
          "name": "DataMeet-derived Census2011 reference districts, five states",
          "attribution": "District maps provided by DataMeet Community Maps Project, CC BY 2.5 India. Names/extents derived from Census Administrative Atlas; geometry is third-party derived, not authoritative survey or all-year borders.",
          "features": features})
    counts = {status: sum(r["match_status"] == status for r in crosswalk) for status in sorted({r["match_status"] for r in crosswalk})}
    summary = {"audited_on": "2026-10-20", "source_geographic_rows_reviewed": len(source),
               "official_census2011_district_codes": len(roster), "reference_map_records": 641,
               "non_district_code_zero_map_records": len(excluded), "five_state_reference_geometries": len(features),
               "valid_original_reference_geometries": sum(r["valid_original_geometry"] for r in geometry_audit),
               "reference_name_disagreements_after_normalization": sum(not r["source_name_same_after_case_punctuation"] for r in geometry_audit),
               "source_identity_status_counts": counts, "reviewed_change_events": len(events),
               "district_year_metadata_flags": len(year_flags), "districts_verified_for_entire_1997_2022_span": 0,
               "current_lgd_codes_verified": 0, "all_year_weather_ready_rows": 0,
               "reserved_numeric_outcomes_read": False, "numeric_label_files_read": False,
               "model_training_performed": False, "training_ready": False,
               "decision": "Use the explicit Census2011 reference crosswalk for further geography review. Do not assign old parent polygons to post2011 units or treat matching names/codes as unchanged borders. Resolve source recasting/territorial epochs, or narrow the next study to a documented comparable region, before new weather acquisition.",
               "low_complexity_candidate": "Odisha has 30 reference districts and a government-documented early-1990s reorganization. This is a candidate narrower scope before scores, not proof of every border's constancy or an automatically selected training cohort.",
               "limitations": ["Codes are official Census2011 identifiers, not current LGD identifiers.",
                               "24 explicit spelling/translation rules are review candidates, not a source-issued DES code crosswalk.",
                               "Recorded split evidence is not an exhaustive history of intradistrict transfers or boundary corrections.",
                               "Map geometry is derived by DataMeet from taluk sources and Census extent references, under CC BY 2.5 India.",
                               "Raw geometry is neither silently repaired nor reused as crop-masked weather support."]}
    _json(OUT / "summary.json", summary)
    commit = (RAW / "datameet_commit.txt").read_text().strip()
    files = [RAW / "census_2011_pca_catalogue.html", RAW / "datameet_README.md"] + [RAW / f"2011_Dist.{ext}" for ext in ("shp","shx","dbf","prj")]
    receipt = {"retrieved_on": "2026-10-20", "official_identity_source": CENSUS_URL,
               "geometry_commit": commit, "geometry_publisher": "DataMeet Community Maps Project",
               "geometry_licence": "Creative Commons Attribution 2.5 India, per Districts/README.md; do not substitute repository software MIT licence",
               "files": [{"relative_path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": _hash(p),
                          "url": CENSUS_URL if p.name.endswith("catalogue.html") else f"https://raw.githubusercontent.com/datameet/maps/{commit}/Districts/" + ("README.md" if p.name.endswith("README.md") else "Census_2011/"+p.name)} for p in files],
               "current_lgd_attempt": "Official DILRMP district roster request timed out after 30 seconds; no LGD codes fabricated.",
               "centroid_policy": "Representative interior points are diagnostic only; no weather or crop-area weighting is claimed."}
    _json(OUT / "source_manifest.json", receipt)
    return summary
