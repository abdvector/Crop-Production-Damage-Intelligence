# Rice Yield and Low-Yield Risk Research

Institution: Birla Institute of Technology, Mesra

Department: Quantitative Economics and Data Science

Guide: Dr. Manish Kumar Pandey

## Research question

Using information available before harvest, how accurately can weather and rice genotype information predict grain yield per hectare and low-yield risk at unseen locations? Does adding verified genotype-linked protein sequence embeddings improve those predictions?

The current dashboard uses real published rice trials, SNP markers and NASA POWER weather estimates. Protein embeddings await verified variety-to-sequence links. Aluminium data belong to a separate CIRAD study. Low yield is a risk proxy, not measured disease damage.

## Run

Run `python app.py` with the project interpreter. From PowerShell, the existing environment can be used with `.\.venv\Scripts\python.exe app.py`. For a new environment, install `requirements.txt` first. Stop the server with Ctrl+C. The sole application entry point is `app.py`; no separate launcher is required. Restart after source edits because file watching is disabled.

## Data and first baseline

Primary dataset: [Nguyen et al.](https://doi.org/10.1186/s12284-023-00623-6).

- 1,046 eligible yield records, excluding 10 conflicting genotype/environment records.
- 107 genotypes, 882 SNPs, 15 environments and 12 locations.
- Default cutoff: 60 days after seeding, including days 0 through 60.
- Entire locations are held out; preprocessing is fitted inside each training fold.
- Low-yield thresholds use each training fold's 20th yield percentile.

| Model | MAE (kg/ha) | RMSE (kg/ha) | R squared |
| --- | ---: | ---: | ---: |
| Training mean | 840.1 | 1036.5 | -0.164 |
| Weather Ridge | 1040.8 | 1221.1 | -0.616 |
| Genetics Ridge | 849.6 | 1051.0 | -0.197 |
| Weather + genetics Ridge | 1044.5 | 1228.9 | -0.636 |

The combined model does not beat the mean baseline. Low-yield classifier Brier score is 0.306 versus 0.167 for training prevalence; lower is better. These results do not establish reliable forecasting or monetary savings. There are only 15 distinct weather environments despite 1,046 yield records. Genotypes may occur in training and testing at different locations. See [the baseline report](docs/Rice_Baseline_Results.md) for the design and limitations.

## Improvement experiment

The first improvement used nested location validation. Its predeclared search tested stronger regularisation, five training-fitted genetic PCs, genetic/weather interactions and environment-level forests. Candidate choices used inner held-out locations only. It remains available through Evaluation method alongside the original baseline and latest experiment.

Nested selection reduced RMSE to **1,045.3 kg/ha** from 1,228.9, but the mean baseline is still better at 1,036.5. Risk Brier score improved to **0.174** from 0.306, but prevalence remains better at 0.167. Genetic candidates were never selected. These are development findings, not externally validated forecasting skill. See [the improvement report](docs/Rice_Improvement_Results.md) and [the declared protocol](docs/Rice_Improvement_Protocol.md).

## Latest planting and full-SNP experiment

The default Planting and full-SNP evaluation adds observed planting context, 15-day weather summaries and a relationship benchmark retaining all SNP information. RMSE is **1,004.8 kg/ha**, about **3.1% better** than training mean; eight locations improve and four worsen. Genetics adds no improvement to context selection. Risk falls back to prevalence. Physical density and primary irrigation/fertiliser/soil remain unresolved. See [results](docs/Rice_Context_Results.md), [paper comparison](docs/Rice_Paper_Comparison.md) and [data search](docs/Rice_Management_Data_Search.md). This remains development evidence with substantial errors.

## Files

- `app.py`: rice dashboard, benchmark controls, trial explorer and readiness status.
- `src/rice_baseline.py`: cutoff checks, predictor construction, grouped evaluation and result loading.
- `src/rice_validation.py`: nested candidate selection, training-only genetic compression and location diagnostics.
- `src/rice_context.py`: planting/weather features and full-SNP relationship kernels.
- `data/raw/rice/`: original acquired sources.
- `data/processed/rice/`: audited tables, linkage maps and baseline results.
- `data/processed/rice/baseline/day_60/`: predictions, metrics, forecast windows and input SHA-256 hashes.
- `data/processed/rice/nested/day_60/`: nested results, inner scores, selected candidates, diagnostics and provenance.
- `data/processed/rice/context/day_60/`: new results, feature catalogue and within-trial rankings.
- `docs/`: research question, audits, linkage boundaries and results.
- `Research Papers/` and `Presentation_Figures/`: retained documents and figures.

Earlier wheat prototype modules and model artifacts are retained for reference and are not used by the rice dashboard. Their simulated benchmarks are not evidence for this rice study. No temporary generation scripts or additional launchers were created.

The 89 MB supporting BAAP genetics archive is retained locally and excluded from Git. Its source URL and checksum are recorded in `data/raw/rice/baap_genetics_2018/download_manifest.json`. It is not required to run the primary rice benchmark.
