# Planting, weather and full-SNP experiment

Declared 11 October 2026 before fitting this candidate set. Previous experiments remain unchanged. This continues development on previously inspected trials; nested validation is not an independent external test.

## Inputs

Keep the same 1,046 audited yields and 60-day issue date. Add circular seeding day-of-year, observed establishment delay and time in field, establishment completion by issue date, recorded method, season and categorical source spacing layout. Source spacing has no explicit units in Table S2; no physical planting density or plants-per-hill value will be inferred. Completed establishment dates can enter only if no later than the forecast date; later event dates are masked.

Weather summaries: first 15 days, last 15 days and preceding 15 days; mean of each weather variable except summed precipitation. Add cumulative rainfall, solar radiation, counts of maximum temperature above 35 C, minimum temperature above 25 C, cumulative maximum-temperature exceedance above 35 C, and longest rainfall spell below 1 mm/day. Also summarise observed in-field weather through the issue date. These thresholds are predeclared descriptive proxies, not validated rice damage thresholds. Rainfall does not measure irrigation supply. No future flowering, harvest-weather or published full-season covariates are forecast inputs.

## Genetic benchmark

Build a VanRaden-style relationship from 0/2 homozygous allele counts, using frequencies from unique training genotypes. Divide centred-marker cross-products by sum(2*p*(1-p)), then normalise mean training diagonal to one. Retain every positive eigencomponent, with numerical tolerance 1e-10; this is an exact kernel factorisation on the training span, not five-PC truncation. Validation markers are projected using training frequencies and basis. Report it as genomic kernel Ridge with training-selected penalties, not an exact REML/BGLR replication of the published GBLUP analysis.

Standardise/impute numerical context using unique training environments; fit categorical encoding within each training split. An environmental RBF kernel has gamma=1/context_dimension and unit diagonal. Additive genomic/environment models combine context kernel features with genetic kernel features scaled by square root of genetic weight. Ridge includes an intercept.

## Fixed search

Thirteen regression candidates: mean; context Ridge alpha {100,10000}; context RBF kernel alpha {1,100}; genomic-only kernel alpha {1,100}; additive context/genomic kernels with genetic weight {0.1,1} and alpha {1,100}; environment-mean forests with 128 trees, minimum leaf environments {2,4}, seed 42.

Three selection procedures: context-only; context plus genomic candidates; and genomic-only control (mean or genomic kernels). Risk candidates: training prevalence, context logistic C {0.001,0.01}, or context plus all genetic kernel components logistic C {0.001,0.01}. The low-yield threshold is each split's training-only 20th percentile.

For each of twelve outer held-out locations, tune on the eleven remaining locations with inner leave-one-location-out. Select by equal-location MSE/Brier. Fit all preprocessing within each training split. Report pooled errors, equal-location errors, within-location Pearson correlation, candidate choices, input hashes and forecast-feature catalogue. Constant predictions have undefined correlation; do not record zero as a measured correlation.

No adaptive candidate expansion using these outer outcomes. The paper comparison will separate ranking from absolute error and environment holdouts from location holdouts. Additional management studies remain separate until trial/sample identities, units and feature timing match.
