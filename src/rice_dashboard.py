"""One presentation interface for the retained annual and Kharif forecasts."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
ANNUAL = ROOT / "data/processed/rice/regional_forecast"
KHARIF = ROOT / "data/processed/rice/odisha_seasonal/model"
PAGES = ["Forecast", "Model results", "Data & methods", "Presentation guide"]


@st.cache_data
def study(season):
    if season == "Kharif rice":
        summary = json.loads((KHARIF / "summary.json").read_text(encoding="utf-8"))
        records = pd.read_csv(KHARIF / "selected_assessment_predictions.csv", dtype={"district_code_census2011": str})
        records = records.rename(columns={"district_code_census2011": "district_id", "district_source": "district",
            "agricultural_start_year": "year", "actual_yield_kg_ha": "actual", "predicted_yield_kg_ha": "prediction",
            "reference_yield_kg_ha": "reference", "low_yield_threshold_kg_ha": "threshold"})
        inputs = pd.read_csv(KHARIF / "assessment_inputs.csv", dtype={"district_code_census2011": str}).rename(
            columns={"district_code_census2011": "district_id", "agricultural_start_year": "year"})
        scores = pd.read_csv(KHARIF / "assessment_metrics.csv").sort_values("candidate_order").rename(
            columns={"candidate": "model", "wape": "wape_fraction"})
        model = summary["selected_candidate"]["id"]
        records["state"] = "Odisha"
        dates = "2018–2022"
    else:
        summary = json.loads((ANNUAL / "summary.json").read_text(encoding="utf-8"))
        records = pd.read_csv(ANNUAL / "assessment_predictions.csv").rename(columns={"yield_kg_ha": "actual",
            "prediction_kg_ha": "prediction", "reference_yield": "reference", "low_yield_threshold": "threshold"})
        records["state"] = records.state.replace({"Orissa": "Odisha"})
        inputs = records.copy()
        scores = pd.read_csv(ANNUAL / "assessment_metrics.csv")
        scores["wape_fraction"] = scores.wape_percent / 100
        model = summary["selected_model"]
        dates = "2012–2017"
    return {"summary": summary, "records": records, "inputs": inputs, "scores": scores,
            "model": model, "dates": dates, "season": season}


def table(rows, first="Measure", second="Value"):
    st.table(pd.DataFrame(rows, columns=[first, second]).astype({second: str}).set_index(first))


def percent(value):
    return "Unavailable" if value is None or pd.isna(value) else f"{value:.1%}"


def navigate(page):
    st.session_state["page"] = page


def selectors():
    with st.sidebar:
        st.title("Rice Yield")
        st.caption("Forecasting research")
        page = st.session_state.setdefault("page", "Data & methods")
        for name in PAGES:
            st.button(name, key="nav_" + name, type="primary" if name == page else "secondary",
                      width="stretch", on_click=navigate, args=(name,))
        st.divider()
        state = st.selectbox("State", ["Odisha", "Bihar", "Chhattisgarh", "Jharkhand", "West Bengal"])
        seasons = ["Kharif rice", "Annual rice"] if state == "Odisha" else ["Annual rice"]
        season = st.selectbox("Coverage", seasons, help="The Kharif study covers Odisha. The annual study covers five states.")
        data = study(season)
        available = data["records"].loc[data["records"].state.eq(state)]
        districts = available[["district_id", "district"]].drop_duplicates().sort_values("district")
        labels = districts.set_index("district_id").district.to_dict()
        code = st.selectbox("District", districts.district_id.tolist(), format_func=lambda v: labels[v].title(),
                            key="district_" + season + "_" + state)
        years = sorted(available.loc[available.district_id.eq(code), "year"].unique().tolist(), reverse=True)
        year = st.selectbox("Agricultural start year", years, format_func=lambda v: f"{v}–{str(v+1)[-2:]}", key="year_" + season)
        st.caption("Historical replay · yield in kg/ha")
    return page, data, state, code, year


def forecast_page(data, code, year):
    row = data["records"].loc[data["records"].district_id.eq(code) & data["records"].year.eq(year)].iloc[0]
    source = data["inputs"].loc[data["inputs"].district_id.eq(code) & data["inputs"].year.eq(year)].iloc[0]
    st.subheader("Yield forecast")
    st.caption(f"{row.district.title()} · {year}–{str(year+1)[-2:]} · {data['model']}")
    reveal = st.checkbox("Show recorded harvest yield", value=False)
    result = [("Estimated yield", f"{row.prediction:,.0f} kg/ha"),
              ("Past-yield reference", f"{row.reference:,.0f} kg/ha"),
              ("Change from reference", f"{100*(row.prediction/row.reference-1):+.1f}%"),
              ("Approximate 80% interval", f"{row.lower_80_kg_ha:,.0f}–{row.upper_80_kg_ha:,.0f} kg/ha"),
              ("Low-yield threshold", f"{row.threshold:,.0f} kg/ha"),
              ("Point forecast below threshold", "Yes" if row.prediction < row.threshold else "No")]
    if reveal:
        result += [("Recorded yield", f"{row.actual:,.0f} kg/ha"),
                   ("Absolute forecast error", f"{abs(row.actual-row.prediction):,.0f} kg/ha")]
    table(result)
    st.caption("Low yield means below 80% of the past-yield reference. This is a research flag, not a measured damage diagnosis.")
    if data["season"] == "Kharif rice":
        st.caption("Intervals are wide and low-yield detection is weak; see Model results for the measured performance.")
    st.subheader("Yield history used")
    history = pd.DataFrame({"Start year": [int(year-lag) for lag in range(6, 1, -1)],
                            "Yield (kg/ha)": [source[f"yield_lag{lag}"] for lag in range(6, 1, -1)]})
    history["Start year"] = history["Start year"].astype(str)
    st.line_chart(history.set_index("Start year"), color="#245e9d", height=220)
    st.caption(f"Issue date: 31 August {year}. History: {year-6}–{year-2}. The selected model uses yield history; weather was tested separately.")
    export = pd.DataFrame({"district": [row.district], "state": [row.state], "start_year": [year],
        "model": [data["model"]], "forecast_kg_ha": [row.prediction], "reference_kg_ha": [row.reference],
        "lower_80_kg_ha": [row.lower_80_kg_ha], "upper_80_kg_ha": [row.upper_80_kg_ha]})
    if reveal:
        export["recorded_yield_kg_ha"] = row.actual
    st.download_button("Download forecast", export.to_csv(index=False), "rice_forecast.csv", "text/csv")


def results_page(data, code):
    with st.sidebar:
        section = st.selectbox("Result to view", ["Accuracy", "Model comparison", "Uncertainty", "Low-yield flags", "By year", "Selected district"])
    st.subheader(section)
    st.caption(f"{data['season']} · all assessment records, {data['dates']} · selected: {data['model']}")
    summary, records = data["summary"], data["records"]
    scores = data["scores"]
    selected = scores.loc[scores.model.eq(data["model"])].iloc[0]
    if section == "Accuracy":
        table([("Selected model", data["model"]), ("Assessment records", f"{len(records):,}"),
            ("Mean absolute error (MAE)", f"{selected.mae_kg_ha:,.1f} kg/ha"),
            ("Root mean squared error (RMSE)", f"{selected.rmse_kg_ha:,.1f} kg/ha"),
            ("R squared", f"{selected.r_squared:.3f}"), ("Weighted absolute percentage error", percent(selected.wape_fraction))])
        st.write("MAE is the average size of a forecast error. Lower is better. The model was chosen on earlier years, not on these results.")
        if data["season"] == "Kharif rice":
            st.caption("The error improvement over simple history baselines remains uncertain across five years. Negative R squared and weak low-yield recall limit the findings.")
    elif section == "Model comparison":
        display = scores[["model", "mae_kg_ha", "rmse_kg_ha"]].rename(columns={"model": "Configuration", "mae_kg_ha": "MAE (kg/ha)", "rmse_kg_ha": "RMSE (kg/ha)"})
        st.dataframe(display, hide_index=True, width="stretch")
        if data["season"] == "Kharif rice":
            st.caption("Thirteen fixed configurations. Random Forest depth 4 reached MAE 405.3 kg/ha, but was not selected on development years. It remains a secondary finding.")
    elif section == "Uncertainty":
        table([("Nominal interval coverage", "80%"), ("Observed coverage", percent(summary["interval_coverage_80"])),
               ("Average interval width", f"{summary['mean_interval_width_kg_ha']:,.0f} kg/ha")])
        st.write("Coverage counts how often the recorded yield falls inside the interval. A very wide interval can cover many outcomes while being less useful for decisions.")
    elif section == "Low-yield flags":
        actual = records.actual < records.threshold
        flagged = records.prediction < records.threshold
        tp, fp, fn, tn = [int(x) for x in [(actual & flagged).sum(), (~actual & flagged).sum(), (actual & ~flagged).sum(), (~actual & ~flagged).sum()]]
        table([("Observed low-yield records", int(actual.sum())), ("Correct low-yield flags", tp),
               ("False flags", fp), ("Missed low-yield records", fn), ("Correct normal-yield records", tn),
               ("Precision", percent(tp/(tp+fp) if tp+fp else None)), ("Recall", percent(tp/(tp+fn) if tp+fn else None))])
        st.caption("These are point-forecast threshold flags. No calibrated probability or causal crop damage is claimed.")
    else:
        group = records if section == "By year" else records.loc[records.district_id.eq(code)]
        rows = []
        for year, part in group.groupby("year"):
            rows.append({"Start year": int(year), "Records": len(part), "MAE (kg/ha)": float(abs(part.prediction-part.actual).mean()),
                         "Recorded mean (kg/ha)": float(part.actual.mean()), "Forecast mean (kg/ha)": float(part.prediction.mean())})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.download_button("Download model comparison", scores.to_csv(index=False), "rice_model_comparison.csv", "text/csv")


def methods_page(data, code, year):
    with st.sidebar:
        section = st.selectbox("Topic", ["Data exploration", "Study summary", "Predictors", "Validation", "Limitations", "Protein and aluminium"])
    st.subheader(section)
    kharif = data["season"] == "Kharif rice"
    if section == "Data exploration":
        if not kharif:
            st.info("These development-data graphs describe the main Odisha Kharif study. Select Odisha and Kharif rice to explore them. Annual rice has different geographic units and is not pooled with this data.")
            return
        folder = ROOT / "data/processed/rice/foundation"
        if not (folder / "audit.json").exists():
            st.info("The development data audit has not been generated yet.")
            return
        st.caption("Odisha Kharif · 1998–2017 development data only · 30 districts · 600 records. Graphs describe the data; they do not establish causes or predictive value.")
        choices = {
            "Data coverage": ("01_coverage", "Every district has 20 observed development yields. Earlier years without sufficient lag history remain visible here but are excluded from the 420-row modelling cohort."),
            "Yield over time": ("02_yield_trend", "The line is the median across districts; the band is the middle 50% of districts, not a confidence interval. This is not an area-weighted state yield."),
            "District distributions": ("03_district_yields", "Each box summarises 20 annual yields. The line marks the median; the box spans the middle 50%. Whiskers use 1.5 IQR; outside points remain in the data."),
            "Weather relationships": ("04_weather_correlations", "A representative subset of weather predictors. Strong correlations show redundancy, not causation. This pooled district-year plot does not provide independent-observation significance tests.")}
        choice = st.selectbox("Graph", list(choices))
        name, explanation = choices[choice]
        st.image(str(folder / "figures" / (name + ".png")), width="stretch")
        st.write(explanation)
        st.download_button("Download graph (SVG)", (folder / "figures" / (name + ".svg")).read_bytes(), name + ".svg", "image/svg+xml")
        records = pd.read_csv(folder / "development_records.csv", dtype={"district_code_census2011": str})
        district = records.loc[records.district_code_census2011.eq(str(code))]
        with st.expander("Selected district: source records"):
            st.dataframe(district[["district_source", "agricultural_start_year", "yield_kg_ha"]], hide_index=True)
        st.caption("Revised modelling is on hold. Previously reported forecasts belong to the legacy experiment; the new foundation does not validate them anew.")
    elif section == "Study summary":
        table([("Crop", "Rice"), ("Target", "Yield per hectare, kg/ha"), ("Coverage", "30 Odisha districts" if kharif else "50 historical districts in five states"),
               ("Season", "Kharif" if kharif else "Annual: combines rice seasons"),
               ("Yield source", "Government DES" if kharif else "ICRISAT District Level Database"),
               ("Weather source", "NASA POWER"), ("Issue date", "31 August of the starting year"),
               ("Assessment years", data["dates"]), ("Selected model", data["model"])])
        st.markdown("Sources: [DES](https://www.data.desagri.gov.in/website/apy-query-report-web) · [ICRISAT](https://doi.org/10.21421/D2/XFB1BZ) · [NASA POWER](https://power.larc.nasa.gov/)")
    elif section == "Predictors":
        table([("Used by the selected model", "Five past yields, their mean/trend and study metadata"),
               ("Also tested", "Rainfall, maximum/minimum temperature and humidity" + (", solar energy" if kharif else "")),
               ("Weather observation window", "1 June–24 August; 19 summaries" if kharif else "June–August; 12 monthly variables"),
               ("Never predictors", "Target-year production, target-year area and harvest yield")])
        source = data["inputs"].loc[data["inputs"].district_id.eq(code) & data["inputs"].year.eq(year)].iloc[0]
        rows = []
        for m in (6, 7, 8):
            rows.append({"Window": {6: "June", 7: "July", 8: "1–24 August" if kharif else "August"}[m],
                         "Rain (mm total)" if kharif else "Rain (mm/day)": source[f"PRECTOTCORR_{m:02d}"],
                         "Mean Tmax (C)": source[f"T2M_MAX_{m:02d}"], "Mean Tmin (C)": source[f"T2M_MIN_{m:02d}"],
                         "Humidity (%)": source[f"RH2M_{m:02d}"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Displayed weather belongs to the selected district/year. Weather candidates were tested, but the selected history model does not use these weather inputs.")
    elif section == "Validation":
        table([("Model selection", "2009–2012, expanding windows" if kharif else "1998–2005, expanding windows"),
               ("Interval calibration", "2014–2016" if kharif else "2006–2011"), ("Later-year assessment", data["dates"]),
               ("Fitting rule", "Annual refit through Y−2" if kharif else "Frozen estimator fitted through 2004"),
               ("Yield history", "Y−2 through Y−6; assumed reporting delay"),
               ("Algorithms compared", "History baselines, Ridge, Random Forest, histogram gradient boosting")])
        st.write("Training uses earlier years. Model selection and interval calibration were fixed before the assessment outcomes were opened.")
    elif section == "Limitations":
        table([("Forecast scope", "Historical replay, not a live current-season service"),
               ("Geography", "Fixed 2011 reference polygons assumed" if kharif else "Historical 1966-apportioned districts"),
               ("Weather", "Revised gridded estimates; actual historical release vintages unverified"),
               ("Reporting dates", "Two-year yield delay assumed, not independently verified"),
               ("Evidence", "Few assessment years; baseline gains are uncertain"),
               ("Low-yield flags", "Limited detection; not measured injury or financial loss")])
        if kharif:
            st.caption("Map attribution: DataMeet Community Maps Project, CC BY 2.5 India. Weights cover whole districts, not verified rice areas.")
    else:
        st.write("Proteins and aluminium are supporting biological research. They are not predictors in either district forecasting model.")
        table([("Aluminium", "Can harm roots in acidic soil; district-year exposure was not linked"),
               ("Protein experiment", "Separate rice trials tested genetic variants with reference protein context"),
               ("Finding", "No reliable protein-context forecasting improvement was established"),
               ("Presentation claim", "Biological motivation and a separate experiment, not a district model input")])


def guide_page():
    st.subheader("Your presentation in five points")
    for title, body in [
        ("1. The question", "Can early-season weather improve rice yield forecasts over a district's recent yield history?"),
        ("2. The data", "The main seasonal study uses official Kharif rice yields for 30 Odisha districts and NASA daily weather. A separate ICRISAT annual study provides five-state coverage."),
        ("3. The method", "We compare simple baselines, Ridge, Random Forest and boosting. Models are chosen on earlier years and then evaluated on later years."),
        ("4. The result", "For the Odisha study, development selected history-only Ridge: MAE 517 kg/ha versus 578 for recent mean. Random Forest reached 405 kg/ha as a secondary finding."),
        ("5. The conclusion", "This is a completed research prototype with real data and mixed results. Weather's added value is not established, low-yield detection is weak, and uncertainty intervals are wide."),
    ]:
        st.markdown(f"**{title}**")
        st.write(body)
    st.download_button("Download presentation guide", (ROOT / "docs/Project_Guide.md").read_bytes(), "Rice_Project_Guide.md", "text/markdown")


def render_dashboard():
    page, data, state, code, year = selectors()
    st.title("Rice Yield Outlook")
    st.caption("Birla Institute of Technology, Mesra · Department of Quantitative Economics and Data Science  \nGuide: Dr. Manish Kumar Pandey")
    st.divider()
    st.caption(f"{state} · {data['season']} · historical assessment {data['dates']}")
    if page in ("Forecast", "Model results"):
        st.caption("Legacy experiment: revised modelling is on hold while the statistical foundation is reviewed.")
    if page == "Forecast":
        forecast_page(data, code, year)
    elif page == "Model results":
        results_page(data, code)
    elif page == "Data & methods":
        methods_page(data, code, year)
    else:
        guide_page()
