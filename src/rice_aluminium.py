"""Descriptive paired soil-condition study, kept separate from yield forecasting."""
import hashlib
import json

import numpy as np
import pandas as pd

from src.rice_baseline import DATA


def load_aluminium_study():
    folder = DATA / "cirad_aluminium"
    source = folder / "adjusted_yields_audited.csv"
    adjusted = pd.read_csv(source)
    families = adjusted.loc[adjusted.Gen.eq("Fam")].copy()
    if families.duplicated(["DNAID", "SOIL"]).any():
        raise ValueError("Duplicate family/condition keys in supporting aluminium study.")
    if set(families.SOIL) != {"ALU", "LIM"}:
        raise ValueError("Expected the published ALU and LIM conditions.")
    paired = families.pivot(index="DNAID", columns="SOIL", values="yield_kg_ha_14pct_moisture")
    if paired.isna().any().any() or not np.isfinite(paired.to_numpy()).all():
        raise ValueError("Supporting study requires complete finite paired yields.")
    paired = paired.reset_index().rename(columns={"ALU": "ALU_yield_kg_ha", "LIM": "LIM_yield_kg_ha"})
    paired["LIM_minus_ALU_kg_ha"] = paired.LIM_yield_kg_ha - paired.ALU_yield_kg_ha
    soil = pd.read_csv(folder / "soil_condition_summaries.csv")
    audit = json.loads((folder / "audit_summary.json").read_text(encoding="utf-8"))
    summary = {"paired_families": len(paired), "ALU_mean_kg_ha": float(paired.ALU_yield_kg_ha.mean()),
               "LIM_mean_kg_ha": float(paired.LIM_yield_kg_ha.mean()),
               "mean_LIM_minus_ALU_kg_ha": float(paired.LIM_minus_ALU_kg_ha.mean()),
               "median_LIM_minus_ALU_kg_ha": float(paired.LIM_minus_ALU_kg_ha.median()),
               "families_with_higher_LIM_yield": int(paired.LIM_minus_ALU_kg_ha.gt(0).sum()),
               "independent_site_seasons": audit["independent_site_seasons"],
               "adjusted_yield_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "soil_summary_sha256": hashlib.sha256((folder / "soil_condition_summaries.csv").read_bytes()).hexdigest()}
    return paired, soil, summary
