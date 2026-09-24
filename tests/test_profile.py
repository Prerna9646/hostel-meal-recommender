"""
test_profile.py

Unit tests for UserProfile and anthropometric modeling (Phase 9).
Validates BMI calculations, ethnic Asian Indian cut-offs (Misra et al., 2009)
vs WHO international standards, profile integrity constraints, and dietary filtering.
"""

from pathlib import Path
import pandas as pd
import pytest
from src.recommender.profile import UserProfile


def test_default_profile():
    p = UserProfile()
    assert p.student_id == "STU_DEFAULT"
    assert p.age == 20
    assert p.sex == "MALE"
    assert p.height_cm == 170.0
    assert p.weight_kg == 65.0
    assert p.bmi == 22.49
    assert p.bmi_category_asian == "NORMAL"
    assert p.bmi_category_who == "NORMAL"
    assert p.dietary_preference == "VEGETARIAN"
    assert p.hostel_type == "COMMON"


def test_bmi_calculation():
    # 70 kg at 1.75 m = 70 / 3.0625 = 22.857... -> 22.86
    p = UserProfile(height_cm=175.0, weight_kg=70.0)
    assert p.bmi == 22.86
    assert p.height_m == 1.75


def test_asian_indian_cutoffs():
    # Underweight: < 18.5
    p_under = UserProfile(height_cm=170.0, weight_kg=50.0)  # BMI ~ 17.30
    assert p_under.bmi_category_asian == "UNDERWEIGHT"

    # Normal: 18.5 - 22.9
    p_norm = UserProfile(height_cm=170.0, weight_kg=60.0)  # BMI ~ 20.76
    assert p_norm.bmi_category_asian == "NORMAL"

    # Overweight: 23.0 - 24.9
    p_over = UserProfile(height_cm=170.0, weight_kg=68.0)  # BMI ~ 23.53
    assert p_over.bmi_category_asian == "OVERWEIGHT"

    # Obese: >= 25.0
    p_obese = UserProfile(height_cm=170.0, weight_kg=75.0)  # BMI ~ 25.95
    assert p_obese.bmi_category_asian == "OBESE"


def test_ethnic_disparity_asian_vs_who():
    """
    Key viva defense test: Demonstrates why Asian Indian cut-offs are clinically necessary.
    BMI 24.0 is OVERWEIGHT under Asian consensus (Misra 2009), but NORMAL under WHO standard.
    BMI 27.0 is OBESE under Asian consensus (Misra 2009), but OVERWEIGHT under WHO standard.
    """
    # BMI = 69.36 / (1.7^2) = 24.00
    p_border_over = UserProfile(height_cm=170.0, weight_kg=69.36)
    assert p_border_over.bmi == 24.00
    assert p_border_over.bmi_category_asian == "OVERWEIGHT"
    assert p_border_over.bmi_category_who == "NORMAL"

    # BMI = 78.03 / (1.7^2) = 27.00
    p_border_obese = UserProfile(height_cm=170.0, weight_kg=78.03)
    assert p_border_obese.bmi == 27.00
    assert p_border_obese.bmi_category_asian == "OBESE"
    assert p_border_obese.bmi_category_who == "OVERWEIGHT"


def test_healthy_weight_range():
    # Height 170 cm: 18.5 * 2.89 = 53.5 kg, 22.9 * 2.89 = 66.2 kg
    p = UserProfile(height_cm=170.0)
    min_w, max_w = p.healthy_weight_range_asian_kg
    assert min_w == 53.5
    assert max_w == 66.2


def test_dietary_filtering_logic():
    p_veg = UserProfile(dietary_preference="VEGETARIAN")
    assert p_veg.allows_dish_diet("VEGETARIAN") is True
    assert p_veg.allows_dish_diet("EGGETARIAN") is False
    assert p_veg.allows_dish_diet("NON_VEG") is False

    p_egg = UserProfile(dietary_preference="EGGETARIAN")
    assert p_egg.allows_dish_diet("VEGETARIAN") is True
    assert p_egg.allows_dish_diet("EGGETARIAN") is True
    assert p_egg.allows_dish_diet("NON_VEG") is False

    p_nv = UserProfile(dietary_preference="NON_VEG")
    assert p_nv.allows_dish_diet("VEGETARIAN") is True
    assert p_nv.allows_dish_diet("EGGETARIAN") is True
    assert p_nv.allows_dish_diet("NON_VEG") is True


def test_validation_constraints():
    with pytest.raises(ValueError, match="Age"):
        UserProfile(age=12)

    with pytest.raises(ValueError, match="Height"):
        UserProfile(height_cm=280.0)

    with pytest.raises(ValueError, match="Weight"):
        UserProfile(weight_kg=20.0)

    with pytest.raises(ValueError, match="Invalid sex"):
        UserProfile(sex="UNKNOWN")

    with pytest.raises(ValueError, match="Invalid diet"):
        UserProfile(dietary_preference="KETO")

    with pytest.raises(ValueError, match="GIRLS_HOSTEL"):
        UserProfile(sex="MALE", hostel_type="GIRLS_HOSTEL")

    with pytest.raises(ValueError, match="PCOS"):
        UserProfile(sex="MALE", health_conditions=["PCOS"])


def test_bmi_rules_csv_consistency():
    path = Path(__file__).resolve().parent.parent / "data" / "rules" / "bmi_rules.csv"
    assert path.exists(), f"Missing {path}"
    df = pd.read_csv(path)

    asian_df = df[df["standard"] == "ASIAN_INDIAN_MISRA2009"].set_index("category")
    assert asian_df.loc["UNDERWEIGHT", "max_bmi"] == 18.49
    assert asian_df.loc["NORMAL", "min_bmi"] == 18.5
    assert asian_df.loc["NORMAL", "max_bmi"] == 22.99
    assert asian_df.loc["OVERWEIGHT", "min_bmi"] == 23.0
    assert asian_df.loc["OVERWEIGHT", "max_bmi"] == 24.99
    assert asian_df.loc["OBESE", "min_bmi"] == 25.0
