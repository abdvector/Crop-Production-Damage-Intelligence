# Numerical-input rice yield model

This is a new, simplified retrospective experiment, declared on 22 October 2026. Earlier studies and their original results are retained in the previous-studies archive. No accuracy improvement is presumed and these already examined years are not an independent new test.

## Question and target

Can five past yields and June-August weather estimate annual rice yield per hectare more accurately than the mean of those five yields? The target is annual rice yield in kg/ha, including all rice seasons. This is not a Kharif-only, plot-level or damage-cause model.

## Data and predictors

Use the existing verified ICRISAT/NASA prepared annual table: 1,490 complete district-year records, 1987-2017, 50 historical districts across five eastern Indian states. ICRISAT provides the annual administrative yield labels. NASA POWER provides monthly reanalysis at representative district coordinates, not field sensors or rice-area averages. The exact original prepared-file SHA256 is checked before use.

There are 17 numerical predictors: yield at Y-2, Y-3, Y-4, Y-5 and Y-6, plus NASA monthly maximum temperature, minimum temperature, corrected precipitation (mm/day) and relative humidity (%) for June, July and August. Use the source monthly summaries as supplied; rainfall is not a monthly total. The Y-1 yield is deliberately excluded under the original two-year reporting-delay assumption. Y denotes the agricultural start year. Full August weather means this design does not satisfy the seasonal study's August 24 cutoff. Historical archives do not establish real-time availability.

District, state, coordinates, calendar year, current yield, current acreage and production are excluded from X. Area names are optional example selectors only. Protein, aluminium, soil and satellite features are not included. Existing satellite and seasonal datasets remain preserved as separate studies and must not be joined across incompatible geographic units.

## Fixed model and baseline

Use one Random Forest: 300 trees, maximum depth 4, minimum leaf size 10, seed 42, remaining scikit-learn defaults. Fit the departure from the five-lag mean and add that reference back at inference; clip negative yields to zero. The comparator is the same five-lag mean. The forest configuration is fixed before this run, without a search over assessment results. This choice demonstrates numerical-input inference and does not claim the forest is universally best.

Fit on all complete records through 2004. Freeze this model for both the 2006-2011 earlier check and the 2012-2017 later check; 2005 is unused because of the two-year label-delay rule. Do not refit on assessment labels, select a winner after inspecting results, or mix errors across these periods. The application loads this exact evaluated fit, not an unevaluated refit on all years. Report MAE, RMSE, R squared, bias and yearly errors beside the baseline. Each year has only 50 correlated district observations; pooled errors are descriptive and no IID significance claim is made. These regions were seen in fitting; this is not a test of transfer to unseen regions.

## Checks and limitations

Verify original source checksum, unique district/year keys, finite complete X and Y, positive yields, temperature ordering, physical units/ranges and agreement of the reference with the five lags. Preserve the original source cleaning and missing-label exclusions; never substitute missing labels. No scaling or imputation is needed for this complete-data forest. Test inference after removing all label and identity columns. Hash the code, method, source and output artifacts. Out-of-fitting-range values trigger a warning; values inside marginal ranges can still form unsupported combinations.

Random Forest prediction does not require Gaussian predictors, normally distributed errors or linear relationships. This does not establish causality, independence, absence of confounding or reliable uncertainty. We provide no p-values, calibrated prediction interval, causal damage attribution, financial savings or operational low-yield alert. Manual weather edits are model scenarios, not agronomic intervention effects. Accuracy can be poor, and applicability remains limited to settings represented by the historical source data. No current-year or farm-level accuracy has been validated.
