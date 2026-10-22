# Current-project cleanup

Updated 22 October 2026 following the decision to retain the existing rice project and stop pursuing further replication branches.

## Retained scope

- Annual rice study for the five existing states, its selected model and seven-method comparison.
- Original Odisha Kharif study, later-year assessment, revised nested comparison and statistical foundation audit.
- Completed vegetation/surface-soil-moisture comparison, including its negative results, original four v3 exports and reproducibility records.
- `app.py` as the sole launcher, with imported preparation, validation and dashboard modules.
- Research papers, literature matrix, presentation figures/images and local mentor materials. Mentor materials remain ignored by Git.

Raw data now occupy five study-specific folders: `crop_state`, `des_kharif_2026`, `icrisat_district`, `odisha_seasonal_weather` and `seasonal_geography`. Processed data occupy nine folders: `crop_state`, `crop_state_model`, `foundation`, `odisha_seasonal`, `regional_comparison`, `regional_forecast`, `revised_modelling`, `seasonal_geography` and `seasonal_source`. Only `models/rice_regional.joblib` is needed from the old model-artifact folder.

## Removed

The removal inventory contained 614 files, about 334 MiB, across 43 checked targets, including bytecode caches and the empty temporary folder. Some originals were local ignored files; this is disk space removed, not a claimed reduction of Git's historical object storage.

- Unused protein/genetic and aluminium trial downloads: Nguyen, CIRAD, BAAP, Ptr and molecular references/linkage outputs; the duplicate root CIRAD archive.
- Farm-survey experiments and weather caches; unused nitrogen/AWD, Smart-Valleys, Arbelaez, Juma and Bhandari trial downloads; old survey documentation.
- Restricted IRRI metadata and abandoned source-search, context, baseline, literature, nested and reliability outputs unrelated to the retained studies.
- Bowden's recently inspected sample/code and feasibility note, because that replication was not adopted.
- The original synthetic wheat CSV and obsolete `model_bundle.joblib`/`xgboost_champion_model.json` artifacts.
- Archived exploratory notes under `docs/research_notes/`, bytecode caches and the empty temporary folder.

This supersedes the previous cleanup's policy of preserving every experimental dataset. The retained completed crop-state experiment is part of the current research record, not an adopted replacement for the dashboard model.

## Preservation and validation

Removal targets were resolved and checked to remain inside the project before deletion. None was a dependency of the retained code or pinned study receipts. A SHA256 tree fingerprint over 726 retained data, source, model, paper and presentation files was recorded before cleanup and checked afterwards. The protected files remain byte-for-byte identical.

The app data loaders and existing study verification commands were checked after cleanup. No forecasts were retrained or improved by deleting files. Scientific findings and limitations remain as recorded in the retained results notes. Git history was not rewritten; previously committed retired files can still exist in earlier revisions. Ignored local originals are not recoverable from Git merely because the project uses Git.
