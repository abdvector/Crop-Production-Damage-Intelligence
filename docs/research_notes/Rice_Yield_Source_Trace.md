# Source yield trace and unresolved unit review

All 17,862 normalised project yields match the publisher's tonnes-per-hectare column multiplied by 1,000, including missing/nonpositive records retained for audit. **The extreme labels were not introduced by our conversion.** The original model selection, primary assessment and row-level predictions remain unchanged, with hashes checked before and after this investigation.

## Evidence from the raw publisher archive

The inspected file is `Data/all_year_data.RData` inside the validated publisher Supplementary Data 1–2 ZIP for [Nayak et al. (2024)](https://doi.org/10.1038/s41467-024-52448-6). Its archive SHA-256 is recorded in `yield_label_trace.json`. Only numeric yield/area columns are used in the review ledger; names, phones and GPS are not exported.

| Year | Raw records | Project conversion agreement | Candidate quantity/area agreement, within 1% and 0.01 t/ha |
| --- | ---: | ---: | ---: |
| 2017 | 6,192 | 6,192 | 1,135 |
| 2018 | 7,443 | 7,443 | 7,021 |
| 2019 | 4,227 | 4,227 | 4,227 |

The candidate arithmetic is reported quantity divided by stored plot acres multiplied by 0.25. The 0.25 corresponds to a quintal-to-tonne factor and the source's approximate 0.4 hectares per acre. This checks stored arithmetic, not actual questionnaire units or respondents' interpretation.

For 2017, the available quantity is `totalGrainYieldQUINTAL`, whereas 2018/2019 have `largestPlotYieldQUNITAL`. The 2017 quantity's scope is unverified: it may not be the quantity underlying the published field-yield label. Its low arithmetic agreement is a reason to obtain the questionnaire/source processing definitions, not evidence that 5,057 yield labels are necessarily wrong.

For 2018, `L.quintalPerAcre × 0.25` agrees with 7,440 of 7,443 tonne-per-hectare values at a 0.0051 tolerance. At a wider 0.051 tolerance allowing one-decimal rounding, 7,441 agree. The remaining two need clarification about author corrections or source semantics; their labels are not overwritten. Disagreement between raw plot quantities and target values may reflect curation, rounding or reporting differences, which are not established here.

## The 13 pre-existing 2019 review flags

All 13 yield labels above the previously declared 15,000 kg/ha review threshold reconcile with their stored quantity and plot acreage. Seven records have quantities of 1,400–2,400 in `largestPlotYieldQUNITAL`, a column labelled as quintals. The source consequently reports 350–400 t/ha for those seven records.

Example: reported quantity 2,400 and plot area 1.5 acres produce 1,600 quintals/acre and 400 tonnes/ha under the source arithmetic, then 400,000 kg/ha in our normalised table. If 2,400 actually meant kilograms, a factor-of-100 unit problem could explain the scale. **That interpretation is a hypothesis and has not been verified.** We do not divide those labels by 100 or use guessed replacements for modelling.

The other six flags have reported quantities below 1,000 and source yields of roughly 17.06–60 t/ha. A single universal correction is not supported. Quantity errors, acreage errors, field-versus-farm scope and legitimate source edits must be investigated separately. A threshold flag is not a validated biological exclusion.

The local `yield_review_local.csv` contains source-object/row references, numeric quantities and areas, calculation results and unresolved status for all 13 records. It contains no personal names, contact fields or exact coordinates and remains excluded from GitHub. It is a review ledger, not a corrected training dataset. Aggregate traces and preserved-result hashes are published.

## What remains unresolved

The [2018 source survey article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9679526/) identifies accompanying variable definitions, ODK Build files and code in the [CIMMYT repository](https://data.cimmyt.org/dataset.xhtml?persistentId=hdl:11529/10548656). The user has now supplied the 2018 codebook, guide, variable workbook and descriptive HTML report. The [documentation review](Rice_Survey_Documentation_Review.md) records quintal-versus-kilogram and reciprocal land-conversion conflicts. A 2018 form alone does not establish unchanged 2017/2019 definitions or confirm what a respondent entered in an individual record.

The received files are stored in `data/raw/rice/cimmyt_2018_documentation/`. The HTML summarises an existing CSV and contains no complete correction procedure. The remaining evidence needed is year-specific 2017/2019 definitions, the relevant processing/curation code, or author-confirmed corrected records. The 2018 product-amount and timing definitions can support a separately audited 2018 management preparation step. Additional precise GPS or another full dataset copy is not needed for this check. No email has been sent.

Until evidence confirms corrections, retain source labels and the existing results. Any later correction must record source row, old/new value, evidence and rationale. A revised analysis must be identified as a revised analysis of an opened test; the 2019 data cannot become an untouched assessment again. The weaker performance on the unflagged diagnostic subset also remains an unresolved model-transfer problem.

## Checks and reproduction

`src/rice_field_labels.py` provides `trace_source_yields(objects, archive_path)`. It accepts the publisher RData objects, verifies all project/source conversions, writes the local unresolved review ledger and public aggregate trace, and verifies the original assessment hashes. It never modifies labels or fits a model. The temporary R-reader runtime is removed after inspection; there is no retained audit launcher. `app.py` displays the trace inside Yield-label quality diagnostic.
