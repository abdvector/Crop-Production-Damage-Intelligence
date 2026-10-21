# Yield forecasting reliability protocol

Declared 11 October 2026 before running this reliability experiment. Existing day-60 results have already been inspected; this is development analysis, not an independent external test.

The main question is: how accurately can information available before harvest predict rice yield per hectare at unseen locations, and do genetic markers improve prediction beyond weather and planting context? Low-yield risk is secondary. Protein embeddings are conditional future work; aluminium remains a separate supporting study.

## Location-level comparison

Use the existing nested, held-out-location predictions without changing their models. Compare each regression procedure against training mean using equal-location mean absolute error and root mean squared error. Resample whole locations together for both models, 10,000 times with seed 20261011. Report percentile 95% bootstrap ranges for paired improvements. Positive means less error than baseline. These are descriptive stability ranges: only twelve locations exist, cross-validation fits overlap, and development decisions used this dataset. They are not proof of statistical significance or external reliability.

## Prediction intervals: separate experiment

Sort the twelve location names, permute with NumPy default_rng seed 20261011, and assign the first six to fitting, next four to calibration and final two to assessment. Assignment uses location identifiers only, never outcomes. Save the membership. Do not search over splits.

Select a regression candidate from the existing thirteen-candidate context/full-SNP grid using inner leave-one-location-out MSE on the six fitting locations only. Calibration and assessment locations must be excluded from candidate choice, transformations and model fitting. Preserve a separately fitted training-mean comparator. Fit once; do not refit after calibration.

For each of four calibration locations, compute its maximum absolute yield error over all its observed trial rows. Use these four location scores, not hundreds of correlated individual rows. At coverage c, take sorted score rank ceil((m+1)*c), with an infinite extra score if the rank exceeds m. Intervals are prediction +/- that score, lower bound clipped to zero because the observed target is nonnegative. Report 80% and 90% targets, row coverage, the fraction of assessment locations with every row covered, width, and point errors. With four calibration locations, the 80% interval is finite and the 90% interval is necessarily unbounded. Do not silently substitute a finite percentile for 90%.

This adapts split conformal prediction to one maximum-residual score per location. Its nominal guarantee would require exchangeability of entire calibration and future location datasets with the fitting model fixed. Geography, season, genotype composition and trial selection can violate that assumption here. Thus coverage is an assumption-dependent target, not a demonstrated farm guarantee. Two assessment locations cannot establish calibration. These intervals belong to this separately fitted model and cannot be attached to the main twelve-fold predictions.

Method reference: [Angelopoulos and Bates, A Gentle Introduction to Conformal Prediction](https://arxiv.org/abs/2107.07511).

## Environmental transfer diagnostics

For each main outer fold, fit numeric imputation/scaling and categorical encoding on unique training environments only. Compute nearest-training-environment root mean squared feature distance for each held-out environment. Compare with the largest leave-one-environment-out nearest-neighbour distance among training environments. Also list numeric inputs beyond observed training ranges, unseen categories, and the three largest scaled differences from the nearest environment. StandardScaler uses training standard deviations, with scale one for constant inputs; these scaled units are not always observed standard deviations. Labels are excluded. These are descriptive novelty flags; they are not causal explanations, calibrated risk estimates, or proof that an unflagged input is safe.

## Reproduction

Expose the workflow through app.py only; rice_reliability.py is an imported module. Save all results, split membership, calibration scores, seeds and hashes. Check location separation, calibration rank, coverage recomputation, assessment-label independence, and dashboard rendering. Retain no temporary test/generation scripts.
