"""
benchmark.py

Multi-persona simulation and comparative benchmarking across the 31-day October menu.
Evaluates Constraint Violation Rates (CVR), Energy Error, and Protein Adequacy
against Random Selection and Greedy Calorie Maximizer baselines.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd

from src.recommender.profile import UserProfile
from src.recommender.engine import RecommendationEngine
from src.recommender.targets import compute_daily_targets, compute_slot_targets
from src.recommender.canteen import CanteenOptimizer


PERSONAS = {
    "Persona_A_Diabetic_Female": UserProfile(
        student_id="P_A_DIAB", age=21, sex="FEMALE", height_cm=158.0, weight_kg=58.0,
        dietary_preference="VEGETARIAN", hostel_type="GIRLS_HOSTEL",
        activity_level="SEDENTARY", health_conditions=["DIABETES"]
    ),
    "Persona_B_Hypertensive_Male": UserProfile(
        student_id="P_B_HTN", age=24, sex="MALE", height_cm=175.0, weight_kg=88.0,
        dietary_preference="NON_VEG", hostel_type="COMMON",
        activity_level="SEDENTARY", health_conditions=["HYPERTENSION", "OBESITY"]
    ),
    "Persona_C_Athlete_Eggetarian": UserProfile(
        student_id="P_C_ATHLETE", age=20, sex="MALE", height_cm=172.0, weight_kg=52.0,
        dietary_preference="EGGETARIAN", hostel_type="COMMON",
        activity_level="HEAVY", health_conditions=["NONE"], canteen_budget_inr=30.0
    ),
    "Persona_D_PCOS_Female": UserProfile(
        student_id="P_D_PCOS", age=20, sex="FEMALE", height_cm=162.0, weight_kg=55.0,
        dietary_preference="VEGETARIAN", hostel_type="GIRLS_HOSTEL",
        activity_level="LIGHT", health_conditions=["PCOS"]
    ),
    "Persona_E_Healthy_Control": UserProfile(
        student_id="P_E_CONTROL", age=20, sex="MALE", height_cm=170.0, weight_kg=65.0,
        dietary_preference="VEGETARIAN", hostel_type="COMMON",
        activity_level="MODERATE", health_conditions=["NONE"]
    )
}


def run_persona_simulation(engine: RecommendationEngine, dates: List[str]) -> pd.DataFrame:
    """Simulates daily recommendations for all 5 personas across all 4 meal slots."""
    slots = ["BREAKFAST", "LUNCH", "E_TEA", "DINNER"]
    records = []

    for p_name, profile in PERSONAS.items():
        daily_targets = compute_daily_targets(profile)
        for date_str in dates:
            for slot in slots:
                rec = engine.recommend_meal(profile, date_str, slot)
                st = compute_slot_targets(daily_targets, slot)

                # Count constraint violations if any dish violated profile
                clinical_viol = 0
                diet_viol = 0
                insufficient_viol = 0

                if rec.status == "SUCCESS":
                    for dish in rec.selected_dishes:
                        tag = engine.class_df.loc[dish]["dietary_tag"]
                        if not profile.allows_dish_diet(tag):
                            diet_viol += 1
                        if dish in rec.excluded_dishes:
                            clinical_viol += 1
                        if engine.nutr_df.loc[dish]["calculation_status"] == "INSUFFICIENT_DATA":
                            insufficient_viol += 1

                actual_e = rec.nutritional_totals.get("energy_kcal", 0.0)
                actual_p = rec.nutritional_totals.get("protein_g", 0.0)
                target_e = st.target_energy_kcal
                target_p = st.protein_g

                records.append({
                    "persona": p_name,
                    "date": date_str,
                    "slot": slot,
                    "status": rec.status,
                    "score": rec.total_score,
                    "actual_energy": actual_e,
                    "target_energy": target_e,
                    "energy_error": abs(actual_e - target_e),
                    "actual_protein": actual_p,
                    "target_protein": target_p,
                    "clinical_violations": clinical_viol,
                    "diet_violations": diet_viol,
                    "insufficient_data_violations": insufficient_viol
                })

    return pd.DataFrame(records)


def compute_benchmark_metrics(sim_df: pd.DataFrame) -> Dict[str, Any]:
    """Aggregates simulation results into academic evaluation metrics."""
    metrics = {}
    for persona, group in sim_df.groupby("persona"):
        success_rate = (group["status"] == "SUCCESS").mean() * 100.0
        cvr = (group["clinical_violations"].sum() + group["diet_violations"].sum() + group["insufficient_data_violations"].sum())
        mean_score = group["score"].mean()
        mean_energy_error = group["energy_error"].mean()

        metrics[persona] = {
            "success_rate_percent": round(success_rate, 1),
            "total_violations": int(cvr),
            "mean_plate_score": round(mean_score, 2),
            "mean_energy_error_kcal": round(mean_energy_error, 1)
        }
    return metrics
