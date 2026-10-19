"""Reproducible variety-linkage and measured-SNP protein feasibility audit.

Annotations describe single variants relative to a reference, not reconstructed
complete cultivar proteins. This module does not train or alter a yield model.
"""
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/rice/molecular_linkage_audit"
OUT = ROOT / "data/processed/rice/molecular_linkage_audit"
REST = "https://rest.ensembl.org"
ALLELES = set("ACGT")


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def request_json(name, endpoint, body=None):
    path = RAW / name
    url = endpoint if endpoint.startswith("https://") else REST + endpoint
    if path.exists():
        receipt = json.loads(path.with_suffix(".request.json").read_bytes())
        if receipt["url"] != url or receipt.get("body") != body or receipt["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Cached response does not match this request or its checksum")
        return json.loads(path.read_bytes())
    last = None
    for _ in range(2):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read()
            result = json.loads(raw)
            if isinstance(result, dict) and result.get("error"):
                raise ValueError(result["error"])
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            save_json(path.with_suffix(".request.json"), {"url": url, "method": "POST" if body else "GET", "body": body,
                      "sha256": hashlib.sha256(raw).hexdigest()})
            return result
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:400]
            if error.code in [400, 404, 410]:
                raise RuntimeError(f"{name}: HTTP {error.code}: {detail}") from error
            last = f"HTTP {error.code}: {detail}"
        except (OSError, ValueError) as error:
            last = error
    raise RuntimeError(f"{name}: {last}")


def normalize(value):
    return re.sub("[^A-Z0-9]", "", str(value).upper())


def acquire_catalogues():
    """Small public catalogues linked by IRRI; no bulk genomes are downloaded."""
    ids = {"3k_irri": "1esF_d7ZMWNQSetzOfgwqfUv4aC6sPfMbgYrbEFf0S40",
           "3k_caas": "1R6lbHRhV1C2cBgkcpdNuubXMC-1-WjN0N-Xa38K5W9A"}
    manifest = []
    RAW.mkdir(parents=True, exist_ok=True)
    for name, identifier in ids.items():
        path = RAW / f"{name}.csv"
        url = f"https://docs.google.com/spreadsheets/d/{identifier}/export?format=csv"
        if not path.exists():
            with urllib.request.urlopen(url, timeout=25) as response:
                raw = response.read()
            if raw.lstrip().startswith(b"<"):
                raise ValueError("Provider returned HTML instead of accession data")
            path.write_bytes(raw)
        previous_manifest = RAW / "successful_catalogues.json"
        if previous_manifest.exists():
            previous = {r["name"]: r for r in json.loads(previous_manifest.read_bytes())["files"]}
            if name in previous and hashlib.sha256(path.read_bytes()).hexdigest() != previous[name]["sha256"]:
                raise ValueError("Cached catalogue checksum differs from its acquisition record")
        manifest.append({"name": name, "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    save_json(RAW / "successful_catalogues.json", {"provider_page": "https://iric.irri.org/resources/snp-seek-datasets", "files": manifest})
    return manifest


def catalogue_matches():
    metadata = pd.read_csv(ROOT / "data/processed/rice/accession_metadata.csv", dtype=str).fillna("")
    lookup = {}
    for _, r in metadata.iterrows():
        # Parentage is deliberately excluded: a parent is not the sequenced child.
        for c in ["DESIGNATION", "DERIVATIVE NAME", "LINE NAME", "OTHER NAME"]:
            for alias in [r[c]] + re.split(r"[.;]", r[c]):
                if normalize(alias):
                    lookup.setdefault(normalize(alias), set()).add(r.GID)
    rows, counts = [], {}
    fields = {"3k_irri": ["GS_IRIS_varname", "3K_DNA_IRIS_UNIQUE_ID"],
              "3k_caas": ["DNA VARNAME source", "DNA Othername source", "DNA UNIQUE ID"]}
    for name, columns in fields.items():
        frame = pd.read_csv(RAW / f"{name}.csv", dtype=str).fillna("")
        counts[name] = len(frame)
        for i, r in frame.iterrows():
            for column in columns:
                aliases = {r[column].split("::")[0], *re.split(r"[;,]", r[column].split("::")[0])}
                for alias in aliases:
                    for gid in lookup.get(normalize(alias), []):
                        rows.append({"GID": gid, "catalogue": name, "source_row": i + 2, "field": column, "source_name": r[column], "status": "candidate_exact_normalized_alias_not_sample_identity_proof"})
    pd.DataFrame(rows, columns=["GID", "catalogue", "source_row", "field", "source_name", "status"]).to_csv(OUT / "catalogue_name_matches.csv", index=False, lineterminator="\n")
    return counts, rows


def annotate_markers():
    assembly = request_json("assembly.json", "/info/assembly/oryza_sativa?content-type=application/json")
    request_json("software.json", "/info/software?content-type=application/json")
    if assembly["assembly_name"] != "IRGSP-1.0":
        raise ValueError("Unexpected assembly; do not lift or assume compatible coordinates")
    markers = pd.read_csv(ROOT / "data/processed/rice/marker_metadata.csv")
    if markers["rs#"].duplicated().any() or not markers.strand.eq("+").all():
        raise ValueError("Audit expects unique forward-strand markers")
    chunks = [markers.iloc[i:i+50] for i in range(0, len(markers), 50)]

    def fetch_reference(job):
        i, part = job
        regions = [f"{int(r.chrom)}:{int(r.pos)}..{int(r.pos)}:1" for r in part.itertuples()]
        original = RAW / f"reference_{i:02d}.json"
        if original.exists():
            return request_json(original.name, "/sequence/region/oryza_sativa?content-type=application/json", {"regions": regions})
        # Small batches avoid intermittent provider errors at the maximum size.
        result = []
        for j in range(0, len(regions), 25):
            result.extend(request_json(f"reference_{i:02d}_part{j//25}.json", "/sequence/region/oryza_sativa?content-type=application/json", {"regions": regions[j:j+25]}))
        return result

    bases = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i, result in enumerate(pool.map(fetch_reference, enumerate(chunks))):
            for r in result:
                if ":IRGSP-1.0:" not in r["id"] or len(r["seq"]) != 1:
                    raise ValueError("Unexpected sequence coordinate or length")
                bases[r["query"]] = r["seq"].upper()
            print(f"Reference bases {i+1}/{len(chunks)}", flush=True)
    matched, excluded = [], []
    for _, r in markers.iterrows():
        ref = bases[f"{int(r.chrom)}:{int(r.pos)}..{int(r.pos)}:1"]
        alleles = r.alleles.split("/")
        if len(alleles) != 2 or not set(alleles).issubset(ALLELES) or ref not in alleles:
            excluded.append({"marker": r["rs#"], "reported_alleles": r.alleles, "reference_base": ref, "reason": "reference_not_in_forward_marker_alleles_or_not_biallelic"})
            continue
        alt = next(a for a in alleles if a != ref)
        matched.append({"marker": r["rs#"], "chromosome": int(r.chrom), "position": int(r.pos), "reference": ref, "alternate": alt})
    compatible = pd.DataFrame(matched)
    compatible.to_csv(OUT / "reference_checked_markers.csv", index=False, lineterminator="\n")
    pd.DataFrame(excluded, columns=["marker", "reported_alleles", "reference_base", "reason"]).to_csv(OUT / "excluded_markers.csv", index=False, lineterminator="\n")
    variant_chunks = [compatible.iloc[i:i+50] for i in range(0, len(compatible), 50)]

    def fetch_effects(job):
        i, part = job
        variants = [f"{r.chromosome} {r.position} {r.marker} {r.reference} {r.alternate} . . ." for r in part.itertuples(index=False)]
        return request_json(f"vep_{i:02d}.json", "/vep/oryza_sativa/region?content-type=application/json", {"variants": variants, "protein": 1, "canonical": 1, "uniprot": 1})

    effects, variant_summary = [], []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i, result in enumerate(pool.map(fetch_effects, enumerate(variant_chunks))):
            for variant in result:
                if variant["assembly_name"] != "IRGSP-1.0":
                    raise ValueError("Unexpected annotation assembly")
                marker = variant["id"]
                expected = compatible.loc[compatible.marker.eq(marker)]
                if len(expected) != 1 or variant["allele_string"] != f"{expected.iloc[0].reference}/{expected.iloc[0].alternate}":
                    raise ValueError("Annotation alleles do not match the reference-checked query")
                variant_summary.append({"marker": marker, "most_severe_consequence": variant["most_severe_consequence"]})
                for t in variant.get("transcript_consequences", []):
                    if t.get("amino_acids") and t.get("protein_start"):
                        effects.append({"marker": marker, "gene": t["gene_id"], "gene_symbol": t.get("gene_symbol", ""), "transcript": t["transcript_id"],
                            "protein_id": t.get("protein_id", ""), "canonical": t.get("canonical", 0), "consequence": ";".join(t["consequence_terms"]),
                            "impact": t["impact"], "protein_start": t["protein_start"], "protein_end": t.get("protein_end", t["protein_start"]),
                            "amino_acids": t["amino_acids"], "codons": t.get("codons", ""),
                            "uniprot_ids": ";".join(sorted({x.split(".")[0] for key in ["swissprot", "trembl"] for x in t.get(key, [])}))})
            print(f"Variant consequences {i+1}/{len(variant_chunks)}", flush=True)
    if len(variant_summary) != len(compatible) or len({v["marker"] for v in variant_summary}) != len(compatible):
        raise ValueError("Incomplete or duplicate annotation response")
    pd.DataFrame(variant_summary).to_csv(OUT / "variant_consequences.csv", index=False, lineterminator="\n")
    proteins = pd.DataFrame(effects)
    proteins.to_csv(OUT / "coding_consequences.csv", index=False, lineterminator="\n")
    return markers, compatible, proteins


def prepare_measured_variant_features(compatible, proteins):
    """Measured genotypes plus reference consequences, never invented full alleles."""
    selected = proteins.loc[proteins.canonical.eq(1) & proteins.consequence.str.contains("missense_variant|stop_gained|stop_lost", regex=True)].copy()
    selected = selected.drop_duplicates(["marker", "protein_id", "protein_start", "amino_acids"])
    selected.to_csv(OUT / "canonical_changed_residues.csv", index=False, lineterminator="\n")
    calls = pd.read_csv(ROOT / "data/processed/rice/genotype_marker_calls.csv").set_index("genotype_id")
    dosage = pd.DataFrame(index=calls.index)
    ambiguity = {"R": set("AG"), "Y": set("CT"), "S": set("GC"), "W": set("AT"), "K": set("GT"), "M": set("AC")}
    refs = compatible.set_index("marker")
    for marker in sorted(selected.marker.unique()):
        ref, alt = refs.at[marker, "reference"], refs.at[marker, "alternate"]
        def convert(value):
            if value == ref:
                return 0.
            if value == alt:
                return 2.
            if ambiguity.get(value) == {ref, alt}:
                return 1.
            return np.nan
        dosage[marker] = calls[marker].map(convert)
    dosage.to_csv(OUT / "measured_variant_dosages.csv", lineterminator="\n")
    availability = pd.read_csv(ROOT / "data/processed/rice/dataset_map/genotype_availability.csv").set_index("genotype_id")
    coverage = pd.DataFrame({"called_changed_markers": dosage.notna().sum(axis=1), "alternate_allele_dosage_total": dosage.sum(axis=1, min_count=1),
                             "eligible_yield_records": availability.eligible_yield_records.reindex(dosage.index)})
    coverage.to_csv(OUT / "genotype_feature_coverage.csv", lineterminator="\n")
    return selected, dosage, coverage


def audit_structural_links(maximum_proteins=20):
    """Bounded reference-structure feasibility sample, ordered without yield scores.

    Exact full reference-sequence equality is required before residue coordinates
    can transfer from Ensembl to AlphaFold. A missing model is not imputed.
    """
    selected = pd.read_csv(OUT / "canonical_changed_residues.csv").fillna("")
    pairs = []
    for r in selected.sort_values(["marker", "protein_id"]).itertuples():
        for uniprot in str(r.uniprot_ids).split(";"):
            if uniprot:
                pairs.append((r.protein_id, uniprot))
    pairs = list(dict.fromkeys(pairs))[:maximum_proteins]
    statuses, mapped = [], []
    aa3 = dict(zip(["ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"], "ARNDCQEGHILKMFPSTWYV"))
    for i, (protein, uniprot) in enumerate(pairs):
        status = {"protein_id": protein, "uniprot": uniprot, "status": "unresolved"}
        try:
            sequence = request_json(f"protein_{protein}.json", f"/sequence/id/{protein}?type=protein;content-type=application/json")["seq"]
            af = request_json(f"alphafold_{uniprot}.json", f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot}")
            entries = [e for e in af if e.get("uniprotSequence", e.get("sequence")) == sequence
                       and e.get("uniprotStart", e.get("sequenceStart", 1)) == 1
                       and e.get("uniprotEnd", e.get("sequenceEnd", len(sequence))) == len(sequence)]
            if not entries:
                status["status"] = "reference_sequence_mismatch_or_partial_model"
            else:
                entry = entries[0]
                url = entry["pdbUrl"]
                path = RAW / f"structure_{uniprot}.pdb"
                if not path.exists():
                    with urllib.request.urlopen(url, timeout=25) as response:
                        raw = response.read()
                    if b"ATOM  " not in raw:
                        raise ValueError("No coordinates in structure")
                    path.write_bytes(raw)
                    save_json(path.with_suffix(".request.json"), {"url": url, "sha256": hashlib.sha256(raw).hexdigest()})
                residues = {}
                coordinates = {}
                for line in path.read_text(encoding="ascii").splitlines():
                    if line.startswith("ATOM  ") and line[12:16].strip() == "CA" and line[21:22] == entry.get("chainId", "A"):
                        position = int(line[22:26])
                        if position in residues:
                            raise ValueError("Ambiguous residue numbering")
                        plddt = float(line[60:66])
                        if not 0 <= plddt <= 100:
                            raise ValueError("Invalid AlphaFold confidence value")
                        residues[position] = (aa3.get(line[17:20], "X"), plddt)
                        coordinates[position] = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
                if set(residues) != set(range(1, len(sequence)+1)) or "".join(residues[p][0] for p in range(1, len(sequence)+1)) != sequence:
                    status["status"] = "coordinate_sequence_mismatch"
                else:
                    status["status"] = "exact_reference_sequence_and_coordinates"
                    status["reference_length"] = len(sequence)
                    for r in selected.loc[selected.protein_id.eq(protein)].itertuples():
                        position = int(r.protein_start)
                        ref = r.amino_acids.split("/")[0]
                        if len(ref) == 1 and position == int(r.protein_end) and residues[position][0] == ref:
                            confident = [p for p in residues if residues[p][1] >= 70]
                            contacts, radial = np.nan, np.nan
                            if residues[position][1] >= 70 and confident:
                                cloud = np.array([coordinates[p] for p in confident])
                                center = cloud.mean(axis=0)
                                radius = np.sqrt(np.mean(np.sum((cloud-center)**2, axis=1)))
                                radial = float(np.linalg.norm(coordinates[position]-center) / radius) if radius > 0 else np.nan
                                contacts = sum(abs(p-position) > 2 and np.linalg.norm(coordinates[p]-coordinates[position]) <= 8 for p in confident)
                            mapped.append({"marker": r.marker, "protein_id": protein, "uniprot": uniprot,
                                "protein_position": position, "amino_acids": r.amino_acids, "reference_residue_plddt": residues[position][1],
                                "confident_nonlocal_ca_neighbors_8A": contacts, "radial_position_over_confident_rg": radial,
                                "structure_url": url, "interpretation": "Single measured variant in reference structure; not cultivar-specific folding or a measured tolerance effect"})
        except (RuntimeError, OSError, ValueError, KeyError, IndexError) as error:
            status["status"] = "retrieval_or_validation_failed"
            status["detail"] = str(error)
        statuses.append(status)
        print(f"Reference structure audit {i+1}/{len(pairs)}: {status['status']}", flush=True)
    pd.DataFrame(statuses).to_csv(OUT / "structure_link_status.csv", index=False, lineterminator="\n")
    mapped_frame = pd.DataFrame(mapped, columns=["marker", "protein_id", "uniprot", "protein_position", "amino_acids", "reference_residue_plddt", "confident_nonlocal_ca_neighbors_8A", "radial_position_over_confident_rg", "structure_url", "interpretation"])
    mapped_frame.to_csv(OUT / "structure_mapped_variants.csv", index=False, lineterminator="\n")
    unique = mapped_frame.sort_values(["marker", "reference_residue_plddt", "uniprot"], ascending=[True, False, True]).drop_duplicates("marker")
    unique.to_csv(OUT / "reference_structure_features.csv", index=False, lineterminator="\n")
    summary = {"audited_on": date.today().isoformat(), "scope": "First 20 distinct protein/UniProt pairs sorted by measured marker ID, independent of yield. Not an exhaustive structure search.",
               "pairs_checked": len(statuses), "pairs_with_exact_sequence_and_coordinates": sum(s["status"] == "exact_reference_sequence_and_coordinates" for s in statuses),
               "unique_measured_markers_mapped": len({r["marker"] for r in mapped}), "residue_mappings": len(mapped),
               "unique_reference_proteins_mapped": len({r["protein_id"] for r in mapped}),
               "unique_sites_with_plddt_at_least_70": int(unique.reference_residue_plddt.ge(70).sum()),
               "structural_descriptors": "Reference C-alpha nonlocal contacts within 8 Angstrom (exclude positions within 2 residues) and radial distance/rg of confident residues. Only sites and neighbors with pLDDT>=70; missing geometry remains missing. Exploratory engineering descriptors, not validated damage or solvent accessibility scores.",
               "one_model_per_site": "Highest local pLDDT among exactly sequence-matched checked models; ties use UniProt lexical order. Selection is independent of yield.",
               "full_cultivar_proteins_assigned": 0, "trained_model_changed": False}
    save_json(OUT / "structure_summary.json", summary)
    return summary


def run_linkage_audit():
    OUT.mkdir(parents=True, exist_ok=True)
    acquire_catalogues()
    counts, names = catalogue_matches()
    markers, compatible, proteins = annotate_markers()
    selected, dosages, coverage = prepare_measured_variant_features(compatible, proteins)
    counts_out = proteins.groupby("consequence").marker.nunique().to_dict() if not proteins.empty else {}
    summary = {"audited_on": date.today().isoformat(), "primary_trial_metadata_genotypes": 111, "primary_yield_genotypes": 107,
               "catalogue_rows": counts, "exact_catalogue_alias_matches": len(names),
               "measured_markers": len(markers), "reference_compatible_markers": len(compatible), "excluded_markers": len(markers)-len(compatible),
               "markers_with_amino_acid_annotation": int(proteins.marker.nunique()) if not proteins.empty else 0,
               "coding_consequence_counts": {k: int(v) for k, v in counts_out.items()},
               "canonical_changed_markers": int(selected.marker.nunique()), "genotypes_with_changed_variant_calls": int((coverage.called_changed_markers > 0).sum()),
               "yield_records_with_changed_variant_calls": int(coverage.loc[coverage.called_changed_markers > 0, "eligible_yield_records"].sum()),
               "complete_variety_specific_protein_sequences_verified": 0,
               "interpretation": "Measured variants can carry reference-protein annotations. These are not full cultivar sequences, structural measurements, experimentally measured functional impacts, or evidence of yield forecasting gain.",
               "predictive_model_changed": False}
    save_json(OUT / "summary.json", summary)
    return summary
