"""Input-first dashboard; geographic labels only load editable examples."""
import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.data import ROOT, FEATURES, LAGS, LABELS, MONTHS, TARGET, load_data
from src.model import OUT, load_model, predict


@st.cache_resource
def resources():
    return load_data(), *load_model()


def table(rows):
    st.table(pd.DataFrame(rows, columns=["Measure", "Value"]).set_index("Measure"))


def chart(value, height=290):
    st.altair_chart(value.properties(height=height).configure_view(stroke=None).configure_axis(
        labelColor="#111111", titleColor="#111111", gridColor="#e3edf8").configure_legend(
        labelColor="#111111", titleColor="#111111"), width="stretch")


def fill_example(frame):
    st.caption("Optional: load real historical predictor values, then edit them.")
    state = st.selectbox("State", sorted(frame.state.unique()))
    part = frame.loc[frame.state.eq(state) & frame.year.between(2012, 2017)]
    names = part[["district_id", "district"]].drop_duplicates().set_index("district_id").district.to_dict()
    district = st.selectbox("District", sorted(names, key=names.get), format_func=lambda code: names[code])
    year = st.selectbox("Example agricultural start year", sorted(part.year.unique(), reverse=True))
    if st.button("Load example values", width="stretch"):
        row = part.loc[part.district_id.eq(district) & part.year.eq(year)].iloc[0]
        for column in FEATURES:
            st.session_state[column] = float(row[column])
        st.session_state["example"] = f"{names[district]}, {state}, {year}"
        st.session_state.pop("result", None)


def inputs(frame, bundle, report):
    st.title("Estimate rice yield")
    st.write("Enter past yields and weather. Get an estimated annual yield per hectare.")
    st.caption("Research model trained on historical district data. Farm-level and current-season accuracy are unverified.")
    if "example" in st.session_state:
        st.caption("Loaded example: "+st.session_state["example"]+". All values below remain editable.")
    else:
        st.caption("Starting values are fitting-period medians, not observations from a particular location.")
    with st.form("prediction_inputs"):
        st.subheader("Past rice yields")
        st.caption("Y is the year you want to estimate. Enter yields from Y-2 through Y-6; the original study assumes a reporting delay.")
        columns = st.columns(3)
        for index, name in enumerate(LAGS):
            columns[index % 3].number_input(LABELS[name], min_value=0.01, step=50., key=name, format="%.2f")
        st.subheader("June-August weather")
        st.caption("Use NASA-compatible monthly summaries. Rainfall is mean mm/day, not monthly rainfall in mm.")
        for month, label in MONTHS.items():
            st.markdown(f"**{label}**")
            columns = st.columns(2)
            for index, (parameter, unit, minimum, maximum, step) in enumerate([
                ("T2M_MAX", "Maximum temperature (C)", -60., 65., .5),
                ("T2M_MIN", "Minimum temperature (C)", -60., 65., .5),
                ("PRECTOTCORR", "Rainfall (mm/day)", 0., None, .5),
                ("RH2M", "Relative humidity (%)", 0., 100., 1.)]):
                columns[index % 2].number_input(unit, min_value=minimum, max_value=maximum, step=step,
                                                key=f"{parameter}_{month:02d}", format="%.2f")
        submitted = st.form_submit_button("Estimate yield", type="primary")
    if submitted:
        values = {name: st.session_state[name] for name in FEATURES}
        try:
            st.session_state["result"] = {"values": values, **predict(values, bundle)}
        except ValueError as error:
            st.session_state.pop("result", None)
            st.error(str(error))
    result = st.session_state.get("result")
    if result:
        st.subheader("Estimate")
        later = next(row for row in report["scores"] if row["Method"] == "Numerical Random Forest" and "2012" in row["Period"])
        table([
            ("Estimated annual rice yield", f"{result['estimate']:,.0f} kg/ha"),
            ("Five-past-yield mean baseline", f"{result['reference']:,.0f} kg/ha"),
            ("Estimate relative to baseline", f"{result['change_percent']:+.1f}%"),
            ("Historical later-period MAE", f"{later['MAE (kg/ha)']:,.0f} kg/ha (study-wide, not an interval)")])
        if result["outside"]:
            st.warning("Outside fitting-period ranges: "+", ".join(LABELS[name] for name in result["outside"])+". Treat the estimate as extrapolation.")
        st.caption("A difference from past yields does not identify crop damage or its cause. Editing inputs does not demonstrate a causal effect.")
        with st.expander("Inputs used for this estimate"):
            table([(LABELS[name], f"{result['values'][name]:,.2f}") for name in FEATURES])
        st.download_button("Download estimate and inputs", json.dumps(result, indent=2),
                           "rice_yield_estimate.json", "application/json")


@st.cache_data
def india_outlines():
    return json.loads((ROOT / "data/india_states.geojson").read_text(encoding="utf-8"))["features"]


def map_chart(observations, measure, focus=None):
    """Context outlines and source coordinates, without inventing district polygons."""
    outlines = india_outlines()
    fitted = [feature for feature in outlines if feature["properties"]["state"] == focus] if focus else outlines
    background = alt.Chart(alt.Data(values=outlines)).mark_geoshape(
        fill="#edf4fc", stroke="#9bb7d5", strokeWidth=.7, clip=True)
    pick = alt.selection_point(name="district_pick", fields=["district_id"], on="click", clear="dblclick", toggle=False, empty=False)
    labels = {TARGET: "Annual rice yield (kg/ha)", **LABELS}
    points = alt.Chart(observations).mark_circle(clip=True).encode(
        longitude=alt.Longitude("longitude:Q"), latitude=alt.Latitude("latitude:Q"),
        color=alt.Color(f"{measure}:Q", title=labels[measure], scale=alt.Scale(scheme="blues"),
                        legend=alt.Legend(orient="bottom", gradientLength=250)),
        size=alt.condition(pick, alt.value(180), alt.value(105)),
        stroke=alt.condition(pick, alt.value("#111111"), alt.value("#225b96")),
        strokeWidth=alt.condition(pick, alt.value(2.5), alt.value(1)),
        tooltip=[alt.Tooltip("district:N", title="District"), alt.Tooltip("state:N", title="State"),
                 alt.Tooltip("year:Q", title="Year", format="d"),
                 alt.Tooltip(f"{measure}:Q", title=labels[measure], format=",.2f")]).add_params(pick)
    return alt.layer(background, points).project(
        type="mercator", fit={"type": "FeatureCollection", "features": fitted or outlines}
    ).properties(height=470).configure_view(stroke=None).configure_legend(labelColor="#111111", titleColor="#111111")


def data_view(frame):
    st.title("Explore the data")
    st.caption("Annual administrative rice yields and NASA monthly weather, 1987-2017. Historical district boundaries apply.")
    state = st.selectbox("Show state", ["All states"]+sorted(frame.state.unique()), key="data_state")
    part = frame if state == "All states" else frame.loc[frame.state.eq(state)]
    names = part[["district_id", "district", "state"]].drop_duplicates().set_index("district_id")
    district_ids = st.multiselect("Districts", names.index.tolist(), key="data_districts",
                                 format_func=lambda code: f"{names.loc[code, 'district']}, {names.loc[code, 'state']}",
                                 placeholder="All available districts")
    if district_ids:
        part = part.loc[part.district_id.isin(district_ids)]
    first_year, last_year = int(frame.year.min()), int(frame.year.max())
    start, end = st.slider("Year range", first_year, last_year, (first_year, last_year), key="data_year_range")
    part = part.loc[part.year.between(start, end)]
    if part.empty:
        st.info("No observations for these districts and years. Change the filters.")
        return
    st.subheader("India map")
    left, right = st.columns(2)
    year = left.selectbox("Map year", sorted(part.year.unique(), reverse=True), key="map_year")
    measure = right.selectbox("Map measure", [TARGET]+FEATURES, key="map_measure",
                              format_func=lambda name: "Annual rice yield (kg/ha)" if name == TARGET else LABELS[name])
    focus = state if state != "All states" and st.checkbox("Focus map on selected state", key="map_focus") else None
    mapped = part.loc[part.year.eq(year)]
    event = st.altair_chart(map_chart(mapped, measure, focus), key="india_map", width="stretch",
                           on_select="rerun", selection_mode=["district_pick"])
    picked = event.get("selection", {}).get("district_pick", [])
    selected_ids = [row["district_id"] for row in picked if row.get("district_id") in mapped.district_id.values]
    if selected_ids:
        part = part.loc[part.district_id.isin(selected_ids)]
        st.write("Showing plots for: "+", ".join(part.district.unique())+". Double-click the map to clear the selection.")
    st.caption(f"{len(mapped)} available district observations in {year}. Click a marker to filter the plots below. "
               "Markers are representative coordinates, not district boundaries or field locations. "
               "Only the five study states have data; other states are shown for context.")
    with st.expander("Map values and source"):
        columns = list(dict.fromkeys(["state", "district", "year", TARGET, measure]))
        st.dataframe(mapped[columns].sort_values(["state", "district"]), hide_index=True)
        st.markdown("2011 state outlines: [DataMeet Community Maps](https://github.com/datameet/maps), "
                    "[CC BY 2.5 India](https://creativecommons.org/licenses/by/2.5/in/). "
                    "These are historical outlines, not current administrative boundaries.")
    st.subheader("1. Yield over time")
    group = "district" if district_ids or selected_ids else "state"
    trend = part.groupby([group, "year"], as_index=False)[TARGET].mean()
    chart(alt.Chart(trend).mark_line().encode(x=alt.X("year:Q", title="Agricultural start year", axis=alt.Axis(format="d")),
        y=alt.Y(f"{TARGET}:Q", title="Unweighted district mean yield (kg/ha)"),
        color=alt.Color(f"{group}:N", scale=alt.Scale(scheme="blues")), tooltip=[group, "year", TARGET]))
    st.subheader("2. Yield variation")
    chart(alt.Chart(part).mark_boxplot(color="#225b96").encode(x=alt.X("state:N", title=None),
        y=alt.Y(f"{TARGET}:Q", title="Annual yield (kg/ha)")))
    st.subheader("3. Weather and yield")
    feature = st.selectbox("Weather predictor", FEATURES[5:], format_func=lambda name: LABELS[name])
    chart(alt.Chart(part).mark_circle(color="#225b96", opacity=.35, size=25).encode(
        x=alt.X(f"{feature}:Q", title=LABELS[feature]), y=alt.Y(f"{TARGET}:Q", title="Yield (kg/ha)"),
        tooltip=["state", "district", "year", feature, TARGET]))
    st.caption("Association in these observations does not establish causation.")
    st.subheader("4. Available records")
    counts = part.groupby(["state", "year"]).size().reset_index(name="records")
    chart(alt.Chart(counts).mark_rect().encode(x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("state:N", title=None), color=alt.Color("records:Q", scale=alt.Scale(scheme="blues")), tooltip=["state", "year", "records"]), 160)
    with st.expander("First records and dataset scope"):
        st.write("The model uses 17 numerical predictors. Area names identify examples; they are excluded from the forest.")
        st.dataframe(part[["state", "district", "year", TARGET]+FEATURES].head(10), hide_index=True)
        st.write("Other retained seasonal and satellite datasets belong to the earlier studies and are not inputs to this model.")


def evidence(report):
    st.title("Model and results")
    st.write("One numerical Random Forest, compared with the mean of five past yields.")
    period = st.selectbox("Evaluation period", list(dict.fromkeys(row["Period"] for row in report["scores"])), index=1)
    rows = [row for row in report["scores"] if row["Period"] == period]
    st.dataframe(pd.DataFrame(rows).drop(columns="Period").set_index("Method").T, width="stretch")
    forest, baseline = rows
    difference = baseline["MAE (kg/ha)"]-forest["MAE (kg/ha)"]
    st.write(f"Forest MAE is {abs(difference):.1f} kg/ha {'lower' if difference > 0 else 'higher'} than the baseline in this period.")
    st.caption("These years were examined in earlier experiments. This is a retrospective comparison, not a new independent test.")
    predictions = pd.read_csv(OUT / "evaluation.csv")
    predictions = predictions.loc[predictions.period.eq(period)]
    with st.expander("Errors by year"):
        yearly = []
        for year, group in predictions.groupby("year"):
            yearly.append({"Year": int(year), "Records": len(group),
                           "Forest MAE (kg/ha)": float((group.prediction-group[TARGET]).abs().mean()),
                           "Baseline MAE (kg/ha)": float((group.baseline-group[TARGET]).abs().mean()),
                           "Forest bias (kg/ha)": float((group.prediction-group[TARGET]).mean())})
        st.dataframe(pd.DataFrame(yearly), hide_index=True, width="stretch")
    states = sorted(predictions.state.unique())
    state = st.selectbox("Example state", states)
    part = predictions.loc[predictions.state.eq(state)]
    district = st.selectbox("Example district", sorted(part.district.unique()))
    part = part.loc[part.district.eq(district)]
    left, right = st.columns([3, 1])
    left.subheader("Actual and estimated yield")
    show = right.toggle("Show estimate", value=True)
    names = {TARGET: "Actual yield", "baseline": "Recent mean baseline"}
    if show:
        names["prediction"] = "Numerical Random Forest"
    lines = part.melt(id_vars="year", value_vars=list(names), var_name="Method", value_name="Yield")
    lines["Method"] = lines.Method.replace(names)
    chart(alt.Chart(lines).mark_line(point=True).encode(x=alt.X("year:Q", title="Agricultural start year", axis=alt.Axis(format="d")),
        y=alt.Y("Yield:Q", title="Yield (kg/ha)", scale=alt.Scale(zero=True)),
        color=alt.Color("Method:N", scale=alt.Scale(range=["#102d4f", "#7b9aba", "#2879c1"])),
        strokeDash="Method:N", tooltip=["year", "Method", "Yield"]))
    with st.expander("How this works"):
        table([("Target", "Annual rice yield (kg/ha), all rice seasons"),
               ("Predictors", "5 past yields + 12 June-August weather values"),
               ("Excluded", "District/state identity, coordinates, year, current area/production/yield"),
               ("Model", "300 trees; depth 4; minimum 10 records per leaf"),
               ("Fitting years", "1987-2004; same frozen fit used in this app"),
               ("Fitting rows", str(report["training_rows"])),
               ("Interpretation", "Historical district-scale estimation; no validated damage alert")])
        st.markdown("Sources: [ICRISAT DLD](https://doi.org/10.21421/D2/XFB1BZ) and [NASA POWER](https://power.larc.nasa.gov/).")
        st.write("Physical ranges, duplicate keys, missing values, labels, source hashes and temporal cutoffs are checked. Forest prediction does not require Gaussian predictors. Regional transfer and current operational accuracy remain unverified.")


def render():
    try:
        frame, bundle, report = resources()
    except ValueError as error:
        st.error(str(error))
        st.stop()
    draft = st.session_state.setdefault("draft", {})
    for name in FEATURES:
        if name in st.session_state:
            draft[name] = st.session_state[name]
        st.session_state.setdefault(name, draft.get(name, float(frame.loc[frame.year <= 2004, name].median())))
    with st.sidebar:
        st.markdown('<div class="brand-label">RICE YIELD</div>', unsafe_allow_html=True)
        page = st.radio("Navigate", ["Estimate yield", "Explore data", "Model and results"])
        if page == "Estimate yield":
            st.divider()
            if st.checkbox("Load an area example"):
                fill_example(frame)
    {"Estimate yield": lambda: inputs(frame, bundle, report),
     "Explore data": lambda: data_view(frame), "Model and results": lambda: evidence(report)}[page]()
