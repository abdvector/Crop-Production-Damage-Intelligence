# Additional public rice datasets acquired

Acquired and inspected 10 October 2026. These sources remain separate from Nguyen and CIRAD. No modelling or application changes were made.

## Smart-Valleys

Source: https://zenodo.org/records/20345853

Original: `data/raw/rice/smart_valleys_2026/Smart-Valleys dataset.xlsx`.

Verified: publisher MD5 matches, XLSX archive integrity passes, workbook opens. It contains 243 rows and 84 columns; 7 countries, 242 unique valley codes and years 2013–2024. Columns include two yield fields, fertilizer rates, soil nutrients/pH/texture, management flags, coordinates and monthly/seasonal weather. There are 122 missing cells. These are counts of source rows, not a verified panel of repeated independent trials.

The Variety field contains only three broad labels, not genotype IDs suitable for a molecular join. The downloaded workbook has one data sheet and no separate dictionary. Yield/moisture, soil units, measurement methods, transformations, sampling dates and weather provenance require confirmation. Some soil columns have few unique values and repeated numeric patterns; do not assume they are raw field measurements without documentation. Full-season weather cannot enter an earlier forecast. No explicit aluminium or protein data were identified. The two yield columns do not establish which soil/management fields apply to each production system; clarify before reshaping or treating them as paired interventions.

## BAAP nitrogen field trials

Source: https://catalogue.ceh.ac.uk/documents/1e20a1c8-6aeb-4365-866d-71b24c497586

Stored originals and support ZIPs: `data/raw/rice/baap_nitrogen_2025/`. Both ZIPs pass archive integrity checks; local SHA256 hashes are in the download manifest. No separate authoritative checksum was identified for these ZIPs.

Main CSV has 37899 rows and 29 columns, including trailing unnamed columns. It contains 17952 numeric grain-yield values, four sites, 10 site-season codes and 300 unique nonmissing BAAP IDs. Source row counts include rows with no numeric yield; all originals are preserved. A full row/identity/replicate audit remains necessary.

Supporting metadata describes two nitrogen treatments (50% and 100% of the normal rate), replicated row trials and grain yield in grams per plant. It reports spacing and notes that measurements average the middle six plants of each row. This is not a measured kg/ha harvest target. A density-based conversion would be a derived estimate requiring explicit assumptions, moisture and field-representativeness checks. Absolute fertilizer doses and exact establishment dates are not resolved by the percentage-treatment label. SPAD has no physical nitrogen-concentration unit; it is an index.

The metadata references a BAAP genetic resource of about two million SNPs, but those marker data are not included in these downloaded ZIPs. Match BAAP accession IDs and obtain that resource separately before molecular modelling. The files do not complete measured aluminium or variety-specific protein structures for the primary panel.

## Acquisition boundary

The identified public Smart-Valleys workbook and complete BAAP data/support packages have been downloaded. Existing CIRAD, Nguyen, Juma, Arbelaez and Bhandari originals were retained. Do not concatenate unrelated studies to claim a complete weather–soil–management–protein forecasting dataset. Missing measurements matched to the primary trials and family-specific protein inputs still have no verified downloadable source in this acquisition.

Next scientific step is a source-by-source quality and identifier audit, with Smart-Valleys unit/provenance confirmation and BAAP yield-basis/genetic matching taking priority. Unavailable trial records still require repository access or an author request. No email was sent.

## Further molecular acquisition: 10 October 2026

### BAAP variants

Downloaded `data/raw/rice/baap_genetics_2018/Aus_Admix_260_99_bi_01_005_beagle.vcf.gz` from Harvard Dataverse, DOI https://doi.org/10.7910/DVN/AUMTIH, file endpoint https://dataverse.harvard.edu/api/access/datafile/3376701. Size 89,354,152 bytes. Publisher MD5 matches and a full gzip read passed integrity checking.

Contains 2,053,863 variant records for 260 samples. The sample names follow n_n labels; all 260 numbers occur among nitrogen-trial BAAP IDs. This is a candidate linkage, not yet an independently verified accession crosswalk. The 300-ID nitrogen panel is not fully covered. The VCF labels REF alleles as provisional, explicitly warning they may not be real genome reference alleles. Genome assembly, REF/ALT reconciliation, sample identity and imputation provenance must be checked before coding-effect or protein reconstruction. Only the VCF was downloaded; the larger TGZ is an alternative representation and was not needed as a duplicate. The source download manifest records SHA256 and caveats.

### Ptr gene supplements

Downloaded all 11 CSV files listed in Zenodo record https://zenodo.org/records/20025230, plus repository metadata. Each file matches its repository MD5. Files are in `data/raw/rice/ptr_gene_2026/`. The associated article is https://pmc.ncbi.nlm.nih.gov/articles/PMC13492586/.

Table S2 contains 101 accession rows with two diagnostic SNP calls, H1/H2 haplotypes and blast-response information for some entries. There are 40 candidate matches to our primary accession table using punctuation-insensitive designation/line/derivative aliases; 32 candidates carry H1 and eight H2. The candidate map is `data/processed/rice/ptr_candidate_identity_matches.csv`. It is not an approved model join: the table has names rather than primary GIDs, and punctuation removal can disguise biological identity differences. Confirm pedigrees, sample origins and synonym mappings. The two diagnostic SNPs are not automatically the causal coding variant.

This is a promising gene-informed feature source, not complete protein sequences or structures and not aluminium tolerance measurements. Do not assign the same gene haplotype to unmatched varieties or infer absence from missing rows. Study-level disease phenotypes measured separately cannot be treated as disease exposure in our yield trials. Any analysis restricted to the matched subset needs coverage and selection-bias reporting.

### Current boundary

The new molecular downloads strengthen candidate genetic linkage. They do not supply original multi-environment trial soil/aluminium/management records or full variety-specific proteins. These remain unavailable or unverified after this acquisition. No model was trained and no source datasets were concatenated. Author/repository access is still required for those original trial records; no email has been sent.

## Soil summaries and published Ptr alleles: 11 October 2026

### CIRAD soil measurements acquired

Original article XML is stored in `data/raw/rice/cirad_aluminium_2024/journal.pone.0307009.xml`, downloaded from the publisher. Table 1 was extracted into `data/processed/rice/cirad_aluminium/soil_condition_summaries.csv`: means and standard deviations for pH, organic matter, P, Ca, Mg, K, Al and aluminium saturation. Units and 0–20 cm sampling depth are recorded exactly as published; each condition summary represents six soil samples. Raw individual sample values and plot assignments are not available in this table. Al units were retained as cmol/dm3 without adding a charge subscript not shown in the source.

ALU means: pH 4.39, Al 2.32 cmol/dm3, aluminium saturation 35.17%. LIM means: pH 5.19, Al 0.53 cmol/dm3, aluminium saturation 7.35%. These summaries link to CIRAD outcomes by ALU/LIM only. They are not measurements for Nguyen environments and cannot establish independent effects of pH, Al and the other nutrients with only two condition profiles.

### Published Ptr coding alleles acquired

The 2018 Ptr discovery article (https://www.nature.com/articles/s41467-018-04369-4) identifies GenBank coding records MG385187–MG385192. Downloaded these records as `data/raw/rice/ptr_alleles_2018/Ptr_coding_records_MG385187_MG385192.gb`. Recorded source URL and SHA256 in its download manifest. All six contain annotated protein translations, extracted unchanged into `data/processed/rice/ptr_alleles_2018/published_protein_translations.fasta`, with a cultivar catalogue.

Cultivars and annotated lengths: Katy 905 aa; PINo.1 909 aa; PI4 905 aa; YT16 909 aa; Amane 909 aa; BHA 909 aa. These are real published allele sequences suitable for an ESM feasibility comparison. There are no exact punctuation-normalised cultivar matches to the primary accession metadata. Therefore they have not been attached to the primary yield rows. No reference allele was mutated to manufacture trial-variety sequences. Partial SNP/haplotype matches cannot guarantee complete protein sequence identity.

### Remaining boundary

Condition-level measured soil data are now acquired for CIRAD, and multiple published Ptr protein alleles are available. The complete embedding-based forecasting dataset is still not assembled: full allele assignments to the actual yield genotypes, original primary-trial soil/management records, and suitable observed damage labels remain missing or unverified. Model weights were not downloaded yet: they cannot supply missing biological input assignments. Author or repository access remains necessary for these matched records; no message has been sent.
