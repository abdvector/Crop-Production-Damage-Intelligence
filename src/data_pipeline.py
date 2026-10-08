"""
Module: data_pipeline.py
Description: Multi-Modal Data Ingestion & Feature Fusion Pipeline.
Fuses biological protein embeddings (ESM-2), edaphic soil chemistry (SoilGrids),
and phenology-aligned climate time-series (NASA POWER) into a unified dataset.
"""

import os
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict

from src.bio_embeddings import BioEmbeddingExtractor, WHEAT_PROTEIN_SEQUENCES
from src.edaphic_features import EdaphicFeatureEngine, DISTRICT_SOIL_PROFILES
from src.weather_phenology import WeatherPhenologyEngine


class MultiModalDataPipeline:
    """
    Constructs the end-to-end multi-modal training and evaluation dataset
    across districts, growing seasons, and wheat variety genotypes.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

        self.bio_extractor = BioEmbeddingExtractor()
        self.edaphic_engine = EdaphicFeatureEngine()
        self.weather_engine = WeatherPhenologyEngine()

    def build_dataset(self, years: List[int] = None) -> pd.DataFrame:
        """
        Builds multi-modal dataset across all districts, years, and varieties.
        """
        if years is None:
            years = list(range(2008, 2024))  # 16 seasons

        districts = self.edaphic_engine.get_all_districts()
        varieties = list(WHEAT_PROTEIN_SEQUENCES.keys())

        records = []
        print(f"[MultiModalDataPipeline] Synthesizing multi-modal dataset across {len(districts)} districts, {len(years)} seasons, {len(varieties)} varieties...")

        for district_name in districts:
            soil_prof = self.edaphic_engine.get_district_profile(district_name)
            lat = soil_prof["latitude"]
            state = soil_prof["state"]

            for year in years:
                # 1. Weather extraction for season
                weather_df = self.weather_engine.simulate_rabi_season_weather(lat, state, year)
                weather_feats = self.weather_engine.extract_phenological_features(weather_df)

                for var_name in varieties:
                    bio_prof = self.bio_extractor.get_variety_resilience_profile(var_name)
                    bio_resilience = bio_prof["baseline_resilience"]

                    # 2. Compute Biologically Grounded Yield Loss Target
                    # Interaction physics:
                    # - Al toxicity causes severe root damage UNLESS crop has high ALMT1 resilience
                    al_hazard = soil_prof["feat_soil_al_hazard"]
                    effective_al_stress = max(0.0, al_hazard * (1.15 - bio_resilience))

                    # - Flowering heat shock (> 30°C) causes loss UNLESS crop has high HSP resilience
                    edd30 = weather_feats["feat_EDD30_Flowering"]
                    effective_heat_stress = min(0.40, (edd30 / 120.0) * (1.10 - (0.5 * bio_resilience)))

                    # - Terminal heat in grain filling
                    term_heat = weather_feats["feat_TerminalHeatDays_P4"]
                    terminal_loss = min(0.25, (term_heat / 25.0) * 0.20)

                    # - Drought interaction (CDD in shallow acidic soils)
                    cdd = weather_feats["feat_ConsecutiveDryDays_Reproductive"]
                    compound_drought_acidity = (cdd / 40.0) * (1.0 + 0.8 * al_hazard)
                    drought_loss = min(0.25, compound_drought_acidity * 0.18)

                    # Total Yield Deviation from Normal (% loss)
                    # Baseline district yield potential
                    base_yield_potential = 3800.0 if state == "Punjab" else (3200.0 if state in ["Bihar", "UP"] else 2400.0)
                    total_stress_fraction = min(0.85, (0.35 * effective_al_stress +
                                                      0.35 * effective_heat_stress +
                                                      0.15 * terminal_loss +
                                                      0.15 * drought_loss))

                    # Add realistic empirical field noise (measurement error, microclimate)
                    noise = np.random.normal(0.0, 0.03)
                    yield_loss_pct = float(np.clip((total_stress_fraction + noise) * 100.0, 0.0, 85.0))
                    actual_yield = base_yield_potential * (1.0 - yield_loss_pct / 100.0)

                    # Categorical Insurance Damage Class:
                    # 0: Low / Normal (< 15% loss)
                    # 1: Moderate Damage (15% - 30% loss)
                    # 2: Severe Failure (>= 30% loss)
                    if yield_loss_pct < 15.0:
                        damage_class = 0
                        claim_recommendation = "No Payout"
                    elif yield_loss_pct < 30.0:
                        damage_class = 1
                        claim_recommendation = "Partial Claim (50%)"
                    else:
                        damage_class = 2
                        claim_recommendation = "Full Claim (100%)"

                    # Assembling Row
                    row = {
                        "district": district_name,
                        "state": state,
                        "season_year": year,
                        "variety_key": var_name,
                        "variety_type": bio_prof["tolerance_type"],
                        "target_yield_loss_pct": yield_loss_pct,
                        "target_actual_yield_kg_ha": actual_yield,
                        "target_damage_class": damage_class,
                        "target_claim_recommendation": claim_recommendation,
                        
                        # Molecular feature
                        "feat_bio_resilience_score": bio_resilience,
                        
                        # Edaphic features
                        **{k: v for k, v in soil_prof.items() if k.startswith("feat_")},
                        
                        # Weather features
                        **weather_feats,
                        
                        # Novel compound feature: Compound Drought-Acidity Index (CDAI)
                        "feat_CDAI_compound": float(compound_drought_acidity)
                    }

                    # Add first 16 principal components of ESM-2 embedding for tabular modeling
                    emb = bio_prof["embedding_vector"]
                    for idx in range(16):
                        row[f"feat_esm2_dim_{idx:02d}"] = float(emb[idx])

                    records.append(row)

        df = pd.DataFrame(records)
        out_csv = os.path.join(self.processed_dir, "wheat_stress_multimodal_dataset.csv")
        df.to_csv(out_csv, index=False)
        print(f"[MultiModalDataPipeline] Successfully generated {len(df)} multi-modal rows with {len(df.columns)} columns!")
        print(f"[MultiModalDataPipeline] Saved to: {out_csv}")
        return df


if __name__ == "__main__":
    pipeline = MultiModalDataPipeline()
    df_data = pipeline.build_dataset()
    print("Dataset Summary:")
    print(df_data[["district", "season_year", "variety_key", "feat_soil_al_hazard", "feat_EDD30_Flowering", "target_yield_loss_pct", "target_claim_recommendation"]].head())
