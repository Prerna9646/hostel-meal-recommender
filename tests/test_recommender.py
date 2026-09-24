"""
test_recommender.py

Unit tests for RecommendationEngine, plate grammar assembly, and multi-attribute scoring (Phase 12).
Validates end-to-end recommendation generation, dietary filtering, clinical exclusions,
insufficient data protection, and graceful fallback when candidate pools are depleted.
"""

from pathlib import Path
import pytest
from src.recommender.profile import UserProfile
from src.recommender.engine import RecommendationEngine, MealRecommendation
from src.recommender.plate_grammar import assemble_candidate_plates, AssemblyResult


@pytest.fixture(scope="module")
def engine():
    return RecommendationEngine()


def test_standard_recommendation_lunch(engine):
    profile = UserProfile(age=20, sex="MALE", height_cm=170.0, weight_kg=65.0, dietary_preference="VEGETARIAN")
    rec = engine.recommend_meal(profile, date_str="2026-10-01", slot_str="LUNCH")

    assert rec.status == "SUCCESS"
    assert rec.slot == "LUNCH"
    assert rec.date == "2026-10-01"
    assert len(rec.selected_dishes) >= 2  # At least Staple + Dal

    totals = rec.nutritional_totals
    assert totals["energy_kcal"] > 0
    assert totals["protein_g"] > 0
    assert totals["carbohydrate_g"] > 0

    assert rec.total_score > 0
    assert "energy_score" in rec.score_breakdown
    assert "protein_reward" in rec.score_breakdown


def test_plate_grammar_assembly_fallback():
    """Validates graceful fallback when candidates cannot satisfy required plate grammar roles."""
    # 1. Empty candidate pool
    res_empty = assemble_candidate_plates("LUNCH", [])
    assert res_empty.success is False
    assert res_empty.status_code == "NO_VALID_COMBINATION"
    assert "empty" in res_empty.diagnostic_message.lower()

    # 2. Missing required primary role (e.g., only Staples available, no DAL_PROTEIN)
    staple_only = [{"canonical_dish": "Plain Rice", "plate_role": "STAPLE"}]
    res_no_dal = assemble_candidate_plates("LUNCH", staple_only)
    assert res_no_dal.success is False
    assert res_no_dal.status_code == "NO_VALID_COMBINATION"
    assert "DAL_PROTEIN" in res_no_dal.diagnostic_message


def test_engine_graceful_fallback_on_impossible_constraints(engine):
    """
    Simulates a case where all dishes in a slot are excluded by hard constraints,
    verifying the engine returns NO_VALID_COMBINATION rather than crashing or returning an empty meal.
    """
    profile = UserProfile(
        age=20, sex="FEMALE", height_cm=160.0, weight_kg=55.0,
        dietary_preference="VEGETARIAN",
        health_conditions=["DIABETES", "HYPERTENSION"]
    )
    # Test on an artificially empty date
    rec = engine.recommend_meal(profile, date_str="2026-10-99", slot_str="LUNCH")
    assert rec.status == "NO_VALID_COMBINATION"
    assert rec.selected_dishes == []
    assert "Candidate pool is empty" in rec.diagnostic_message


def test_diabetic_dessert_exclusion(engine):
    profile_diab = UserProfile(
        age=20, sex="MALE", height_cm=170.0, weight_kg=65.0,
        dietary_preference="VEGETARIAN",
        health_conditions=["DIABETES"]
    )
    # On 2026-10-01 DINNER, Custard was served
    rec = engine.recommend_meal(profile_diab, date_str="2026-10-01", slot_str="DINNER")
    assert rec.status == "SUCCESS"
    assert "Custard" not in rec.selected_dishes
    assert "Custard" in rec.excluded_dishes
    assert any("HR_DIAB_001" in r for r in rec.excluded_dishes["Custard"])

    # On 2026-10-06 DINNER, Gulab Jamun was served
    rec_gj = engine.recommend_meal(profile_diab, date_str="2026-10-06", slot_str="DINNER")
    assert "Gulab Jamun" not in rec_gj.selected_dishes
    assert "Gulab Jamun" in rec_gj.excluded_dishes
    assert any("HR_DIAB_001" in r for r in rec_gj.excluded_dishes["Gulab Jamun"])


def test_hypertensive_pickle_exclusion(engine):
    profile_htn = UserProfile(
        age=20, sex="MALE", height_cm=170.0, weight_kg=65.0,
        dietary_preference="VEGETARIAN",
        health_conditions=["HYPERTENSION"]
    )
    rec = engine.recommend_meal(profile_htn, date_str="2026-10-01", slot_str="LUNCH")
    assert rec.status == "SUCCESS"
    assert "Pickle" not in rec.selected_dishes


def test_dietary_strict_filtering(engine):
    profile_veg = UserProfile(dietary_preference="VEGETARIAN")
    rec_veg = engine.recommend_meal(profile_veg, date_str="2026-10-01", slot_str="DINNER")
    for d in rec_veg.selected_dishes:
        role_tag = engine.class_df.loc[d]["dietary_tag"]
        assert role_tag == "VEGETARIAN"


def test_insufficient_data_exclusion(engine):
    """Verifies that commercial unmapped items with NaN nutrition are excluded from plate scoring."""
    profile = UserProfile()
    rec = engine.recommend_meal(profile, date_str="2026-10-01", slot_str="E_TEA")
    # Commercial snacks with INSUFFICIENT_DATA must not be on the plate
    for d in rec.selected_dishes:
        assert engine.nutr_df.loc[d]["calculation_status"] != "INSUFFICIENT_DATA"
