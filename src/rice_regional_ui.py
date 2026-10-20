"""Forecast-first dashboard views, called by the sole app.py entry point."""
import json

import numpy as np
import pandas as pd
import streamlit as st

from src.rice_regional import OUT, CLIMATE, HISTORY, NUMERIC, forecast, load_study


@st.cache_data
def load_tables():
    return pd.read_csv(OUT / "district_years.csv"), pd.read_csv(OUT / "assessment_predictions.csv")


def render_regional():
    summary = load_study()
    if summary is None:
        st.info("The regional study is being prepared. Results appear after data checks and training complete.")
        return
    table, predictions = load_tables()
    forecast_tab, evidence, data = st.tabs(["Yield forecast", "Performance on later years", "Data and research scope"])
    with forecast_tab:
        st.subheader("Rice yield outlook")
        st.write("Choose a historical district and agricultural year. The model estimates annual rice yield using information through 31 August of the starting year.")
        st.info("Historical replay: 2012–2017. The available yield archive ends in 2017; this is not a live 2026 forecast. District names represent historical 1966 boundaries.")
        a, b, c = st.columns([1, 2, 1])
        state = a.selectbox("State", sorted(predictions.state.unique()))
        available = predictions.loc[predictions.state.eq(state), ["district_id", "district"]].drop_duplicates().sort_values("district")
        district_id = b.selectbox("Historical district", available.district_id.tolist(), format_func=lambda v: available.set_index("district_id").at[v, "district"])
        years = sorted(predictions.loc[predictions.district_id.eq(district_id), "year"].unique().tolist(), reverse=True)
        year = c.selectbox("Agricultural start year", years, format_func=lambda v: f"{v}–{str(v+1)[-2:]}")
        row = table.loc[table.district_id.eq(district_id) & table.year.eq(year)].copy()
        st.caption(f"Forecast cutoff: 31 August {year}. Historical yields use {year-6}–{year-2}; {year-1} and current-year yield are excluded.")
        with st.expander("Historical yield inputs", expanded=False):
            st.caption("Edit past yields for a hypothetical history scenario. All values are kg/ha. The reference and trend are calculated automatically.")
            past = pd.DataFrame({"Year": [year-lag for lag in range(2, 7)],
                                 "Rice yield (kg/ha)": [float(row.iloc[0][f"yield_lag{lag}"]) for lag in range(2, 7)]})
            past_edited = st.data_editor(past, disabled=["Year"], hide_index=True, width="stretch", key=f"history_{district_id}_{year}")
            for i, lag in enumerate(range(2, 7)):
                row.loc[:, f"yield_lag{lag}"] = past_edited.iloc[i]["Rice yield (kg/ha)"]
            row = row.drop(columns=["reference_yield", "history_trend"])
        uses_weather = summary["selected_model"].startswith("Weather")
        if not uses_weather:
            st.caption("The development comparison selected a history-based model. Weather is shown for the research comparison and does not change this forecast.")
        with st.expander("Weather observations and scenario inputs", expanded=False):
            st.write("Monthly weather estimates used in the candidate comparison. Rainfall is monthly mean daily rainfall in mm/day. A weather scenario only changes a forecast if a weather-based estimator was selected.")
            weather = pd.DataFrame({"Month": ["June", "July", "August"],
                "Maximum temperature (C)": [float(row.iloc[0][f"T2M_MAX_{m:02d}"]) for m in [6, 7, 8]],
                "Minimum temperature (C)": [float(row.iloc[0][f"T2M_MIN_{m:02d}"]) for m in [6, 7, 8]],
                "Rainfall (mm/day)": [float(row.iloc[0][f"PRECTOTCORR_{m:02d}"]) for m in [6, 7, 8]],
                "Relative humidity (%)": [float(row.iloc[0][f"RH2M_{m:02d}"]) for m in [6, 7, 8]]})
            edited = st.data_editor(weather, disabled=["Month"] if uses_weather else True, hide_index=True, width="stretch", key=f"weather_{district_id}_{year}")
            for p, label in zip(["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"], weather.columns[1:]):
                for i, m in enumerate([6, 7, 8]):
                    row.loc[:, f"{p}_{m:02d}"] = edited.iloc[i][label]
        try:
            result = forecast(row).iloc[0]
        except (ValueError, OSError) as error:
            st.error(str(error))
            return
        changed = not np.allclose(row[CLIMATE + HISTORY[:5]].to_numpy(), table.loc[row.index, CLIMATE + HISTORY[:5]].to_numpy(), equal_nan=True)
        if changed:
            st.caption("A hypothetical input scenario is active.")
        a, b, c = st.columns(3)
        a.metric("Estimated annual yield", f"{result.predicted_yield_kg_ha:,.0f} kg/ha")
        b.metric("Historical reference", f"{result.reference_yield_kg_ha:,.0f} kg/ha")
        change = 100 * (result.predicted_yield_kg_ha / result.reference_yield_kg_ha - 1)
        c.metric("Expected change from reference", f"{change:+.1f}%")
        st.write(f"Approximate 80% yield interval: **{result.lower_80_kg_ha:,.0f}–{result.upper_80_kg_ha:,.0f} kg/ha**.")
        if summary["risk_beats_prevalence"] and summary["risk_auc"] > .5:
            st.write(f"Estimated chance of yield below **{result.low_yield_threshold_kg_ha:,.0f} kg/ha**: **{result.low_yield_probability:.1%}**.")
        else:
            st.caption("Low-yield probabilities rank outcomes poorly in the later-year test. They remain research diagnostics and are not shown here as reliable alerts.")
        st.caption("Low yield means at least 20% below the five-year historical reference. This does not identify disease, aluminium damage, causal losses or proven financial savings. Interval and risk reliability are measured in Performance on later years.")
        if result.outside_training_range:
            st.warning("Some inputs exceed the estimator's fitting-period range: " + result.outside_training_range + ". Treat this result as extrapolation.")
        chart = pd.DataFrame({"Yield (kg/ha)": [result.reference_yield_kg_ha, result.predicted_yield_kg_ha, result.low_yield_threshold_kg_ha]},
                             index=["Historical reference", "Forecast", "Low-yield threshold"])
        st.bar_chart(chart, horizontal=True, color="#38BDA6")
        if st.checkbox("Reveal the recorded harvest outcome"):
            if changed:
                st.caption("The recorded outcome belongs to the original observed inputs, not the hypothetical scenario.")
            observed = float(table.loc[row.index, "yield_kg_ha"].iloc[0])
            st.write(f"Recorded annual yield: **{observed:,.0f} kg/ha**. Forecast absolute error: **{abs(observed-result.predicted_yield_kg_ha):,.0f} kg/ha**.")
        st.download_button("Download this forecast", result.to_frame().T.assign(district_id=district_id, state=state, agricultural_start_year=year,
                           forecast_cutoff=f"{year}-08-31", hypothetical_inputs=changed).to_csv(index=False),
                           file_name=f"rice_forecast_{district_id}_{year}.csv", mime="text/csv")
        with st.expander("Yield history and input template"):
            history = pd.DataFrame({"Agricultural start year": [year-lag for lag in range(6, 1, -1)], "Rice yield (kg/ha)": [float(row.iloc[0][f"yield_lag{lag}"]) for lag in range(6, 1, -1)]})
            st.line_chart(history.set_index("Agricultural start year"))
            required = ["district_id", "year"] + HISTORY[:5] + (CLIMATE if uses_weather else [])
            st.download_button("Download inference input template", row[required].to_csv(index=False), "rice_forecast_inputs.csv", "text/csv")
            uploaded = st.file_uploader("Replay a batch of historical forecast inputs", type=["csv"])
            if uploaded is not None:
                try:
                    incoming = pd.read_csv(uploaded)
                    if len(incoming) > 10000:
                        raise ValueError("Use at most 10,000 rows per batch")
                    batch = forecast(incoming)
                    st.dataframe(batch, hide_index=True, width="stretch")
                    st.download_button("Download batch predictions", batch.to_csv(index=False), "rice_batch_forecasts.csv", "text/csv")
                except (ValueError, OSError, KeyError) as error:
                    st.error(str(error))
    with evidence:
        st.subheader("Forecasts tested on 2012–2017")
        st.write(f"Selected by expanding-window evaluation in 1998–2005: **{summary['selected_model']}**. The fixed estimator was fitted through 2004; 2006–2011 calibrated uncertainty. Later-year outcomes did not choose or tune the model.")
        a, b, c, d = st.columns(4)
        a.metric("Test district-years", f"{summary['assessment_records']:,}")
        b.metric("MAE", f"{summary['regression']['mae_kg_ha']:,.0f} kg/ha")
        c.metric("RMSE", f"{summary['regression']['rmse_kg_ha']:,.0f} kg/ha")
        d.metric("R squared", f"{summary['regression']['r_squared']:.3f}")
        st.dataframe(pd.read_csv(OUT / "assessment_metrics.csv"), hide_index=True, width="stretch")
        st.caption("R squared can reflect stable differences between districts. Compare the district-history baselines to judge additional forecasting value. Target-year harvested area and production are never predictors.")
        st.write(f"Approximate 80% interval: observed coverage **{summary['interval_coverage_80']:.1%}**, average width **{summary['mean_interval_width_kg_ha']:,.0f} kg/ha**. Temporal and regional dependence prevent a guaranteed coverage claim.")
        st.write(f"Low-yield risk Brier score: **{summary['risk_brier']:.4f}**, versus **{summary['prevalence_brier']:.4f}** for development prevalence; lower is better. ROC AUC: **{summary['risk_auc']:.3f}**. Observed low-yield frequency: **{summary['assessment_low_yield_rate']:.1%}**.")
        st.dataframe(pd.read_csv(OUT / "risk_calibration.csv"), hide_index=True, width="stretch")
        st.write("Results by agricultural start year")
        st.dataframe(pd.read_csv(OUT / "assessment_year_metrics.csv"), hide_index=True, width="stretch")
        st.write("Results by state")
        st.dataframe(pd.read_csv(OUT / "assessment_state_metrics.csv"), hide_index=True, width="stretch")
        with st.expander("Development comparison and declared protocol"):
            st.dataframe(pd.read_csv(OUT / "development_metrics.csv"), hide_index=True, width="stretch")
            st.json(json.loads((OUT / "protocol.json").read_text()))
        st.download_button("Download all later-year forecasts", (OUT / "assessment_predictions.csv").read_bytes(), "rice_test_forecasts.csv", "text/csv")
    with data:
        st.subheader("A focused, reproducible rice forecasting study")
        st.write("Research question: can weather through August improve annual district rice yield and low-yield-risk forecasts over recent-yield baselines in eastern India?")
        st.write("The model uses 50 historical districts across Bihar, Jharkhand, Odisha (labelled Orissa in the source), Chhattisgarh and West Bengal. Agricultural year 2017 means 2017–18. The annual target combines rice seasons; it is not a Kharif-only or individual farm forecast.")
        st.markdown("Yield source: [ICRISAT District Level Database](https://doi.org/10.21421/D2/XFB1BZ), retrieved directly from the provider's API. Weather: [NASA POWER](https://power.larc.nasa.gov/), monthly gridded estimates at the provider's district coordinates.")
        st.write("Predictors: five past rice yields from Y−2 to Y−6; their mean and trend; year; district/state and source coordinates; June, July and August maximum temperature, minimum temperature, rainfall and relative humidity. Two years of reporting delay are assumed conservatively; historical release dates are not verified.")
        st.write("Protein, aluminium and plot management are retained in Earlier research. They do not have a verified district-year link and are excluded from this estimator. District effects summarize persistent regional differences without claiming to measure soil chemistry or protein biology.")
        st.warning("This is a historical forecasting prototype. Updated official yields, boundary mapping and timely weather must be supplied and revalidated before forecasting a current season. Weather uses representative points rather than district-wide rice masks; source-coordinate accuracy is not independently established. Reanalysis can be revised after a forecast date.")
        coordinate_check = OUT / "coordinate_screen.json"
        if coordinate_check.exists():
            screen = json.loads(coordinate_check.read_text())
            st.caption("A modern state-boundary screen flags four source coordinates for review. It does not verify historical district centroids. No source values or test cohort were changed after seeing assessment results.")
            st.dataframe(pd.DataFrame(screen["flagged"]), hide_index=True, width="stretch")
        st.json(json.loads((OUT / "data_audit.json").read_text()))
        linkage = OUT.parent / "predictor_audit"
        if (linkage / "summary.json").exists():
            with st.expander("Predictor linkage audit and next data needs"):
                audit = json.loads((linkage / "summary.json").read_text(encoding="utf-8"))
                st.write("The local audit checks source labels, historical lags and weather joins. It does not retrain the forecast or combine farm and district records.")
                a, b = st.columns(2)
                a.metric("District rows with matched history and weather", f"{audit['regional']['complete_history_weather_records']:,}")
                b.metric("Separate 2018 rows with timed management", f"{audit['field']['matched_2018_management_records']:,}")
                st.warning("Weather dates are truncated, but historical publication availability is unverified. NASA reports typical publication delays; these are retrospective archive studies rather than verified real-time backtests.")
                seasonal_available = (OUT.parent / "seasonal_source/summary.json").exists()
                st.write("Official Kharif rice labels have now been acquired; compatible district boundaries and dated weather are the next requirements." if seasonal_available else "Next priority: official Kharif rice yield records with units, agricultural years and compatible district boundaries.")
                st.caption("Annual/all-season labels cannot be renamed Kharif. New weather or management features must match the same geographic units and dates.")
                st.caption("The existing annual-yield model and its saved results are unchanged. Nonmissing values alone do not establish measurement quality or availability before a forecast.")
                st.dataframe(pd.read_csv(linkage / "coverage.csv").drop(columns="columns"), hide_index=True, width="stretch")
                st.download_button("Download predictor coverage audit", (linkage / "coverage.csv").read_bytes(), "rice_predictor_coverage.csv", "text/csv")
                st.markdown("Sources: [NASA publication delays](https://power.larc.nasa.gov/docs/faqs/data/), [official APY query form](https://www.data.desagri.gov.in/website/apy-query-report-web). The original audit preceded the subsequent official seasonal-data acquisition shown below.")
        seasonal = OUT.parent / "seasonal_source"
        if (seasonal / "summary.json").exists():
            with st.expander("Official Kharif rice source: acquired, awaiting boundary verification"):
                source = json.loads((seasonal / "summary.json").read_text(encoding="utf-8"))
                st.write("Official DES report: Rice, Kharif, agricultural years 1997–98 through 2022–23. This is a separate source for a future study; it is not the annual model currently serving forecasts.")
                a, b, c = st.columns(3)
                a.metric("National geographic report rows", f"{source['national_district_rows']:,}")
                b.metric("Five-state geographic rows", sum(source["five_state_district_rows"].values()))
                c.metric("Positive complete development triplets", f"{source['positive_complete_development_triplets']:,}")
                st.caption("Development years end in 2017–18. The 515 missing/nonpositive combinations are retained with flags. District-name rows are not yet verified stable geographic units.")
                st.warning("Not ready for model fitting: district codes/boundary histories and new aligned weather are not verified. Start-year 2018–2022 numeric outcomes remain reserved in the local raw report.")
                st.write("Official yield headers are tonnes/ha. Development preparation retains source values and multiplies by 1,000 for kg/ha. Same-year area and production are audit fields, not forecasting inputs.")
                st.dataframe(pd.DataFrame(list(source["five_state_district_rows"].items()), columns=["State", "Geographic report rows"]), hide_index=True, width="stretch")
                st.download_button("Download seasonal-source coverage metadata", (seasonal / "state_year_coverage.csv").read_bytes(), "rice_kharif_coverage.csv", "text/csv")
        geography = OUT.parent / "seasonal_geography"
        if (geography / "summary.json").exists():
            with st.expander("Census reference geography and territorial changes"):
                geo = json.loads((geography / "summary.json").read_text(encoding="utf-8"))
                counts = geo["source_identity_status_counts"]
                a, b, c = st.columns(3)
                a.metric("Exact 2011 reference-name matches", counts["exact_case_punctuation_2011_reference"])
                b.metric("Reviewed alias candidates", counts["reviewed_alias_to_2011_reference"])
                c.metric("Units requiring different territorial geometry", counts["post2011_territorial_unit_not_same_geometry"])
                st.write("The official Census register has 640 unique district codes. A pinned DataMeet-derived map supplies 129 valid reference polygons for the five states. Census identifiers are distinct from current LGD codes, which remain unverified.")
                st.warning("A matching name or code does not prove unchanged borders. No district has been certified for the entire 1997–2022 span, and no new row is marked weather-ready. The twenty changed units cannot inherit whole old parent polygons.")
                st.caption("Example: Purba and Paschim Bardhaman are parts of the old Barddhaman district, not two aliases for the same whole polygon. Sarangarh–Bilaigarh has more than one parent lineage.")
                table = pd.read_csv(geography / "district_crosswalk.csv", dtype={"district_code_census2011_reference": str})
                st.dataframe(table[["state_source", "district_source", "match_status", "district_code_census2011_reference", "related_2011_ancestor_codes_not_identity", "reviewed_change_years"]], hide_index=True, width="stretch")
                st.download_button("Download district identity crosswalk", (geography / "district_crosswalk.csv").read_bytes(), "rice_district_crosswalk.csv", "text/csv")
                st.download_button("Download territorial year flags", (geography / "district_year_flags.csv").read_bytes(), "rice_territorial_flags.csv", "text/csv")
                st.caption("DataMeet Community Maps Project, CC BY 2.5 India. Geometry is a third-party reference, not an authoritative survey or rice-area weather mask. Newer numeric outcomes were not read in this review.")
        odisha = OUT.parent / "odisha_seasonal"
        if (odisha / "protocol.json").exists():
            with st.expander("Odisha Kharif study: daily weather and frozen evaluation plan", expanded=True):
                st.write("The next study focuses on 30 Odisha districts and official Kharif rice yield in kg/ha. It asks whether daily early-season weather improves forecasts over recent-yield baselines.")
                st.caption("Issue date: 31 August. Weather: 1 June–24 August, allowing a seven-day buffer. Historical yields: Y−2 through Y−6. Neither buffer establishes actual historical release vintages.")
                st.warning("Spatial assumption: fixed 2011 reference polygons, with whole-district area weights. Annual boundary equivalence is not certified, and these are not rice-area weights. This new study has not replaced the annual forecast.")
                if (odisha / "summary.json").exists():
                    study = json.loads((odisha / "summary.json").read_text(encoding="utf-8"))
                    a, b, c = st.columns(3)
                    a.metric("Weather district-years", study["weather_district_years"])
                    b.metric("Development rows with yield history", study["development_model_rows_with_history"])
                    c.metric("Fixed weather predictors", study["weather_predictors"])
                    st.write("Daily weather preparation is complete. The next step is the declared comparison of history baselines, Ridge, Random Forest and histogram gradient boosting. No new forecasting accuracy is claimed yet.")
                    st.download_button("Download Odisha prepared inputs", (odisha / "prepared_inputs.csv").read_bytes(), "odisha_kharif_inputs.csv", "text/csv")
                    st.download_button("Download district weather weights", (odisha / "grid_weights.csv").read_bytes(), "odisha_weather_weights.csv", "text/csv")
                else:
                    st.info("The protocol is frozen; daily weather acquisition and validation are in progress.")
                st.write("Model selection: 2009–2012. Uncertainty calibration: 2014–2016. Reserved assessment: 2018–2022, with annual refitting using labels only through Y−2. The timing amendment applies the reporting delay to selection and calibration as well as fitting. Reserved numeric outcomes remain unopened during data preparation.")
                st.download_button("Download Odisha study protocol", (odisha / "protocol.json").read_bytes(), "odisha_study_protocol.json", "application/json")
