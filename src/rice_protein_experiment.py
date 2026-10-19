"""Frozen, nested location comparison of measured SNP representations.

Imported research functionality; app.py remains the sole application launcher.
Reference structure descriptors are priors on measured SNPs, not new observations.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from src.rice_baseline import DATA, ROOT
from src.rice_literature import COMPACT, prepare_literature
from src.rice_validation import INPUTS

OUT = DATA / "protein_experiment" / "day_60"
AUDIT = DATA / "molecular_linkage_audit"
MODELS = {
    "Training mean": (),
    "Environment": ("environment",),
    "Environment + all SNPs": ("environment", "all"),
    "Environment + coding SNPs": ("environment", "coding"),
    "Environment + six SNPs": ("environment", "six"),
    "Environment + SNP PCA control": ("environment", "pca"),
    "Environment + structure": ("environment", "structure"),
    "Environment + shuffled structure": ("environment", "shuffled"),
    "Environment + all SNPs + structure": ("environment", "all", "structure"),
}
ALPHAS = [0.1, 1.0, 10.0, 100.0]
PRIMARY = "Environment + all SNPs + structure"
CONTROL = "Environment + all SNPs"


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs():
    paths = [DATA / n for n in INPUTS]
    paths += [AUDIT / n for n in ["measured_variant_dosages.csv", "reference_structure_features.csv"]]
    paths += [ROOT / "src" / n for n in ["rice_protein_experiment.py", "rice_baseline.py",
                                        "rice_context.py", "rice_literature.py", "rice_validation.py"]]
    return {p.relative_to(ROOT).as_posix(): _hash(p) for p in paths}


def _load():
    frame, windows = prepare_literature(60)
    frame = frame.reset_index(drop=True)
    frame["record_id"] = np.arange(len(frame))
    unique = frame.drop_duplicates("genotype_id").set_index("genotype_id")
    all_snps = unique[[c for c in frame if c.startswith("snp_")]].astype(float) * 2
    coding = pd.read_csv(AUDIT / "measured_variant_dosages.csv").set_index("genotype_id").reindex(unique.index)
    sites = pd.read_csv(AUDIT / "reference_structure_features.csv")
    descriptors = ["confident_nonlocal_ca_neighbors_8A", "radial_position_over_confident_rg"]
    sites = sites.loc[sites.reference_residue_plddt.ge(70)].dropna(subset=descriptors).sort_values("marker")
    six = coding[sites.marker.tolist()]
    weights = StandardScaler().fit_transform(sites[descriptors])
    permutation = np.random.default_rng(42).permutation(len(sites))
    tables = {"all": all_snps, "coding": coding, "six": six}
    for name, annotation in [("structure", weights), ("shuffled", weights[permutation])]:
        tables[name] = pd.DataFrame(np.c_[six.mean(axis=1), six.to_numpy() @ annotation / len(sites)],
                                    index=six.index)
    if any(t.isna().any().any() for t in tables.values()):
        raise ValueError("Molecular linkage is incomplete; no silent cohort reduction allowed.")
    if (len(frame), frame.genotype_id.nunique(), frame.environment_id.nunique(),
            frame.location_group.nunique(), len(sites)) != (1046, 107, 15, 12, 6):
        raise ValueError("Audited cohort or structure-site count changed; revise protocol explicitly.")
    return frame, windows, tables, sites, permutation


def freeze_protocol():
    """Run before fitting; refuse changes to an already frozen protocol."""
    frame, windows, tables, sites, permutation = _load()
    protocol = {
        "version": "protein-context-location-v1", "frozen_on": "2026-10-20",
        "status": "Development experiment; outcomes in these trials were examined in earlier studies.",
        "target": "Published adjusted trial grain yield, kg/ha; not direct causal damage or district yield.",
        "cohort": {"records": len(frame), "genotypes": 107, "environments": 15, "location_groups": 12},
        "forecast_cutoff": "Inclusive days 0..60 after recorded seeding; strictly before harvest.",
        "environment_columns": COMPACT + [c for c in frame if c.startswith("plant_")],
        "genetic_dimensions": {k: t.shape[1] for k, t in tables.items()},
        "structure_markers": sites.marker.tolist(), "shuffle_permutation_seed42": permutation.tolist(),
        "structure_features": "Mean alternate dosage; mean dosage weighted by standardized reference contacts and radial position. Annotation standardization across six fixed sites, independent of trial outcomes.",
        "pca_control": "Mean six-site dosage plus first two PCs of standardized six SNPs; PCA fitted only to unique training genotypes.",
        "quality_filter": "Local pLDDT >=70 and both reference geometry descriptors present. Confidence is not function.",
        "models": MODELS, "ridge_alpha_grid": ALPHAS,
        "outer_split": "Leave one complete country/location group out; 12 folds.",
        "inner_split": "Leave one remaining location out; select lowest equal-location macro RMSE; grid-order tie break.",
        "preprocessing": "Median numeric imputation and standardization, categorical one-hot encoding fitted on unique training environments. Genetic standardization fitted on unique training genotypes. Each block divided by sqrt(its original column count). All-SNP block uses exact positive-eigenvalue training span, with no truncated fitted directions. No post-concatenation scaling.",
        "training_weights": "Inverse training environment record count, normalized to mean one. Mean baseline uses the same weights.",
        "primary_comparison": [PRIMARY, CONTROL],
        "primary_metric": "Equal-location macro RMSE = sqrt(mean(location MSE)); positive improvement means lower error.",
        "secondary_metrics": ["pooled MAE", "pooled RMSE", "pooled R squared", "equal-location MAE", "within-environment genotype Pearson correlation"],
        "stability": "5000 paired bootstrap samples of the 12 held-out locations, seed42, percentile95% interval; descriptive development stability only.",
        "claim_rule": "Primary macro RMSE improvement >0, bootstrap lower bound >0, >=6 locations improve; structure-only representation must also beat both PCA and shuffled-annotation controls on macro RMSE to suggest annotation specificity. No external validation or operational promotion.",
        "limitations": "Six sites from a bounded structural audit; additive engineered representations only. Locations held out, genotypes may overlap; no claim about unseen cultivars, full cultivar folding, aluminium tolerance, damage causality or temporal forecasting.",
        "source_sha256": _inputs(),
        "regional_model_sha256": _hash(ROOT / "models" / "rice_regional.joblib"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "protocol.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(protocol)):
            raise ValueError("Frozen protocol differs. Do not overwrite it after seeing results.")
    else:
        path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
        windows.to_csv(OUT / "forecast_windows.csv", index=False)
    return protocol


def _scaled(table, train_ids, test_ids):
    scale = StandardScaler().fit(table.loc[pd.unique(train_ids)])
    return (scale.transform(table.loc[train_ids]) / np.sqrt(table.shape[1]),
            scale.transform(table.loc[test_ids]) / np.sqrt(table.shape[1]))


def _designs(train, test, tables, columns):
    unique = train.drop_duplicates("environment_id")
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(unique[c])]
    categorical = [c for c in columns if c not in numeric]
    impute = SimpleImputer(strategy="median", keep_empty_features=True).fit(unique[numeric])
    scaler = StandardScaler().fit(impute.transform(unique[numeric]))
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(unique[categorical])
    def environment(rows):
        x = np.c_[scaler.transform(impute.transform(rows[numeric])), encoder.transform(rows[categorical])]
        return x / np.sqrt(x.shape[1])
    designs = {"environment": (environment(train), environment(test))}
    ids, other = train.genotype_id, test.genotype_id
    for name, table in tables.items():
        a, b = _scaled(table, ids, other)
        if name == "all":
            # Rotate to the full fitted genotype span: exact linear-kernel Ridge.
            u = a[~ids.duplicated().to_numpy()]
            eigen, vectors = np.linalg.eigh(u @ u.T)
            keep = eigen > max(eigen.max(), 1) * 1e-12
            basis = u.T @ (vectors[:, keep] / np.sqrt(eigen[keep]))
            a, b = a @ basis, b @ basis
        designs[name] = (a, b)
    six_train, six_test = designs["six"]
    pca = PCA(n_components=2, svd_solver="full").fit(six_train[~ids.duplicated().to_numpy()])
    pca_table = pd.DataFrame(np.c_[tables["six"].mean(axis=1),
                                   pca.transform(StandardScaler().fit(tables["six"].loc[pd.unique(ids)])
                                                 .transform(tables["six"]) / np.sqrt(6))],
                             index=tables["six"].index)
    designs["pca"] = _scaled(pca_table, ids, other)
    return designs


def _predict(train, designs, model, alpha):
    counts = train.groupby("environment_id").environment_id.transform("size").to_numpy()
    weights = 1 / counts
    weights /= weights.mean()
    keys = MODELS[model]
    if not keys:
        return np.full(len(designs["environment"][1]), np.average(train.yield_kg_ha, weights=weights))
    a = np.concatenate([designs[k][0] for k in keys], axis=1)
    b = np.concatenate([designs[k][1] for k in keys], axis=1)
    return Ridge(alpha=alpha, solver="cholesky").fit(a, train.yield_kg_ha, sample_weight=weights).predict(b)


def _metrics(rows):
    residual = rows.predicted_yield_kg_ha - rows.observed_yield_kg_ha
    per = rows.assign(ae=abs(residual), se=residual**2).groupby("location_group")[["ae", "se"]].mean()
    return {"mae_kg_ha": mean_absolute_error(rows.observed_yield_kg_ha, rows.predicted_yield_kg_ha),
            "rmse_kg_ha": float(np.sqrt(mean_squared_error(rows.observed_yield_kg_ha, rows.predicted_yield_kg_ha))),
            "r_squared": r2_score(rows.observed_yield_kg_ha, rows.predicted_yield_kg_ha),
            "macro_mae_kg_ha": per.ae.mean(), "macro_rmse_kg_ha": float(np.sqrt(per.se.mean()))}


def run_experiment():
    protocol = freeze_protocol()
    if (OUT / "summary.json").exists():
        raise FileExistsError("Completed experiment exists; inspect it rather than refitting.")
    frame, _, tables, _, _ = _load()
    predictions, selections = [], []
    with threadpool_limits(limits=1):
        for group in sorted(frame.location_group.unique()):
            train = frame.loc[frame.location_group.ne(group)]
            test = frame.loc[frame.location_group.eq(group)]
            losses = {name: np.zeros(len(ALPHAS)) for name in MODELS if MODELS[name]}
            for inner in sorted(train.location_group.unique()):
                fit = train.loc[train.location_group.ne(inner)]
                valid = train.loc[train.location_group.eq(inner)]
                designs = _designs(fit, valid, tables, protocol["environment_columns"])
                for model in losses:
                    for j, alpha in enumerate(ALPHAS):
                        pred = _predict(fit, designs, model, alpha)
                        mse = np.mean((pred - valid.yield_kg_ha.to_numpy())**2)
                        losses[model][j] += mse / train.location_group.nunique()
                        selections.append({"held_out_location": group, "inner_location": inner,
                                           "model": model, "alpha": alpha, "inner_mse": mse})
            designs = _designs(train, test, tables, protocol["environment_columns"])
            for model in MODELS:
                alpha = ALPHAS[int(np.argmin(losses[model]))] if MODELS[model] else None
                pred = _predict(train, designs, model, alpha)
                rows = test[["record_id", "genotype_id", "environment_id", "location_group"]].copy()
                rows["observed_yield_kg_ha"] = test.yield_kg_ha
                rows["predicted_yield_kg_ha"] = pred
                rows["model"], rows["selected_alpha"] = model, alpha
                predictions.append(rows)
            print(f"Completed held-out location: {group}", flush=True)
    predictions = pd.concat(predictions, ignore_index=True)
    metrics = pd.DataFrame([{"model": name, **_metrics(rows)} for name, rows in predictions.groupby("model", sort=False)])
    residual = predictions.predicted_yield_kg_ha - predictions.observed_yield_kg_ha
    folds = predictions.assign(ae=abs(residual), se=residual**2).groupby(["model", "location_group"], sort=False).agg(
        mae_kg_ha=("ae", "mean"), mse_kg2_ha2=("se", "mean"), records=("record_id", "size"), selected_alpha=("selected_alpha", "first")).reset_index()
    per = folds.pivot(index="location_group", columns="model", values="mse_kg2_ha2")
    samples = np.random.default_rng(42).integers(0, len(per), size=(5000, len(per)))
    pairs = []
    for candidate, control in [(PRIMARY, CONTROL), ("Environment + structure", "Environment + SNP PCA control"),
                               ("Environment + structure", "Environment + shuffled structure"),
                               ("Environment + structure", "Environment + six SNPs")]:
        x, y = per[candidate].to_numpy(), per[control].to_numpy()
        boot = np.sqrt(y[samples].mean(axis=1)) - np.sqrt(x[samples].mean(axis=1))
        pairs.append({"candidate": candidate, "control": control,
                      "macro_rmse_improvement_kg_ha": float(np.sqrt(y.mean()) - np.sqrt(x.mean())),
                      "bootstrap_lower_95": float(np.quantile(boot, .025)),
                      "bootstrap_upper_95": float(np.quantile(boot, .975)),
                      "locations_improved": int((x < y).sum())})
    ranking = []
    for (model, env), rows in predictions.groupby(["model", "environment_id"]):
        corr = rows.observed_yield_kg_ha.corr(rows.predicted_yield_kg_ha) if rows.predicted_yield_kg_ha.std() > 1e-8 else np.nan
        ranking.append({"model": model, "environment_id": env, "records": len(rows), "pearson_r": corr})
    primary = pairs[0]
    supported = (primary["macro_rmse_improvement_kg_ha"] > 0 and primary["bootstrap_lower_95"] > 0
                 and primary["locations_improved"] >= 6 and all(p["macro_rmse_improvement_kg_ha"] > 0 for p in pairs[1:3]))
    for name, table in [("predictions", predictions), ("metrics", metrics), ("location_results", folds),
                        ("inner_selection", pd.DataFrame(selections)), ("paired_comparisons", pd.DataFrame(pairs)),
                        ("within_environment_rankings", pd.DataFrame(ranking))]:
        table.to_csv(OUT / f"{name}.csv", index=False)
    summary = {"completed_on": "2026-10-20", "protocol_sha256": _hash(OUT / "protocol.json"),
               "records_per_model": len(frame), "models": len(MODELS), "outer_locations": 12,
               "annotation_value_claim_supported": bool(supported), "primary_comparison": primary,
               "regional_model_unchanged": _hash(ROOT / "models" / "rice_regional.joblib") == protocol["regional_model_sha256"],
               "interpretation": "Development comparison of deterministic measured-SNP representations; no independent external validation."}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
