"""
test_ifct_units.py

Unit and biological sanity tests for ifct_2017_clean.csv.
Validates energy and mineral conversions against known reference foods.
Ensures zero-energy oil anomaly is resolved and non-negativity invariants hold.
"""

from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def clean_ifct_df():
    data_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "ifct_2017_clean.csv"
    assert data_path.exists(), f"Missing clean IFCT file at {data_path}"
    return pd.read_csv(data_path)


def test_row_and_column_integrity(clean_ifct_df):
    """Asserts all 542 foods are present with unique codes and non-empty identity fields."""
    assert len(clean_ifct_df) == 542
    assert clean_ifct_df["ifct_code"].nunique() == 542
    assert clean_ifct_df["food_name"].isnull().sum() == 0
    assert clean_ifct_df["food_group"].isnull().sum() == 0


def test_cow_milk_calcium(clean_ifct_df):
    """Whole cow milk (L002) calcium must be ~118 mg/100g (converted from 0.118 g)."""
    milk = clean_ifct_df[clean_ifct_df["ifct_code"] == "L002"].iloc[0]
    assert 117.0 <= milk["calcium_mg_per_100g"] <= 119.0
    assert milk["calcium_mg_per_100g"] == 118.0


def test_cow_milk_energy(clean_ifct_df):
    """Whole cow milk (L002) energy must be ~72.9 kcal/100g (converted from 305 kJ)."""
    milk = clean_ifct_df[clean_ifct_df["ifct_code"] == "L002"].iloc[0]
    assert 72.0 <= milk["energy_kcal_per_100g"] <= 74.0
    assert milk["energy_kcal_per_100g"] == 72.90


def test_cow_milk_electrolytes(clean_ifct_df):
    """Validates cow milk sodium and potassium converted to mg."""
    milk = clean_ifct_df[clean_ifct_df["ifct_code"] == "L002"].iloc[0]
    assert 25.0 <= milk["sodium_mg_per_100g"] <= 26.0
    assert 114.0 <= milk["potassium_mg_per_100g"] <= 116.0


def test_atta_energy(clean_ifct_df):
    """Whole wheat flour atta (A019) energy must be ~320.3 kcal/100g (converted from 1340 kJ)."""
    atta = clean_ifct_df[clean_ifct_df["ifct_code"] == "A019"].iloc[0]
    assert 318.0 <= atta["energy_kcal_per_100g"] <= 322.0
    assert atta["energy_kcal_per_100g"] == 320.27


def test_bengal_gram_nutrients(clean_ifct_df):
    """Bengal gram dal (B001) protein must be ~21.55 g/100g and iron ~6.08 mg/100g."""
    chana = clean_ifct_df[clean_ifct_df["ifct_code"] == "B001"].iloc[0]
    assert 21.0 <= chana["protein_g_per_100g"] <= 22.0
    assert 5.9 <= chana["iron_mg_per_100g"] <= 6.3


def test_edible_oils_energy_derivation(clean_ifct_df):
    """All 14 Group T oils must have energy ~900 kcal/100g (fatce * 9 kcal/g), resolving raw 0 kJ defect."""
    oils = clean_ifct_df[clean_ifct_df["ifct_code"].str.startswith("T")]
    assert len(oils) == 14
    for _, row in oils.iterrows():
        # Analytical fatce in IFCT ranges from 99.99g to 100.01g -> energy 899.91 to 900.09 kcal
        assert 895.0 <= row["energy_kcal_per_100g"] <= 905.0, f"Oil {row['ifct_code']} energy is {row['energy_kcal_per_100g']}"


def test_non_negativity_invariant(clean_ifct_df):
    """Every nutritional column must be strictly non-negative across all foods."""
    nutrient_cols = [
        "energy_kcal_per_100g", "protein_g_per_100g", "fat_g_per_100g",
        "carbohydrate_g_per_100g", "fibre_g_per_100g", "calcium_mg_per_100g",
        "iron_mg_per_100g", "potassium_mg_per_100g", "sodium_mg_per_100g",
        "water_g_per_100g"
    ]
    for col in nutrient_cols:
        min_val = clean_ifct_df[col].min()
        assert min_val >= 0.0, f"Negative value found in column {col}: {min_val}"


def test_dietary_tag_domain(clean_ifct_df):
    """All dietary tags must adhere strictly to the allowed three-state classification."""
    allowed_tags = {"VEGETARIAN", "EGGETARIAN", "NON_VEG"}
    actual_tags = set(clean_ifct_df["dietary_tag"].unique())
    assert actual_tags.issubset(allowed_tags)
    assert len(clean_ifct_df[clean_ifct_df["dietary_tag"] == "VEGETARIAN"]) == 328
    assert len(clean_ifct_df[clean_ifct_df["dietary_tag"] == "EGGETARIAN"]) == 15
    assert len(clean_ifct_df[clean_ifct_df["dietary_tag"] == "NON_VEG"]) == 199


def test_source_class_annotation(clean_ifct_df):
    """All rows must carry explicit provenance classification."""
    assert (clean_ifct_df["source_class"] == "IFCT_DERIVED").all()
