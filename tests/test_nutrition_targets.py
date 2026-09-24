"""
test_nutrition_targets.py

Unit tests for personalized nutrition target derivation (Phase 10).
Validates Mifflin-St Jeor BMR, profile-adjustable Physical Activity Levels (PAL),
ICMR-NIN (2020) RDA macronutrient and mineral targets, sex-differentiated iron,
and diurnal meal-slot distributions (Breakfast 25%, Lunch 35%, E-Tea 10%, Dinner 30%).
"""

from pathlib import Path
import pandas as pd
import pytest
from src.recommender.profile import UserProfile
from src.recommender.targets import (
    compute_bmr,
    compute_daily_targets,
    compute_slot_targets,
    PAL_FACTORS,
    SLOT_ENERGY_FRACTIONS
)


def test_bmr_calculation():
    # Male: 20y, 170cm, 65kg -> 10(65) + 6.25(170) - 5(20) + 5 = 650 + 1062.5 - 100 + 5 = 1617.5
    p_male = UserProfile(age=20, sex="MALE", height_cm=170.0, weight_kg=65.0)
    assert compute_bmr(p_male) == 1617.5

    # Female: 20y, 160cm, 55kg -> 10(55) + 6.25(160) - 5(20) - 161 = 550 + 1000 - 100 - 161 = 1289.0
    p_female = UserProfile(age=20, sex="FEMALE", height_cm=160.0, weight_kg=55.0)
    assert compute_bmr(p_female) == 1289.0


def test_profile_adjustable_pal_factors():
    """Validates that PAL scales dynamically with user's activity level (crucial for Athlete persona)."""
    p_sed = UserProfile(activity_level="SEDENTARY")
    t_sed = compute_daily_targets(p_sed)
    assert t_sed.pal == 1.40
    assert t_sed.tdee_kcal == round(t_sed.bmr_kcal * 1.40, 2)

    p_athlete = UserProfile(activity_level="HEAVY")
    t_athlete = compute_daily_targets(p_athlete)
    assert t_athlete.pal == 2.20
    assert t_athlete.tdee_kcal == round(t_athlete.bmr_kcal * 2.20, 2)
    assert t_athlete.tdee_kcal > t_sed.tdee_kcal * 1.5


def test_weight_goal_energy_adjustments():
    # Normal weight: maintenance = TDEE
    p_norm = UserProfile(height_cm=170.0, weight_kg=60.0)  # BMI ~ 20.76 (NORMAL)
    t_norm = compute_daily_targets(p_norm)
    assert t_norm.target_energy_kcal == t_norm.tdee_kcal

    # Underweight: +400 kcal surplus
    p_under = UserProfile(height_cm=170.0, weight_kg=50.0)  # BMI ~ 17.30 (UNDERWEIGHT)
    t_under = compute_daily_targets(p_under)
    assert t_under.target_energy_kcal == round(t_under.tdee_kcal + 400.0, 2)

    # Overweight: -400 kcal deficit
    p_over = UserProfile(height_cm=170.0, weight_kg=70.0)  # BMI ~ 24.22 (OVERWEIGHT)
    t_over = compute_daily_targets(p_over)
    assert t_over.target_energy_kcal == round(t_over.tdee_kcal - 400.0, 2)


def test_sex_differentiated_iron_target():
    """ICMR-NIN 2020 specifies 19mg for adult males vs 29mg for adult reproductive females."""
    p_male = UserProfile(sex="MALE")
    p_female = UserProfile(sex="FEMALE")
    t_male = compute_daily_targets(p_male)
    t_female = compute_daily_targets(p_female)

    assert t_male.iron_mg == 19.0
    assert t_female.iron_mg == 29.0


def test_macronutrient_and_mineral_rdas():
    p = UserProfile(weight_kg=65.0, activity_level="SEDENTARY")
    t = compute_daily_targets(p)

    # Sedentary protein: 65 * 0.83 = 53.95 g
    assert t.protein_g == 53.95
    # Fat: 25% of calories
    expected_fat = round((t.target_energy_kcal * 0.25) / 9.0, 2)
    assert t.fat_g == expected_fat
    # Minerals
    assert t.calcium_mg == 1000.0
    assert t.potassium_mg == 3500.0
    assert t.sodium_max_mg == 2000.0


def test_slot_target_allocations_sum_to_daily():
    """Verifies that Breakfast(25%) + Lunch(35%) + E-Tea(10%) + Dinner(30%) sums to 100%."""
    assert sum(SLOT_ENERGY_FRACTIONS.values()) == pytest.approx(1.0, abs=1e-5)

    p = UserProfile()
    daily = compute_daily_targets(p)

    slots = ["BREAKFAST", "LUNCH", "E_TEA", "DINNER"]
    slot_targets = [compute_slot_targets(daily, s) for s in slots]

    total_slot_energy = sum(st.target_energy_kcal for st in slot_targets)
    total_slot_protein = sum(st.protein_g for st in slot_targets)
    total_slot_calcium = sum(st.calcium_mg for st in slot_targets)

    assert total_slot_energy == pytest.approx(daily.target_energy_kcal, abs=0.1)
    assert total_slot_protein == pytest.approx(daily.protein_g, abs=0.1)
    assert total_slot_calcium == pytest.approx(daily.calcium_mg, abs=0.1)


def test_rda_rules_csv_consistency():
    path = Path(__file__).resolve().parent.parent / "data" / "rules" / "rda_targets.csv"
    assert path.exists(), f"Missing {path}"
    df = pd.read_csv(path)

    assert len(df) == 6  # 2 sexes x 3 activity levels
    male_sed = df[(df["sex"] == "MALE") & (df["activity_level"] == "SEDENTARY")].iloc[0]
    assert male_sed["reference_weight_kg"] == 65.0
    assert male_sed["pal"] == 1.40
    assert male_sed["energy_kcal"] == 2110.0
    assert male_sed["protein_g"] == 54.0

    fem_sed = df[(df["sex"] == "FEMALE") & (df["activity_level"] == "SEDENTARY")].iloc[0]
    assert fem_sed["reference_weight_kg"] == 55.0
    assert fem_sed["iron_mg"] == 29.0
