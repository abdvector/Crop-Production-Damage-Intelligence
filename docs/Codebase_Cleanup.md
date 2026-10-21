# Final-project cleanup

The current project keeps the two district forecasting studies and one presentation interface. `app.py` is the only launcher. State and district selection remain available; Kharif coverage is restricted to Odisha, and annual coverage includes all five original states.

## Removed from active source

Twenty-seven retired Python modules were removed: initial wheat/synthetic demonstration code, duplicate dashboard implementations, and exploratory trial, farm, protein and aluminium runners. They are not dependencies of the retained district preparation or model modules. The package now has six functional Python modules plus `__init__.py`.

Their removal does not invalidate the recorded experiments or remove their datasets. To reproduce a retired experiment, use its matching historical source revision, `de3ecbc`, together with its recorded inputs and environment. The current checkout reproduces the annual and Odisha district studies. No Git history was rewritten.

## Preserved

- Every dataset file, processed result, source receipt and model artifact.
- Research papers, the literature matrix, images and presentation figures.
- The original frozen seasonal protocol, timing amendment, implementation rules and model module, with their exact checksums.
- Earlier research documentation, organized under `docs/research_notes/` with relative links updated.
- Local mentor documents, which remain ignored and are not included in the GitHub update.

A before/after SHA256 comparison verified **1,206 protected files unchanged byte for byte**, covering data, models, papers, presentation figures and root dataset archives. The interface redesign does not retrain, relabel or replace any result. Earlier source/output checksum records remain historical receipts. Navigation checks covered all five states, district changes, both coverage options, all result/method views and the presentation guide; no metric cards or horizontal tabs remain.

## New reading order

1. `README.md`: what the project does and how to run it.
2. `docs/Project_Guide.md`: presentation explanation and terminology.
3. `docs/Rice_Odisha_Model_Results.md`: exact results and limitations.
4. Original methods/protocol documents when detailed justification is needed.

Dependencies for retired deep-learning, SHAP and XGBoost demonstrations were removed from the active requirements. Installed environment packages were not uninstalled.
