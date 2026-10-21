> Current primary workflow: [regional annual rice yield forecasting](../Rice_Regional_Forecast.md). This page preserves the earlier field/trial research scope and readiness findings; those studies remain supporting evidence.

# Research question and data readiness

Updated 11 October 2026.

## Main question

How accurately can early-season weather, planting information and genetic markers predict rice yield per hectare at unseen locations, and do genetic markers improve prediction beyond environmental inputs?

Low-yield risk is a secondary outcome. Verified protein embeddings are an optional extension, not a prerequisite for completing the current research question. Aluminium remains a separate supporting analysis. The restricted IRRI files are optional additional data. See [Rice_Reliability_Protocol.md](Rice_Reliability_Protocol.md) for location-level uncertainty and the separate interval experiment.

Protein embeddings are explanatory inputs. The project does not forecast protein structures. ESM-2 operates on amino-acid sequences; its representations can contain learned structural/functional information, but are not explicit measurements of a variety's three-dimensional structure or resistance.

Target: published trial yield in kg/ha, with the existing adjusted-label limitations. Low-yield risk must be defined before evaluation, using a defensible threshold or training-only reference. It is a yield-risk proxy; do not call it observed crop damage percentage. Actual disease severity or causal production loss requires its own observed target and design.

## Ready to start

The Nguyen panel, linked markers and NASA weather support a weather-plus-genetics research benchmark: 1,046 yield entries passing the repeated-key audit, 107 marker genotypes, 882 SNPs and 15 trial environments. Weather has been acquired through harvest; choose an issue date and use only observations available by that date. Forecasting across environments is a validation objective, not an established capability. The small number of independent environments limits conclusions.

## Molecular extension: still conditional

The subsequent nested improvement experiment reduced the original combined model's RMSE but still did not beat the mean baseline. Compressed genetic candidates were not selected. See [Rice_Improvement_Results.md](Rice_Improvement_Results.md); this is development evidence, not an independent external evaluation.

Ptr supplementary data provide 40 candidate alias matches to the primary panel. These are not yet independently verified sample mappings or complete protein alleles. We now also have the Ptr reference FASTA and JSON for UniProt A0A2U9K3S3. The entry is unreviewed; the sequence download is a reference, not a verified sequence for each matched rice variety. The existing STAR1/STAR2 reference sequences likewise do not supply trial-specific variation.

Next establish accession identity, the correct gene/transcript and coding coordinates, reference orientation, and verified amino-acid variants/full protein sequences for the analysis subset. Two diagnostic SNPs or broad haplotype labels do not automatically recover every amino-acid difference. Do not fabricate complete variety proteins by assigning a reference or a single mutation without supporting evidence.

Then generate frozen ESM embeddings, fit dimensionality reduction/preprocessing within each training fold, and compare models with and without embeddings on the same observations and splits. Compare against ordinary SNP/gene-allele predictors as well; embeddings must show added value, not merely encode the same two alleles with many numbers. A small number of unique alleles provides few distinct protein representations despite many repeated yield rows. ESM model weights have not been downloaded yet because the required genotype-linked sequence inputs are still unresolved.

## Separate supporting studies

CIRAD provides genetic families and yield in two soil conditions at one site-season. It is a separate aluminium-related analysis; liming changes other soil properties too. BAAP nitrogen data and its downloaded variants form another candidate linked study, but its yield is g/plant and reference alleles are provisional. Smart-Valleys supplies soil/management/weather fields but lacks an established molecular accession mapping and complete unit/provenance documentation. None can supply missing soil/Al observations for the Nguyen trials by substitution.

## Readiness decision

The latest literature-guided experiment achieves RMSE 982.5 kg/ha, compared with 1,004.8 for the earlier context experiment and 1,036.5 for training mean. Its improvement is concentrated in Los Banos; genetic benefit remains negligible and risk still uses prevalence. No new data were required. This is development evidence with substantial remaining error. See [Rice_Literature_Results.md](Rice_Literature_Results.md).

The planting/full-SNP experiment now achieves RMSE about 1,005 kg/ha versus 1,037 for training mean, a modest development gain. Genetic candidates add no improvement to context selection, and risk uses prevalence. Additional disease/management observations were acquired but do not add linked yield records. See [Rice_Context_Results.md](Rice_Context_Results.md) and [Rice_Management_Data_Search.md](Rice_Management_Data_Search.md). Primary soil, irrigation, fertiliser, physical density and protein links remain unresolved.

Enough data to start the environmental/genetic benchmark and molecular linkage work. Not enough verified linked data to train the complete protein-embedding extension or an all-variable soil/aluminium/management model. No further indiscriminate downloads are required. The first rice baseline has now been evaluated at a 60-day cutoff with 12 held-out locations. Weather-plus-genetics Ridge did not beat the training-mean comparator, and the low-yield classifier did not beat training prevalence. See [Rice_Baseline_Results.md](Rice_Baseline_Results.md). Matched molecular inputs remain unresolved.

Sources:

- https://link.springer.com/article/10.1186/s12284-023-00623-6
- https://github.com/facebookresearch/esm
- https://www.uniprot.org/uniprotkb/A0A2U9K3S3/entry
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13492586/

## Additional acquisition on 11 October 2026

CIRAD measured soil-condition summaries have now been extracted from published Table 1, with means, standard deviations, units and sampling depth. Six published Ptr coding records and their annotated protein translations have also been acquired. They represent named cultivars absent from the primary metadata under exact normalised-name matching, so the molecular extension remains conditional on verified allele-to-yield-genotype assignment. These downloads improve source coverage, not the number of linked independent trial environments. See `Additional_Rice_Downloads.md` for locations and limitations.
