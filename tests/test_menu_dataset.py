"""
test_menu_dataset.py

Unit tests for normalized mess menu and dish classification (Phase 8).
Validates row counts, date formatting, meal slot normalisation, hostel scope,
compound dish decomposition, plate grammar classification, and dietary tag inheritance.
"""

from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def menu_df():
    path = Path(__file__).resolve().parent.parent / "data" / "processed" / "mess_menu_final.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def class_df():
    path = Path(__file__).resolve().parent.parent / "data" / "processed" / "dish_classification_final.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def dish_nutrition_df():
    path = Path(__file__).resolve().parent.parent / "data" / "processed" / "dish_nutrition_final.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


def test_menu_row_count(menu_df):
    """Test normalized menu contains exactly 635 rows (624 raw - 11 compound + 22 split = 635)."""
    assert len(menu_df) == 635, f"Expected 635 normalized menu rows, found {len(menu_df)}"


def test_iso_dates(menu_df):
    """Test all dates are formatted as ISO YYYY-MM-DD across October 2026."""
    dates = pd.to_datetime(menu_df["normalized_date"], format="%Y-%m-%d", errors="coerce")
    assert not dates.isna().any(), "Found invalid date formats in normalized_date"
    assert menu_df["normalized_date"].nunique() == 31, "Expected 31 distinct October dates"
    assert menu_df["normalized_date"].min() == "2026-10-01"
    assert menu_df["normalized_date"].max() == "2026-10-31"


def test_normalized_meal_slots(menu_df):
    """Test all normalized meal slots belong to the four standardized operational slots."""
    allowed = {"BREAKFAST", "LUNCH", "DINNER", "E_TEA"}
    slots = set(menu_df["normalized_meal"].unique())
    assert slots.issubset(allowed), f"Unexpected operational slots: {slots - allowed}"


def test_hostel_scope(menu_df):
    """Test Girls Hostel scope normalisation into E_TEA slot with GIRLS_HOSTEL scope."""
    gh_rows = menu_df[menu_df["original_meal"] == "Girls Hostel"]
    assert len(gh_rows) == 62, f"Expected 62 Girls Hostel rows, found {len(gh_rows)}"
    assert (gh_rows["normalized_meal"] == "E_TEA").all(), "All Girls Hostel rows must normalize to E_TEA slot"
    assert (gh_rows["hostel_scope"] == "GIRLS_HOSTEL").all(), "All Girls Hostel rows must carry GIRLS_HOSTEL scope"

    common_rows = menu_df[menu_df["original_meal"] != "Girls Hostel"]
    assert (common_rows["hostel_scope"] == "COMMON").all(), "Non-Girls Hostel rows must carry COMMON scope"


def test_dessert_attachment(menu_df):
    """Test all 14 raw Dessert rows are attached to DINNER slot with is_dessert_flag=True."""
    dessert_rows = menu_df[menu_df["original_meal"] == "Dessert"]
    assert len(dessert_rows) == 14, f"Expected 14 Dessert rows, found {len(dessert_rows)}"
    assert (dessert_rows["normalized_meal"] == "DINNER").all(), "Desserts must normalize to DINNER slot"
    assert (dessert_rows["is_dessert_flag"] == True).all(), "Desserts must have is_dessert_flag True"
    assert (dessert_rows["hostel_scope"] == "COMMON").all(), "Desserts must carry COMMON scope"


def test_compound_dish_decomposition(menu_df):
    """Test that compound menu dishes were decomposed and do not appear in canonical_dish."""
    compound_raw_dishes = {
        "White Chana Khata Mitha Kaddu",
        "Mix Dal Amritsari Gobhi Adraki",
        "Mix Dal Amritsari Aloo Capsicum",
        "Mix Dal Amritsari Khata Mitha Kaddu",
        "Aloo Onion Kadhi Jeera Aloo",
        "Amritsari Badi Jeera Aloo",
        "Dhaba Dal Gobhi Adraki",
    }
    canonical_dishes = set(menu_df["canonical_dish"].unique())
    for comp in compound_raw_dishes:
        assert comp not in canonical_dishes, f"Compound dish {comp} should not appear as a canonical dish"

    split_rows = menu_df[menu_df["provenance_notes"].str.startswith("COMPOUND_SPLIT")]
    assert len(split_rows) == 22, f"Expected 22 split dish rows (11 * 2), found {len(split_rows)}"


def test_dish_classification_count(class_df, dish_nutrition_df):
    """Test dish classification table contains exactly 132 dishes matching dish_nutrition."""
    assert len(class_df) == 132, f"Expected 132 classified dishes, found {len(class_df)}"
    assert set(class_df["canonical_dish"]) == set(dish_nutrition_df["dish"]), "Dish mismatch with dish_nutrition"


def test_dish_classification_roles(class_df):
    """Test plate grammar roles are well-formed and exhaustive across 8 roles."""
    valid_roles = {
        "STAPLE", "DAL_PROTEIN", "DRY_SABZI", "GRAVY_SABZI",
        "SNACK", "BEVERAGE", "DESSERT", "ACCOMPANIMENT"
    }
    roles = set(class_df["plate_role"].unique())
    assert roles.issubset(valid_roles), f"Unexpected plate roles: {roles - valid_roles}"
    assert not class_df["plate_role"].isna().any(), "Found missing plate role"

    # Verify counts per role
    role_counts = class_df["plate_role"].value_counts().to_dict()
    assert role_counts["STAPLE"] == 18
    assert role_counts["DAL_PROTEIN"] == 28
    assert role_counts["GRAVY_SABZI"] == 13
    assert role_counts["DRY_SABZI"] == 19
    assert role_counts["SNACK"] == 19
    assert role_counts["DESSERT"] == 11
    assert role_counts["BEVERAGE"] == 4
    assert role_counts["ACCOMPANIMENT"] == 20


def test_dietary_tag_inheritance(class_df):
    """Test conservative dietary tag inheritance across all 132 dishes."""
    nv = set(class_df[class_df["dietary_tag"] == "NON_VEG"]["canonical_dish"])
    egg = set(class_df[class_df["dietary_tag"] == "EGGETARIAN"]["canonical_dish"])
    veg = set(class_df[class_df["dietary_tag"] == "VEGETARIAN"]["canonical_dish"])

    assert nv == {"Chicken Curry", "Butter Chicken", "Chicken Kolhapuri"}
    assert egg == {"Boiled Egg", "Egg Curry", "Egg Bhurji", "Omelette"}
    assert len(veg) == 125
    assert len(nv) + len(egg) + len(veg) == 132


def test_foreign_key_integrity(menu_df, class_df, dish_nutrition_df):
    """Test that all canonical dishes in menu map cleanly to dish nutrition and classification."""
    menu_dishes = set(menu_df["canonical_dish"].unique())
    nutr_dishes = set(dish_nutrition_df["dish"].unique())
    class_dishes = set(class_df["canonical_dish"].unique())

    assert menu_dishes.issubset(nutr_dishes), f"Menu contains dishes without nutrition: {menu_dishes - nutr_dishes}"
    assert menu_dishes.issubset(class_dishes), f"Menu contains dishes without classification: {menu_dishes - class_dishes}"
