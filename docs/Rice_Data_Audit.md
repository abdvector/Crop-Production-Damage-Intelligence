# Rice data acquisition and feasibility audit

Prepared 9 October 2026. Department of Quantitative Economics and Data Science. Guide: Dr. Manish Kumar Pandey.

## Decision

The downloaded data provide a defensible starting point for predicting rice variety yield across trial environments. They do not yet support the full proposed model combining soil, management, measured aluminium exposure and variety-specific protein structure. No rice model has been trained and no economic benefit has been estimated.

Use the Nguyen et al. dataset as the primary candidate for initial environmental and genetic benchmarking. Its advantages are linked genotype identifiers, multiple locations, accessible marker calls, trial coordinates and dates. Continue molecular and soil feasibility work before fixing the final model specification. The existing wheat application and simulated dataset have not been converted into a real rice model by this acquisition.

## Primary dataset

Nguyen et al. (2023), *Multi-environment Genomic Selection in Rice Elite Breeding Lines*, Rice 16:7. [Article and methods](https://doi.org/10.1186/s12284-023-00623-6).

Downloaded original supplementary files:

| File | Content |
| --- | --- |
| `data/raw/rice/nguyen_2023/12284_2023_623_MOESM1_ESM.xlsx` | Accession identities, trial locations, coordinates, establishment dates and technical information |
| `data/raw/rice/nguyen_2023/12284_2023_623_MOESM3_ESM.txt` | HapMap nucleotide calls for 107 rice genotypes at 882 SNP markers |
| `data/raw/rice/nguyen_2023/12284_2023_623_MOESM4_ESM.csv` | Published yield, flowering and plant-height values |
| `data/raw/rice/nguyen_2023/12284_2023_623_MOESM5_ESM.csv` | 24 environmental covariates per trial, covering vegetative, reproductive and ripening phases |

The raw directory contains a download manifest recording source URLs, retrieval times, file sizes and SHA-256 checksums. Originals are preserved unchanged. Supplementary downloads are linked under the article's supplementary information; [the repository copy of Additional file 1](https://springernature.figshare.com/articles/dataset/26567243) is another manual access route.

### Verified local counts

| Measure | Count |
| --- | ---: |
| Original yield entries | 1,056 |
| Yield entries flagged for conflicting repeated keys | 10 |
| Entries passing the repeated-key check | 1,046 |
| Genotypes with marker data | 107 |
| SNP markers | 882 |
| Trial environments, defined by location, year and season | 15 |
| Distinct locations | 12 |
| Countries | 6 |
| Trial years | 2018–2020 |
| Retrieved daily weather records | 2,032 |

Countries are Bangladesh, India, Kenya, Mozambique, the Philippines and Tanzania. This is an irrigated breeding-trial panel; it is not a representative sample of all Indian rice farms or rainfed systems. A thousand variety–environment records do not constitute a thousand independent environments: there are only 15 environments.

### Target definition

The original yield unit is tonnes/ha. Prepared data multiply these values by 1,000 to obtain kg/ha. The study standardised harvested grain to 14% moisture.

Most published labels are trial-level adjusted phenotypes, obtained using mixed models and BLUPs. They are derived from measured harvests, but they are not the original plot measurements. The methods also state that unreplicated trials used phenotypic values directly. The source descriptions of unreplicated trials do not identify the Hyderabad year consistently enough to assign a precise adjustment method to each row without clarification, so prepared data retain a general target-kind label.

Performance against these adjusted labels must not be presented as independently validated farm-harvest accuracy. For stronger validation, seek original plot yields, experimental-design records and adjustment uncertainties. Do not recompute trial adjustment jointly across training and test outcomes.

### Conflicting keys

GID `4016512`, identified in Table S1 as IRRI 154, occurs twice with different yields in each of five environments:

| Environment | First yield (t/ha) | Second yield (t/ha) |
| --- | ---: | ---: |
| BD_GZ_19W | 3.6930 | 3.9373 |
| BD_NM_19W | 5.6500 | 4.3400 |
| MZ_CK_20W | 6.3804 | 6.1070 |
| MZ_MP_20W | 4.6891 | 4.8656 |
| TZ_DK_20W | 5.5213 | 5.6348 |

Both entries of each conflicting key remain in the audited table, with original CSV row numbers. All ten are marked ineligible pending clarification. They were not averaged, relabelled, or treated as independent replicates. The remaining 1,046 entries pass this key check; this does not certify every aspect of their measurement quality.

## Daily weather acquisition

Daily records were retrieved from the [NASA POWER daily point API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) using the original Table S2 trial coordinates, from seeding through the recorded harvest date, in local solar time (LST). Original responses and their request URLs are retained in `data/raw/rice/nasa_power/`.

| Prepared field | NASA parameter | Unit |
| --- | --- | --- |
| temperature_mean_c | T2M | degrees C |
| temperature_min_c | T2M_MIN | degrees C |
| temperature_max_c | T2M_MAX | degrees C |
| precipitation_mm_day | PRECTOTCORR | mm/day |
| relative_humidity_percent | RH2M | percent |
| solar_radiation_mj_m2_day | ALLSKY_SFC_SW_DWN | MJ/m2/day |
| wind_speed_2m_m_s | WS2M | m/s |

These are gridded, observation-informed products, not trial-plot weather-station measurements. Current API downloads need not reproduce the historical paper's processed covariates exactly.

Checks confirmed complete daily date coverage for all 15 environments, zero missing/fill values for the seven retrieved parameters, minimum temperature no greater than maximum temperature, nonnegative rainfall and radiation, and humidity between 0 and 100 percent. These are consistency checks, not independent verification of weather accuracy.

## Molecular references

Downloaded reviewed UniProt annotations and sequences:

| Gene | Accession | Reference sequence length |
| --- | --- | ---: |
| STAR1 | [Q0D9V6](https://www.uniprot.org/uniprotkb/Q0D9V6/entry) | 346 amino acids |
| STAR2 | [Q5W7C1](https://www.uniprot.org/uniprotkb/Q5W7C1/entry) | 285 amino acids |

Reference JSON annotations, FASTA sequences, AlphaFold metadata and predicted PDB structures are in `data/raw/rice/molecular_reference/`, with a download manifest. These references belong to *Oryza sativa* subsp. *japonica*. The primary trial panel is indica. Therefore, they must not be assigned to its trial varieties as their actual protein sequences.

The structures are predictions, not experimentally determined structures. Structural confidence is not crop resistance. Before structural interpretation, inspect confidence and alignment uncertainty; before using any molecular feature as an X, establish verified sequence variation linked to each trial genotype. The 882-marker panel does not provide complete protein-coding sequences. It cannot automatically reconstruct STAR1/STAR2 alleles or other proteins. ART1 was not retrieved by the exact-gene UniProt search and no substitute accession was guessed.

## First candidate: supporting material

Bhandari et al. (2019), *Selection of trait-specific markers and multi-environment models improve genomic predictive ability in rice*. [Article](https://doi.org/10.1371/journal.pone.0208871). Its original S1 workbook is downloaded in `data/raw/rice/bhandari_2019/`.

Inspection found 280 distinct study identifiers of the form `RP...`, with 275 numeric yield values under non-drought conditions and 204 in each drought treatment. These are adjusted yields at 12.5% moisture. The treatments were conducted at one IRRI station in the 2015 dry season, so this is useful stress-response evidence but limited for geographic transfer validation.

The workbook has repeated GIDs across distinct RP accessions. Use the study/accession identifiers and resolve mapping before joining genetics; a simple GID join could incorrectly merge different entries. Missing stress outcomes must not be converted to zeros without evidence: the paper describes reproductive failure under severe drought, which makes missingness potentially informative.

The cited [TropGene repository](https://tropgenedb.cirad.fr/tropgene/JSP/interface.jsp?module=RICE) identifies GS-Ruse marker sets. Its page was readable through web retrieval, but the direct Python connection failed certificate verification. Those genetic files have not been downloaded. Manual navigation is possible through STUDIES, study type Genotypes, GS-Ruse; accessibility and exact identifier matching still require checking.

Keep this source separate from the primary dataset. Do not concatenate different moisture bases, yield-adjustment methods or accession identities without reconciliation.

## Prepared tables

Files are in `data/processed/rice/`:

| File | Role |
| --- | --- |
| yield_observations_audited.csv | All primary yield entries, original source row, converted yield, trial metadata and ambiguity flags |
| trial_metadata.csv | 15 trial locations, establishment information, coordinates and dates |
| accession_metadata.csv | Original panel identities and aliases |
| genotype_marker_calls.csv | Transposed nucleotide calls, one genotype per row |
| marker_metadata.csv | Original marker identity, alleles, chromosome and position |
| daily_weather.csv | Daily weather joined by environment ID and date |
| weather_coverage.csv | Expected days, retrieved days and missing-value counts per trial |
| audit_summary.json | Machine-readable verified counts and feasibility gaps |

Yield rows join to markers using `genotype_id`, and to daily weather using `environment_id`. Daily weather is a separate repeated-measures table: expanding a yield row over days does not produce independent yield labels. All 1,056 yield genotype IDs match both the marker table and accession metadata.

No marker imputation, feature selection, PCA, fitting or train/test split has been performed. Source-marker nucleotide calls are preserved, rather than converted into arbitrary protein-resilience scores.

## Input availability and remaining gaps

| Input group | Status | Decision |
| --- | --- | --- |
| Yield labels | Acquired, mainly adjusted trial phenotypes | Suitable for an initial benchmark with explicit target limitations |
| Weather | Seven daily variables acquired | Derive features only up to a chosen forecast cutoff |
| Genetics | 882 linked markers acquired | Available for genetic benchmarks; not protein structures |
| Establishment method and dates | Acquired | Available before forecast issue where recorded accurately |
| Row/hill spacing | Present in source | Confirm units and interpretation before feature construction |
| Fertiliser rates and irrigation amounts | Not provided in the acquired files | Seek original trial management records; do not fabricate |
| Measured soil properties | Not provided | Seek site/plot soil measurements matched to trial depth and date |
| Aluminium exposure | Not provided | Cannot infer exchangeable Al or Al saturation from pH alone |
| Variety-specific proteins and functional variants | Not acquired | Establish accession-to-sequence/variant linkage first |
| Independent harvest validation | Not acquired | Needed before deployment or farm-level accuracy claims |

[SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html) could provide modelled regional soil context, not measured trial soil or aluminium exposure. Its [official FAQ](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_04.html) advises against local/farm-level use. It was not substituted for field measurements in these prepared data.

## Forecasting and validation requirements

1. Choose the prediction issue date before constructing features. The archived weather extends through harvest for research completeness; later weather must not enter an earlier forecast as if already observed.
2. The paper's phase covariates use observed flowering/harvest timing and full-season weather. Retain them for retrospective comparisons only unless their availability at forecast time is established. Final plant height and future flowering dates are not automatically eligible predictors.
3. Training-only preprocessing must include imputation, scaling, genetic dimension reduction, variant selection and feature selection. Keep the final test outcomes untouched.
4. Compare a simple baseline, regularised regression and suitable nonlinear/genetic benchmarks before choosing a model. There are only 15 independent environments, so a large feature collection can overfit despite the number of variety observations.
5. Test unseen locations separately from unseen location-year-season environments; withholding one environment at a previously seen location does not establish transfer to a new location. Also evaluate unseen genotypes and forward-year prediction when feasible.
6. Years and geography are confounded: 2018 is represented by one Hyderabad environment and 2020 by African trials. Year holdouts also change geography. Report this limitation rather than claiming broad temporal reliability.
7. Report MAE/RMSE in kg/ha, bias, prediction-interval coverage, subgroup performance and residual diagnostics. These assess reliability within the tested scope; they do not prove the absence of misspecification or causal effects.

The next scientific task is to establish missing genotype-to-protein and soil/management links. A model combining those inputs must wait for linked evidence. The downloaded primary dataset can support an initial environmental-plus-genetic benchmark while those gaps are investigated.


## Manually acquired supplementary workbooks: 9 October 2026

The user supplied the two recommended publisher workbooks. Both passed XLSX archive CRC checks, opened with the expected supplementary sheets, and were moved without editing; pre/post-move SHA256 hashes matched. Each source folder contains a `download_manifest.json` with the DOI, publisher URL, byte count and local checksum. No independent publisher checksum was available for this inspection.

| Source | Stored original | Contents confirmed |
| --- | --- | --- |
| Arbelaez et al. (2019), DOI 10.1186/s12284-019-0311-0 | `data/raw/rice/arbelaez_2019/12284_2019_311_MOESM1_ESM.xlsx` | Eight sheets: accession information, pipeline, 995-marker annotation table, HapMap datasets and adjusted means |
| Juma et al. (2021), DOI 10.1186/s12284-021-00533-5 | `data/raw/rice/juma_2021/12284_2021_533_MOESM1_ESM.xlsx` | Seven sheets: historical breeding values, 703 markers for 76 entries, 37-gene information, dosage matrix, blast/BLB evaluations and related trials |

Initial candidate overlap with the Nguyen data:

- Juma genotyped entries: 66 exact GID matches out of our 107 genotypes; all 703 marker chromosome/position pairs occur in our 882-marker table. Historical breeding-value records share 81 exact GIDs. These counts do not establish sample concordance or make breeding values valid observed-yield targets.
- Arbelaez annotations: 879 exact marker-ID matches. Of the 995 rows, 967 have explicit numeric chromosome/position fields, with 863 coordinate matches. The remaining 28 trait-marker rows have blank dedicated position fields, although their marker IDs encode positions; 18 of those marker IDs occur in our dataset. ID and coordinate counts use different matching rules and must not be treated as interchangeable.
- Juma S3 supplies aggregate favourable-allele frequencies, not individual genotypes. S5/S6 contain line-level disease phenotypes and reported favourable genes, which may support additional features after matching and checking how those alleles were established.

Original workbooks were preserved byte-for-byte. An oversized formatted range in Arbelaez's accession sheet is not an accession count. Reading libraries warn about unsupported Excel extensions; no workbook was saved through those libraries. Detailed counts are in `data/processed/rice/supplementary_workbook_audit.json`.

These are correct, relevant supplements. They do not complete measured soil/aluminium, detailed management, or variety-specific protein-structure inputs. No new workbook values have been added to the application or used to fit a model. Next checks are genome assembly, strand and allele reconciliation, sample concordance, and gene-feature availability.
