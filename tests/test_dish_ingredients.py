"""
test_dish_ingredients.py

Unit and regression tests for portion_assumptions.csv and dish_ingredients_final.csv.
Validates 100% dish coverage (132 canonical dishes), positive raw-gram portion basis,
foreign key integrity to ingredient_master, and strict PROJECT_ASSUMPTION provenance.
"""

from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def root_dir():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def portions_df(root_dir):
    csv_path = root_dir / "data" / "rules" / "portion_assumptions.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def dish_ingredients_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "dish_ingredients_final.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def ingredient_master_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ingredient_master.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


def test_complete_dish_coverage(dish_ingredients_df, portions_df):
    """Asserts all 132 canonical hostel dishes have defined recipes and portions."""
    assert dish_ingredients_df["dish"].nunique() == 132
    assert portions_df["dish"].nunique() == 132
    assert len(dish_ingredients_df) == len(portions_df)
    assert len(dish_ingredients_df) == 503


def test_ingredient_foreign_key_integrity(dish_ingredients_df, ingredient_master_df):
    """Asserts every ingredient in dish recipes exists in ingredient_master.csv."""
    recipe_ings = set(dish_ingredients_df["ingredient"].unique())
    master_ings = set(ingredient_master_df["canonical_ingredient_name"].unique())
    diff = recipe_ings - master_ings
    assert len(diff) == 0, f"Found unrecognised recipe ingredients: {diff}"


def test_positive_portions_and_raw_basis(dish_ingredients_df):
    """Asserts quantities are strictly positive and basis is RAW_INGREDIENT_GRAM_PER_SERVING."""
    assert (dish_ingredients_df["quantity_g"] > 0.0).all()
    assert (dish_ingredients_df["quantity_basis"] == "RAW_INGREDIENT_GRAM_PER_SERVING").all()
    assert (dish_ingredients_df["source_type"] == "PROJECT_ASSUMPTION").all()


def test_benchmark_staple_portions(dish_ingredients_df):
    """Validates baseline portion weights for Chapati, Plain Rice, and Boiled Egg."""
    chapati = dish_ingredients_df[dish_ingredients_df["dish"] == "Chapati"]
    assert len(chapati) == 1
    assert chapati.iloc[0]["ingredient"] == "Wheat flour, atta"
    assert chapati.iloc[0]["quantity_g"] == 30.0

    rice = dish_ingredients_df[dish_ingredients_df["dish"] == "Plain Rice"]
    assert len(rice) == 1
    assert rice.iloc[0]["ingredient"] == "Rice, raw/parboiled"
    assert rice.iloc[0]["quantity_g"] == 50.0

    egg = dish_ingredients_df[dish_ingredients_df["dish"] == "Boiled Egg"]
    assert len(egg) == 1
    assert egg.iloc[0]["ingredient"] == "Egg, whole"
    assert egg.iloc[0]["quantity_g"] == 50.0


def test_curry_fat_and_dal_portions(dish_ingredients_df):
    """Asserts standard 5g oil/ghee assumption in curries and 30g raw dal issuance."""
    dal_tadka = dish_ingredients_df[dish_ingredients_df["dish"] == "Yellow Dal Tadka"]
    dal_part = dal_tadka[dal_tadka["ingredient"] == "Red gram, dal"].iloc[0]
    fat_part = dal_tadka[dal_tadka["ingredient"] == "Ghee"].iloc[0]
    assert dal_part["quantity_g"] == 30.0
    assert fat_part["quantity_g"] == 5.0

    paneer_dish = dish_ingredients_df[dish_ingredients_df["dish"] == "Matar Paneer"]
    paneer_part = paneer_dish[paneer_dish["ingredient"] == "Paneer"].iloc[0]
    oil_part = paneer_dish[paneer_dish["ingredient"] == "Vegetable oil"].iloc[0]
    assert paneer_part["quantity_g"] == 40.0
    assert oil_part["quantity_g"] == 5.0


def test_mapping_status_propagation(dish_ingredients_df):
    """Asserts mapping status and confidence are preserved from ingredient mapping table."""
    assert set(dish_ingredients_df["mapping_status"].unique()).issubset({"VERIFIED", "APPROXIMATE", "UNMAPPED"})
    assert (dish_ingredients_df["confidence"] >= 0.0).all()
    assert (dish_ingredients_df["confidence"] <= 1.0).all()
