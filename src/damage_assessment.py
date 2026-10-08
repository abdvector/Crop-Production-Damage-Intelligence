"""
Module: damage_assessment.py
Description: Crop Production & Damage Assessment Engine.
Translates multi-factor stress predictions into agronomic crop damage severity,
biomass loss diagnostics, and scientific determinant attribution.
"""

from typing import Dict, Any


class CropDamageAssessmentEngine:
    """
    Evaluates crop production decline, yield loss severity tiers,
    and biophysical damage diagnostics for agronomists, researchers, and regional planners.
    """

    def __init__(self):
        # Agronomic Damage Severity Thresholds (ICAR / FAO standard yield loss categories)
        self.thresh_mild = 10.0      # < 10% loss: Mild / Tolerable fluctuation
        self.thresh_moderate = 25.0  # 10% - 25% loss: Moderate stress / Economic threshold
        self.thresh_severe = 40.0    # 25% - 40% loss: Severe damage / Crop stress alert
        # > 40% loss: Catastrophic crop failure

    def assess_damage(self, explanation: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes comprehensive crop production and damage diagnostics report.
        """
        predicted_loss = explanation["predicted_loss_pct"]
        breakdown = explanation["determinants_breakdown"]

        al_stress = breakdown.get("Soil_Aluminium_Toxicity", 0.0)
        heat_stress = breakdown.get("Climatic_Heat_Shock", 0.0)
        drought_stress = breakdown.get("Drought_Moisture_Deficit", 0.0)
        molecular_mitigation = breakdown.get("Molecular_Protein_Mitigation", 0.0)

        # Categorize Damage Severity
        if predicted_loss < self.thresh_mild:
            severity = "Low / Normal Production"
            severity_color = "green"
            status_desc = "Crop is thriving within normal biological yield expectations."
        elif predicted_loss < self.thresh_moderate:
            severity = "Moderate Production Stress"
            severity_color = "orange"
            status_desc = "Noticeable biomass suppression detected; requires monitoring and soil conditioning."
        elif predicted_loss < self.thresh_severe:
            severity = "Severe Crop Damage"
            severity_color = "red"
            status_desc = "Significant yield loss across critical reproductive phases; major production deficit."
        else:
            severity = "Catastrophic Crop Failure"
            severity_color = "darkred"
            status_desc = "Overwhelming multi-factor stress has collapsed grain formation and biomass accumulation."

        # Identify Primary & Secondary Limiting Determinants
        stress_ranks = sorted([
            ("Soil Aluminium Toxicity (Al³⁺)", al_stress),
            ("Flowering Thermal Shock (>30°C)", heat_stress),
            ("Moisture Deficit & Drought", drought_stress)
        ], key=lambda x: x[1], reverse=True)

        primary_determinant, primary_val = stress_ranks[0]
        secondary_determinant, secondary_val = stress_ranks[1]

        # Calculate estimated production numbers
        district = metadata.get("district", "Unknown") if metadata else "Unknown"
        state = metadata.get("state", "Jharkhand") if metadata else "Jharkhand"
        base_pot = 3800.0 if state == "Punjab" else (3200.0 if state in ["Bihar", "UP"] else 2400.0)
        harvested_yield = base_pot * (1.0 - predicted_loss / 100.0)
        lost_biomass_kg = base_pot - harvested_yield

        # Scientific Agronomic Recommendation
        recommendations = []
        if al_stress > 5.0:
            recommendations.append("Apply agricultural lime (CaCO₃) to raise soil pH above 5.5 and precipitate toxic Al³⁺ ions.")
            recommendations.append("Select Al-tolerant wheat varieties exhibiting high ALMT1 malate transporter expression.")
        if heat_stress > 5.0:
            recommendations.append("Advance sowing date by 10–14 days to escape terminal March heatwaves during grain filling.")
            recommendations.append("Adopt heat-tolerant cultivars expressing elevated Heat Shock Protein (HSP70) chaperones.")
        if drought_stress > 5.0:
            recommendations.append("Implement light micro-irrigation at Crown Root Initiation (CRI) and anthesis stages.")

        if not recommendations:
            recommendations.append("Maintain current agronomic management practices.")

        return {
            "district": district,
            "season": metadata.get("season_year", "2024") if metadata else "2024",
            "variety": metadata.get("variety_key", "Wheat") if metadata else "Wheat",
            "base_potential_yield_kg_ha": base_pot,
            "predicted_loss_pct": predicted_loss,
            "harvested_yield_kg_ha": harvested_yield,
            "production_loss_kg_ha": lost_biomass_kg,
            "damage_severity": severity,
            "severity_color": severity_color,
            "status_description": status_desc,
            "primary_limiting_factor": f"{primary_determinant} (+{primary_val:.1f}%)",
            "secondary_limiting_factor": f"{secondary_determinant} (+{secondary_val:.1f}%)",
            "protein_defense_mitigation": f"{molecular_mitigation:.1f}% reduction in damage",
            "agronomic_recommendations": recommendations,
            "stress_contributions": {
                "Soil_Aluminium_Toxicity": al_stress,
                "Climatic_Heat_Shock": heat_stress,
                "Moisture_Deficit": drought_stress
            }
        }


if __name__ == "__main__":
    from src.explainability import ExplainabilityEngine
    import pandas as pd

    engine = CropDamageAssessmentEngine()
    xai = ExplainabilityEngine()
    df = pd.read_csv("data/processed/wheat_stress_multimodal_dataset.csv")

    ranchi_row = df[df["district"] == "Ranchi"].iloc[0].to_dict()
    expl = xai.explain_instance(ranchi_row)
    diag = engine.assess_damage(expl, ranchi_row)
    print("--- Crop Production & Damage Diagnostics ---")
    for k, v in diag.items():
        if k != "stress_contributions":
            print(f"{k:<32}: {v}")
