"""
canteen.py

Canteen Extras & Budget Optimization Layer.
Evaluates nutritional gaps on the mess plate against slot targets,
filters candidate extras by diet, clinical constraints, and budget,
and greedily optimizes knapsack utility using strictly verified IFCT items (no NaN data).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.recommender.profile import UserProfile
from src.recommender.targets import SlotNutrientTargets
from src.recommender.health_rules import HealthRuleEngine
from src.recommender.engine import MealRecommendation


@dataclass
class CanteenRecommendation:
    status: str
    selected_extras: List[Dict[str, Any]] = field(default_factory=list)
    total_cost_inr: float = 0.0
    remaining_budget_inr: float = 0.0
    combined_totals: Dict[str, float] = field(default_factory=dict)
    gap_closure_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class CanteenOptimizer:
    def __init__(self, extras_csv_path: Path = None):
        if extras_csv_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            extras_csv_path = root / "data" / "rules" / "canteen_extras.csv"

        self.df = pd.read_csv(extras_csv_path)
        # Enforce research integrity: strictly filter out any item with NaN nutrition
        self.verified_extras = self.df[
            self.df["energy_kcal"].notna() &
            self.df["protein_g"].notna() &
            (self.df["calculation_status"] != "INSUFFICIENT_DATA")
        ].copy()
        self.health_engine = HealthRuleEngine()

    def optimize_extras(
        self,
        rec: MealRecommendation,
        profile: UserProfile,
        slot_targets: SlotNutrientTargets
    ) -> CanteenRecommendation:
        budget = float(profile.canteen_budget_inr)
        if budget <= 0.0:
            return CanteenRecommendation(
                status="NO_BUDGET",
                remaining_budget_inr=0.0,
                combined_totals=rec.nutritional_totals
            )

        plate_totals = rec.nutritional_totals
        gap_p = max(0.0, slot_targets.protein_g - plate_totals.get("protein_g", 0.0))
        gap_e = max(0.0, slot_targets.target_energy_kcal - plate_totals.get("energy_kcal", 0.0))
        gap_fib = max(0.0, slot_targets.fibre_g - plate_totals.get("fibre_g", 0.0))

        # Filter candidate extras
        eligible = []
        for _, row in self.verified_extras.iterrows():
            price = float(row["price_inr"])
            if price > budget:
                continue
            if not profile.allows_dish_diet(row["dietary_tag"]):
                continue

            allowed, _ = self.health_engine.evaluate_hard_constraints(
                row["dish"], row["plate_role"], profile.health_conditions
            )
            if not allowed:
                continue

            # Calculate gap-closure utility
            p_val = min(gap_p, float(row["protein_g"]))
            e_val = min(gap_e, float(row["energy_kcal"]))
            fib_val = min(gap_fib, float(row["fibre_g"]))

            # Utility weights: protein prioritization (5.0), fibre (3.0), energy (0.05)
            util = (p_val * 5.0) + (fib_val * 3.0) + (e_val * 0.05)

            # Soft clinical modifier bonus
            delta, _ = self.health_engine.calculate_soft_adjustments(
                row["dish"], row["plate_role"], profile.health_conditions
            )
            util += max(0.0, delta)

            efficiency = util / max(1.0, price)
            eligible.append((efficiency, row.to_dict()))

        eligible.sort(key=lambda x: x[0], reverse=True)

        selected = []
        current_budget = budget
        notes = []
        combined = dict(plate_totals)

        for _, item in eligible:
            cost = float(item["price_inr"])
            if cost <= current_budget and len(selected) < 2:  # max 2 extras per slot
                selected.append(item)
                current_budget -= cost
                notes.append(
                    f"Selected {item['dish']} (₹{cost:.0f}): +{item['protein_g']:.1f}g protein, "
                    f"+{item['energy_kcal']:.0f} kcal, +{item['fibre_g']:.1f}g fibre"
                )
                for nutrient in ["energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "fibre_g", "calcium_mg", "iron_mg", "potassium_mg", "sodium_mg"]:
                    combined[nutrient] = round(combined.get(nutrient, 0.0) + float(item.get(nutrient, 0.0)), 1)

        status = "SUCCESS" if selected else "NO_COMPLIANT_EXTRA"
        return CanteenRecommendation(
            status=status,
            selected_extras=selected,
            total_cost_inr=round(budget - current_budget, 1),
            remaining_budget_inr=round(current_budget, 1),
            combined_totals=combined,
            gap_closure_notes=notes
        )
