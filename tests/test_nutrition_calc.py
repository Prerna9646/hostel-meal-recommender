"""
test_nutrition_calc.py

Unit, golden-dish regression, and coverage tests for dish_nutrition_final.csv
and dish_nutrition_coverage.csv.
Validates raw ingredient aggregation, mathematical fidelity against golden benchmarks,
and rigorous propagation of INSUFFICIENT_DATA (NaN) for commercial unmapped items.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pytest


@pytest.fixture(scope="module")
def root_dir():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def dish_nutrition_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "dish_nutrition_final.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def dish_coverage_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "dish_nutrition_coverage.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


def test_coverage_dimensions_and_keys(dish_nutrition_df, dish_coverage_df):
    """Asserts exactly 132 dishes are evaluated in both tables."""
    assert len(dish_nutrition_df) == 132
    assert len(dish_coverage_df) == 132
    assert dish_nutrition_df["dish"].nunique() == 132
    assert (dish_nutrition_df["dish"] == dish_coverage_df["dish"]).all()


def test_insufficient_data_propagation_for_commercial_foods(dish_nutrition_df, dish_coverage_df):
    """Asserts all 17 commercial unmapped items roll up to INSUFFICIENT_DATA with NaN nutrients."""
    insufficient_cov = dish_coverage_df[dish_coverage_df["calculation_status"] == "INSUFFICIENT_DATA"]
    insufficient_nut = dish_nutrition_df[dish_nutrition_df["calculation_status"] == "INSUFFICIENT_DATA"]

    assert len(insufficient_cov) == 17
    assert len(insufficient_nut) == 17

    expected_commercial = {
        "Biscuit", "Brownie", "Chips", "Chocolate", "Chocolate Pie",
        "Cornflakes", "Cream Roll", "Fat Spread", "Fryums", "Jam",
        "Muffin", "Namkeen", "Pickle", "Pink Sauce Pasta", "Rusk",
        "Tea Cake", "Tomato Ketchup"
    }
    assert set(insufficient_cov["dish"]) == expected_commercial

    for _, row in insufficient_nut.iterrows():
        assert np.isnan(row["energy_kcal"]), f"Expected NaN energy for {row['dish']}"
        assert np.isnan(row["protein_g"]), f"Expected NaN protein for {row['dish']}"
        assert row["data_coverage_percent"] == 0.0


def test_golden_dish_chapati(dish_nutrition_df):
    """Golden regression benchmark for Chapati (30g raw atta)."""
    chapati = dish_nutrition_df[dish_nutrition_df["dish"] == "Chapati"].iloc[0]
    assert 95.0 <= chapati["energy_kcal"] <= 97.0
    assert 3.1 <= chapati["protein_g"] <= 3.3
    assert 0.4 <= chapati["fat_g"] <= 0.6
    assert 19.0 <= chapati["carbohydrate_g"] <= 19.5
    assert chapati["calculation_status"] == "COMPLETE_IFCT"


def test_golden_dish_plain_rice(dish_nutrition_df):
    """Golden regression benchmark for Plain Rice (50g raw parboiled rice)."""
    rice = dish_nutrition_df[dish_nutrition_df["dish"] == "Plain Rice"].iloc[0]
    assert 174.0 <= rice["energy_kcal"] <= 178.0
    assert 3.8 <= rice["protein_g"] <= 4.0
    assert 38.0 <= rice["carbohydrate_g"] <= 39.0
    assert rice["calculation_status"] == "COMPLETE_IFCT"


def test_golden_dish_boiled_egg(dish_nutrition_df):
    """Golden regression benchmark for Boiled Egg (50g whole egg)."""
    egg = dish_nutrition_df[dish_nutrition_df["dish"] == "Boiled Egg"].iloc[0]
    assert 72.0 <= egg["energy_kcal"] <= 75.0
    assert 6.5 <= egg["protein_g"] <= 7.0
    assert 5.0 <= egg["fat_g"] <= 5.5
    assert egg["carbohydrate_g"] == 0.0
    assert egg["calculation_status"] == "COMPLETE_IFCT"


def test_golden_dish_yellow_dal_tadka(dish_nutrition_df):
    """Golden regression benchmark for Yellow Dal Tadka (30g toor dal + aromatics + 5g ghee)."""
    dal = dish_nutrition_df[dish_nutrition_df["dish"] == "Yellow Dal Tadka"].iloc[0]
    assert 135.0 <= dal["energy_kcal"] <= 145.0
    assert 6.3 <= dal["protein_g"] <= 7.0
    assert 5.3 <= dal["fat_g"] <= 6.0
    assert dal["calculation_status"] == "COMPLETE_IFCT"


def test_golden_dish_matar_paneer(dish_nutrition_df):
    """Golden regression benchmark for Matar Paneer (40g paneer + 30g peas + 5g oil)."""
    dish = dish_nutrition_df[dish_nutrition_df["dish"] == "Matar Paneer"].iloc[0]
    assert 180.0 <= dish["energy_kcal"] <= 190.0
    assert 9.8 <= dish["protein_g"] <= 10.5
    assert 10.5 <= dish["fat_g"] <= 11.5
    assert dish["calculation_status"] == "COMPLETE_IFCT"


def test_golden_dish_plain_curd(dish_nutrition_df):
    """Golden regression benchmark for Plain Curd (100g curd = whole cow milk model)."""
    curd = dish_nutrition_df[dish_nutrition_df["dish"] == "Plain Curd"].iloc[0]
    assert 71.0 <= curd["energy_kcal"] <= 74.0
    assert 3.1 <= curd["protein_g"] <= 3.4
    assert 115.0 <= curd["calcium_mg"] <= 120.0
    assert curd["calculation_status"] == "ASSUMPTION_INCLUDED"


def test_non_negativity_across_all_calculated_dishes(dish_nutrition_df):
    """Asserts all non-null nutrients are >= 0.0."""
    nutrient_cols = [
        "energy_kcal", "protein_g", "fat_g", "carbohydrate_g",
        "fibre_g", "potassium_mg", "sodium_mg", "calcium_mg", "iron_mg"
    ]
    for col in nutrient_cols:
        valid_vals = dish_nutrition_df[col].dropna()
        assert (valid_vals >= 0.0).all(), f"Found negative values in {col}"
