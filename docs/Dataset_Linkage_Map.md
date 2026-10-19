# Verified dataset linkage map

Prepared 11 October 2026. No new source downloads, protein assignments, model training or application changes were made during this map audit.

## What links now

| Component | Finding | Status |
| --- | --- | --- |
| Yield plus markers plus archived weather | 1046 eligible records, 107 yield genotypes, 15 environments | Available for benchmark construction after cutoff/split decisions |
| Juma to Nguyen genetic identities | 66 shared GIDs; 44948 matching A/C/G/T calls and zero discordances | Strong support for these shared GIDs; no full protein sequences inferred |
| Ptr candidate aliases | 40 metadata genotypes, of which 38 have yield records | Candidate identity links only |
| Eligible yield records with Ptr candidates | 387 | Potential subset, not embedding-ready |
| Verified complete protein sequences linked to primary yield genotypes | 0 | Unavailable/unconfirmed |
| Trial-linked soil/aluminium/detailed management | 0 primary environments | Unavailable/unconfirmed |
| Observed damage labels in primary trials | None identified | Yield-risk proxy must be defined or new labels obtained |

The complete baseline archive includes post-cutoff weather. Available records do not mean the forecast features or train/test split are already ready. Published yield adjustment and repeated-key limitations remain as documented in Rice_Data_Audit.md.

## Files to inspect or attach to the author request

All maps are in `data/processed/rice/dataset_map/`:

- `genotype_availability.csv`: all 111 metadata genotypes, yield counts, marker availability, candidate Ptr aliases and unverified protein status. Four metadata lines lack the acquired marker/yield representation. No protein sequence has been assigned.
- `environment_availability.csv`: the 15 trials, dates/coordinates, weather coverage and missing soil/Al/management/damage status.
- `yield_record_availability.csv`: all 1,056 original yield source rows, including ambiguity flags and linked input status. Ten ambiguous rows are not marked baseline-available.
- `juma_marker_concordance.csv`: per-GID counts at shared exact marker IDs. Only A/C/G/T calls were compared; ambiguity/missing codes were excluded, not silently imputed. This nucleotide agreement does not prove complete genomic or protein identity.
- `summary.json`: aggregate counts and limitations.

These are availability maps, not a new concatenated modelling dataset. Raw values remain in the original files.

## Molecular identity decision

Neither Chr12:10,833,400 nor Chr12:10,845,095 occurs in our 882-marker table. Therefore the primary marker panel cannot independently verify the diagnostic Ptr calls. The downloaded 2026 study lists accessions by name rather than our GIDs. Matching designation/line/derivative names produces candidates, but confirming source sample identity and full alleles remains necessary. Both candidate H1/H2 groups occur; this alone does not establish complete protein sequences.

The six GenBank Ptr proteins belong to named cultivars with no exact normalised-name matches in primary metadata. They support reference-level ESM feasibility, not primary-variety prediction. STAR1/STAR2 references are also not assigned to trial varieties.

## Study boundaries

CIRAD soil summaries can link to its own records by ALU/LIM only. They cannot populate Nguyen soil columns. BAAP variants have 260 numeric ID candidates in its nitrogen panel, but accession crosswalk and provisional REF alleles still require reconciliation. Smart-Valleys broad variety labels do not establish molecular accession links. Bhandari IDs and moisture basis also require separate handling.

## One remaining request

Use `Consolidated_Rice_Data_Request.md` as the current request. It asks for the unavailable linked records and source crosswalks, and asks providers to identify unmeasured fields. No email has been sent. An author's confirmation or traceable repository mapping is needed before promoting candidates into verified protein inputs.

The benchmark has subsequently been implemented and evaluated at a 60-day cutoff; see [Rice_Baseline_Results.md](Rice_Baseline_Results.md). Its combined model does not beat the mean baseline at held-out locations. The full molecular/soil model remains conditional on the requested links and measurements. Existing structures/sequence embeddings are explanatory features; the project does not forecast protein structure. Low yield, observed disease damage and causal aluminium loss are distinct targets and must not be conflated.


## Protein-context update, 20 October 2026

The complete-cultivar-sequence count above remains zero. A new [reference-protein linkage audit](Rice_Molecular_Linkage_Audit.md) now establishes 89 measured canonical protein-altering SNPs linked to all 107 trial genotypes and 1,046 eligible yield rows. Eleven measured markers map exactly to predicted reference structures in a 20-pair sample; six sites have local pLDDT at least 70 and exploratory geometry descriptors. The subsequent [controlled protein-context comparison](Rice_Protein_Context_Experiment.md) trained and evaluated those representations without establishing improved yield prediction. Full cultivar sequences were not assigned.

The [current predictor linkage audit](Rice_Predictor_Linkage_Audit.md) separately verifies district, field and trial joins and sets the next data priority: official season-specific rice labels with compatible district geography and dated predictor availability.
