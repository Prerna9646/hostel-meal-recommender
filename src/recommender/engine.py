"""
engine.py

Core recommendation engine for Indian hostel dining.
Applies diet, clinical constraints, and data-coverage filters,
assembles plates via plate grammar, and scores candidates using transparent
multi-attribute optimization against ICMR-NIN 2020 targets.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.recommender.profile import UserProfile
from src.recommender.targets import compute_daily_targets, compute_slot_targets, SlotNutrientTargets
from src.recommender.health_rules import HealthRuleEngine
from src.recommender.plate_grammar import assemble_candidate_plates, AssemblyResult


@dataclass
class MealRecommendation:
    status: str  # "SUCCESS" or "NO_VALID_COMBINATION"
    slot: str
    date: str
    selected_dishes: List[str] = field(default_factory=list)
    nutritional_totals: Dict[str, float] = field(default_factory=dict)
    target_nutrients: Dict[str, float] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    excluded_dishes: Dict[str, List[str]] = field(default_factory=dict)
    diagnostic_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class RecommendationEngine:
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

        self.menu_df = pd.read_csv(data_dir / "mess_menu_final.csv")
        self.nutr_df = pd.read_csv(data_dir / "dish_nutrition_final.csv").set_index("dish")
        self.class_df = pd.read_csv(data_dir / "dish_classification_final.csv").set_index("canonical_dish")
        self.health_engine = HealthRuleEngine()

    def recommend_meal(self, profile: UserProfile, date_str: str, slot_str: str) -> MealRecommendation:
        norm_slot = slot_str.strip().upper()
        daily_targets = compute_daily_targets(profile)
        slot_targets = compute_slot_targets(daily_targets, norm_slot)

        # 1. Filter raw menu by date and slot
        day_menu = self.menu_df[
            (self.menu_df["normalized_date"] == date_str) &
            (self.menu_df["normalized_meal"] == norm_slot)
        ]
        # Filter by hostel facility scope
        if profile.hostel_type == "COMMON":
            day_menu = day_menu[day_menu["hostel_scope"] == "COMMON"]
        elif profile.hostel_type == "GIRLS_HOSTEL":
            day_menu = day_menu[day_menu["hostel_scope"].isin(["COMMON", "GIRLS_HOSTEL"])]

        candidates = sorted(list(day_menu["canonical_dish"].unique()))
        available_dishes = []
        excluded_dishes: Dict[str, List[str]] = {}

        for dish in candidates:
            # Completeness filter: exclude INSUFFICIENT_DATA (NaN nutrition)
            nutr = self.nutr_df.loc[dish]
            if nutr["calculation_status"] == "INSUFFICIENT_DATA":
                excluded_dishes[dish] = ["INSUFFICIENT_DATA: Commercial unmapped item cannot be scored"]
                continue

            # Dietary preference filter
            dish_class = self.class_df.loc[dish]
            diet_tag = dish_class["dietary_tag"]
            if not profile.allows_dish_diet(diet_tag):
                excluded_dishes[dish] = [f"DIET_FILTER: {diet_tag} dish violates {profile.dietary_preference} preference"]
                continue

            # Clinical hard constraint filter
            plate_role = dish_class["plate_role"]
            allowed, reasons = self.health_engine.evaluate_hard_constraints(dish, plate_role, profile.health_conditions)
            if not allowed:
                excluded_dishes[dish] = reasons
                continue

            # Candidate passed all filters
            dish_payload = nutr.to_dict()
            dish_payload["canonical_dish"] = dish
            dish_payload["plate_role"] = plate_role
            dish_payload["dietary_tag"] = diet_tag
            available_dishes.append(dish_payload)

        # 2. Assemble candidate plates
        assembly = assemble_candidate_plates(norm_slot, available_dishes)
        if not assembly.success:
            return MealRecommendation(
                status=assembly.status_code,
                slot=norm_slot,
                date=date_str,
                target_nutrients=slot_targets.to_dict(),
                excluded_dishes=excluded_dishes,
                diagnostic_message=assembly.diagnostic_message
            )

        # 3. Transparent Multi-Attribute Scoring
        best_plate = None
        best_score = -9999.0
        best_breakdown = {}
        best_totals = {}

        for plate in assembly.plates:
            # Compute nutritional sums
            e = sum(d["energy_kcal"] for d in plate)
            p = sum(d["protein_g"] for d in plate)
            fib = sum(d["fibre_g"] for d in plate)

            # Energy score: proximity to slot target energy (max 100)
            target_e = slot_targets.target_energy_kcal
            e_score = round(max(0.0, 100.0 * (1.0 - (abs(e - target_e) / target_e))), 2)

            # Protein reward: up to 50 points
            target_p = slot_targets.protein_g
            p_score = round(min(50.0, 50.0 * (p / max(1.0, target_p))), 2)

            # Fibre reward: up to 25 points
            target_fib = slot_targets.fibre_g
            fib_score = round(min(25.0, 25.0 * (fib / max(1.0, target_fib))), 2)

            # Health soft modifiers
            h_delta = 0.0
            for d in plate:
                delta, _ = self.health_engine.calculate_soft_adjustments(
                    d["canonical_dish"], d["plate_role"], profile.health_conditions
                )
                h_delta += delta
            h_delta = round(h_delta, 2)

            plate_total_score = round(e_score + p_score + fib_score + h_delta, 2)
            if plate_total_score > best_score:
                best_score = plate_total_score
                best_plate = plate
                best_breakdown = {
                    "energy_score": e_score,
                    "protein_reward": p_score,
                    "fibre_reward": fib_score,
                    "health_modifiers": h_delta
                }
                best_totals = {
                    "energy_kcal": round(e, 1),
                    "protein_g": round(p, 1),
                    "fat_g": round(sum(d["fat_g"] for d in plate), 1),
                    "carbohydrate_g": round(sum(d["carbohydrate_g"] for d in plate), 1),
                    "fibre_g": round(fib, 1),
                    "calcium_mg": round(sum(d["calcium_mg"] for d in plate), 1),
                    "iron_mg": round(sum(d["iron_mg"] for d in plate), 1),
                    "potassium_mg": round(sum(d["potassium_mg"] for d in plate), 1),
                    "sodium_mg": round(sum(d["sodium_mg"] for d in plate), 1)
                }

        selected_names = [d["canonical_dish"] for d in best_plate]
        return MealRecommendation(
            status="SUCCESS",
            slot=norm_slot,
            date=date_str,
            selected_dishes=selected_names,
            nutritional_totals=best_totals,
            target_nutrients=slot_targets.to_dict(),
            score_breakdown=best_breakdown,
            total_score=best_score,
            excluded_dishes=excluded_dishes,
            diagnostic_message=f"Optimal {norm_slot} plate assembled from {len(assembly.plates)} candidate combinations."
        )
