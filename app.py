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
st.write("A research benchmark using published rice trials, genetic markers and weather observed before the forecast date.")
with st.sidebar:
    st.header("Research controls")
    cutoff = st.selectbox("Forecast date: days after seeding", [60, 30, 45, 75, 90])
    st.caption("Includes weather from seeding day through the selected day. Later observations are excluded.")
    st.write("Validation: hold out one complete location at a time.")
    if st.button("Run verified-data benchmark", type="primary", width="stretch"):
        try:
            with st.spinner("Evaluating held-out locations..."):
                run_benchmark(cutoff)
        except (ValueError, OSError) as error:
            st.error(str(error))
    st.divider()
    st.caption("Protein embeddings: pending variety linkage. Aluminium: separate CIRAD study. No causal damage or monetary savings are estimated.")

results = load_results(cutoff)
validation, explore, readiness = st.tabs(["Validation results", "Trial explorer", "Data readiness"])
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
        combined_rmse = metrics.loc[metrics.model == "Weather + genetics Ridge", "RMSE_kg_ha"].iloc[0]
        mean_rmse = metrics.loc[metrics.model == "Training mean", "RMSE_kg_ha"].iloc[0]
        if combined_rmse >= mean_rmse:
            st.warning("The combined model does not beat the training-mean baseline at unseen locations. These results do not support deployment.")
        model = st.selectbox("Inspect model", metrics.model.tolist(), index=3)
        selected = predictions.loc[predictions.model == model]
        left, right = st.columns([3,2])
        with left:
            st.write("Observed and predicted yield (kg/ha)")
            st.scatter_chart(selected, x="observed_yield_kg_ha", y="predicted_yield_kg_ha", color="held_out_location", height=370)
        with right:
            st.write("Performance by held-out location")
            st.dataframe(folds.loc[folds.model == model, ["held_out_location","test_records","MAE_kg_ha","bias_kg_ha"]], hide_index=True, height=370)
        st.subheader("Low-yield risk: exploratory")
        st.write(summary['low_yield_definition'])
        a,b = st.columns(2)
        a.metric("Model Brier score", f"{summary['risk_Brier']:.3f}")
        b.metric("Training-prevalence Brier score", f"{summary['prevalence_Brier']:.3f}")
        st.caption("Lower Brier scores are better. This is low-yield risk, not observed crop damage. Probabilities have not been externally calibrated.")
        with st.expander("Evaluation assumptions and limitations"):
            st.write("Ridge alpha is fixed at 100; logistic C is fixed at 0.1. Preprocessing is fitted within each training fold. These first-pass settings were not selected using held-out results.")
            for limitation in summary['limits']:
                st.write("- " + limitation)
        st.download_button("Download held-out predictions", predictions.to_csv(index=False), "rice_held_out_predictions.csv", "text/csv")
with explore:
    st.subheader("Published rice trials")
    trials = pd.read_csv(PROJECT_ROOT / "data/processed/rice/trial_metadata.csv")
    st.dataframe(trials[["environment_id","country","location","year","season","seeding_date","establishment_date"]], hide_index=True, width="stretch")
    if results is not None:
        window = pd.read_csv(PROJECT_ROOT / f"data/processed/rice/baseline/day_{cutoff}/forecast_windows.csv")
        st.write("Weather windows used in this benchmark")
        st.dataframe(window, hide_index=True, width="stretch")
with readiness:
    st.subheader("What the current model uses")
    st.dataframe(pd.DataFrame([
        ["Yield", "Published adjusted labels; 10 conflicting records excluded"],
        ["Genetics", "882 SNPs linked to 107 rice genotypes"],
        ["Weather", "NASA POWER estimates truncated at the selected forecast day"],
        ["Protein embeddings", "Full variety-linked sequences not verified; not used"],
        ["Soil and aluminium", "CIRAD condition summaries available for a separate population; not used here"],
        ["Management", "Detailed rates/amounts not verified for these trials; not used"],
    ], columns=["Component","Status"]), hide_index=True, width="stretch")
    st.write("Research question: Does verified molecular information improve pre-harvest yield and low-yield-risk predictions beyond environmental and genetic data?")
    st.caption("The current benchmark establishes the comparison model. The ESM extension remains conditional on confirmed protein-to-variety links.")
    st.link_button("Primary dataset and methods", "https://doi.org/10.1186/s12284-023-00623-6")
