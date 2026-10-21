# Indian rice field-survey audit

Audit date: 13 October 2026.

Source: [Nayak et al. (2024), Nature Communications](https://doi.org/10.1038/s41467-024-52448-6). The publisher Supplementary Data 1–2 ZIP was downloaded and passed ZIP CRC checks. Source URLs, sizes and SHA-256 hashes are in `data/processed/rice/india_field_survey/source_manifest.json`.

## What was acquired

| R object | Year | Raw rows | Columns | Distinct reported variety labels |
| --- | ---: | ---: | ---: | ---: |
| rice_2017 | 2017 | 6,192 | 253 | 121 |
| data | 2018 | 7,443 | 302 | 501 |
| data1 | 2019 | 4,227 | 264 | 76 |

There are 17,862 raw survey records, spanning 92 distinct state/district label combinations. One record is labelled maize. 17,855 records are labelled rice with finite positive reported yields. These are source counts, not the paper's filtered analysis sample of 15,876. The published filters have not been reproduced; raw records include Punjab in addition to the paper's seven states. Variety-label counts do not establish distinct genotypes.

The archive also includes `.Random.seed` and a separate RData file containing the authors' fitted model and Shapley results. Neither is used as our observations, predictors or evaluation results. Publisher descriptions, supplementary information and the article XML were acquired. Requests for Supplementary Code 1 returned HTML challenge pages; no valid code archive was acquired or executed.

## Normalisation and checks

Yield uses `L.tonPerHectare` in 2017/2018 and `K.tonPerHectare` in 2019, multiplied by 1,000 to obtain kg/ha. The moisture convention is unresolved. These are survey-reported yields; the paper describes crop-cut checks for a subset, but we have not identified that subset in the archive.

Field establishment dates use `seedingSowingTransDate1` in 2017 and `seedingSowingTransDate` in 2018/2019. Harvest dates use `harvestDate1` in 2017 and `harvestDate` in the later objects. The 2017 numeric harvest index is not parsed as a calendar date. Explicit date strings are parsed with their source format; the numeric `Sow` field is not used to reconstruct dates.

For a proposed day-60 forecast, 17,855 rows have positive rice yields, India-range coordinates and establishment/harvest dates consistent with an issue date before harvest. This is a linkage candidate count, not a training-ready count. Coordinate bounds are only a plausibility check, not field-location verification. There are 13,699 distinct coordinate pairs among candidates, and 5,845 rows share a coordinate/year pair with another row. Repeated coordinates can reflect common survey locations, rounding or repeat records; their meaning requires investigation. No within-object survey-instance IDs are duplicated. Thirteen yields exceed 15,000 kg/ha and are flagged for review rather than silently removed.

All original rows are retained in the local normalised table with quality flags. Conversion was checked against all source yield values, record IDs are unique, and year/state coverage reconciles with the source total. This does not validate every reported value or establish independent farms across years.

## Predictor availability and limitations

Planting date, establishment method, reported variety, categorical soil texture and irrigation availability are potential early inputs. Application amounts and timing fields exist, but fertiliser units and missing timing require reconciliation before inclusion. Whole-season fertiliser totals, irrigation counts and sowing-to-harvest weather averages are blocked as early predictors. Harvest dates are for audit only. Retrospective drought/flood/weed/insect/disease severity reports are possible separate ordinal outcomes, not measured percentage yield losses; these severity fields are absent in the 2019 object.

Daily weather through the issue date has been acquired and linked for all 17,855 candidates, with 61 complete dates per field and no missing parameter-days. See the weather protocol and audit for linkage tests and source-resolution limits. The first core regression comparison has subsequently completed; [its report](Rice_Field_Model_Results.md) documents weak temporal transfer and the influence of the pre-existing yield review flags. There are no verified variety-linked protein alleles/sequences or measured field aluminium/pH inputs in this survey. The existing trial benchmark and separate CIRAD aluminium analysis remain available.

## Privacy and reproducibility

Source records include names, phone numbers and other identifiers. The raw archive, exact coordinates and row-level table remain local and are excluded from GitHub. Only aggregate coverage, predictor policy, audit summary, provenance and processing code are published. An independent researcher must obtain the original publisher archive to reproduce the row-level audit. The local raw path is `data/raw/rice/nayak_2024_lcas/Supplementary_Data_1_2.zip`; the local derived table is `data/processed/rice/india_field_survey/field_records_local.csv`.

The optional manual code download is on the source article under Supplementary information → Supplementary Code 1. Save a valid ZIP in the local raw source folder. It helps reconcile publisher filtering and units; it is not necessary to inspect the raw observations and is not a prerequisite for our own independent model design.
