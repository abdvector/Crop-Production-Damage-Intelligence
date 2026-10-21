# CIRAD rice aluminium dataset audit

Audited 10 October 2026. Original archive retained in the project root as `CIRAD_Rice_Aluminium_HSIM8E_Original.zip`.

## Decision

Suitable for a separate genetic prediction and soil-condition response study in the tested rice families. Not sufficient for a general forecast accepting arbitrary weather, soil, aluminium and protein inputs across new regions. Keep the earlier Nguyen dataset as the main candidate for environmental transfer benchmarking; use CIRAD as a separate aluminium-related case study. Do not concatenate their records or transplant soil values between studies.

## Source and integrity

Dataset: https://doi.org/10.18167/DVN1/HSIM8E

Associated methods: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0307009

ZIP archive integrity passed. All six original dataset files match publisher MD5 values obtained from the repository API. The original ZIP is unchanged. Source dictionaries and data were read directly from it; no temporary helper scripts were retained.

## Local verified counts

| Component | Verified finding |
| --- | --- |
| Raw plot observations | 1,008: 504 ALU and 504 LIM |
| Adjusted BLUE records | 680: 668 family-condition values and 12 check-condition values |
| Genetic matrix | 334 unique family IDs by 9,928 unique markers |
| Marker coding | Observed numeric codes 0, 1, 2; zero missing values; 11 constant markers |
| Raw plots linked to markers | 936 family plots; 72 check plots have no marker data |
| Yield missingness | Zero missing raw or adjusted YLD values |
| Other outcome missingness | Three missing raw ZN values; adjusted FL/PH/ZN have no missing values |
| Germplasm table | 469 source rows, including 79 fully blank rows; 390 nonblank designations |
| Duplicate identity checks | No repeated adjusted DNAID/SOIL keys; no repeated raw TRIAL_INSTANCE or SOIL/ROW/RANGE keys |

The dictionary identifies YLD as kg/ha at 14% humidity. Preserve those values without multiplying by 1,000. BLUEs are adjusted estimates rather than independent additional harvests. The archive contains both raw and adjusted versions of the same experiment, so these must not be stacked as separate training observations.

## Identity matching

All 334 family IDs in BLUEs have genetic data. All raw plot designations map uniquely to germplasm on DESIGN and TYPE. Fifty temporary family designations share DNAIDs with their corresponding family designations; they are repeated representations of the same genetic family, not new unrelated genotypes.

The six check varieties have names as IDs in the BLUE table, while their germplasm rows use the shared placeholder LINE. Never join all checks through that placeholder or assign them family markers. Checks remain valid plot observations for experimental adjustment but cannot enter the current molecular prediction benchmark as genotyped samples.

## Yield scaling clarification

From raw grain weight, humidity and published yield, the implied harvested area is approximately 1.50 m2 (median 1.500003 m2). Using 1.50 m2 reproduces published YLD within 0.379 kg/ha, consistent with rounded inputs. The paper's nominal plot dimensions, two 3 m rows at 0.26 m spacing, give 1.56 m2. A harvested-area convention could explain this; it has not been confirmed. Preserve published YLD and request harvested-area/scaling clarification before claiming independently reproduced yield calculations.

## Predictor availability and interpretation

The methods place the trial at Aguazul, Colombia, in 2020, with two field conditions: untreated acid soil and limed soil. The paper supplies condition-level soil chemistry and a management description, not a plot-level soil table in this archive. These are one site-season and two soil conditions, not multiple independent regional environments.

| Candidate input | Status and appropriate use |
| --- | --- |
| Genetic markers | Available and family-linked; codes are imputed in the source. Confirm allele orientation before biological interpretation |
| ALU/LIM condition | Available before harvest; suitable as a categorical treatment/environment descriptor |
| Soil pH, aluminium and nutrients | Paper-level condition descriptions; cannot estimate separate effects from only two correlated condition profiles |
| Fertiliser/irrigation | Study-level management descriptions; no demonstrated independent variation for estimating their effects |
| Weather | No daily weather series in this archive; exact establishment dates need confirmation before matching |
| FL, PH, ZN | Published outcomes; final flowering/height and grain zinc are not automatically eligible pre-harvest inputs |
| GRNW, HUM | Harvest measurements used in yield calculation; exclude as explanatory inputs for a pre-harvest forecast |
| ROW, RANGE | Experimental spatial coordinates for trial adjustment; not transferable agronomic predictors |
| RBHV | Virus-related score with dictionary spelling RHBV; observation timing must be resolved before forecasting use |
| Protein structure | No family-specific sequences, amino-acid variants or structures supplied |

Liming changes more than aluminium availability. A difference between ALU and LIM cannot be attributed solely to aluminium or used to estimate an independent continuous aluminium effect. Soil/weather/management values repeated across families do not add independent environmental observations.

SNP identifiers encode chromosome/position and a nucleotide suffix. These provide candidate annotation coordinates, not complete protein sequences. Reference assembly, allele meaning, marker-to-gene mapping and verified coding variants require further work. Genetic markers currently suffice for a genomic model; they do not establish a protein-structure model.

## Defensible modelling and validation scope

For CIRAD, the supported question is: can genomic information predict harvested rice yield and differential performance between these two soil conditions in families not used for training? Use the reported kg/ha target with its adjustment caveat. A condition-only baseline and regularised genetic/GBLUP benchmarks are appropriate candidates; 9,928 predictors for 334 families require shrinkage and training-only dimension reduction or selection.

Group evaluation by DNAID so all temporary designations, replicate plots and soil conditions for a withheld family follow the intended holdout protocol. Predicting a family's ALU outcome after observing its LIM yield is a different, easier task from predicting an entirely unseen family; label it separately. Never use a yield ratio derived from the held-out ALU yield as its input.

Published BLUEs were adjusted using the full experiment. Report this dependence if benchmarking against them. For stronger independent validation, design plot-level evaluation and training-only nuisance adjustment rather than fitting spatial effects jointly with test outcomes. Do not use a random plot split that shares the same family across training and testing to claim new-family accuracy.

Use MAE/RMSE in kg/ha, bias and uncertainty coverage under family holdouts. One site-season cannot establish geographic or future-season reliability, and residual diagnostics cannot prove absence of misspecification. Forecast issue date remains to be selected before features are constructed.

## Saved audit artifacts

`data/processed/rice/cirad_aluminium/` contains:

- `adjusted_yields_audited.csv`: original adjusted values, source row numbers, explicit kg/ha field and marker availability.
- `plot_observations_audited.csv`: original raw values, source row numbers and verified family linkage; check rows are flagged without genetic family IDs.
- `germplasm_nonblank.csv`: source germplasm values excluding only fully blank rows.
- `audit_summary.json`: counts, publisher checksums, ZIP SHA256 and unresolved issues.

No model has been trained and no application changes have been made. Recommended next step: settle a single main research question using the Nguyen multi-environment panel, with this CIRAD experiment as separate supporting analysis if aluminium remains part of the scope. Family-specific proteins and broader soil/management inputs are still not verified.
