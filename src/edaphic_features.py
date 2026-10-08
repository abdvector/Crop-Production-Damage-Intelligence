"""
Module: edaphic_features.py
Description: Edaphic & Soil Chemistry Layer (SoilGrids 2.0 & Regional Soil Profiles).
Models Aluminium toxicity (Al³⁺), acidic soil pH stress, and Cation Exchange Capacity (CEC)
based on mechanisms established by Kochian et al. (2004).
"""

import numpy as np
from typing import Dict, Any, List

# Regional District Soil Profiles (Jharkhand, Bihar, UP, MP, Punjab)
# Reflecting real soil survey data (SoilGrids 2.0 & ICAR Soil Health Cards)
DISTRICT_SOIL_PROFILES = {
    # Jharkhand (Acidic, High-Aluminium, Lateritic Soils)
    "Ranchi": {
        "state": "Jharkhand",
        "latitude": 23.3441, "longitude": 85.3096,
        "soil_type": "Red & Lateritic (Acidic)",
        "pH": 4.8,               # Critical acid range (< 5.5)
        "al_saturation_pct": 58.0, # High Al³⁺ toxicity hazard (> 30% threshold)
        "cec_cmol_kg": 11.2,      # Low cation exchange capacity
        "soc_g_kg": 5.4,          # Low organic carbon
        "bulk_density_g_cm3": 1.48,
        "clay_fraction_pct": 28.0
    },
    "Hazaribagh": {
        "state": "Jharkhand",
        "latitude": 23.9925, "longitude": 85.3637,
        "soil_type": "Red Acidic Loam",
        "pH": 5.0,
        "al_saturation_pct": 52.0,
        "cec_cmol_kg": 12.5,
        "soc_g_kg": 6.1,
        "bulk_density_g_cm3": 1.45,
        "clay_fraction_pct": 25.0
    },
    "Palamu": {
        "state": "Jharkhand",
        "latitude": 24.0416, "longitude": 84.0722,
        "soil_type": "Gravelly Red Soil (Drought Prone)",
        "pH": 5.3,
        "al_saturation_pct": 42.0,
        "cec_cmol_kg": 13.8,
        "soc_g_kg": 4.8,
        "bulk_density_g_cm3": 1.52,
        "clay_fraction_pct": 22.0
    },
    "Dhanbad": {
        "state": "Jharkhand",
        "latitude": 23.7957, "longitude": 86.4304,
        "soil_type": "Lateritic Acidic",
        "pH": 4.9,
        "al_saturation_pct": 55.0,
        "cec_cmol_kg": 10.9,
        "soc_g_kg": 5.2,
        "bulk_density_g_cm3": 1.50,
        "clay_fraction_pct": 26.0
    },
    # Bihar (Neutral to Alkaline Alluvial Soils)
    "Patna": {
        "state": "Bihar",
        "latitude": 25.5941, "longitude": 85.1376,
        "soil_type": "Indo-Gangetic Alluvial",
        "pH": 7.2,
        "al_saturation_pct": 3.0,  # Negligible Al toxicity
        "cec_cmol_kg": 24.5,
        "soc_g_kg": 9.8,
        "bulk_density_g_cm3": 1.35,
        "clay_fraction_pct": 34.0
    },
    "Gaya": {
        "state": "Bihar",
        "latitude": 24.7914, "longitude": 85.0002,
        "soil_type": "Old Alluvial Loam",
        "pH": 6.6,
        "al_saturation_pct": 8.0,
        "cec_cmol_kg": 19.2,
        "soc_g_kg": 7.5,
        "bulk_density_g_cm3": 1.38,
        "clay_fraction_pct": 30.0
    },
    # Uttar Pradesh
    "Varanasi": {
        "state": "Uttar Pradesh",
        "latitude": 25.3176, "longitude": 82.9739,
        "soil_type": "Alluvial Loam",
        "pH": 7.0,
        "al_saturation_pct": 4.0,
        "cec_cmol_kg": 22.1,
        "soc_g_kg": 8.5,
        "bulk_density_g_cm3": 1.36,
        "clay_fraction_pct": 32.0
    },
    # Madhya Pradesh
    "Indore": {
        "state": "Madhya Pradesh",
        "latitude": 22.7196, "longitude": 75.8577,
        "soil_type": "Deep Black Cotton Soil (Vertisol)",
        "pH": 7.8,
        "al_saturation_pct": 1.0,
        "cec_cmol_kg": 38.0,
        "soc_g_kg": 11.2,
        "bulk_density_g_cm3": 1.28,
        "clay_fraction_pct": 48.0
    },
    # Punjab (High-Yield Intensive Agro-Ecosystem)
    "Ludhiana": {
        "state": "Punjab",
        "latitude": 30.9010, "longitude": 75.8573,
        "soil_type": "Fertile Alluvial Loam",
        "pH": 7.4,
        "al_saturation_pct": 2.0,
        "cec_cmol_kg": 21.0,
        "soc_g_kg": 7.9,
        "bulk_density_g_cm3": 1.37,
        "clay_fraction_pct": 29.0
    }
}


class EdaphicFeatureEngine:
    """
    Computes edaphic stress features and biophysical indices
    from soil physicochemical attributes.
    """

    @staticmethod
    def compute_al_toxicity_hazard(al_saturation_pct: float, ph: float) -> float:
        """
        Computes Aluminium Toxicity Hazard Score H_Al in [0, 1].
        Mechanisms (Kochian 2004):
        - Al³⁺ becomes soluble and toxic only when pH < 5.5.
        - Severe root stunting occurs when Al saturation exceeds 30%.
        """
        if ph >= 5.5:
            return 0.0  # Al³⁺ precipitated as non-toxic Al(OH)₃
        # When pH < 5.5, hazard scales with Al saturation above 20%
        excess_al = max(0.0, al_saturation_pct - 20.0)
        ph_amplification = (5.5 - ph) / 1.5  # Amplification as acidity deepens
        hazard = (excess_al / 60.0) * min(1.5, ph_amplification + 0.5)
        return float(np.clip(hazard, 0.0, 1.0))

    @staticmethod
    def compute_soil_stress_indices(profile: Dict[str, Any]) -> Dict[str, float]:
        """
        Extracts 6 normalized edaphic features and composite risk scores.
        """
        ph = profile["pH"]
        al_sat = profile["al_saturation_pct"]
        cec = profile["cec_cmol_kg"]
        soc = profile["soc_g_kg"]
        bd = profile["bulk_density_g_cm3"]
        clay = profile["clay_fraction_pct"]

        al_hazard = EdaphicFeatureEngine.compute_al_toxicity_hazard(al_sat, ph)
        acidity_stress = max(0.0, (5.5 - ph) / 1.5) if ph < 5.5 else 0.0
        cec_buffering_deficit = max(0.0, (25.0 - cec) / 20.0)
        soc_deficit = max(0.0, (12.0 - soc) / 10.0)

        # Composite Edaphic Stress Index (CESI)
        cesi = (0.45 * al_hazard +
                0.25 * acidity_stress +
                0.15 * cec_buffering_deficit +
                0.15 * soc_deficit)

        return {
            "feat_soil_pH": ph,
            "feat_soil_al_sat_pct": al_sat,
            "feat_soil_al_hazard": al_hazard,
            "feat_soil_acidity_stress": acidity_stress,
            "feat_soil_cec": cec,
            "feat_soil_soc": soc,
            "feat_soil_bulk_density": bd,
            "feat_soil_clay_pct": clay,
            "feat_composite_edaphic_stress": float(np.clip(cesi, 0.0, 1.0))
        }

    @staticmethod
    def get_district_profile(district_name: str) -> Dict[str, Any]:
        """Returns raw soil profile and computed features for a district."""
        raw = DISTRICT_SOIL_PROFILES.get(district_name, DISTRICT_SOIL_PROFILES["Ranchi"])
        features = EdaphicFeatureEngine.compute_soil_stress_indices(raw)
        return {**raw, **features}

    @staticmethod
    def get_all_districts() -> List[str]:
        return list(DISTRICT_SOIL_PROFILES.keys())


if __name__ == "__main__":
    engine = EdaphicFeatureEngine()
    print("--- Soil Stress Indices Across Sample Districts ---")
    for d in ["Ranchi", "Hazaribagh", "Patna", "Ludhiana"]:
        p = engine.get_district_profile(d)
        print(f"District: {d:<12} | pH: {p['pH']:<4} | Al_Sat: {p['al_saturation_pct']}% | Al_Hazard: {p['feat_soil_al_hazard']:.2f} | CESI: {p['feat_composite_edaphic_stress']:.2f}")
