"""Rice yield research dashboard; app.py is the sole application entry point."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli
        cli.main(args=["run", str(PROJECT_ROOT / "app.py"), "--server.fileWatcherType=none", *sys.argv[1:]])
        raise SystemExit(0)

import streamlit as st
import pandas as pd
from src.rice_baseline import load_results, run_benchmark
from src.rice_validation import load_nested_results, run_nested_benchmark
from src.rice_context import load_context_results, run_context_benchmark
from src.rice_reliability import load_reliability, run_reliability
from src.rice_aluminium import load_aluminium_study
from src.rice_literature import load_literature_results, run_literature_benchmark
from src.rice_field_data import load_field_audit

st.set_page_config(page_title="Rice Yield Research", layout="wide")
st.markdown("""<style>
.block-container {max-width:1400px;padding-top:3rem;}
[data-testid="stMetric"] {background:#111C2E;border:1px solid #26364C;border-radius:10px;padding:18px;}
[data-testid="stMetricLabel"] {color:#A9B8CA;}
[data-testid="stTabs"] button {font-size:1rem;}
h1 {letter-spacing:-0.03em;}
</style>""", unsafe_allow_html=True)

st.title("Rice yield and low-yield risk")
st.caption("Birla Institute of Technology, Mesra | Department of Quantitative Economics and Data Science | Guide: Dr. Manish Kumar Pandey")
st.write("Forecasting yield per hectare at unseen locations using published trials, early-season weather, planting records and genetic markers.")
with st.sidebar:
    st.header("Research controls")
    evaluation = st.selectbox("Evaluation method", ["Planting and full-SNP validation", "Literature-guided validation", "Nested location validation", "Original fixed baseline"])
    contextual = evaluation == "Planting and full-SNP validation"
    literature = evaluation == "Literature-guided validation"
    nested = evaluation != "Original fixed baseline"
    cutoff = st.selectbox("Forecast date: days after seeding", [60, 30, 45, 75, 90])
    st.caption("Includes weather from seeding day through the selected day. Later observations are excluded.")
    st.write("Validation: hold out one complete location at a time.")
    if st.button("Run verified-data benchmark", type="primary", width="stretch"):
        progress = st.progress(0.0) if nested else None
        try:
            with st.spinner("Evaluating held-out locations..."):
                if nested:
                    runner = run_literature_benchmark if literature else run_context_benchmark if contextual else run_nested_benchmark
                    runner(cutoff, progress=lambda n, total, group: progress.progress(
                        (n - 1) / total, text=f"Location {n}/{total}: {group}"))
                    if contextual:
                        run_reliability(cutoff, progress=lambda text: progress.progress(0.95, text=text))
                else:
                    run_benchmark(cutoff)
        except (ValueError, OSError) as error:
            st.error(str(error))
        finally:
            if progress is not None:
                progress.empty()
    if contextual and st.button("Update reliability report", width="stretch",
                                disabled=load_context_results(cutoff) is None):
        try:
            with st.spinner("Evaluating location stability and separate prediction intervals..."):
                run_reliability(cutoff)
        except (ValueError, OSError) as error:
            st.error(str(error))
    st.divider()
    st.caption("Protein embeddings: pending variety linkage. Aluminium: separate CIRAD study. No causal damage or monetary savings are estimated.")

results = load_literature_results(cutoff) if literature else load_context_results(cutoff) if contextual else load_nested_results(cutoff) if nested else load_results(cutoff)
result_folder = "literature" if literature else "context" if contextual else "nested" if nested else "baseline"
validation, reliability, aluminium, explore, readiness = st.tabs(["Validation results", "Reliability and uncertainty", "Aluminium supporting study", "Trial explorer", "Data readiness"])
with validation:
    st.subheader("Transfer to unseen locations")
    if results is None:
        st.info("Run the benchmark for this forecast date to generate results from the acquired rice data.")
    else:
        metrics, predictions, folds, summary = results
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Eligible yield records", f"{summary['records']:,}")
        c2.metric("Rice genotypes", summary['genotypes'])
        c3.metric("Trial environments", summary['environments'])
        c4.metric("Held-out locations", summary['held_out_locations'])
        st.caption("Targets are published adjusted yield estimates at 14% moisture. Results are experimental validation, not farm deployment accuracy.")
        st.dataframe(metrics, hide_index=True, width="stretch",
                     column_config={"MAE_kg_ha":st.column_config.NumberColumn("MAE (kg/ha)",format="%.1f"),
                                    "RMSE_kg_ha":st.column_config.NumberColumn("RMSE (kg/ha)",format="%.1f"),
                                    "R2":st.column_config.NumberColumn("R squared",format="%.3f"),
                                    "bias_kg_ha":st.column_config.NumberColumn("Bias (kg/ha)",format="%.1f")})
        combined_name = "Literature full selection" if literature else "Context + full-SNP selection" if contextual else "Nested weather + genetics selection" if nested else "Weather + genetics Ridge"
        combined_rmse = metrics.loc[metrics.model == combined_name, "RMSE_kg_ha"].iloc[0]
        mean_rmse = metrics.loc[metrics.model == "Training mean", "RMSE_kg_ha"].iloc[0]
        if combined_rmse >= mean_rmse:
            st.warning("The procedure with genetics available does not beat the training-mean baseline at unseen locations. These results do not support deployment.")
        else:
            st.info(f"RMSE is {100 * (1 - combined_rmse / mean_rmse):.1f}% lower than the training-mean baseline. This is development validation; external reliability is not established.")
        if literature:
            previous = load_context_results(cutoff)
            if previous is not None:
                previous_rmse = previous[0].loc[previous[0].model.eq("Context + full-SNP selection"), "RMSE_kg_ha"].iloc[0]
                st.caption(f"Previous context benchmark RMSE: {previous_rmse:,.1f} kg/ha. Literature experiment RMSE: {combined_rmse:,.1f} kg/ha. The same records and outer locations are used.")
                with st.expander("Compare each location with the previous benchmark"):
                    earlier = previous[2].loc[previous[2].model.eq("Context + full-SNP selection"), ["held_out_location", "RMSE_kg_ha"]].rename(columns={"RMSE_kg_ha": "previous_RMSE_kg_ha"})
                    current = folds.loc[folds.model.eq(combined_name), ["held_out_location", "RMSE_kg_ha"]].rename(columns={"RMSE_kg_ha": "literature_RMSE_kg_ha"})
                    comparison = earlier.merge(current, on="held_out_location", validate="one_to_one")
                    comparison["improvement_kg_ha"] = comparison.previous_RMSE_kg_ha - comparison.literature_RMSE_kg_ha
                    st.dataframe(comparison, hide_index=True, width="stretch")
        if nested:
            st.caption("Candidate choices use inner held-out locations only. The outer test location is excluded from tuning. Each location receives equal weight in selection.")
            original = load_results(cutoff)
            if original is not None:
                original_rmse = original[0].loc[original[0].model == "Weather + genetics Ridge", "RMSE_kg_ha"].iloc[0]
                st.caption(f"Original fixed combined model RMSE: {original_rmse:,.1f} kg/ha. Original results are preserved separately.")
        model = st.selectbox("Inspect model", metrics.model.tolist(), index=metrics.model.tolist().index(combined_name))
        selected = predictions.loc[predictions.model == model]
        left, right = st.columns([3,2])
        with left:
            st.write("Observed and predicted yield (kg/ha)")
            st.scatter_chart(selected, x="observed_yield_kg_ha", y="predicted_yield_kg_ha", color="held_out_location", height=370)
        with right:
            st.write("Performance by held-out location")
            display_columns = ["held_out_location","test_records","MAE_kg_ha","bias_kg_ha"]
            if contextual or literature:
                display_columns.append("Pearson_r")
            st.dataframe(folds.loc[folds.model == model, display_columns], hide_index=True, height=370)
            if contextual or literature:
                st.caption("Within-location correlation can mix seasons. It does not measure absolute yield accuracy or isolate variety ranking; constant predictions have no defined correlation.")
        st.subheader("Low-yield risk: exploratory")
        st.write(summary['low_yield_definition'])
        a,b = st.columns(2)
        a.metric("Model Brier score", f"{summary['risk_Brier']:.3f}")
        b.metric("Training-prevalence Brier score", f"{summary['prevalence_Brier']:.3f}")
        st.caption("Lower Brier scores are better. This is low-yield risk, not observed crop damage. Probabilities have not been externally calibrated.")
        with st.expander("Evaluation assumptions and limitations"):
            if literature:
                st.write("The declared search preserves all thirteen earlier candidates and adds ten compact weather PLS/Ridge, balanced genomic PLS and centred genomic/reaction-norm candidates. Six weather summaries include diurnal temperature range and approximate VPD. Each transform uses training inputs only; candidate choice uses inner locations.")
                st.write("These are literature-guided adaptations, not exact published-model replications. The two-stage models learn genetic deviations from observed training environment means; no test environment mean is used. This dataset has already informed development, so the run is not an independent external test.")
                st.link_button("Rice PLS and reaction-norm study", "https://doi.org/10.1534/g3.119.400064")
            elif contextual:
                st.write("The declared search adds observed planting dates/methods, 15-day weather summaries, descriptive heat/rainfall proxies and a full-SNP relationship kernel. All positive genetic kernel components are retained. Penalties and model choices use inner locations only.")
                st.write("This is a genomic kernel benchmark, not an exact reproduction of the paper's Bayesian GBLUP. Physical planting density is excluded because spacing units and plants per hill are unresolved.")
                st.write("This development dataset has been inspected previously; external evaluation remains necessary.")
            elif nested:
                st.write("A predeclared candidate set compares stronger Ridge regularisation, five genetic PCs, weather/genetic interactions and environment-level forests. The mean and prevalence baselines can be selected. All scaling and PCA are fitted within training splits.")
                st.write("The dataset was previously inspected. Nested evaluation controls this parameter search, but is not an independent external test or proof of correct specification.")
            else:
                st.write("Ridge alpha is fixed at 100; logistic C is fixed at 0.1. Preprocessing is fitted within each training fold. These first-pass settings were not selected using held-out results.")
            for limitation in summary['limits']:
                st.write("- " + limitation)
        if nested:
            with st.expander("Location diagnostics and selected candidates"):
                diagnostics = pd.read_csv(PROJECT_ROOT / f"data/processed/rice/{result_folder}/day_{cutoff}/location_diagnostics.csv")
                if contextual or literature:
                    diagnostics = diagnostics.rename(columns={"weather_features_outside_training_range": "context_features_outside_training_range", "fraction_records_outside_weather_range": "fraction_records_outside_context_range"})
                st.dataframe(diagnostics, hide_index=True, width="stretch")
                st.dataframe(folds[["model", "held_out_location", "selected_candidate"]], hide_index=True, width="stretch")
                if contextual or literature:
                    st.write("Variety ranking within each trial environment")
                    st.dataframe(pd.read_csv(PROJECT_ROOT / f"data/processed/rice/{result_folder}/day_{cutoff}/environment_ranking.csv"), hide_index=True, width="stretch")
                    st.caption("Environment-only predictions are constant within a trial, so they cannot rank its varieties. A blank correlation means ranking is undefined, not zero measured skill.")
        st.download_button("Download held-out predictions", predictions.to_csv(index=False), "rice_held_out_predictions.csv", "text/csv")
with reliability:
    st.subheader("How stable are the findings?")
    reliable = load_reliability(cutoff) if contextual else None
    if literature:
        if results is None:
            st.info("Run the literature-guided benchmark for this forecast date first.")
        else:
            st.dataframe(pd.read_csv(PROJECT_ROOT / f"data/processed/rice/literature/day_{cutoff}/location_stability.csv"), hide_index=True, width="stretch")
            st.caption("Paired equal-location improvements against training mean, with descriptive 95% bootstrap ranges. Overlapping folds and prior development prevent treating these as formal significance tests.")
            st.info("Prediction intervals have not been calibrated for the literature-guided model. The context experiment's separate split intervals do not apply to this model.")
    elif not contextual:
        st.info("Select Planting and full-SNP validation to inspect its reliability experiment.")
    elif reliable is None:
        st.info("Run the planting benchmark or update its reliability report for this forecast date.")
    else:
        tables, reliability_summary = reliable
        st.write("Error comparisons resample entire locations, keeping each model paired with the same baseline locations.")
        st.dataframe(tables["location_stability"], hide_index=True, width="stretch")
        st.caption("Positive improvement means less error than training mean. A range crossing zero includes both improvement and deterioration. These are descriptive 95% bootstrap ranges over twelve locations, not proof of significance; cross-validation fits overlap.")
        st.subheader("Separate prediction-interval experiment")
        st.write("Six complete locations fit and select the model; four separate locations calibrate intervals; two assess them. This model differs from the main twelve-fold benchmark.")
        interval_metrics = tables["interval_metrics"]
        st.dataframe(interval_metrics, hide_index=True, width="stretch",
                     column_config={"target_coverage": st.column_config.NumberColumn("Coverage target (fraction)", format="%.2f"),
                                    "row_coverage": st.column_config.NumberColumn("Observed row coverage", format="%.3f"),
                                    "whole_location_coverage": st.column_config.NumberColumn("Whole-location coverage", format="%.3f")})
        st.warning("Four calibration locations can produce a finite 80% interval. The finite-sample 90% interval is unbounded; blank width/radius values mean no finite bound, not zero uncertainty. Nominal coverage assumes exchangeable locations, which is not established here.")
        st.caption("Scores use the maximum error within each calibration location. Only two previously inspected locations assess coverage; this is development evidence, not external validation or a guarantee for farms.")
        finite = tables["interval_predictions"].loc[tables["interval_predictions"].target_coverage.eq(0.8)]
        interval_model = st.selectbox("Interval model", finite.model.unique().tolist())
        interval_location = st.selectbox("Assessment location", finite.location_group.unique().tolist())
        shown = finite.loc[finite.model.eq(interval_model) & finite.location_group.eq(interval_location)]
        st.write("Assessment yields and 80% interval bounds (kg/ha)")
        st.line_chart(shown.set_index("source_csv_row")[["observed_yield_kg_ha", "predicted_yield_kg_ha", "lower_kg_ha", "upper_kg_ha"]], height=330)
        st.caption("The horizontal axis identifies original source rows; connecting lines do not represent time or a biological trend.")
        with st.expander("Split membership, calibration scores and model choice"):
            st.dataframe(tables["interval_split"], hide_index=True, width="stretch")
            st.dataframe(tables["calibration_scores"], hide_index=True, width="stretch")
            st.dataframe(tables["interval_candidate_scores"], hide_index=True, width="stretch")
        st.download_button("Download interval assessment", tables["interval_predictions"].to_csv(index=False),
                           "rice_split_interval_assessment.csv", "text/csv")
        st.subheader("Where environmental transfer is difficult")
        st.dataframe(tables["environment_transfer"], hide_index=True, width="stretch")
        st.caption("Distances, unseen categories and range flags use training inputs only. Largest differences describe a nearby trial; they do not identify causes of yield loss. An unflagged environment is not certified reliable.")
with aluminium:
    st.subheader("Rice families in two soil conditions")
    try:
        paired, soil_summaries, aluminium_summary = load_aluminium_study()
    except (ValueError, OSError) as error:
        st.error(str(error))
    else:
        a, b, c = st.columns(3)
        a.metric("Paired genetic families", aluminium_summary["paired_families"])
        b.metric("Mean LIM minus ALU", f"{aluminium_summary['mean_LIM_minus_ALU_kg_ha']:,.0f} kg/ha")
        c.metric("Independent site-seasons", aluminium_summary["independent_site_seasons"])
        st.write("Published spatially adjusted yields from the separate CIRAD experiment. Each point is the same genetic family observed under ALU and LIM conditions.")
        st.scatter_chart(paired, x="ALU_yield_kg_ha", y="LIM_yield_kg_ha", height=350)
        st.caption(f"LIM yield is higher for {aluminium_summary['families_with_higher_LIM_yield']} of {aluminium_summary['paired_families']} families. This describes the condition contrast; it does not isolate an aluminium effect.")
        st.warning("Liming changes pH and several nutrients as well as aluminium. One site-season cannot establish transfer to new regions. These families and soil measurements are not merged into the main forecasting trials.")
        st.write("Published soil-condition measurements")
        st.dataframe(soil_summaries, hide_index=True, width="stretch")
        st.caption("Condition-level summaries, not individual plot measurements. Published yield scaling is preserved; harvested-area clarification remains pending.")
        with st.expander("Paired family yields"):
            st.dataframe(paired, hide_index=True, width="stretch")
        st.download_button("Download paired condition comparison", paired.to_csv(index=False),
                           "rice_aluminium_condition_comparison.csv", "text/csv")
        st.link_button("Supporting study methods", "https://doi.org/10.1371/journal.pone.0307009")
with explore:
    st.subheader("Published rice trials")
    trials = pd.read_csv(PROJECT_ROOT / "data/processed/rice/trial_metadata.csv")
    st.dataframe(trials[["environment_id","country","location","year","season","seeding_date","establishment_date"]], hide_index=True, width="stretch")
    if results is not None:
        window = pd.read_csv(PROJECT_ROOT / f"data/processed/rice/{result_folder}/day_{cutoff}/forecast_windows.csv")
        st.write("Weather windows used in this benchmark")
        st.dataframe(window, hide_index=True, width="stretch")
        if contextual:
            st.write("Planting and weather inputs used in this experiment")
            feature_folder = PROJECT_ROOT / f"data/processed/rice/context/day_{cutoff}"
            st.dataframe(pd.read_csv(feature_folder / "environment_features.csv"), hide_index=True, width="stretch")
            with st.expander("Feature provenance and units"):
                st.dataframe(pd.read_csv(feature_folder / "feature_catalogue.csv"), hide_index=True, width="stretch")
        elif literature:
            feature_folder = PROJECT_ROOT / f"data/processed/rice/literature/day_{cutoff}"
            st.write("Compact weather inputs added by the literature experiment")
            st.dataframe(pd.read_csv(feature_folder / "compact_features.csv"), hide_index=True, width="stretch")
            st.dataframe(pd.read_csv(feature_folder / "compact_feature_catalogue.csv"), hide_index=True, width="stretch")
            st.caption("VPD is an approximation from daily temperatures and mean humidity. Rainfall is not irrigation. Calendar windows stop at the issue date and do not claim observed reproductive-stage timing.")
with readiness:
    st.subheader("What the current model uses")
    st.dataframe(pd.DataFrame([
        ["Yield", "Published adjusted labels; 10 conflicting records excluded"],
        ["Genetics", "882 SNPs linked to 107 genotypes; full relationship kernel available in the planting experiment"],
        ["Weather", "NASA POWER estimates truncated at the selected forecast day"],
        ["Protein embeddings", "Full variety-linked sequences not verified; not used"],
        ["Soil and aluminium", "CIRAD condition summaries available for a separate population; not used here"],
        ["Planting", "Recorded dates, establishment method and source spacing categories available; physical density unresolved"],
        ["Irrigation and fertiliser", "Detailed rates/amounts not verified for these trials; not used"],
        ["Additional disease study", "10 publisher-checksummed irrigation/nitrogen files acquired; no yield labels or primary-trial mapping"],
        ["Additional long-term yields", "IRRI 1974 archive files require permission; metadata acquired only"],
    ], columns=["Component","Status"]), hide_index=True, width="stretch")
    st.write("Research question: How accurately can early-season weather, planting information and genetic markers predict rice yield per hectare at unseen locations, and do genetic markers improve prediction beyond environmental inputs?")
    st.caption("Low-yield risk is secondary. Protein embeddings are optional future work requiring verified variety-to-sequence links. Aluminium remains a separate supporting analysis. Restricted IRRI files are not required for the current project.")
    st.link_button("Primary dataset and methods", "https://doi.org/10.1186/s12284-023-00623-6")
    st.subheader("Indian field-survey extension: preparation stage")
    field_audit = load_field_audit()
    if field_audit is not None:
        field_summary, field_coverage, field_policy = field_audit
        a, b, c = st.columns(3)
        a.metric("Raw survey records", f"{field_summary['raw_rows']:,}")
        b.metric("Candidates for weather linkage", f"{field_summary['candidate_weather_rows']:,}")
        c.metric("Survey years", "2017–2019")
        st.info("The survey is downloaded and audited. No field-survey forecast model has been trained. Daily weather through day 60 after field establishment and management timing checks are still required.")
        st.caption("These counts describe the raw archive, not the paper's filtered analysis sample. Repeated coordinates and reported yields require further checks. Candidate counts do not establish model readiness.")
        st.dataframe(field_coverage, hide_index=True, width="stretch")
        with st.expander("Which survey variables can support a forecast?"):
            st.dataframe(field_policy, hide_index=True, width="stretch")
        st.link_button("Field-survey source and methods", "https://doi.org/10.1038/s41467-024-52448-6")
    else:
        st.write("Field-survey audit is not available in this checkout.")
