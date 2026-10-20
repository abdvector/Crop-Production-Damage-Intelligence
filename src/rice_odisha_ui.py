"""Historical Odisha Kharif forecasts and transparent temporal evaluation."""
import json

import pandas as pd
import streamlit as st

from src.rice_odisha_seasonal import OUT as DATA, ROOT

OUT = DATA / "model"
YEAR = "agricultural_start_year"
CODE = "district_code_census2011"


@st.cache_data
def load_tables():
    names = ["selected_assessment_predictions.csv", "assessment_inputs.csv", "assessment_metrics.csv",
             "assessment_year_metrics.csv", "interval_year_metrics.csv", "selected_district_metrics.csv"]
    return {name: pd.read_csv(OUT / name, dtype={CODE: str}) for name in names}


def _percentage(value):
    return "Unavailable" if value is None or pd.isna(value) else f"{value:.1%}"


def render_odisha():
    st.subheader("Odisha Kharif rice study")
    st.write("Can early-season weather improve district rice yield forecasts over recent-yield baselines?")
    if not (OUT / "summary.json").exists():
        st.info("Daily weather is prepared. The declared model comparison and later-year assessment must complete before forecasts are shown.")
        return
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    choice = summary["selected_candidate"]
    tables = load_tables()
    predictions = tables["selected_assessment_predictions.csv"]
    inputs = tables["assessment_inputs.csv"]
    scores = tables["assessment_metrics.csv"]
    st.info("Historical replay of 2018–2022, issued on 31 August of each start year. This is not a live current-season forecast. Fixed 2011 district boundaries and assumed reporting delays remain limitations.")
    st.caption(f"Development-selected configuration: {choice['id']}. The choice was frozen before opening these later-year outcomes.")
    st.warning("Measured limitations: the selected model has negative later-year R squared, weak low-yield detection and very wide intervals. Its modest baseline error gains are uncertain across the five assessment years.")
    forecast, performance, methods = st.tabs(["Historical yield forecast", "Later-year performance", "Methods and data"])
    with forecast:
        a, b = st.columns([2, 1])
        names = predictions[[CODE, "district_source"]].drop_duplicates().set_index(CODE).district_source.to_dict()
        code = a.selectbox("Study district", sorted(names, key=lambda v: names[v]), format_func=lambda v: names[v].title())
        years = sorted(predictions.loc[predictions[CODE].eq(code), YEAR].unique().tolist(), reverse=True)
        year = b.selectbox("Kharif start year", years, format_func=lambda v: f"{v}–{str(v+1)[-2:]}")
        row = predictions.loc[predictions[CODE].eq(code) & predictions[YEAR].eq(year)].iloc[0]
        source = inputs.loc[inputs[CODE].eq(code) & inputs[YEAR].eq(year)].iloc[0]
        a, b, c = st.columns(3)
        a.metric("Estimated Kharif yield", f"{row.predicted_yield_kg_ha:,.0f} kg/ha")
        b.metric("Past-yield reference", f"{row.reference_yield_kg_ha:,.0f} kg/ha")
        c.metric("Forecast change from reference", f"{100*(row.predicted_yield_kg_ha/row.reference_yield_kg_ha-1):+.1f}%")
        st.write(f"Approximate 80% interval: **{row.lower_80_kg_ha:,.0f}–{row.upper_80_kg_ha:,.0f} kg/ha**.")
        st.caption(f"Later-year interval coverage: {summary['interval_coverage_80']:.1%}; mean width: {summary['mean_interval_width_kg_ha']:,.0f} kg/ha. Wide intervals mean substantial uncertainty; coverage is not guaranteed.")
        st.write("Point-forecast low-yield flag: **" + ("below" if row.predicted_low_yield else "not below") +
                 f" 80% of the historical reference** ({row.low_yield_threshold_kg_ha:,.0f} kg/ha).")
        st.caption("This flag is not a calibrated probability, injury measurement, aluminium diagnosis, causal loss estimate or financial saving.")
        st.bar_chart(pd.DataFrame({"Yield (kg/ha)": [row.reference_yield_kg_ha, row.predicted_yield_kg_ha,
                                                    row.low_yield_threshold_kg_ha]},
                                 index=["Historical reference", "Forecast", "Low-yield threshold"]), horizontal=True, color="#38BDA6")
        st.caption(f"Training outcomes end in {int(row.training_end_year)}; history uses {year-6}–{year-2}. Weather ends on 24 August {year}.")
        if not choice["weather"]:
            st.write("The selected configuration uses yield history. Weather was tested in the declared comparison, but it does not change this selected forecast.")
        with st.expander("Yield histories and observed early-season weather"):
            history = pd.DataFrame({"Start year": [year-lag for lag in range(6, 1, -1)],
                                    "Yield (kg/ha)": [source[f"yield_lag{lag}"] for lag in range(6, 1, -1)]})
            st.dataframe(history, hide_index=True, width="stretch")
            weather = pd.DataFrame({"Window": ["June", "July", "1–24 August"],
                "Rain total (mm)": [source[f"PRECTOTCORR_{m:02d}"] for m in (6, 7, 8)],
                "Mean Tmax (C)": [source[f"T2M_MAX_{m:02d}"] for m in (6, 7, 8)],
                "Mean Tmin (C)": [source[f"T2M_MIN_{m:02d}"] for m in (6, 7, 8)],
                "Mean humidity (%)": [source[f"RH2M_{m:02d}"] for m in (6, 7, 8)],
                "Mean solar energy (MJ/m2/day)": [source[f"ALLSKY_SFC_SW_DWN_{m:02d}"] for m in (6, 7, 8)]})
            st.dataframe(weather, hide_index=True, width="stretch")
            st.caption("Whole-district area-weighted reanalysis; these are calendar windows, not verified crop growth stages or field weather measurements.")
        reveal = st.checkbox("Reveal this Kharif harvest outcome")
        if reveal:
            st.write(f"Recorded yield: **{row.actual_yield_kg_ha:,.0f} kg/ha**. Absolute forecast error: **{abs(row.actual_yield_kg_ha-row.predicted_yield_kg_ha):,.0f} kg/ha**.")
        export = row.to_frame().T
        if not reveal:
            export = export.drop(columns=["actual_yield_kg_ha", "interval_covers"])
        st.download_button("Download Kharif replay forecast", export.to_csv(index=False), f"odisha_kharif_{code}_{year}.csv", "text/csv")
    with performance:
        st.write("The primary result is the configuration selected in 2009–2012. The 2018–2022 comparison does not select a replacement winner.")
        result = summary["selected_metrics"]
        a, b, c, d = st.columns(4)
        a.metric("Assessment district-years", summary["assessment_records"])
        b.metric("Equal-year MAE", f"{result['equal_year_mae_kg_ha']:,.0f} kg/ha")
        c.metric("RMSE", f"{result['rmse_kg_ha']:,.0f} kg/ha")
        d.metric("R squared", "Unavailable" if result["r_squared"] is None else f"{result['r_squared']:.3f}")
        display = scores.sort_values("candidate_order").copy()
        display.insert(1, "Selected in development", display.candidate.eq(choice["id"]))
        st.dataframe(display[["candidate", "Selected in development", "equal_year_mae_kg_ha", "rmse_kg_ha", "r_squared", "wape"]], hide_index=True, width="stretch")
        st.caption("Equal-year MAE is the declared primary metric. WAPE is a fraction. District rows within a year share shocks and are not independent time replications.")
        annual = tables["assessment_year_metrics.csv"]
        st.write("Errors by start year")
        st.line_chart(annual.loc[annual.candidate.isin([choice["id"], "Recent mean", "Last available yield"])].pivot(
            index=YEAR, columns="candidate", values="mae_kg_ha"))
        st.write("Paired year-level error comparisons")
        st.dataframe(pd.DataFrame(summary["paired_year_comparisons"]), hide_index=True, width="stretch")
        st.caption("Positive improvement means lower error than the named reference. The 95% bootstrap range resamples whole years; only a few years are available. The paired Ridge comparison holds the algorithm family fixed.")
        st.write("Approximate interval coverage and width by year")
        st.dataframe(tables["interval_year_metrics.csv"], hide_index=True, width="stretch")
        st.write("Low-yield flags on the same assessment records")
        a, b, c = st.columns(3)
        a.metric("Precision", _percentage(result["precision"]))
        b.metric("Recall", _percentage(result["recall"]))
        c.metric("F1", _percentage(result["f1"]))
        st.caption(f"True positives {result['true_positive']}; false positives {result['false_positive']}; false negatives {result['false_negative']}; true negatives {result['true_negative']}. Observed low-yield records: {result['low_yield_count']}. Undefined ratios are shown as unavailable.")
        with st.expander("District results and source exclusions"):
            st.dataframe(tables["selected_district_metrics.csv"], hide_index=True, width="stretch")
            st.write(f"Source labels excluded: {summary['assessment_labels_excluded']}; forecast rows excluded: {summary['forecast_rows_excluded']}.")
            st.dataframe(pd.read_csv(OUT / "assessment_exclusions.csv"), hide_index=True, width="stretch")
        st.download_button("Download selected Kharif assessment forecasts", (OUT / "selected_assessment_predictions.csv").read_bytes(), "odisha_kharif_assessment.csv", "text/csv")
    with methods:
        st.write("Official DES Kharif rice yield is converted from tonnes/ha to kg/ha. Thirty reviewed Odisha names link to fixed 2011 Census-derived reference polygons. Annual territorial equivalence and historical publication vintages remain unverified.")
        st.write("NASA daily weather covers 1 June–24 August: maximum/minimum temperature, rain, relative humidity and solar energy. Nineteen fixed summaries are compared with Y−2…Y−6 yields, their mean/trend, year and district. Target-year production and area never enter predictors.")
        st.write("Configuration selection: expanding-window 2009–2012. Uncertainty calibration: rolling 2014–2016. Assessment: sequential 2018–2022. Every forecast fits only through Y−2. Earlier assessment labels can enter later fitting under this fixed rule, but cannot tune the configuration.")
        st.write("No variety-linked protein, measured aluminium, farm management, soil or satellite variables are used in this district estimator. Earlier experiments remain available in the other workspaces.")
        st.markdown("Sources: [official DES report](https://www.data.desagri.gov.in/website/apy-query-report-web), [NASA POWER](https://power.larc.nasa.gov/), [DataMeet maps](https://projects.datameet.org/maps/) under [CC BY 2.5 India](https://creativecommons.org/licenses/by/2.5/in/).")
        with st.expander("Development comparison and frozen selection"):
            st.dataframe(pd.read_csv(OUT / "development_metrics.csv"), hide_index=True, width="stretch")
            st.json(json.loads((OUT / "selection.json").read_text(encoding="utf-8")))
        st.download_button("Download modelling methods", (ROOT / "docs/Rice_Odisha_Model_Implementation.md").read_bytes(), "odisha_model_methods.md", "text/markdown")
        st.download_button("Download source and preparation inputs", (OUT / "assessment_inputs.csv").read_bytes(), "odisha_assessment_inputs.csv", "text/csv")
