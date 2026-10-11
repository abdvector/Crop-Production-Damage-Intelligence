# Literature-guided rice model results

Evaluated 11 October 2026 at day 60, following [the declared protocol](Rice_Literature_Protocol.md). Ten new candidates were added to the thirteen existing candidates. The models use the same 1,046 audited observations and twelve held-out locations. The data have previously informed development, so this is not an external replication.

## Outcome

| Procedure | MAE (kg/ha) | RMSE (kg/ha) | R squared | Equal-location RMSE (kg/ha) |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 840.1 | 1036.5 | -0.1641 | 983.7 |
| Previous context/full-SNP selection | 786.8 | 1004.8 | -0.0939 | 951.3 |
| Literature environment selection | 771.7 | 982.6 | -0.0461 | 941.8 |
| Literature full selection | 771.4 | 982.5 | -0.0458 | 941.8 |
| Full-SNP genomic control | 839.8 | 1035.9 | -0.1626 | 982.6 |

The full selection reduces pooled RMSE by **5.2%** versus training mean and **2.2%** versus the previous context benchmark. MAE is **8.2%** below training mean. These are modest development improvements; pooled R squared remains negative, substantial location errors persist, and external reliability has not been established.

## What changed and where

Eleven location folds keep exactly the previous candidates and predictions. Only Los Banos changes: environment selection chooses compact environment PLS with one component, while full selection chooses that same environmental stage plus a strongly shrunk centred genomic residual (alpha=100). Its location RMSE falls from 1,257.9 to 1,168.4 kg/ha. The gain is concentrated in one location with two seasons, not a consistent improvement across all twelve locations. Hyderabad remains the largest failure, RMSE about 1,666 kg/ha.

Full versus environment-only selection changes pooled RMSE by just **0.126 kg/ha** and MAE by **0.300 kg/ha**. This tiny difference does not establish useful incremental genetic forecasting skill. The genetic adjustment provides within-trial correlations of 0.155 in Los Banos dry season and -0.132 in wet season; ranking remains undefined for the other thirteen trials because selected predictions are constant within each environment. No reaction-norm or balanced genomic PLS candidate is selected by the outer training procedures. Retaining unsuccessful candidates and their scores makes the comparison reviewable.

## Stability and risk

RMSE improves against training mean in eight of twelve locations. Equal-location RMSE improvement is 41.9 kg/ha, with a descriptive paired 95% bootstrap range **-105.8 to 180.6 kg/ha**. The range crosses zero, and overlapping cross-validation fits plus prior development prevent a formal significance claim. The location-weighted and record-weighted results answer different questions; both are retained.

The unchanged exploratory low-yield grid still chooses training prevalence throughout. Brier score remains 0.1673, with no individualised risk discrimination. This experiment improves the yield benchmark; it does not improve every output.

## Literature learnings and limits

The PLS result is consistent with testing correlated environmental information through a small number of latent components, motivated by [Monteverde et al. (2019)](https://doi.org/10.1534/g3.119.400064). Our small weather block, absolute-error objective, forecast cutoff and location holdout differ from their setup; it is not a numerical reproduction.

The lack of useful interaction/genetic gain is compatible with [Nguyen et al. (2023)](https://doi.org/10.1186/s12284-023-00623-6), which cautions that cross-environment yield relationships can be weak. Their full-season covariates and environmental ranking scores are not substitutes for our day-60 forecasting inputs and kg/ha errors. The training design lessons from [He et al. (2023)](https://doi.org/10.1186/s12284-023-00643-2) concern heading/height and cannot be presented as proven grain-yield gains.

No model was given future flowering or harvest-period weather, test-environment yield means, or unverified soil/protein features. VPD is an approximate daily weather-derived feature, not a measured stress variable. Calendar windows do not identify flowering or reproductive phases. No prediction intervals have been calibrated for this model; the separate context split intervals cannot be transferred to it.

## Reproduction

Run python app.py and select Literature-guided validation, day 60. The preceding context mode remains the default. Saved outputs under data/processed/rice/literature/day_60 include all outer predictions, location errors, 336 inner candidate score rows, diagnostics, forecast windows, within-trial rankings, paired stability, six compact features, units and source/code hashes. There are 23 regression and five risk candidates, selected within eleven inner locations per outer fold. No temporary launchers or test scripts are retained.

Verification passed: syntax; identical audited outcome records across experiments; pooled and per-location metric recomputation; selected inner candidates minimising their declared scores; unchanged training transforms after test-input perturbation; unchanged predictions for all 23 candidates after test-label perturbation; identical predictions from the thirteen preserved candidates; exclusion of all weather after the issue date; independent VPD calculation; and Streamlit checks for all four evaluation modes, literature model controls and an uncomputed day-30 state. The earlier uncertainty report still loads and is kept separate.
