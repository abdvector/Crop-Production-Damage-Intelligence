# Rice protein-context forecasting experiment

Completed 20 October 2026. The prespecified comparison **does not establish improved yield prediction from these protein-structure annotations**. The regional forecasting artifact and earlier studies are preserved.

## Question and data

Does reference protein structure context improve day-60 rice trial yield prediction at held-out locations beyond environmental/planting information and ordinary measured SNPs?

The existing audited [Nguyen et al. rice trial study](https://doi.org/10.1186/s12284-023-00623-6) supplies **1,046 eligible genotype/environment yield records, 107 genotypes, 15 environments and 12 country/location groups**. The target is published adjusted grain yield in kg/ha, not independent raw plot harvests. Earlier project studies inspected these outcomes, making this development evidence. Published yield adjustment is inherited from the source and is not re-estimated within project folds.

Environmental inputs are six early-season weather summaries: minimum and mean temperature, diurnal temperature range, solar radiation, accumulated rainfall and approximate vapour-pressure deficit. Eight planting/context columns describe seeding seasonality, whether establishment has occurred, establishment delay and field days observed by issue date, planting method, season and the source spacing category. The spacing category is not verified physical plant density. Weather includes days 0 through 60 after seeding and must precede harvest. Later phenology, final biomass, harvested area and production are excluded as predictors.

The panel has 882 measured SNPs. The [molecular audit](Rice_Molecular_Linkage_Audit.md) identifies 89 canonical protein-altering SNPs with complete dosage calls for these genotypes. A bounded reference-structure check supplies six sites with local AlphaFold pLDDT at least 70 and both reference packing and radial-position descriptors. These are available audited sites, not an exhaustive biologically selected panel. Confidence does not measure mutation effect or aluminium tolerance. Complete cultivar proteins and ESM embeddings are not used.

## Fixed comparison

The saved [protocol](../data/processed/rice/protein_experiment/day_60/protocol.json) was written before fitting. Every configuration uses the same cohort:

1. Environment-balanced training mean.
2. Environment and planting context.
3. Environment plus all 882 SNPs.
4. Environment plus 89 protein-altering SNPs.
5. Environment plus the same six structure-mapped SNPs without annotations.
6. Environment plus a three-dimensional SNP PCA control.
7. Environment plus a three-dimensional structure representation.
8. Environment plus a three-dimensional shuffled-structure control.
9. Environment plus all SNPs and the structure representation: **primary candidate**, compared with configuration 3.

The structure representation consists of mean alternate dosage across six sites, mean dosage weighted by standardized reference contact count, and mean dosage weighted by standardized radial position. Annotation weights are standardized across the six reference sites without yield outcomes. These are deterministic transformations of measured SNPs, not additional independent genotype observations or tolerance scores.

The PCA control has mean six-site dosage and two PCs of those SNPs. PCA and genotype scaling fit unique training genotypes only. The shuffle applies a fixed seed-42 joint permutation of the two annotations across the same six sites. One shuffle is a representation probe, not a calibrated permutation significance test. The complete six-SNP control retains all six original directions.

Outer validation leaves out an entire country/location group, producing 12 folds. Each outer training set runs inner leave-one-location-out selection among Ridge alpha 0.1, 1, 10 and 100, minimizing equal-location mean squared error. Grid order resolves ties. Each alpha is selected without the outer location's yields. Genotypes can recur across training and held-out locations; this tests environment transfer, not unseen-cultivar transfer or future-year forecasting.

Numeric environmental imputation and scaling fit unique training environments; categorical encoding handles unseen levels. Genetic scaling fits unique training genotypes. Each feature block is divided by the square root of its original dimension. The 882-SNP block is rotated into its complete positive-eigenvalue training span for efficient Ridge fitting. Training weights are inverse environment record counts, normalized to mean one; the mean baseline uses those same weights. Preprocessing and selection repeat inside inner folds.

## Results

MAE and pooled RMSE weight records equally. Macro RMSE is the square root of the mean of the 12 location MSEs, weighting locations equally.

| Configuration | MAE kg/ha | Pooled RMSE kg/ha | Macro RMSE kg/ha | Pooled R squared |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 829.0 | 1,022.5 | 983.4 | -0.133 |
| Environment | 795.3 | 972.3 | 962.9 | -0.024 |
| Environment + all SNPs | 795.8 | 972.9 | 963.8 | -0.026 |
| Environment + coding SNPs | 794.5 | 972.4 | 963.1 | -0.024 |
| Environment + six SNPs | 796.3 | 974.4 | 965.6 | -0.029 |
| Environment + SNP PCA control | 796.1 | 974.0 | 965.3 | -0.028 |
| Environment + structure | 796.4 | 975.3 | 965.8 | -0.031 |
| Environment + shuffled structure | 796.0 | 973.7 | 965.2 | -0.027 |
| Environment + all SNPs + structure | 796.3 | 974.4 | 965.1 | -0.029 |

The primary candidate **worsened macro RMSE by 1.35 kg/ha**, improving only **5 of 12 locations**. Defining improvement as control RMSE minus candidate RMSE, the paired location bootstrap gives **-1.35 kg/ha**, with percentile 95% range **-3.83 to +0.99 kg/ha** across 5,000 seed-42 resamples. The range crosses zero. Shared training data across folds and only 12 clusters limit interpretation; this is descriptive stability, not an independent confirmation guarantee.

The structure-only representation also worsens macro RMSE relative to PCA (0.51 kg/ha), shuffled annotations (0.62 kg/ha) and the same six SNPs (0.20 kg/ha). The prespecified annotation-value claim rule fails. No further model or feature tuning followed inspection of these results.

Negative pooled R squared means the held-out predictions have more squared error than a constant equal to the overall observed target mean. That retrospective constant is a diagnostic, not an available deployment forecast. Environment modestly beats the fold-specific training mean, but forecasting remains weak. These trial metrics and district model metrics describe different prediction tasks and cohorts.

## Scope and next evidence

The project now includes an actual measured-SNP-to-reference-structure modelling experiment with explicit negative results and capacity controls. It does not establish that proteins are irrelevant to rice yield: six sites from a bounded audit, additive representations and 15 environments cannot answer that broader question.

The selected regional model is unchanged. District-year records lack cultivar identity/adoption shares, so trial protein features cannot be assigned to them defensibly. This experiment neither forecasts aluminium damage nor diagnoses causal losses. The separate aluminium study remains available.

A stronger molecular study needs a relevant verified gene/allele panel, more independent environments with aligned management and soil observations, and an external assessment cohort not previously used for development. Cultivar sequence embeddings additionally require verified sample-to-sequence linkage. More arbitrary reference structures alone would not solve these gaps.

## Review and reproduction

`app.py` remains the sole application entry point. Choose **Molecular data audit** for results, controls and downloads. Opening the app neither refits models nor downloads data.

Functionality is in `src/rice_protein_experiment.py`. Outputs under `data/processed/rice/protein_experiment/day_60/` contain the frozen protocol, source/code hashes, forecast windows, all 9,414 held-out predictions, 4,224 inner scores, selected alphas, location errors, within-environment genotype correlations and paired comparisons. Constant predictions have undefined correlation, retained as missing.

Completed outputs are protected from accidental refitting. To independently reproduce from a project-root Python session using the project environment, select a new empty directory while preserving original results:

```python
from pathlib import Path
import src.rice_protein_experiment as experiment
experiment.OUT = Path("data/processed/rice/protein_experiment/independent_replay")
experiment.run_experiment()
```

This freezes another protocol before fitting and records source bytes in that checkout. Source line endings affect code-file byte hashes; compare results numerically and record package versions. Existing results can be reviewed without training or network access.
