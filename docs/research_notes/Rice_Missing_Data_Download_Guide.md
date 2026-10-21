# Rice missing-data download guide

Checked 9 October 2026. This guide follows the acquisition audit in `Rice_Data_Audit.md`.

## Download these two files first

These are relevant supplementary workbooks, not a complete replacement for the missing soil, management and protein data. Their article descriptions and direct download links were verified. Both workbooks were manually downloaded by the user, inspected locally on 9 October 2026, and moved into the destinations below. Their XLSX archive integrity passed, expected supplementary sheets were present, and SHA256 checksums were unchanged after moving. Source URLs and local checksums are recorded in each folder's `download_manifest.json`.

### 1. Original elite-panel workbook

Paper: Juma et al. (2021), *Identification of an Elite Core Panel as a Key Breeding Resource to Accelerate the Rate of Genetic Improvement for Irrigated Rice*.

- [Article](https://doi.org/10.1186/s12284-021-00533-5)
- [Download Additional file 1](https://media.springernature.com/original/springer-static/esm/art%3A10.1186%2Fs12284-021-00533-5/MediaObjects/12284_2021_533_MOESM1_ESM.xlsx)
- Exact filename: `12284_2021_533_MOESM1_ESM.xlsx`
- Approximate published size: 5 MB.
- Verified location: `data/raw/rice/juma_2021/`.

If the direct link does not download, open the article, scroll to Supplementary Information, and select Additional file 1 (XLSX).

Important tables to inspect:

| Table | Why it matters |
| --- | --- |
| S1 | GIDs, designations, pedigree and panel membership for matching identities |
| S2 | Genotypes for 66 elite-panel lines and 10 IRRI varieties at 703 SNPs |
| S3 | Information on 37 high-value genes and favourable allele frequencies where available |
| S7 | Related regional trial information |

This is a related panel, not automatically identical to the 107 genotypes in our primary dataset. The initial audit found 66 exact GID matches between its 76 genotyped entries and our 107 genotypes. All 703 of its marker coordinates occur in our marker table. Allele, assembly and sample concordance still need reconciliation before merging. Gene frequencies for an entire panel cannot be assigned to individual varieties as their alleles. Breeding values in S1 are not interchangeable with observed environment-specific yields.

### 2. Genetic-assay annotation workbook

Paper: Arbelaez et al. (2019), *1k-RiCA (1K-Rice Custom Amplicon) a novel genotyping amplicon-based SNP assay for genetics and breeding applications in rice*.

- [Article](https://doi.org/10.1186/s12284-019-0311-0)
- [Download Additional file 1](https://media.springernature.com/original/springer-static/esm/art%3A10.1186%2Fs12284-019-0311-0/MediaObjects/12284_2019_311_MOESM1_ESM.xlsx)
- Exact filename: `12284_2019_311_MOESM1_ESM.xlsx`
- Approximate published size: 8.7 MB.
- Verified location: `data/raw/rice/arbelaez_2019/`.

If the direct link fails, open the article, scroll to Additional files, and select Additional file 1 (XLSX).

Start with S3, the list of 995 assay SNPs. The paper describes 28 trait-associated markers across 11 genes/QTLs, including SUB1A, GS3, Waxy and disease-resistance loci. Compare their chromosome and position against our 882 markers, checking genome assembly, allele definitions and strand orientation. Then inspect which overlapping loci actually vary across our 107 genotypes.

Do not assume all 28 were retained in the primary dataset. A marker linked to a gene is not automatically a protein-changing mutation. This workbook could support biologically annotated genetic features, but it does not establish variety-specific protein structures or aluminium exposure.

Keep both workbooks in their original form. Do not manually delete rows, rename accessions or change spreadsheet values before the matching audit. No scripts need to be created for downloading them.

## What is not solved by manual downloading

The acquired Nguyen et al. (2023) files do not provide measured trial soil/aluminium values, detailed fertiliser rates or irrigation histories. The associated Juma paper and publicly described supplements did not reveal a download for those same missing measurements during this search. This means no matched public download was identified, not that such records cannot exist.

The next route is to request the original trial records or a repository location from the corresponding author. [Nguyen et al. article](https://doi.org/10.1186/s12284-023-00623-6) lists Jérôme Bartholomé, `jerome.bartholome@cirad.fr`. Verify the contact on the article before sending. No message has been sent.

### Current consolidated request

Use [Consolidated_Rice_Data_Request.md](Consolidated_Rice_Data_Request.md), prepared 11 October 2026. It supersedes the earlier draft and includes verified GID concordance, current molecular gaps, exact trial attachments and optional CIRAD clarification. No message has been sent. See [Dataset_Linkage_Map.md](Dataset_Linkage_Map.md) for the completed availability audit.

## Genomic portals: current access findings

- The [IRRI SNP-Seek landing page](https://snp-seek.irri.org/) currently reports a service interruption and directs users to [snp-seek.org](https://snp-seek.org/).
- The mirror's [3K interface](https://snp-seek.org/3kRG/) was reachable but requires JavaScript. The 19K endpoint returned HTTP 401 during this check. That does not establish whether account-based access is available.
- The [IRIC dataset catalogue](https://iric.irri.org/resources/snp-seek-datasets) describes an IRRI elite-lines panel of 169 genotypes, which is a promising identity-matching lead. Its linked elite-panel and grain-quality metadata URLs returned HTTP 410 through web retrieval. No sample mapping or variant download from those panels has been verified.
- [3K project information](https://iric.irri.org/projects/3000-rice-genomes-project) provides sequencing-data routes, but do not download bulk raw reads. First confirm that the trial accessions are present, select relevant gene regions, and match genome assemblies and sample identities.
- [TropGene](https://tropgenedb.cirad.fr/tropgene/JSP/interface.jsp?module=RICE) is the marker route for the separate Bhandari dataset. Its accessions and single-site drought trials need a separate identity audit. Downloading its markers would not fill the primary dataset's soil or management gaps.

## Local inspection completed; next matching checks

1. Completed: archive integrity, expected sheet contents, source-specific placement and local SHA256 records. See `data/processed/rice/supplementary_workbook_audit.json` for the initial overlap counts.
2. Match panel GIDs and aliases against the existing accession table.
3. Join marker annotations by verified assembly/chromosome/position, not by approximate gene names.
4. Separate causal/functional variants from merely linked markers and reference annotations.
5. Determine whether variable genetic features can be used now, and whether protein-changing variants still require author or sequence-repository data.

The Arbelaez S3 sheet contains 995 annotation rows and shares 879 exact marker IDs with our marker table. Its 28 trait-marker rows have blank values in the dedicated position column; 18 share marker IDs with our dataset. The coordinates encoded in their IDs must be reconciled with reference assemblies before a biological join. Juma S3 reports panel-level gene frequencies, while S5/S6 also contain line-level disease-test results and reported favourable genes; these require identity and provenance checks rather than assigning panel frequencies to individual lines.

The molecular contribution remains a hypothesis. The existing weather-plus-genetics benchmark is feasible, but the full soil/management/protein forecasting dataset remains incomplete.

## Follow-up acquisition search: 9 October 2026

After the two manual downloads, the publisher's Nguyen and Juma articles and the official IRIC dataset catalogue were rechecked for the remaining inputs. Both articles point to their published supplements in their data-availability statements. No additional downloadable measured soil/aluminium, detailed fertiliser/irrigation, or original plot records matched to the 15 primary environments were identified in this search. This is a search result, not proof that the records do not exist.

The official IRIC catalogue describes an IRRI Elite Lines panel of 169 genotypes drawn from irrigated and rainfed breeding programs, including elite core panels. Its linked metadata URL again failed through web retrieval with HTTP 410. The catalogue alone does not establish which of our 107 lines have retrievable whole-genome variants.

The official Global Rice Array page also advertises whole-genome variants for an Antenna panel of 59 samples, plus a separate MAGIC reference panel. Its sample worksheet could not be fetched through web retrieval. No sample overlap with the primary panel has been established; therefore its bulk variant archives were not acquired as substitutes for the required matched data.

Sources checked:

- https://link.springer.com/article/10.1186/s12284-023-00623-6
- https://link.springer.com/article/10.1186/s12284-021-00533-5
- https://iric.irri.org/resources/snp-seek-datasets
- https://sites.google.com/irri.org/globalricearray/data

No new dataset was downloaded during this follow-up. The next acquisition step for the full intended model is the author request drafted above: obtain matched trial measurements, original plot records, and a GID-to-sequence/variant crosswalk or repository location. Sending that request remains for the user; no email has been sent. The complete intended dataset remains unavailable locally.
