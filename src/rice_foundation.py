"""Reproducible development-data audit; never fits or selects a forecasting model."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/rice/odisha_seasonal"
OUT = ROOT / "data/processed/rice/foundation"
FIGURES = OUT / "figures"
CODE, YEAR, TARGET = "district_code_census2011", "agricultural_start_year", "yield_kg_ha"
LAGS = [f"yield_lag{i}" for i in range(2, 7)]
WEATHER = [f"{p}_{m:02d}" for m in (6, 7, 8) for p in
           ("T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN")] + [
               "longest_dry_spell_days", "wet_days", "max_five_day_rain_mm", "tmax_p95_c"]
FEATURES = LAGS + [YEAR] + WEATHER


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(frame):
    """Fail rather than silently repair ambiguous keys, labels or histories."""
    if len(frame) != 750 or frame.duplicated([CODE, YEAR]).any():
        raise ValueError("Expected 750 unique district-years")
    if set(frame[YEAR]) != set(range(1998, 2023)) or frame[CODE].nunique() != 30:
        raise ValueError("Unexpected geography or time coverage")
    if frame.loc[frame[YEAR] >= 2018, TARGET].notna().any():
        raise ValueError("Original reserved targets must remain blank")
    dev = frame.loc[frame[YEAR] <= 2017].copy()
    if len(dev) != 600 or not np.isfinite(dev[[TARGET] + WEATHER]).all().all() or (dev[TARGET] < 0).any():
        raise ValueError("Incomplete or invalid development observations")
    if any(len(g) != 20 for _, g in dev.groupby(CODE)):
        raise ValueError("Incomplete district history")
    lookup = dev.set_index([CODE, YEAR])[TARGET].to_dict()
    for lag in range(2, 7):
        expected = np.array([lookup.get((c, y-lag), np.nan) for c, y in zip(dev[CODE], dev[YEAR])])
        if not np.allclose(expected, dev[f"yield_lag{lag}"], equal_nan=True):
            raise ValueError("Historical lag join mismatch")
    complete = dev.loc[dev[YEAR] >= 2004]
    if len(complete) != 420 or not np.isfinite(complete[FEATURES]).all().all():
        raise ValueError("Expected 420 complete development feature rows")
    if not np.allclose(complete[LAGS].mean(axis=1), complete.history_reference_yield_kg_ha):
        raise ValueError("Historical reference mismatch")
    if not np.allclose(complete[LAGS].to_numpy() @ np.array([2, 1, 0, -1, -2])/10,
                       complete.history_trend_kg_ha_per_year):
        raise ValueError("Historical trend mismatch")
    for month in (6, 7, 8):
        if (dev[f"T2M_MIN_{month:02d}"] > dev[f"T2M_MAX_{month:02d}"]).any():
            raise ValueError("Minimum temperature exceeds maximum")
        if (dev[f"PRECTOTCORR_{month:02d}"] < 0).any() or not dev[f"RH2M_{month:02d}"].between(0, 100).all():
            raise ValueError("Invalid rain or humidity")
    if not dev.wet_days.between(0, 85).all() or not dev.longest_dry_spell_days.between(0, 85).all():
        raise ValueError("Invalid weather event counts")
    return dev


def save_figure(fig, name):
    fig.savefig(FIGURES / (name + ".png"), dpi=180, bbox_inches="tight")
    fig.savefig(FIGURES / (name + ".svg"), bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def data_figures(dev):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "text.color": "#111111", "axes.labelcolor": "#111111", "svg.hashsalt": "rice-foundation-v1"})
    names = dev.groupby(CODE).district_source.first()
    complete = dev.set_index([CODE, YEAR])[TARGET].unstack().notna().astype(int)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(complete, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set(yticks=range(len(complete)), yticklabels=names.reindex(complete.index),
           xticks=range(20), xticklabels=range(1998, 2018), xlabel="Agricultural start year",
           title="Development coverage: all 600 district-year yields available")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    ax.set_xticks(np.arange(-.5, 20, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 30, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    save_figure(fig, "01_coverage")
    yearly = dev.groupby(YEAR)[TARGET].agg(median="median", q25=lambda x: x.quantile(.25), q75=lambda x: x.quantile(.75))
    yearly.to_csv(OUT / "yearly_yield_summary.csv")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(yearly.index, yearly.q25, yearly.q75, color="#c9def2", label="Middle 50% of districts")
    ax.plot(yearly.index, yearly['median'], color="#225b96", label="District median", linewidth=2)
    ax.set(xlabel="Agricultural start year", ylabel="Yield (kg/ha)", title="Yield over time: median and between-district spread")
    ax.set_xticks(range(1998, 2018, 2))
    ax.legend(frameon=False)
    save_figure(fig, "02_yield_trend")
    order = dev.groupby("district_source")[TARGET].median().sort_values().index
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.boxplot([dev.loc[dev.district_source.eq(n), TARGET] for n in order], orientation="horizontal",
               tick_labels=order, patch_artist=True, boxprops={"facecolor": "#c9def2"},
               medianprops={"color": "#123d70"}, flierprops={"marker": ".", "markersize": 3})
    ax.set(xlabel="Yield (kg/ha)", title="District yield distributions, 1998–2017 (20 years each)")
    save_figure(fig, "03_district_yields")
    selected = ["PRECTOTCORR_06", "PRECTOTCORR_07", "PRECTOTCORR_08", "T2M_MAX_06", "T2M_MAX_07",
                "T2M_MAX_08", "RH2M_07", "ALLSKY_SFC_SW_DWN_07", "longest_dry_spell_days", "tmax_p95_c"]
    labels = ["June rain", "July rain", "Aug 1–24 rain", "June Tmax", "July Tmax", "Aug 1–24 Tmax",
              "July humidity", "July solar", "Longest dry spell", "High-end Tmax"]
    corr = dev[selected].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr, cmap="RdBu", vmin=-1, vmax=1)
    ax.set(xticks=range(10), xticklabels=labels, yticks=range(10), yticklabels=labels,
           title="Weather predictor redundancy: Spearman correlation (600 records)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    for i in range(10):
        for j in range(10):
            ax.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center",
                    color="white" if abs(corr.iloc[i,j]) > .65 else "black", fontsize=8)
    fig.colorbar(im, ax=ax, label="Rank correlation; descriptive, not causal")
    save_figure(fig, "04_weather_correlations")


def previous_model_diagnostics():
    """Diagnose existing out-of-time development/calibration errors; no refitting."""
    folder = SOURCE / "model"
    selection = json.loads((folder / "selection.json").read_text())
    name = selection["selected_candidate"]["id"]
    val = pd.read_csv(folder / "development_predictions.csv", dtype={CODE: str})
    val = val.loc[val.candidate.eq(name)].assign(stage="selection (optimistic after selection)")
    cal = pd.read_csv(folder / "calibration_predictions.csv", dtype={CODE: str}).assign(stage="interval calibration")
    errors = pd.concat([val, cal], ignore_index=True).sort_values([CODE, YEAR])
    errors["error_kg_ha"] = errors.predicted_yield_kg_ha - errors.actual_yield_kg_ha
    errors.to_csv(OUT / "legacy_development_errors.csv", index=False)
    yearly = errors.groupby(YEAR).error_kg_ha.agg(["mean", "count", "std"])
    yearly.to_csv(OUT / "legacy_error_by_year.csv")
    adjacent = errors.merge(errors[[CODE, YEAR, "error_kg_ha"]].assign(**{YEAR: lambda d: d[YEAR]+1}),
                            on=[CODE, YEAR], suffixes=("", "_previous"), validate="one_to_one")
    rho = float(adjacent.error_kg_ha.corr(adjacent.error_kg_ha_previous))
    scale_rho = float(stats.spearmanr(errors.predicted_yield_kg_ha, abs(errors.error_kg_ha)).statistic)
    # Fixed geography, symmetric four-nearest-centroid graph; descriptive only.
    # Avoid pooled iid significance tests on this short dependent panel.
    from shapely.geometry import shape
    features = json.loads((SOURCE.parent / "seasonal_geography/reference_geometries.geojson").read_text())["features"]
    centres = {f["properties"][CODE]: shape(f["geometry"]).centroid for f in features}
    codes = sorted(errors[CODE].unique())
    points = np.array([[centres[c].x, centres[c].y] for c in codes])
    points[:, 0] *= np.cos(np.deg2rad(points[:, 1].mean()))
    distance = np.square(points[:, None, :] - points[None, :, :]).sum(axis=2)
    np.fill_diagonal(distance, np.inf)
    weights = np.zeros((len(codes), len(codes)))
    for i, neighbours in enumerate(np.argsort(distance, axis=1)[:, :4]):
        weights[i, neighbours] = 1
    weights = np.maximum(weights, weights.T)
    spatial = []
    for year, part in errors.groupby(YEAR):
        e = part.set_index(CODE).reindex(codes).error_kg_ha.to_numpy()
        z = e-e.mean()
        moran = len(z)/weights.sum() * (z @ weights @ z)/(z @ z) if z @ z > 0 else None
        spatial.append({YEAR: int(year), "moran_I_descriptive": moran, "districts": len(z)})
    pd.DataFrame(spatial).to_csv(OUT / "legacy_spatial_errors.csv", index=False)
    pd.DataFrame(weights, index=codes, columns=codes).to_csv(OUT / "spatial_diagnostic_weights.csv")
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    axes[0, 0].scatter(errors.predicted_yield_kg_ha, errors.error_kg_ha, s=12, color="#225b96", alpha=.6)
    axes[0, 0].axhline(0, color="black", linewidth=.8)
    axes[0, 0].set(xlabel="Predicted yield (kg/ha)", ylabel="Prediction minus observed (kg/ha)", title="Bias and functional form")
    axes[0, 1].scatter(errors.predicted_yield_kg_ha, abs(errors.error_kg_ha), s=12, color="#225b96", alpha=.6)
    axes[0, 1].set(xlabel="Predicted yield (kg/ha)", ylabel="Absolute error (kg/ha)", title="Error size versus prediction")
    annual_bias = yearly['mean'].reindex(range(int(yearly.index.min()), int(yearly.index.max())+1))
    axes[1, 0].plot(annual_bias.index, annual_bias, "o-", color="#225b96")
    axes[1, 0].axhline(0, color="black", linewidth=.8)
    axes[1, 0].set(xlabel="Start year (gaps retained)", ylabel="Mean error (kg/ha)", title="Shared annual forecast bias")
    stats.probplot(errors.error_kg_ha, dist="norm", plot=axes[1, 1])
    axes[1, 1].set(title="Normal Q–Q: descriptive, not a pass/fail gate", ylabel="Ordered error (kg/ha)")
    fig.suptitle("Legacy model diagnostics: 2009–2012 and 2014–2016; no assessment labels")
    save_figure(fig, "05_legacy_error_diagnostics")
    return {"legacy_model": name, "records": len(errors), "consecutive_year_pairs": len(adjacent),
            "lag_one_error_correlation_descriptive": rho,
            "error_magnitude_vs_prediction_spearman_descriptive": scale_rho,
            "mean_error_kg_ha": float(errors.error_kg_ha.mean()),
            "spatial_diagnostic": "Annual Moran I; symmetric four-nearest-centroid graph; approximate local distance; descriptive only, no exchangeability/significance claim",
            "inference": "No iid p-values: repeated districts, shared years and selected validation predictions. These are forecast errors, not OLS fitted residuals."}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    paths = [SOURCE / "prepared_inputs.csv", SOURCE.parent / "seasonal_source/development_labels.csv",
             SOURCE / "model/selection.json", SOURCE / "model/development_predictions.csv",
             SOURCE / "model/calibration_predictions.csv", SOURCE.parent / "seasonal_geography/reference_geometries.geojson",
             Path(__file__), ROOT / "docs/Statistical_Foundation.md"]
    receipt = json.loads((SOURCE / "verification.json").read_text())
    for key, value in receipt["output_sha256"].items():
        if sha(ROOT / key) != value:
            raise ValueError(f"Prepared source no longer matches receipt: {key}")
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths}
    frame = pd.read_csv(paths[0], dtype={CODE: str})
    dev = validate(frame)
    official = pd.read_csv(paths[1])
    official = official.loc[official.state_source.eq("Odisha") & official[YEAR].between(1998, 2017)]
    joined = dev.merge(official[["district_source", YEAR, "area_ha", "production_tonnes", "source_yield_tonnes_ha"]],
                       on=["district_source", YEAR], validate="one_to_one", how="left")
    if not np.isfinite(joined[["area_ha", "production_tonnes", "source_yield_tonnes_ha"]]).all().all():
        raise ValueError("Incomplete source reconciliation")
    difference = abs(joined[TARGET] - 1000*joined.production_tonnes/joined.area_ha)
    if (joined.area_ha <= 0).any() or (joined.production_tonnes < 0).any() or (difference > 5.01).any():
        raise ValueError("Source measurement inconsistency")
    if not np.allclose(joined[TARGET], joined.source_yield_tonnes_ha*1000):
        raise ValueError("Source yield conversion mismatch")
    dev.to_csv(OUT / "development_records.csv", index=False)
    # Keep reference/trend for baseline computation, but not twice in the proposed X.
    complete = dev.loc[dev[YEAR] >= 2004].copy()
    complete[[CODE, "district_source", YEAR, TARGET] + LAGS + WEATHER].to_csv(OUT / "development_features.csv", index=False)
    complete[FEATURES].describe().T.to_csv(OUT / "predictor_summary.csv")
    pd.DataFrame({"missing_development": dev[[TARGET]+FEATURES].isna().sum(),
                  "missing_complete_history_cohort": complete[[TARGET]+FEATURES].isna().sum()}).to_csv(OUT / "missingness.csv")
    complete[FEATURES].corr(method="spearman").to_csv(OUT / "predictor_correlations.csv")
    # IQR flags are review candidates, never automatic exclusions or imputations.
    reviews = []
    for name in [TARGET] + WEATHER:
        q1, q3 = dev[name].quantile([.25, .75]); spread = q3-q1
        subset = dev.loc[(dev[name] < q1-1.5*spread) | (dev[name] > q3+1.5*spread)]
        for row in subset.to_dict("records"):
            reviews.append({CODE: row[CODE], YEAR: row[YEAR], "variable": name, "value": row[name],
                            "action": "retained; pooled IQR flag is not evidence of measurement error"})
    pd.DataFrame(reviews, columns=[CODE, YEAR, "variable", "value", "action"]).to_csv(OUT / "unusual_values_review.csv", index=False)
    data_figures(dev)
    diagnostics = previous_model_diagnostics()
    # The repository preserves data bytes verbatim. Write portable LF outputs,
    # including matplotlib's Windows text exports, before recording checksums.
    for path in OUT.rglob('*'):
        if path.suffix in ('.csv', '.svg'):
            content = path.read_bytes().replace(b'\r\n', b'\n')
            if path.suffix == '.svg':
                content = b'\n'.join(line.rstrip() for line in content.splitlines()) + b'\n'
            path.write_bytes(content)
    scaled = complete[FEATURES].to_numpy(dtype=float)
    scaled = (scaled-scaled.mean(axis=0))/scaled.std(axis=0)
    singular = np.linalg.svd(scaled, compute_uv=False)
    report = {"stage": "development audit complete; revised modelling not started", "development_records": len(dev),
              "complete_history_records": len(complete), "source_rounding_max_difference_kg_ha": float(difference.max()),
              "proposed_numeric_features": FEATURES, "categorical_feature": CODE,
              "removed_from_proposed_X": ["history_reference_yield_kg_ha", "history_trend_kg_ha_per_year"],
              "reason": "Exact combinations of five lags; retained only as baseline auxiliaries in original data",
              "numeric_design_rank": int(np.linalg.matrix_rank(scaled)), "numeric_columns": len(FEATURES),
              "standardized_numeric_condition_number": float(singular[0]/singular[-1]),
              "iqr_review_flags_retained": len(reviews), "legacy_diagnostics": diagnostics,
              "unresolved": ["2018–2022 outcomes already seen: not a fresh confirmatory holdout",
                             "Historical reporting vintages and two-year yield delay unverified",
                             "Fixed 2011 geometry; annual boundary equivalence unverified",
                             "Whole-district weather weights, not rice-area weights",
                             "Dependence-aware inference and revised-model error diagnostics pending",
                             "No causal damage, protein or aluminium predictors"],
              "input_sha256": before}
    if any(sha(ROOT / key) != value for key, value in before.items()):
        raise ValueError("An original input changed during the audit")
    report["output_sha256"] = {str(p.relative_to(OUT)).replace('\\', '/'): sha(p) for p in sorted(OUT.rglob('*'))
                               if p.is_file() and p.name != 'audit.json'}
    (OUT / "audit.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    return report
