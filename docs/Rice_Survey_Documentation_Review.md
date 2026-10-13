# Review of the manually downloaded survey documents

All four requested files are correct, readable source documentation. They have been moved, without changing their bytes, to `data/raw/rice/cimmyt_2018_documentation/`. Their formats, sizes, hashes and scope are recorded in `data/processed/rice/india_field_survey/documentation_audit.json`. The originals remain local; aggregate provenance and findings are published. No model was retrained and no yield label was changed.

## What each file provides

| Source | Verified contents | Limit |
| --- | --- | --- |
| LDS_Codebook.pdf | 53-page CropYieldProductionPracticesSurvey2018 form, with question text and saved-value types | Includes multiple crops; a 2018 form does not establish unchanged 2017/2019 definitions |
| LDS_Guideline.pdf | 22-page LDS survey and sampling guide | General guidance with wheat examples; not a record-level correction register |
| Variable_Details.xlsx | Variables sheet with 225 rows including header, four columns describing variable, description, type and unit | Several descriptions/units conflict with the codebook |
| Rice-2018-Markdown.html | Descriptive R report reading the existing rice CSV, reporting categories and yield histogram | No full yield/fertiliser calculation implementation or confirmed row corrections; embedded code was not executed |

## Confirmed 2018 definitions and conflicts

The codebook's page 50 says the total cultivated-land quantity (`q605_totalGrainYieldQUINTAL`) and largest-plot quantity (`q606_largestPlotYieldQUNITAL`) are self-reported in **quintals**. These quantities have different scopes. The variable workbook describes quintals too, but its Unit cells on rows 207–208 say **kilograms**. That is a conflict within the supplied documentation, not confirmation that particular 2019 respondents entered kilograms. It supports investigating unit confusion and prevents a blanket factor-of-100 repair.

Codebook page 4 asks how many local land units equal one acre. Workbook row 19 instead describes acres per local land unit, the reciprocal direction. The earlier source arithmetic generally agrees with dividing local plot area by the conversion factor. Preserve both source descriptions and use the explicit questionnaire and numerical checks when documenting an area conversion; do not silently reverse all source factors.

Codebook pages 19–20 and the fertiliser workbook rows document **kg of fertiliser product per plot**, not kg of nutrient per hectare. Application-day questions refer to days after **field sowing/transplanting**. Page 16 separates nursery establishment (`q414`) from field establishment (`q415`), supporting the field-based cutoff for the documented form. Missing dates remain unknown, and later applications remain excluded from a day-60 predictor.

Irrigation availability on page 29 is access for the largest plot. It is not the quantity or date of a particular irrigation. Soil texture on page 5 is the reported light/medium/heavy category, not a laboratory measurement.

Another mapping caution: page 50 distinguishes a selected harvest date (`harvDate`) from an auto-calculated duration (`q601_harvestDate`), while the workbook describes the latter as a date. The existing pipeline selected actual calendar-date values from the publisher archive and audited date formats; this workbook must not be applied as a blind renaming/conversion rule.

## What this allows next

We now have a documented basis for a **2018-specific** management-feature preparation step: product kg per plot, plot area, and application days after field establishment. Check actual source columns, area inconsistencies, missing dates and version mapping first. Converting to kg/ha requires a documented hectare conversion; converting product mass to nutrient mass additionally requires verified product composition. This review does not establish nutrient totals for every row.

The 2017 total-grain field likely has a different scope from a largest-plot quantity, based on the analogous 2018 definition; that remains a cross-year inference until the 2017 form or processing code confirms it. The 2019 extreme yields remain unresolved. Actual entered units, acreage mistakes, author edits and any corrected record values require year-specific evidence or author-curated corrections.

The original 2019 assessment is already opened. Any subsequent modelling is a revised/development analysis and needs a new independent assessment before a fresh final-test claim. The first results, flagged-yield diagnostic and source trace remain available.

## Verification

Both PDFs opened successfully, the XLSX ZIP passed CRC checks, and all relevant spreadsheet rows were read without editing the workbook. Relevant complete PDF pages were inspected; the area and yield pages were also rendered for visual confirmation. The HTML's R blocks were inspected as text and do not contain a yield-unit correction procedure. File hashes match before and after moving. Model selection, cohort and assessment hashes are preserved. Temporary rendered images are removed after review.
