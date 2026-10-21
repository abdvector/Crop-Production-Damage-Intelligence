# Management and additional-trial data search

Checked 11 October 2026. This search does not identify every possible public source.

## Exact primary measurements

The Nguyen supplements provide dates, establishment methods, source spacing, phenotypes, markers and environmental covariates. No verified trial-linked irrigation amounts, fertiliser rates or soil analyses were identified. Table S2 spacing headers have no explicit units; the direct-seeded trial lacks hill spacing. Physical density also requires plant/hill information.

Juma's agronomic table describes overlapping locations/seasons. Its breeding-value table is not new independent plot harvests with matched dates and management. These values were not appended as fresh yield observations.

The [consolidated request](Consolidated_Rice_Data_Request.md) covers missing linked measurements and spacing clarification. No author has been messaged. Primary measurement gaps remain unresolved.

## Acquired supporting disease data

[Zenodo 3889800](https://zenodo.org/records/3889800), *Data for Do Alternate Wetting and Drying Irrigation Technology and Nitrogen Rates Affect Rice Sheath Blight?* The request to record 3889799 resolved to this version. All ten files match publisher MD5 checksums; download URLs and SHA-256 hashes are retained in `data/raw/rice/awd_nitrogen_2020/`.

One descriptor and nine CSVs contain 6,768 repeated hill/tiller observations from 2015 and 2016, with water labels AWD/PDL, nitrogen labels, replicates and observed disease measurements. These are not 6,768 independent plots. No grain-yield columns, primary genotype mapping or measured primary soil/Al were identified. The descriptor treats the years as separate experiments because designs and inoculation changed; reconcile treatment codes before assigning absolute nitrogen rates.

This can support a separate observed-disease study, but cannot fill the primary panel's missing management or yield fields. Audit: `data/processed/rice/management_source_audit/awd_nitrogen_audit.json`.

## Sources requiring permission

[IRRI LTCCE 1974](https://doi.org/10.7910/DVN/W2H2SL): metadata were saved to `data/raw/rice/irri_ltcce_1974/repository_metadata.json`. All three season tables and ReadMe are restricted; the API returned HTTP 403. No experimental table was downloaded or access restriction bypassed.

[NSW rice agronomy experiments](https://data.iar.dpi.nsw.gov.au/dataset/rice_agronomy_experiment_results) describes sites, seasons, sowing methods and nitrogen treatments, but its official listing says it is not approved for open data. No table was acquired.

## Remaining requirement

Obtain records linking harvest yield and moisture basis, accession identity, site coordinates, dates, management amounts and measured soil for the same trials. Verify overlap and identifiers before combining sources. Generic genomes and district soil maps cannot supply missing experimental measurements. Additional independent environments remain needed for external evaluation.
