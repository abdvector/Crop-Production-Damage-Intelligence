# Comparison with the original rice study

Sources: [Nguyen et al. 2023](https://doi.org/10.1186/s12284-023-00623-6), the original supplementary workbook, and [Additional file 6](https://doi.org/10.6084/m9.figshare.26567258). Five publisher R scripts are preserved inside the checksum-verified ZIP in `data/raw/rice/nguyen_2023_analysis/`. They were inspected, not executed or extracted as app launchers.

The study uses GBLUP and phased whole-season environmental covariates. Its environment holdouts and selected/random training-environment scenarios report Pearson correlation within the validation environment. Its code uses BGLR kernel components, 25,000 iterations and 5,000 burn-in iterations. These are breeding prediction analyses, not our fixed-day pre-harvest design.

| Aspect | Current project |
| --- | --- |
| Issue date | Day 60 after seeding; later weather and flowering information excluded |
| Split | Entire locations held out, including all their seasons |
| Tuning | Inner location splits restricted to outer training data |
| Target | Audited kg/ha labels; ten conflicting records excluded |
| Genetics | Full-SNP relationship kernel with training-selected Ridge penalties |
| Context | Observed planting metadata and weather through issue date |
| Main evaluation | Absolute yield errors and comparison with training mean |
| Ranking | Pearson correlation within each individual environment |

This is not an exact numerical replication of Bayesian GBLUP, its variance estimation or all published scenarios. RMSE and correlation assess different things. Holding out a location removes other seasons at that site; an environment holdout can retain them.

Our context model predicts one yield per environment and cannot rank its varieties. Pooled or multi-season correlation can reflect environmental shifts rather than genotype discrimination. Its within-environment ranking correlation is undefined. The separate genomic control has defined correlations in all fifteen environments, averaging about 0.114: weak descriptive ranking evidence, not reproduced published accuracy.

The strict pre-harvest, unseen-location question is retained. Full-season covariates will not be added merely to increase forecast scores.
