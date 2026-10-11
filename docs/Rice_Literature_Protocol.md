# Literature-guided day-60 improvement protocol

Declared 11 October 2026 before running the new candidates. Earlier results on these same trials have been inspected. This is another development experiment, not an external confirmation or an exact reproduction of published models.

## Evidence used

1. [Monteverde et al. (2019), rice markers and environmental covariates](https://doi.org/10.1534/g3.119.400064): tested partial least squares (PLS) and reaction norms for predicting untested years in two rice breeding populations. PLS with markers and environmental covariates performed better in their setting. Learning: test low-rank predictors for correlated weather/genetic inputs. Their yield-ranking correlations and year splits are not our absolute-error/location task; reported success is not a promised gain here.
2. [Nguyen et al. (2023), our primary rice panel](https://doi.org/10.1186/s12284-023-00623-6): yield correlations across environments were weak, and interaction models did not significantly outperform main-effects models. Their environmental features included temperature range and vapour pressure deficit. Learning: retain strong shrinkage/baselines and test interactions modestly. Their full-season developmental-phase inputs cannot be used as day-60 observations.
3. [He et al. (2023), sparse phenotyping and haplotypes](https://doi.org/10.1186/s12284-023-00643-2): illustrates training-set and marker representation choices for rice heading/height traits. Learning: training design matters; evidence for these traits is not proof of yield improvement. We do not invent dense haplotypes from this sparse marker panel.

The candidates below are our adaptations, not methods proven effective on this exact pre-harvest task.

## New compact environmental block

For each environment, use all available days from seeding to the issue date inclusive. Six numeric summaries: mean minimum temperature, mean temperature, mean diurnal temperature range, mean solar radiation, cumulative rainfall, and mean approximate vapour pressure deficit (VPD). VPD approximates saturation vapour pressure from daily minimum/maximum temperatures and daily mean relative humidity; it is not a direct observation or an exact hourly calculation. [FAO saturation-vapour-pressure equations and humidity limitations](https://www.fao.org/4/x0490e/x0490e07.htm). Rainfall is not irrigation or drought severity. These windows are calendar windows, not observed reproductive phases. Every window stops at the forecast date.

Imputation and scaling use unique training environments. PLS and environmental Ridge fit one observed training mean per environment. One or two PLS components and two Ridge penalties (1, 100) are declared; two components do not imply two biological mechanisms.

## Fixed candidate grid and hypotheses

Preserve all thirteen previous context candidates, unchanged. Add ten candidates:

- Four compact environment models: PLS with 1 or 2 components; Ridge alpha 1 or 100.
- Two block-balanced PLS models with 1 or 2 components on compact environment inputs plus the full training-centred genomic relationship coordinates. Divide each block by the square root of its dimension; PLS does no further feature scaling. These models fit individual training yields; environmental information remains shared across rows.
- Four two-stage models: compact environment PLS with one component predicts environment mean. A Ridge model (alpha 100 or 1000) predicts within-environment centred training yield deviations using full genomic coordinates, either alone or with products against two training-fitted environmental PCA coordinates. Within-environment centring prevents the residual stage from merely fitting environmental mean shifts. The genetic residual stage has no intercept. Training row weights are inverse environment size and normalised to mean one. The two stages use fitting labels only, and no target-environment mean is used for prediction.

Hypotheses: compact predictors may reduce overfitting; PLS may handle correlated blocks; centred genetic residuals may distinguish genotype differences without absorbing site means; reaction-norm products may allow those differences to vary with observed environment. Each may fail.

## Evaluation and decision

Use the same 1,046 audited observations, twelve outer held-out locations, eleven inner location folds, 882 SNPs, day-60 cutoff and training-mean comparator. Select by equal-location MSE. Compare environment-only selection, full selection, and the full-SNP genomic control. Retain the previous low-yield candidates, whose risk evaluation is exploratory. No test-location labels may influence transforms, model fitting or candidate choice. No later weather, flowering or harvest outcomes enter predictors.

Save all outer predictions and inner scores in a separate literature/day_60 directory. Report pooled and equal-location errors, bias, improvement/worsening by location, and within-trial variety ranking. Apply the existing descriptive paired location bootstrap. Compare against the previous context benchmark on the identical records. Do not change the grid after inspecting this run. Publish a failure as a failure; changing the candidate set or choosing which evaluation to highlight based on these outcomes adds development bias. Keep the existing context mode as the default and add this experiment as a selectable mode irrespective of outcome. Its intervals have not been calibrated; do not attach the earlier split model's intervals to it.
