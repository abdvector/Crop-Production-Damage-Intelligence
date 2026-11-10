# Rice yield under aluminium stress

This separate breeding-trial study asks whether DNA markers improve prediction of upland rice grain yield in aluminium-toxic soil. It does not change the annual district yield model or its app. It adapts [Bartholomé et al. (2024)](https://doi.org/10.1371/journal.pone.0307009) using their [CIRAD Dataverse release, version 1.0](https://doi.org/10.18167/DVN1/HSIM8E).

The six original publisher files and their download/checksum receipt are in `data/raw/rice/colombia_aluminium/`. Dataset attribution: Grenier, Cecile; Bartholomé, Jérôme; Frouin, Julien (2024), *Genomic prediction in upland rice for aluminum tolerance in Latin America*. CIRAD Dataverse, V1, CC BY-SA 4.0. The source files are unmodified. Downloaded bytes were checked against the publisher's original-file MD5 values and recorded with SHA-256.

## Observations and inputs

One modelling observation is one **breeding family** in the 2020 Aguazul, Colombia trial. The source contains 680 adjusted family/check-by-soil rows, including 12 rows for check varieties. Excluding those checks leaves 668 rows: **334 families with one adjusted yield in each treatment**. The SNP file has one row per genotyped source plant. Match the family and SNP rows by `DNAID`, preserving the published link between the source plant and its family. Never join by row order or count the two soil rows as independent families.

| Variable | Role |
| --- | --- |
| `YLD` under `ALU` | Target: adjusted yield in the naturally aluminium-toxic soil, kg/ha according to the dataset dictionary |
| `YLD` under `LIM` | Optional predictor: measured yield of the same family in the limed comparison treatment |
| 9,928 SNPs | Published imputed genotype dosages, coded 0/1/2 |
| `DNAID` | Join key only |

The paper describes how plot grain weight was measured. This benchmark uses the published adjusted `YLD` table and its accompanying kg/ha definition. The soil treatment identifies the environment; it is not a per-family numerical aluminium dose. There are no protein structures, sequence embeddings, or weather predictors in this benchmark. Flowering time, plant height and grain zinc are not used as inputs. As an example of the join, `DNAID=1006` links one SNP profile to limed yield **1,306.3 kg/ha** and aluminium-treatment yield **1,841.0 kg/ha**. That is an observed comparison, not a claim about aluminium's effect for that family.

## Fixed comparison

All four methods predict the same ALU yields. Use repeated five-fold cross-validation, ten repeats, seed 42. Each family is assessed once per repeat; its ALU yield is excluded from fitting that fold. Scores are computed over the 334 pooled out-of-fold predictions for each repeat and then averaged across repeats. SNP centering and linear fits use training families only. Marker models use ridge on the centered genotype kernel (scaled by the SNP count), with a fixed penalty of 1. The combined model fits a linear relationship with LIM yield, then uses SNPs to predict the residual. There is no hyperparameter search or model selection on the assessment results.

| Method | MAE (kg/ha) | RMSE (kg/ha) | Predictive R² | Pearson r |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 503.8 | 641.5 | -0.006 | — |
| Limed yield only (OLS) | 433.8 | 552.8 | 0.253 | 0.503 |
| SNPs only (ridge) | 478.1 | 616.3 | 0.071 | 0.267 |
| Limed yield + SNPs | 438.2 | 559.2 | 0.235 | 0.492 |

**Result:** SNPs alone lowered MAE by 25.7 kg/ha relative to the training mean. When a candidate's limed yield was already known, adding SNPs in this fixed model raised MAE by 4.4 kg/ha. These are descriptive differences on this trial, not significance claims or evidence that genomic information never helps. The LIM-based methods require a measured control yield for the candidate; SNP-only prediction does not.

This is an adaptation, not a numerical replication of the authors' multi-environment GBLUP. Their reported correlation of 0.53 does not validate our model. The publisher's adjusted outcomes and imputed SNP dosages are used as supplied; the original plot adjustments and SNP imputation were not fitted afresh inside our folds. All families belong to one breeding population at one site and season, so the scores do not validate transfer to another location, year or Indian district. The target is **yield under a specified soil condition**, not causal yield loss or district crop damage.

Reproduce with the project environment from the repository root:

```powershell
.\.venv\Scripts\python.exe -c "from src.aluminium_study import write_report; write_report()"
```

See [the machine-readable results](Aluminium_Study_Results.json) for all repeat scores.
