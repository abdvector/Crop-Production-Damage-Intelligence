"""The input contract for the simplified annual rice study."""
from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/rice/regional_forecast/district_years.csv"
SOURCE_SHA = "77163c0c5ae91565ba087c04ee297edc08989245501658e69d77d4f28dee8d74"
LAGS = [f"yield_lag{i}" for i in range(2, 7)]
WEATHER = [f"{p}_{m:02d}" for p in ("T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M") for m in (6, 7, 8)]
FEATURES = LAGS + WEATHER
TARGET = "yield_kg_ha"
MONTHS = {6: "June", 7: "July", 8: "August"}
LABELS = {f"yield_lag{i}": f"Yield Y-{i} (kg/ha)" for i in range(2, 7)}
for parameter, label in [("T2M_MAX", "Maximum temperature (C)"), ("T2M_MIN", "Minimum temperature (C)"),
                         ("PRECTOTCORR", "Rainfall (mm/day)"), ("RH2M", "Relative humidity (%)")]:
    for month, name in MONTHS.items():
        LABELS[f"{parameter}_{month:02d}"] = f"{name}: {label}"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(frame):
    """Reject invalid units/ranges rather than silently replacing manual inputs."""
    values = frame[FEATURES].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Every predictor must contain a finite number.")
    if (frame[LAGS] <= 0).any().any():
        raise ValueError("Past yields must be positive, in kg/ha.")
    for month in MONTHS:
        if (frame[f"T2M_MIN_{month:02d}"] > frame[f"T2M_MAX_{month:02d}"]).any():
            raise ValueError("Minimum temperature cannot exceed maximum temperature.")
        for parameter in ("T2M_MAX", "T2M_MIN"):
            if not frame[f"{parameter}_{month:02d}"].between(-60, 65).all():
                raise ValueError("Temperature must be between -60 and 65 C.")
        if (frame[f"PRECTOTCORR_{month:02d}"] < 0).any():
            raise ValueError("Rainfall cannot be negative; enter mm/day, not monthly totals.")
        if not frame[f"RH2M_{month:02d}"].between(0, 100).all():
            raise ValueError("Relative humidity must be between 0 and 100 percent.")


def load_data():
    if digest(SOURCE) != SOURCE_SHA:
        raise ValueError("The verified prepared source has changed. Review it before modelling.")
    frame = pd.read_csv(SOURCE)
    if frame.duplicated(["district_id", "year"]).any():
        raise ValueError("Duplicate district/year keys.")
    validate_inputs(frame)
    if not np.isfinite(frame[TARGET]).all() or (frame[TARGET] <= 0).any():
        raise ValueError("Invalid yield labels.")
    if not np.allclose(frame[LAGS].mean(axis=1), frame.reference_yield):
        raise ValueError("Historical reference does not match the five lagged yields.")
    frame["state"] = frame.state.replace({"Orissa": "Odisha"})
    return frame
