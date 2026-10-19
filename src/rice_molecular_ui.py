"""Display molecular linkage evidence without changing forecasting estimators."""
import json

import pandas as pd
import streamlit as st

from src.rice_molecular_linkage import OUT
from src.rice_protein_experiment import OUT as EXPERIMENT


def _render_experiment():
    path = EXPERIMENT / "summary.json"
    if not path.exists():
        st.info("The controlled protein-context comparison has not completed.")
        return
    summary = json.loads(path.read_text(encoding="utf-8"))
    metrics = pd.read_csv(EXPERIMENT / "metrics.csv")
    comparison = summary["primary_comparison"]
    st.subheader("Does protein context improve trial yield forecasts?")
    if summary["annotation_value_claim_supported"]:
        st.success("The prespecified development comparison supports further testing of protein context. Independent validation is still required.")
    else:
        st.warning("The prespecified comparison does not establish a reliable benefit from protein structure context.")
    a, b, c = st.columns(3)
    a.metric("Macro RMSE improvement", f"{comparison['macro_rmse_improvement_kg_ha']:+.1f} kg/ha")
    b.metric("Locations with lower error", f"{comparison['locations_improved']} / 12")
    c.metric("Matched yield records per model", f"{summary['records_per_model']:,}")
    st.caption("Positive improvement means lower error than environment plus all 882 SNPs. Macro RMSE gives each held-out location equal weight.")
    st.write(f"Paired location-bootstrap 95% range: **{comparison['bootstrap_lower_95']:+.1f} to {comparison['bootstrap_upper_95']:+.1f} kg/ha**. With 12 locations and previously studied trial outcomes, this is descriptive development stability, not independent confirmation.")
    st.write("All nine configurations use the same 1,046 records and weather/planting information available through day 60. Each outer fold holds out a whole location; Ridge strength and preprocessing use only the remaining locations. Genotypes can occur in both training and held-out locations, so this does not test unseen cultivars.")
    shown = metrics.rename(columns={"model": "Configuration", "mae_kg_ha": "Pooled MAE (kg/ha)",
                                   "rmse_kg_ha": "Pooled RMSE (kg/ha)", "r_squared": "R squared",
                                   "macro_mae_kg_ha": "Macro MAE (kg/ha)", "macro_rmse_kg_ha": "Macro RMSE (kg/ha)"})
    st.dataframe(shown.round(2), hide_index=True, width="stretch")
    with st.expander("Matched structure controls and location results"):
        st.dataframe(pd.read_csv(EXPERIMENT / "paired_comparisons.csv").round(2), hide_index=True, width="stretch")
        st.dataframe(pd.read_csv(EXPERIMENT / "location_results.csv").round(2), hide_index=True, width="stretch")
        st.caption("Controls include the same six SNPs without annotation, a three-dimensional SNP PCA representation and jointly shuffled structural annotations. One fixed shuffle is a representation control, not a calibrated permutation significance test.")
    for filename, label in [("predictions.csv", "Download held-out predictions"),
                            ("metrics.csv", "Download comparison metrics"),
                            ("protocol.json", "Download frozen comparison protocol")]:
        st.download_button(label, (EXPERIMENT / filename).read_bytes(), filename,
                           "application/json" if filename.endswith("json") else "text/csv")
    st.caption("This is a trial-level experiment on published adjusted yields. It does not change the regional forecast, reconstruct cultivar proteins, use ESM embeddings or establish aluminium-damage prediction.")
    st.divider()


def render_molecular_audit():
    st.subheader("Rice molecular data audit")
    path = OUT / "summary.json"
    if not path.exists():
        st.info("The molecular linkage audit has not completed.")
        return
    summary = json.loads(path.read_text(encoding="utf-8"))
    structure_path = OUT / "structure_summary.json"
    structures = json.loads(structure_path.read_text(encoding="utf-8")) if structure_path.exists() else None
    _render_experiment()
    st.info("The audit below documents the measured SNP-to-reference-structure links used in the trial experiment. These are not active predictors in the regional yield forecast.")
    a, b, c = st.columns(3)
    a.metric("Trial genotypes linked", summary["genotypes_with_changed_variant_calls"])
    b.metric("Protein-altering markers", summary["canonical_changed_markers"])
    c.metric("Eligible yield records linked", f"{summary['yield_records_with_changed_variant_calls']:,}")
    st.write(f"All {summary['reference_compatible_markers']} measured marker positions passed the forward reference-allele check on IRGSP-1.0. Ensembl predicts protein-level annotations for {summary['markers_with_amino_acid_annotation']} markers, including synonymous variants. The {summary['canonical_changed_markers']} protein-altering markers use canonical transcript annotations and retain their measured genotype calls.")
    if structures:
        st.write(f"Reference-structure check: **{structures['unique_measured_markers_mapped']} distinct measured markers** mapped to exact sequence-matched public models in a bounded sample of **{structures['pairs_checked']} protein/UniProt pairs**.")
        st.caption("The check requires exact full reference protein sequence equality, matching structure coordinates and the expected reference amino acid at the SNP position. These are predicted reference structures, not experimentally measured cultivar structures.")
        st.write(f"After selecting the most confident checked model per marker, **{structures.get('unique_sites_with_plddt_at_least_70', 0)} sites have local pLDDT of at least 70**. Reference packing and radial-position descriptors are provided only for those sites; low-confidence geometry remains missing.")
        mapped = pd.read_csv(OUT / "structure_mapped_variants.csv")
        st.dataframe(mapped, hide_index=True, width="stretch")
        st.download_button("Download verified reference-structure mappings", (OUT / "structure_mapped_variants.csv").read_bytes(), "rice_reference_structure_links.csv", "text/csv")
        st.download_button("Download one-model-per-marker structure features", (OUT / "reference_structure_features.csv").read_bytes(), "rice_reference_structure_features.csv", "text/csv")
    st.warning("AlphaFold pLDDT measures model confidence, not protein activity, aluminium tolerance or crop damage. Complete variety-specific protein sequences remain unverified. STAR1/STAR2 references cannot be assigned to trial varieties from these data.")
    with st.expander("All canonical protein-changing annotations"):
        st.dataframe(pd.read_csv(OUT / "canonical_changed_residues.csv"), hide_index=True, width="stretch")
    with st.expander("Measured genotype feature coverage"):
        st.dataframe(pd.read_csv(OUT / "genotype_feature_coverage.csv"), hide_index=True, width="stretch")
        st.download_button("Download measured variant allele dosages", (OUT / "measured_variant_dosages.csv").read_bytes(), "rice_measured_variant_dosages.csv", "text/csv")
        st.caption("Dosage 0 is homozygous reference, 1 is heterozygous and 2 is homozygous alternate. Unknown or incompatible calls remain missing; no full protein sequences are inferred.")
    st.write("The published 3K accession tables contain 3,000 records and no exact normalized alias matches to the trial lines. Parentage was excluded from matching. Zero matches in these tables do not prove absence from every public resource.")
    st.write("The controlled trial comparison above tests environmental data, ordinary SNPs and protein-context representations on matched records. The district dataset has no variety/adoption linkage, so these features cannot be attached to district-year rows.")
    st.caption("Protein annotations provide a representation of the existing genetic measurements, not new independent genotype observations. A plain SNP baseline is essential; identical reference embeddings copied to every variety would provide no between-variety signal.")
    st.markdown("Sources: [original yield and marker study](https://doi.org/10.1186/s12284-023-00623-6), [IRRI public accession catalogues](https://iric.irri.org/resources/snp-seek-datasets), [rice reference assembly](https://rice.uga.edu/), [Ensembl annotation API](https://rest.ensembl.org/), [AlphaFold DB](https://alphafold.ebi.ac.uk/).")
