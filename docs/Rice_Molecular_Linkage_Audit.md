# Rice protein linkage audit

Completed 20 October 2026. This audit prepares a molecular extension without changing the regional forecast estimator or any published forecasting results.

## Decision

A limited protein-context experiment is now feasible using the measured SNPs in the existing rice trials. Complete variety-specific protein sequences have not been established. The earlier statement that only complete cultivar protein sequences could support any molecular extension was too restrictive: measured variants can be annotated against a verified reference protein and its predicted structure. That supports a different, explicitly labelled representation of the same genetic measurements.

| Audit component | Verified result |
| --- | --- |
| Published 3K accession catalogue rows inspected | 3,000: IRRI 2,466, CAAS 534 |
| Exact normalized trial-alias matches in those tables | 0 |
| Primary measured marker positions | 882 |
| Forward marker allele pairs containing the reference base | 882 of 882 |
| Markers with amino-acid-level annotation, including synonymous | 151 |
| Canonical protein-altering markers | 89, represented by 90 transcript-effect rows |
| Trial genotypes with calls for these markers | 107 |
| Eligible existing yield records linked | 1,046 |
| Nonmissing measured dosage cells | 9,523 of 9,523 |
| Constant selected markers across the 107 genotypes | 0 |
| Reference protein/UniProt pairs checked for structures | 20, a bounded feasibility sample |
| Pairs with exact full reference sequence and coordinate match | 20 |
| Distinct markers/reference proteins with structure mapping | 11 / 11 |
| Distinct mapped sites with local pLDDT at least 70 in the selected model | 6 |
| Complete cultivar-specific protein sequences assigned | 0 |
| Yield models trained or altered in this audit | 0 |

## Evidence chain

The [original trial paper](https://doi.org/10.1186/s12284-023-00623-6) describes 111 elite IRRI breeding lines, filtering to 107 lines with 882 markers, aligned to the Nipponbare MSU7 reference. The [Rice Genome Annotation Project](https://rice.uga.edu/) explains that the release-7 and RAP/IRGSP-1.0 projects share the same reference pseudomolecules while their gene annotations differ. The audit uses Ensembl's RAP-derived transcript models and preserves that distinction; MSU gene identifiers are not silently treated as RAP identifiers.

[Ensembl REST](https://rest.ensembl.org/) reports IRGSP-1.0 and software release 116. The pipeline downloads the forward reference nucleotide at every marker. All 882 reference bases occur in the reported forward-strand allele pairs. No complements or coordinate lifts were assumed. It then queries VEP with the verified reference and the other measured allele, validates the returned assembly/alleles/marker IDs, and preserves raw responses and request receipts. Eighteen batches cover all 882 markers, with smaller reference batches after intermittent server errors.

The VEP results include synonymous, missense and stop-gained consequences. These are computational predictions against reference annotations, not experimentally demonstrated effects on crop yield or protein function. The 89-marker feature subset uses canonical transcript missense/stop consequences. One marker can have more than one transcript consequence, so transcript counts and unique marker counts differ.

Existing genotype calls are encoded as allele copy counts: reference homozygote 0, compatible IUPAC heterozygote 1, alternate homozygote 2. Missing or incompatible calls remain missing rather than being filled with reference alleles. All 9,523 cells in this selected matrix are called; each selected marker varies across trial genotypes. Genotype IDs link back to the existing audited trial-yield map, covering 1,046 eligible records. No molecular feature is assigned from a district label or a parental genotype.

## Public accession search

The provider-linked [IRRI accession catalogues](https://iric.irri.org/resources/snp-seek-datasets) were downloaded as the two original CSV tables. Matching uses designation, derivative name, line name and other-name aliases, with case/punctuation normalization and explicit alias separators. Parentage is excluded. Exact name matches would be candidates for sample-identity confirmation, not automatic proof of identical seed material.

No matches occur in these two 3,000-row tables. This is not a proof that the lines are absent from every public sequencing resource or the additional accessions in later 3K releases. The publicly linked grain-quality and elite-panel spreadsheet exports returned HTTP 410, and their normal Drive downloads returned 404. These attempts are recorded; no restricted-access bypass or provider messaging was attempted. The IRRI SNP-Seek main host currently reports downtime and points to a mirror. Neither its larger 19K collection nor unavailable metadata was counted as exhaustively audited.

The six previously downloaded named Ptr proteins also remain reference material; no complete primary-cultivar protein assignment is promoted from a name, parental relationship or the separate Ptr diagnostic haplotype candidates.

## Reference structure verification and usable descriptors

The structure audit checks the first 20 distinct protein/UniProt pairs ordered by measured marker ID, independent of yield. This covers 11 distinct reference proteins/sites; some proteins have multiple UniProt cross-references. For each pair:

1. Retrieve the full reference protein sequence through Ensembl.
2. Retrieve [AlphaFold DB](https://alphafold.ebi.ac.uk/) metadata and require exact full sequence equality, matching start/end coverage and the declared chain.
3. Download the actual predicted PDB coordinates. Require a continuous unique residue numbering and an exact amino-acid sequence match across all C-alpha residues.
4. Require the reference amino acid at the VEP protein position to match the coordinate residue.

All 20 pairs passed these identity/coordinate checks. This validates reference mapping, not AlphaFold's physical accuracy or the actual complete protein in each trial cultivar. Public models are predicted structures; they are not measured cultivar structures.

Local confidence varies substantially. One model per measured marker is selected by maximum local pLDDT, breaking ties by UniProt ID; this choice uses no yield outcomes. Six sites meet pLDDT >=70. Only these sites receive two exploratory geometric descriptors: the number of confident C-alpha neighbours within 8 Angstrom excluding residues within two positions in sequence, and the site's radial distance from the confident-residue centroid divided by their radius of gyration. The same pLDDT threshold applies to neighbour/reference-cloud residues. Low-confidence geometry remains missing.

These are reference packing/position descriptors, not solvent-accessible surface area, experimentally validated mutation impacts or damage scores. pLDDT is model confidence and must not be called protein activity, aluminium resilience or toxicity. Coordinates, confidence, descriptor definitions and source URLs are preserved. Every input can be traced from trial genotype to measured marker, reference consequence, residue and predicted structure.

## Aluminium and applicability

The two existing STAR1/STAR2 reference genes have no coding-consequence marker overlap in this panel. No verified cultivar-specific STAR1/STAR2 proteins or trial-linked soil aluminium/pH measurements were obtained. This audit therefore does not establish aluminium-damage prediction. The separate CIRAD aluminium study retains its own population and limitations.

The regional forecasting dataset has annual district yields without cultivar identity or adoption shares. It cannot receive one trial genotype's protein features as if they represented an entire district. A regional molecular extension would additionally need geographically and temporally matched cultivar/adoption data and compatible yield observations.

## Next experiment supported by these inputs

No additional downloads are necessary to start a small trial-level feasibility comparison with the prepared annotations and measured dosages. Before training, freeze a matched-cohort comparison of early-season environment/context alone, environment plus ordinary SNPs, and environment plus a protein-informed representation of the same measured variants. Fit preprocessing and dimensionality reduction inside each training fold. Hold out whole locations/environments; examine genotype transfer separately if claimed. The old trial assessments have already been inspected, so a new analysis on them is development evidence rather than a fresh untouched test.

Protein annotations do not create new independently measured genotype information. Multiplying each SNP column by a constant structural score is only a rescaling and must not be described as new biological data. Any claimed benefit must beat the plain-SNP and matched-capacity baselines. Identical reference embeddings copied to every variety would provide no between-variety signal. Reference-background single-variant embeddings would require explicit counterfactual labelling; they would not be complete cultivar protein embeddings.

For true cultivar-specific sequence embeddings, obtain a verified accession/sample crosswalk and sufficiently complete coding sequences for the selected proteins, with allele/phasing evidence where needed. Whole-genome downloads are not intrinsically required if targeted complete coding sequences are available. Multiple measured variants within a protein and unobserved variants can affect the actual allele; the current sparse panel does not recover them all.

## Files and reproduction

Functional module: `src/rice_molecular_linkage.py`. `app.py` remains the sole application entry point. The Molecular data audit view loads completed evidence and downloads, without launching network requests or training.

Original public catalogues, reference/API responses, request metadata, reference protein sequences and PDBs are in `data/raw/rice/molecular_linkage_audit/`. Derived outputs are in `data/processed/rice/molecular_linkage_audit/`. Key files are reference_checked_markers.csv, canonical_changed_residues.csv, measured_variant_dosages.csv, genotype_feature_coverage.csv, structure_mapped_variants.csv, reference_structure_features.csv and their JSON summaries. Source responses retain checksums and request bodies.

From a project-root Python session, call `run_linkage_audit()` and `audit_structural_links()` from `src.rice_molecular_linkage`. Cached replay was verified without network access. Missing caches require public API access. The audit changes no forecasting model weights, training cohort, final assessment or regional metrics. No ESM computation or yield-model training occurred.
