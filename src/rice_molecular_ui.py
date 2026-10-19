"""Display molecular linkage evidence without changing forecasting estimators."""
import json

import pandas as pd
import streamlit as st

from src.rice_molecular_linkage import OUT


def render_molecular_audit():
    st.subheader("Rice molecular data audit")
    path = OUT / "summary.json"
    if not path.exists():
        st.info("The molecular linkage audit has not completed.")
        return
    summary = json.loads(path.read_text(encoding="utf-8"))
    structure_path = OUT / "structure_summary.json"
    structures = json.loads(structure_path.read_text(encoding="utf-8")) if structure_path.exists() else None
    st.info("These data support a trial-level protein-context experiment. They are not active predictors in the regional yield forecast, and no yield improvement from these annotations has been tested.")
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
    st.write("The next experiment can compare the same trial cohorts with environmental data, ordinary SNPs, and measured variants annotated with protein context. A held-out-environment comparison must establish whether the protein context adds forecasting value. The district dataset has no variety/adoption linkage, so these features cannot be attached to district-year rows.")
    st.caption("Protein annotations provide a representation of the existing genetic measurements, not new independent genotype observations. A plain SNP baseline is essential; identical reference embeddings copied to every variety would provide no between-variety signal.")
    st.markdown("Sources: [original yield and marker study](https://doi.org/10.1186/s12284-023-00623-6), [IRRI public accession catalogues](https://iric.irri.org/resources/snp-seek-datasets), [rice reference assembly](https://rice.uga.edu/), [Ensembl annotation API](https://rest.ensembl.org/), [AlphaFold DB](https://alphafold.ebi.ac.uk/).")
