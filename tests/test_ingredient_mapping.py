"""
test_ingredient_mapping.py

Unit tests for ingredient_mapping_final.csv and ingredient_nutrition_final.csv.
Validates mapping status taxonomy, IFCT code foreign key integrity,
external reference nutrition payloads, and non-zero propagation for missing foods.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pytest


@pytest.fixture(scope="module")
def root_dir():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def mapping_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ingredient_mapping_final.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def nutrition_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ingredient_nutrition_final.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def clean_ifct_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ifct_2017_clean.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def ingredient_master_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ingredient_master.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


def test_mapping_dimensions_and_keys(mapping_df, ingredient_master_df):
    """Asserts mapping table contains exactly 80 rows matching ingredient_master."""
    assert len(mapping_df) == 80
    assert set(mapping_df["ingredient"]) == set(ingredient_master_df["canonical_ingredient_name"])
    assert mapping_df["ingredient"].nunique() == 80


def test_mapping_taxonomy_enums(mapping_df):
    """Asserts mapping status, mapping type, and source type conform to project schema."""
    allowed_status = {"VERIFIED", "APPROXIMATE", "UNMAPPED"}
    allowed_types = {"DIRECT", "SYNONYM", "VARIETY", "FOOD_FORM", "INGREDIENT_FORM", "EXTERNAL", "UNAVAILABLE"}
    allowed_sources = {"IFCT_DIRECT", "IFCT_DERIVED", "EXTERNAL_REFERENCE", "PROJECT_ASSUMPTION", "UNAVAILABLE"}

    assert set(mapping_df["mapping_status"].unique()).issubset(allowed_status)
    assert set(mapping_df["mapping_type"].unique()).issubset(allowed_types)
    assert set(mapping_df["source_type"].unique()).issubset(allowed_sources)


def test_ifct_foreign_key_integrity(mapping_df, clean_ifct_df):
    """Asserts every mapped ifct_code exists in ifct_2017_clean.csv."""
    mapped_codes = mapping_df["ifct_code"].dropna().unique()
    valid_codes = set(clean_ifct_df["ifct_code"].unique())
    for code in mapped_codes:
        if str(code).strip():
            assert code in valid_codes, f"Orphan ifct_code {code} not found in clean IFCT"


def test_curd_modeling_provenance(mapping_df):
    """Curd / Dahi must be explicitly marked as APPROXIMATE / PROJECT_ASSUMPTION."""
    curd = mapping_df[mapping_df["ingredient"] == "Curd / Dahi"].iloc[0]
    assert curd["mapping_status"] == "APPROXIMATE"
    assert curd["source_type"] == "PROJECT_ASSUMPTION"
    assert curd["ifct_code"] == "L002"


def test_external_reference_nutrients(nutrition_df):
    """Asserts external reference items (Sugar, Butter, Condensed milk, Bread) carry cited values."""
    sugar = nutrition_df[nutrition_df["ingredient"] == "Sugar, refined"].iloc[0]
    assert sugar["energy_kcal_per_100g"] == 387.0
    assert sugar["carbohydrate_g_per_100g"] == 99.96
    assert sugar["data_source"] == "EXTERNAL_REFERENCE"
    assert sugar["source_reference"] == "USDA_FDC_169655"

    butter = nutrition_df[nutrition_df["ingredient"] == "Butter"].iloc[0]
    assert butter["energy_kcal_per_100g"] == 717.0
    assert butter["fat_g_per_100g"] == 81.11

    bread = nutrition_df[nutrition_df["ingredient"] == "Commercial bread"].iloc[0]
    assert bread["energy_kcal_per_100g"] == 265.0
    assert bread["protein_g_per_100g"] == 8.85


def test_unavailable_foods_propagate_nan(nutrition_df):
    """Unavailable commercial items must propagate NaN, never zero calories."""
    unavailable = nutrition_df[nutrition_df["data_status"] == "UNAVAILABLE"]
    assert len(unavailable) == 16
    for _, row in unavailable.iterrows():
        assert np.isnan(row["energy_kcal_per_100g"]), f"Expected NaN energy for {row['ingredient']}"
        assert np.isnan(row["protein_g_per_100g"]), f"Expected NaN protein for {row['ingredient']}"


def test_non_negativity_in_nutrition(nutrition_df):
    """All non-null nutritional values must be >= 0.0."""
    nutrient_cols = [
        "energy_kcal_per_100g", "protein_g_per_100g", "fat_g_per_100g",
        "carbohydrate_g_per_100g", "fibre_g_per_100g", "potassium_mg_per_100g",
        "sodium_mg_per_100g", "calcium_mg_per_100g", "iron_mg_per_100g"
    ]
    for col in nutrient_cols:
        valid_vals = nutrition_df[col].dropna()
        assert (valid_vals >= 0.0).all(), f"Found negative values in {col}"
