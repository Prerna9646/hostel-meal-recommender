"""
test_ingredient_master.py

Unit tests for ingredient_master.csv and config/dish_synonyms.yaml.
Validates canonical taxonomy, ID uniqueness, category assignments, and dish coverage.
"""

from pathlib import Path
import pandas as pd
import pytest
import yaml


@pytest.fixture(scope="module")
def root_dir():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def ingredient_master_df(root_dir):
    csv_path = root_dir / "data" / "processed" / "ingredient_master.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def synonyms_config(root_dir):
    yaml_path = root_dir / "config" / "dish_synonyms.yaml"
    assert yaml_path.exists(), f"Missing {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def menu_dishes(root_dir):
    menu_path = root_dir / "data" / "raw" / "mess_menu.csv"
    if not menu_path.exists():
        menu_path = root_dir / "mess_menu.csv"
    return pd.read_csv(menu_path)["dish"].unique()


def test_ingredient_master_dimensions(ingredient_master_df):
    """Asserts ingredient_master contains exactly 80 canonical ingredients with unique IDs."""
    assert len(ingredient_master_df) == 80
    assert ingredient_master_df["ingredient_id"].nunique() == 80
    assert ingredient_master_df["canonical_ingredient_name"].nunique() == 80


def test_ingredient_master_categories(ingredient_master_df):
    """Asserts all categories belong to the defined taxonomy."""
    valid_categories = {
        "Cereal", "Pulse", "Vegetable", "Fruit", "Dairy",
        "Poultry", "Egg", "Fat/Oil", "Spice", "Nut/Seed",
        "Sweetener", "Commercial"
    }
    actual_categories = set(ingredient_master_df["category"].unique())
    assert actual_categories.issubset(valid_categories)


def test_ingredient_master_provenance(ingredient_master_df):
    """Asserts all rows are tagged with DERIVED source class."""
    assert (ingredient_master_df["source_class"] == "DERIVED").all()


def test_compound_dish_coverage(synonyms_config):
    """Asserts all 7 compound dish strings are registered with primary/secondary components."""
    compounds = synonyms_config.get("compound_dish_decompositions", {})
    expected_compounds = {
        "White Chana Khata Mitha Kaddu",
        "Sabut Masoor Dal Aloo Capsicum",
        "Black Chana Mix Veg",
        "White Chana Nutry Keema",
        "Sabut Masoor Dal Palak Corn",
        "Black Chana Aloo Cabbage Matar",
        "Rajmah Ghiya Masala"
    }
    assert set(compounds.keys()) == expected_compounds
    for key, spec in compounds.items():
        assert "primary_dish" in spec
        assert "secondary_dish" in spec
        assert "reason" in spec


def test_all_153_dishes_canonicalised(menu_dishes, synonyms_config):
    """Asserts every single dish string in mess_menu.csv resolves to a valid canonical dish."""
    assert len(menu_dishes) == 153
    canonical_mappings = synonyms_config.get("canonical_dish_mappings", {})
    spelling = synonyms_config.get("spelling_normalisations", {})
    compounds = synonyms_config.get("compound_dish_decompositions", {})

    canonical_dishes = set()
    for d in menu_dishes:
        if d in compounds:
            canonical_dishes.add(compounds[d]["primary_dish"])
            canonical_dishes.add(compounds[d]["secondary_dish"])
        elif d in canonical_mappings:
            canonical_dishes.add(canonical_mappings[d])
        elif d in spelling:
            canonical_dishes.add(spelling[d])
        else:
            canonical_dishes.add(d)

    # 153 raw strings resolve into exactly 132 canonical culinary dishes
    assert len(canonical_dishes) == 132
    assert "Plain Rice" in canonical_dishes
    assert "Plain Curd" in canonical_dishes
    assert "Dal Makhani" in canonical_dishes
    assert "Aloo Onion Kadhi" in canonical_dishes
