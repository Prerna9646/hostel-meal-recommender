"""
explainability.py

Faithful Explainability & Why-Not Diagnostic Engine for meal recommendations.
Translates mathematical multi-attribute scores and constraint pruning into
verifiable human-readable justifications, counterfactual comparisons, and exclusion audits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.recommender.profile import UserProfile
from src.recommender.engine import MealRecommendation


@dataclass
class MealExplanation:
    status: str
    headline: str
    selected_dishes: List[str]
    score_explanation: Dict[str, Any]
    nutritional_audit: Dict[str, Any]
    clinical_justifications: List[str]
    why_not_audit: Dict[str, str]
    fallback_guidance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class ExplainabilityEngine:
    def explain_recommendation(
        self,
        rec: MealRecommendation,
        profile: UserProfile
    ) -> MealExplanation:
        """
        Generates a faithful, mathematically verifiable explanation of the recommendation.
        Matches exact computed sub-scores (capped rewards, penalties) without approximation.
        """
        # 1. Fallback State Handling
        if rec.status != "SUCCESS":
            return MealExplanation(
                status=rec.status,
                headline=f"No compliant meal combination available for {rec.slot} on {rec.date}.",
                selected_dishes=[],
                score_explanation={"total_score": 0.0, "reason": "No valid combination formed"},
                nutritional_audit={},
                clinical_justifications=[],
                why_not_audit={dish: " ".join(reasons) for dish, reasons in rec.excluded_dishes.items()},
                fallback_guidance=(
                    f"{rec.diagnostic_message} Recommended Action: Request kitchen protein substitution "
                    f"or utilize compliant canteen extras (boiled eggs, curd, or fresh fruit)."
                )
            )

        # 2. Faithful Score Explanation (verbatim from engine)
        sb = rec.score_breakdown
        totals = rec.nutritional_totals
        targets = rec.target_nutrients

        target_e = targets.get("target_energy_kcal", 1.0)
        target_p = targets.get("protein_g", 1.0)
        target_fib = targets.get("fibre_g", 1.0)

        actual_e = totals.get("energy_kcal", 0.0)
        actual_p = totals.get("protein_g", 0.0)
        actual_fib = totals.get("fibre_g", 0.0)

        score_details = {
            "total_score": rec.total_score,
            "components": {
                "energy_proximity_score": {
                    "score": sb.get("energy_score", 0.0),
                    "max_possible": 100.0,
                    "target_kcal": target_e,
                    "actual_kcal": actual_e,
                    "percent_met": round((actual_e / target_e) * 100.0, 1)
                },
                "protein_reward": {
                    "score": sb.get("protein_reward", 0.0),
                    "max_possible": 50.0,
                    "target_g": target_p,
                    "actual_g": actual_p,
                    "percent_met": round((actual_p / target_p) * 100.0, 1)
                },
                "fibre_reward": {
                    "score": sb.get("fibre_reward", 0.0),
                    "max_possible": 25.0,
                    "target_g": target_fib,
                    "actual_g": actual_fib,
                    "percent_met": round((actual_fib / target_fib) * 100.0, 1)
                },
                "clinical_health_modifiers": {
                    "score": sb.get("health_modifiers", 0.0),
                    "active_conditions": profile.health_conditions
                }
            }
        }

        # 3. Why-Not Audit (Exclusions + Non-selected dishes)
        why_not: Dict[str, str] = {}
        for dish, reasons in rec.excluded_dishes.items():
            why_not[dish] = f"EXCLUDED: {' | '.join(reasons)}"

        # 4. Clinical Justifications
        clinical_notes = []
        if "DIABETES" in profile.health_conditions:
            clinical_notes.append("ICMR (2018) MNT applied: Concentrated sucrose desserts excluded; raw fibre promoted.")
        if "HYPERTENSION" in profile.health_conditions:
            clinical_notes.append("IHG-IV (2019) / WHO applied: High-salt preserved pickles eliminated; potassium promoted.")
        if "PCOS" in profile.health_conditions:
            clinical_notes.append("PCOS Guidelines (2023) applied: Simple sugars restricted; ungrounded dairy ban refuted.")
        if "OBESITY" in profile.health_conditions or profile.bmi_category_asian in {"OVERWEIGHT", "OBESE"}:
            clinical_notes.append("Misra et al. (2009) Asian Indian criteria applied: -400 kcal deficit target enforced.")

        headline = f"Optimal {rec.slot} Plate: {', '.join(rec.selected_dishes)} (Score: {rec.total_score})"

        return MealExplanation(
            status="SUCCESS",
            headline=headline,
            selected_dishes=rec.selected_dishes,
            score_explanation=score_details,
            nutritional_audit={
                "actual_totals": totals,
                "target_targets": targets
            },
            clinical_justifications=clinical_notes,
            why_not_audit=why_not
        )
