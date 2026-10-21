# Planting context and full-SNP results

Evaluated 11 October 2026 under [Rice_Context_Protocol.md](Rice_Context_Protocol.md). Earlier experiments are preserved.

| Procedure | MAE (kg/ha) | RMSE (kg/ha) | R squared | Equal-location RMSE (kg/ha) |
| --- | ---: | ---: | ---: | ---: |
| Training mean | 840.071 | 1036.542 | -0.164074 | 983.710 |
| Context selection | 786.756 | 1004.817 | -0.093909 | 951.324 |
| Context + full-SNP selection | 786.756 | 1004.817 | -0.093909 | 951.324 |
| Full-SNP genomic control | 839.769 | 1035.894 | -0.162619 | 982.597 |

Context selection improves RMSE by **3.1%** and MAE by **6.4%** against training mean. Eight locations improve and four worsen. Hyderabad is a substantial failure: RMSE about 1,666 versus 1,288 kg/ha for mean prediction. This is modest development evidence, not reliable operational accuracy or financial savings. Negative pooled R squared remains: error exceeds the pooled observed-mean reference used by that metric.

Weather/planting-only and full-set selection produce identical predictions. Ten folds choose environment forests (seven leaf=2, three leaf=4); two choose context Ridge (alpha=100 and 10000). No additive genetic model is selected. The genomic-only control selects alpha=100 in every fold and is only marginally better than mean prediction.

All twelve risk folds select prevalence. Brier score **0.167305** equals its comparator. Conservative fallback improves on earlier fitted classifiers, but provides no individualised low-yield discrimination.

## Completed modelling steps

Thirty-seven context inputs include eight planting variables and twenty-nine weather summaries/proxies. Observed dates, timing, method, season and categorical spacing layout are used. Spacing units and plants per hill are unresolved, so physical density is excluded. All weather windows and field-period summaries stop at the issue date. Rainfall spells do not measure irrigation deficit; temperature thresholds are descriptive proxies, not verified damage thresholds.

The relationship benchmark uses all SNPs, training-only allele frequencies and every positive genetic eigencomponent. Penalties and genetic weights are selected in inner location folds. Forests fit one observed environment mean per fitting environment. No future flowering, harvest-weather, soil substitution or unverified protein assignment is used.

## Ranking and source comparison

Context predictions are constant within a trial; variety-ranking correlations are undefined. Multi-season correlation can instead capture environment shifts. The genomic control's mean within-environment correlation is about 0.114 across fifteen trials. See [Rice_Paper_Comparison.md](Rice_Paper_Comparison.md).

## Acquisition outcome

The original analysis ZIP and ten-file irrigation/nitrogen disease study are checksum-verified. The latter has no grain-yield labels or primary-panel mapping. IRRI's located long-term yield files require permission. Exact primary irrigation/fertiliser/soil measurements and planting density remain unavailable; they were not filled from another population. See [Rice_Management_Data_Search.md](Rice_Management_Data_Search.md).

## Reproduction and limits

Checks passed for future-weather exclusion, masking future establishment dates, reconstruction of the full training genomic kernel, training transforms unchanged by test-input changes, predictions unchanged by test-label changes, metric recomputation, prediction coverage, inner choices, ranking diagnostics and all three dashboard modes. The raw downloads match publisher checksums. No temporary test/generation scripts were retained. These checks establish implementation integrity, not operational or causal validity.

Run `python app.py`, select Planting and full-SNP validation and day 60. Results in `data/processed/rice/context/day_60/` include metrics, outer predictions, inner scores, diagnostics, feature catalogue, forecast windows, per-environment rankings and provenance hashes. Prior evaluations remain selectable.

This candidate set was fixed before its run, but developed after inspecting earlier results on the same trials. Nested tuning does not erase that development history or prove correct model specification. An independent new-trial evaluation remains necessary.
