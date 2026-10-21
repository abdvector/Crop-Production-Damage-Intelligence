"""Interactive exploration of saved rice forecasts and public study observations."""
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/rice"
BLUE, LIGHT = "#225b96", "#c9def2"
PAGES = ["Yield explorer", "Data explorer", "Model evaluation"]
KINDS = {"Revised Kharif study · 2012–2017": "revised", "Saved Kharif forecasts · 2018–2022": "kharif",
         "Saved annual forecasts · 2012–2017": "annual"}
RENAME = {"district_code_census2011": "district_id", "district_source": "district",
          "agricultural_start_year": "year", "actual_yield_kg_ha": "actual",
          "predicted_yield_kg_ha": "prediction", "reference_yield_kg_ha": "reference",
          "low_yield_threshold_kg_ha": "threshold", "candidate": "method"}


def read(folder, name):
    return pd.read_csv(BASE / folder / name, dtype={"district_code_census2011": str, "district_id": str})


@st.cache_data
def study(kind):
    folder = {"annual": "regional_forecast", "revised": "revised_modelling", "kharif": "odisha_seasonal/model"}[kind]
    summary = json.loads((BASE / folder / "summary.json").read_text())
    if kind == "annual":
        primary = summary["selected_model"]
        expanded = (BASE / "regional_comparison/all_method_predictions.csv").exists()
        records = read("regional_comparison" if expanded else folder,
                       "all_method_predictions.csv" if expanded else "assessment_predictions.csv").rename(columns={
            "yield_kg_ha": "actual", "prediction_kg_ha": "prediction", "reference_yield": "reference",
            "low_yield_threshold": "threshold", "model": "method"})
        if not expanded:
            records["method"] = primary
        inputs = read(folder, "district_years.csv")
        history = inputs.copy()
        scores = read("regional_comparison" if expanded else folder, "all_method_metrics.csv" if expanded else "assessment_metrics.csv")
    else:
        records = read(folder, "nested_predictions.csv" if kind == "revised" else "assessment_predictions.csv").rename(columns=RENAME)
        records["state"] = "Odisha"
        inputs = read("odisha_seasonal/model", "assessment_inputs.csv").rename(columns=RENAME)
        history = read("foundation", "development_records.csv").rename(columns=RENAME)
        history["state"] = "Odisha"
        primary = "Nested selection" if kind == "revised" else summary["selected_candidate"]["id"]
        scores = None
        if kind == "kharif":
            intervals = read(folder, "selected_assessment_predictions.csv").rename(columns=RENAME)
            records = records.merge(intervals[["district_id", "year", "method", "lower_80_kg_ha", "upper_80_kg_ha"]],
                                    on=["district_id", "year", "method"], how="left", validate="one_to_one")
    for frame in (records, history, inputs):
        frame["district_id"] = frame.district_id.astype(str)
        if "state" in frame:
            frame["state"] = frame.state.replace({"Orissa": "Odisha"})
    return dict(kind=kind, records=records, inputs=inputs, history=history, primary=primary, summary=summary,
                methods=[primary]+sorted(set(records.method)-{primary}), scores=scores)


def table(rows):
    st.table(pd.DataFrame(rows, columns=["Measure", "Value"]).astype(str).set_index("Measure"))


def percent(value):
    return "Unavailable" if value is None or pd.isna(value) else f"{value:.1%}"


def chart(spec, height=320):
    spec = spec.properties(height=height).configure_view(stroke=None).configure_axis(
        labelColor="#111111", titleColor="#111111", gridColor="#e6eef7", domainColor="#b6cce3",
        labelFontSize=12, titleFontSize=12).configure_legend(labelColor="#111111", titleColor="#111111")
    st.altair_chart(spec, width="stretch")


def navigate(page):
    st.session_state["page"] = page


def controls():
    with st.sidebar:
        st.markdown('<div class="brand-label">RICE YIELD</div>', unsafe_allow_html=True)
        st.caption("Explore yields, data and evidence")
        page = st.session_state.setdefault("page", PAGES[0])
        if page not in PAGES:
            page = st.session_state["page"] = PAGES[0]
        for name in PAGES:
            st.button(name, key="nav_"+name, width="stretch", type="primary" if page == name else "secondary",
                      on_click=navigate, args=(name,))
        st.divider()
        state = st.selectbox("State", ["Odisha", "Bihar", "Chhattisgarh", "Jharkhand", "West Bengal"], key="state")
        options = list(KINDS) if state == "Odisha" else [list(KINDS)[-1]]
        label = st.selectbox("Study", options, key="study_"+state)
        data = study(KINDS[label])
        districts = data["records"].loc[data["records"].state.eq(state), ["district_id", "district"]].drop_duplicates().sort_values("district")
        names = districts.set_index("district_id").district.to_dict()
        code = st.selectbox("District", districts.district_id.tolist(), format_func=lambda v: names[v].title(), key="district_"+data["kind"]+state)
        year = method = None
        if page != "Data explorer":
            method = st.selectbox("Method", data["methods"], key="method_"+data["kind"],
                                  format_func=lambda name: {"Weather forest": "Weather Random Forest", "Weather boosting": "Weather Gradient Boosting"}.get(name, name),
                                  help="Select saved research results; this does not retrain or deploy a model. Annual comparators use the original fixed settings; the selected model remains History Ridge.")
        if page == "Yield explorer":
            years = sorted(data["records"].loc[data["records"].district_id.eq(code), "year"].unique(), reverse=True)
            year = st.selectbox("Harvest start year", years, format_func=lambda v: f"{v}–{str(v+1)[-2:]}", key="year_"+data["kind"])
    return page, data, state, code, names[code].title(), year, method


def selected(data, state, code, method, scope="Full study"):
    frame = data["records"]
    if method is not None:
        frame = frame.loc[frame.method.eq(method)]
    if scope == "Selected state":
        frame = frame.loc[frame.state.eq(state)]
    elif scope == "Selected district":
        frame = frame.loc[frame.district_id.eq(code)]
    return frame.copy()


def yield_lines(actual, predicted, show_actual=True, show_forecast=True):
    """Overlay only saved observations/predictions; never interpolate forecasts."""
    parts = []
    if show_actual and not actual.empty:
        parts.append(actual[["year", "yield"]].assign(Series="Actual yield"))
    if show_forecast and not predicted.empty:
        parts.append(predicted[["year", "yield"]].assign(Series="Forecast yield"))
    if not parts:
        return None
    values = pd.concat(parts, ignore_index=True)
    shown = values.Series.unique().tolist()
    return alt.Chart(values).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("year:Q", title="Agricultural start year", axis=alt.Axis(format="d", tickMinStep=1)),
        y=alt.Y("yield:Q", title="Yield (kg/ha)", scale=alt.Scale(zero=True)),
        color=alt.Color("Series:N", title=None, legend=alt.Legend(orient="top"),
                        scale=alt.Scale(domain=shown, range=[BLUE if name == "Actual yield" else "#527ca8" for name in shown])),
        strokeDash=alt.StrokeDash("Series:N", title=None, legend=alt.Legend(orient="top"),
                                 scale=alt.Scale(domain=shown, range=[[1, 0] if name == "Actual yield" else [7, 4] for name in shown])),
        tooltip=["Series:N", alt.Tooltip("year:Q", format="d", title="Year"),
                 alt.Tooltip("yield:Q", format=",.0f", title="Yield (kg/ha)")])


def yield_page(data, code, year, method):
    row = data["records"].loc[data["records"].district_id.eq(code) & data["records"].year.eq(year) & data["records"].method.eq(method)].iloc[0]
    source = data["inputs"].loc[data["inputs"].district_id.eq(code) & data["inputs"].year.eq(year)].iloc[0]
    with st.container(key="yield_chart_controls"):
        left, right = st.columns([3, 1])
        with left:
            reveal = st.toggle("Show actual yield", value=True)
        with right:
            show_forecast = st.toggle("Show forecast", value=True, key="forecast_line_yield")
    history = pd.DataFrame({"year": [int(year-i) for i in range(6, 1, -1)], "yield": [source[f"yield_lag{i}"] for i in range(6, 1, -1)]})
    district = data["records"].loc[data["records"].district_id.eq(code) & data["records"].method.eq(method)].sort_values("year")
    lines = yield_lines(district.rename(columns={"actual": "yield"}), district.rename(columns={"prediction": "yield"}), reveal, show_forecast)
    if lines is not None:
        marker = alt.Chart(pd.DataFrame({"year": [int(year)]})).mark_rule(color="#b6cce3", strokeDash=[3, 3]).encode(x="year:Q")
        chart(lines+marker, 330)
    else:
        st.info("Turn on actual yield or forecast yield to display the comparison.")
    st.caption("Solid line: actual yield. Dashed line: saved forecast. The vertical guide marks the year selected in the sidebar; the table below refers to that year.")
    rows = [("Estimated yield", f"{row.prediction:,.0f} kg/ha"), ("Past-yield reference", f"{row.reference:,.0f} kg/ha"),
            ("Change from reference", f"{row.prediction/row.reference-1:+.1%}")]
    if reveal:
        rows += [("Recorded harvest", f"{row.actual:,.0f} kg/ha"), ("Absolute error", f"{abs(row.prediction-row.actual):,.0f} kg/ha")]
    if "lower_80_kg_ha" in row.index and pd.notna(row.lower_80_kg_ha):
        rows.append(("Approximate 80% interval", f"{row.lower_80_kg_ha:,.0f}–{row.upper_80_kg_ha:,.0f} kg/ha"))
    if "selected_configuration" in row.index:
        rows.append(("Configuration used", row.selected_configuration))
    table(rows)
    with st.expander("Historical inputs used for this estimate"):
        st.dataframe(history.rename(columns={"year": "Start year", "yield": "Yield (kg/ha)"}), hide_index=True)
        st.caption(f"History: {year-6}–{year-2}. Issue date: 31 August {year}. The previous year's yield is excluded under the assumed reporting delay.")
    st.caption("A change from historical yield is not a measured damage percentage or calibrated risk alert.")
    fields = ["district", "state", "year", "method", "prediction", "reference"]+(["actual"] if reveal else [])
    export = pd.DataFrame([row[fields]]).rename(columns={"prediction": "predicted_yield_kg_ha", "reference": "reference_yield_kg_ha", "actual": "actual_yield_kg_ha"})
    st.download_button("Download this record", export.to_csv(index=False), "rice_yield_record.csv", "text/csv")


def data_page(data, state, code):
    with st.sidebar:
        view = st.radio("Explore", ["Yield over time", "District comparison", "Weather patterns", "Data coverage"], key="data_view")
    full = data["history"].loc[data["history"].state.eq(state)].copy()
    first, last = int(full.year.min()), int(full.year.max())
    window = st.slider("Data years", first, last, (first, last), key="range_"+data["kind"]+state)
    frame = full.loc[full.year.between(*window)].copy()
    st.caption(f"{len(frame):,} prepared district-year records · {frame.district_id.nunique()} districts · {window[0]}–{window[1]} · "+
               ("development observations" if data["kind"] != "annual" else "annual rice; historical district boundaries"))
    if view == "Yield over time":
        with st.container(key="data_chart_controls"):
            _, forecast_control = st.columns([3, 1])
            with forecast_control:
                show_forecast = st.toggle("Show forecast", value=False, key="forecast_line_data")
        summary = frame.groupby("year").yield_kg_ha.agg(median="median", low=lambda x: x.quantile(.25), high=lambda x: x.quantile(.75)).reset_index()
        base = alt.Chart(summary).encode(x=alt.X("year:Q", title="Agricultural start year", axis=alt.Axis(format="d", tickMinStep=1)))
        band = base.mark_area(color=LIGHT, opacity=.7).encode(y=alt.Y("low:Q", title="Yield (kg/ha)"), y2="high:Q")
        median = base.mark_line(color="#7698bc", strokeDash=[5, 4]).encode(y="median:Q", tooltip=["year:Q", alt.Tooltip("median:Q", title="District median", format=",.0f")])
        forecasts = data["records"].loc[data["records"].district_id.eq(code) & data["records"].method.eq(data["primary"]) & data["records"].year.between(*window)]
        district = yield_lines(frame.loc[frame.district_id.eq(code)].rename(columns={"yield_kg_ha": "yield"}),
                               forecasts.rename(columns={"prediction": "yield"}), show_forecast=show_forecast)
        chart(band+median if district is None else band+median+district)
        st.caption("Solid blue: actual district yield. When enabled, the forecast line uses the study's primary method and only years with saved predictions. The pale dashed line is the district median; shading is the middle 50%, not a confidence interval or area-weighted state yield.")
        if show_forecast and forecasts.empty:
            st.info("No saved forecasts fall in this data-year range. Use Yield explorer to compare the study's forecast years.")
    elif view == "District comparison":
        frame["highlight"] = np.where(frame.district_id.eq(code), "Selected district", "Other districts")
        chart(alt.Chart(frame).mark_boxplot(extent=1.5, size=12).encode(
            y=alt.Y("district:N", title=None, sort=frame.groupby("district").yield_kg_ha.median().sort_values(ascending=False).index.tolist()),
            x=alt.X("yield_kg_ha:Q", title="Yield (kg/ha)"), color=alt.Color("highlight:N", title=None,
                scale=alt.Scale(domain=["Selected district", "Other districts"], range=[BLUE, LIGHT])), tooltip=["district:N"]), max(320, 23*frame.district_id.nunique()))
        st.caption("Boxes contain the middle 50% of yields. Outside points are retained; they are not automatically errors.")
    elif view == "Weather patterns":
        district = frame.loc[frame.district_id.eq(code)]
        if district.empty:
            st.info("No prepared observations for this district in the selected year range. Widen the range to explore its weather.")
            return
        weather_year = st.selectbox("Weather year", sorted(district.year.unique(), reverse=True), key="weather_year_"+data["kind"]+state)
        indicators = {"Rainfall": ("PRECTOTCORR", "Rainfall (mm/day)" if data["kind"] == "annual" else "Total rainfall (mm)"),
            "Maximum temperature": ("T2M_MAX", "Mean maximum temperature (C)"), "Minimum temperature": ("T2M_MIN", "Mean minimum temperature (C)"),
            "Humidity": ("RH2M", "Relative humidity (%)")}
        if data["kind"] != "annual":
            indicators["Solar energy"] = ("ALLSKY_SFC_SW_DWN", "Mean daily solar energy (MJ/m²/day)")
        indicator = st.selectbox("Weather variable", list(indicators))
        variable, unit = indicators[indicator]
        row = district.loc[district.year.eq(weather_year)].iloc[0]
        periods = ["June", "July", "August" if data["kind"] == "annual" else "1–24 August"]
        weather = pd.DataFrame({"Window": periods, "value": [row[f"{variable}_{m:02d}"] for m in (6, 7, 8)]})
        chart(alt.Chart(weather).mark_bar(color=BLUE, size=65).encode(x=alt.X("Window:N", sort=periods, title=None),
            y=alt.Y("value:Q", title=unit), tooltip=["Window:N", alt.Tooltip("value:Q", title=unit, format=".2f")]))
        st.caption("NASA POWER gridded estimates. Weather observations support the research comparisons; they do not change a saved history-only forecast.")
    else:
        coverage = frame.assign(available=frame.yield_kg_ha.notna().map({True: "Available", False: "Missing"}))
        chart(alt.Chart(coverage).mark_rect(stroke="white", strokeWidth=1).encode(x=alt.X("year:O", title="Agricultural start year", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("district:N", title=None), color=alt.Color("available:N", title=None, scale=alt.Scale(domain=["Available", "Missing"], range=[BLUE, "#e7edf4"])),
            tooltip=["district:N", "year:O", "available:N"]), max(320, 23*frame.district_id.nunique()))
        st.caption("Availability in the prepared cohort does not certify historical publication dates or unchanged boundaries.")
    with st.expander("View records and definitions"):
        display = frame.loc[frame.district_id.eq(code), ["district", "year", "yield_kg_ha"]].rename(columns={"yield_kg_ha": "Yield (kg/ha)"})
        st.dataframe(display, hide_index=True, width="stretch")
        st.write("Yield = harvested rice per hectare. Annual rice combines seasons; Kharif is season-specific. Studies are not pooled. Missing early lag histories reduce the Kharif modelling cohort from 600 to 420 records.")
        st.download_button("Download selected district data", display.to_csv(index=False), "district_yield_data.csv", "text/csv")


def accuracy(frame):
    error = frame.prediction-frame.actual
    denominator = ((frame.actual-frame.actual.mean())**2).sum()
    return [("Records", len(frame)), ("Average absolute error (MAE)", f"{abs(error).mean():,.1f} kg/ha"),
            ("Root mean squared error (RMSE)", f"{np.sqrt((error**2).mean()):,.1f} kg/ha"), ("Average bias", f"{error.mean():+,.1f} kg/ha"),
            ("R squared", f"{1-(error**2).sum()/denominator:.3f}" if denominator > 0 else "Unavailable"),
            ("Weighted absolute percentage error", percent(abs(error).sum()/abs(frame.actual).sum() if abs(frame.actual).sum() else None))]


def evaluation_page(data, state, code, method):
    with st.sidebar:
        view = st.selectbox("Result to view", ["Accuracy", "Compare methods", "Yearly errors", "Low-yield detection", "Uncertainty", "Error patterns"], key="result_view")
        scope = st.selectbox("Evaluation scope", ["Selected state", "Selected district", "Full study"])
    frame = selected(data, state, code, method, scope)
    st.caption(f"{view} · {scope.lower()} · {frame.year.min()}–{frame.year.max()} · {method}")
    if view == "Accuracy":
        table(accuracy(frame))
        st.caption("Lower MAE means smaller typical errors. Bias is prediction minus observed. Negative R squared indicates poor squared-error performance.")
        if data["kind"] == "revised":
            st.write("The revised selection procedure did not improve on the historical mean across the full study. It is not cleared for reliable forecasting.")
    elif view == "Compare methods":
        if data["kind"] == "annual" and len(data["methods"]) == 1:
            comparison = data["scores"][["model", "mae_kg_ha", "rmse_kg_ha"]].rename(columns={"model": "Method", "mae_kg_ha": "MAE (kg/ha)", "rmse_kg_ha": "RMSE (kg/ha)"})
            st.caption("Archived comparison for the full five-state study. Other methods' district-level predictions were not saved.")
        else:
            all_methods = selected(data, state, code, None, scope)
            comparison = pd.DataFrame([{"Method": name, "MAE (kg/ha)": float(abs(g.prediction-g.actual).mean()),
                "RMSE (kg/ha)": float(np.sqrt(((g.prediction-g.actual)**2).mean()))} for name, g in all_methods.groupby("method")])
        chart(alt.Chart(comparison).mark_bar(color=BLUE).encode(y=alt.Y("Method:N", sort=None, title=None),
            x=alt.X("MAE (kg/ha):Q", title="Average absolute error (kg/ha)"), tooltip=["Method:N", alt.Tooltip("MAE (kg/ha):Q", format=",.1f")]), max(280, 32*len(comparison)))
        st.dataframe(comparison.round(1), hide_index=True, width="stretch")
        st.caption("Comparisons do not authorise choosing a new winner from evaluation outcomes. Different studies cover different years and cannot be compared directly.")
    elif view == "Yearly errors":
        yearly = frame.assign(error=lambda d: abs(d.prediction-d.actual)).groupby("year").error.mean().reset_index()
        chart(alt.Chart(yearly).mark_line(point=True, color=BLUE, strokeWidth=2.5).encode(x=alt.X("year:O", title="Agricultural start year"),
            y=alt.Y("error:Q", title="MAE (kg/ha)"), tooltip=["year:O", alt.Tooltip("error:Q", format=",.1f")]))
    elif view == "Low-yield detection":
        actual, flagged = frame.actual < frame.threshold, frame.prediction < frame.threshold
        tp, fp, fn, tn = [int(v) for v in ((actual & flagged).sum(), (~actual & flagged).sum(), (actual & ~flagged).sum(), (~actual & ~flagged).sum())]
        table([("Observed low-yield outcomes", int(actual.sum())), ("Correct low-yield flags", tp), ("False flags", fp), ("Missed low-yield outcomes", fn),
               ("Correct normal-yield outcomes", tn), ("Precision", percent(tp/(tp+fp) if tp+fp else None)), ("Recall", percent(tp/(tp+fn) if tp+fn else None))])
        st.caption("Low yield is below 80% of the historical reference. These flags are not reliable damage alerts or calibrated probabilities.")
    elif view == "Uncertainty":
        if data["kind"] == "revised":
            intervals = read("revised_modelling", "interval_evaluation.csv").rename(columns=RENAME)
            if scope == "Selected district":
                intervals = intervals.loc[intervals.district_id.eq(code)]
            st.caption("Separate interval experiment: configuration fixed in 2012, evaluated in 2016–2017. These intervals do not belong to the adaptive method selected above.")
        else:
            intervals = frame.loc[frame.lower_80_kg_ha.notna()].copy()
        if intervals.empty:
            st.info("No interval was saved for this method. Choose the study's primary saved method to view its intervals.")
            return
        covered = intervals.actual.between(intervals.lower_80_kg_ha, intervals.upper_80_kg_ha)
        table([("Nominal coverage", "80%"), ("Observed coverage", percent(covered.mean())), ("Records", len(intervals)),
               ("Average interval width", f"{(intervals.upper_80_kg_ha-intervals.lower_80_kg_ha).mean():,.0f} kg/ha")])
        st.caption("Wide intervals can cover many outcomes while being less useful. Coverage varies by year; future coverage is not guaranteed.")
    else:
        errors = frame.assign(error=lambda d: d.prediction-d.actual)
        points = alt.Chart(errors).mark_circle(size=55, color=BLUE, opacity=.65).encode(x=alt.X("prediction:Q", title="Predicted yield (kg/ha)"),
            y=alt.Y("error:Q", title="Predicted minus observed (kg/ha)"), tooltip=["district:N", "year:O", alt.Tooltip("error:Q", format=",.0f")])
        zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(color="#111111").encode(y="zero:Q")
        chart(points+zero)
        st.caption("Look for bias and changes in error spread. This does not prove independence, correct specification or causal effects.")
    with st.expander("How this evaluation was conducted"):
        st.write("Chronological fitting excludes future labels. Revised modelling uses nested selection across 17 configurations; saved Kharif and annual studies retain their original frozen selections. Scaling fits within training data. Publication dates and boundary stability remain assumptions.")
        st.write("The revised archive was already inspected, so it is exploratory rather than independent confirmation. Protein and aluminium are not district-level predictors.")
    export = frame[["district", "state", "year", "method", "actual", "prediction", "reference"]].rename(columns={
        "prediction": "predicted_yield_kg_ha", "actual": "actual_yield_kg_ha", "reference": "reference_yield_kg_ha"})
    st.download_button("Download evaluation records", export.to_csv(index=False), "rice_evaluation.csv", "text/csv")


def render_dashboard():
    page, data, state, code, district, year, method = controls()
    st.markdown('<div class="eyebrow">RICE YIELD OUTLOOK</div>', unsafe_allow_html=True)
    st.title({"Yield explorer": "Explore rice yield", "Data explorer": "Understand the data", "Model evaluation": "Evaluate the forecasts"}[page])
    st.caption(f"{district}, {state} · "+next(name for name, kind in KINDS.items() if kind == data["kind"]))
    st.divider()
    if data["kind"] == "annual" and method is not None and method != data["primary"]:
        st.caption("Fixed-settings annual comparator. The original selected model remains History Ridge; these comparisons are not independent new validation.")
    if page == "Yield explorer":
        st.caption("Historical research estimates. No live forecast or reliable damage alert is available.")
        yield_page(data, code, year, method)
    elif page == "Data explorer":
        data_page(data, state, code)
    else:
        evaluation_page(data, state, code, method)
    with st.expander("Data sources and scope"):
        st.write("Yield: DES (Kharif) or ICRISAT (annual). Weather: NASA POWER. Rice yield is kilograms harvested per hectare. Protein and aluminium are separate supporting research, not district-model inputs.")
        st.markdown("[DES](https://www.data.desagri.gov.in/website/apy-query-report-web) · [ICRISAT](https://doi.org/10.21421/D2/XFB1BZ) · [NASA POWER](https://power.larc.nasa.gov/)")
        st.caption("Kharif weather uses fixed 2011 district reference polygons, whole-district weights and revised historical archives. Map: DataMeet Community Maps Project, CC BY 2.5 India. Annual data use historical 1966-apportioned districts; ICRISAT data-sharing terms apply.")
