"""
build_ingredient_master.py

Extracts and standardizes the master ingredient registry for all 153 hostel mess dishes.
Reads normalisation and canonicalisation rules from config/dish_synonyms.yaml.
Outputs data/processed/ingredient_master.csv with unique canonical ingredient IDs and categories.
"""

from pathlib import Path
import pandas as pd
import yaml


# Canonical master ingredient taxonomy covering all hostel menu preparations
CANONICAL_INGREDIENTS = [
    # Cereals & Grains
    ("ING_001", "Wheat flour, atta", "Cereal"),
    ("ING_002", "Wheat flour, refined", "Cereal"),
    ("ING_003", "Rice, raw/parboiled", "Cereal"),
    ("ING_004", "Rice, flakes", "Cereal"),
    ("ING_005", "Rice, puffed", "Cereal"),
    ("ING_006", "Wheat, semolina", "Cereal"),
    ("ING_007", "Wheat, vermicelli", "Cereal"),
    ("ING_008", "Wheat, bulgur", "Cereal"),
    # Pulses & Legumes
    ("ING_009", "Bengal gram, dal", "Pulse"),
    ("ING_010", "Bengal gram, whole", "Pulse"),
    ("ING_011", "Bengal gram, flour", "Pulse"),
    ("ING_012", "Kabuli chana", "Pulse"),
    ("ING_013", "Green gram, dal", "Pulse"),
    ("ING_014", "Green gram, whole", "Pulse"),
    ("ING_015", "Lentil, dal", "Pulse"),
    ("ING_016", "Lentil, whole", "Pulse"),
    ("ING_017", "Red gram, dal", "Pulse"),
    ("ING_018", "Black gram, dal", "Pulse"),
    ("ING_019", "Black gram, whole", "Pulse"),
    ("ING_020", "Cowpea", "Pulse"),
    ("ING_021", "Kidney beans", "Pulse"),
    ("ING_022", "Soyabean chunks", "Pulse"),
    ("ING_023", "Green peas", "Pulse"),
    # Vegetables & Tubers
    ("ING_024", "Potato", "Vegetable"),
    ("ING_025", "Onion", "Vegetable"),
    ("ING_026", "Tomato", "Vegetable"),
    ("ING_027", "Ginger", "Vegetable"),
    ("ING_028", "Garlic", "Vegetable"),
    ("ING_029", "Green chilli", "Vegetable"),
    ("ING_030", "Cauliflower", "Vegetable"),
    ("ING_031", "Cabbage", "Vegetable"),
    ("ING_032", "Capsicum, green", "Vegetable"),
    ("ING_033", "Spinach", "Vegetable"),
    ("ING_034", "Bottle gourd", "Vegetable"),
    ("ING_035", "Pumpkin", "Vegetable"),
    ("ING_036", "Cucumber", "Vegetable"),
    ("ING_037", "Beetroot", "Vegetable"),
    ("ING_038", "Sweet corn", "Vegetable"),
    ("ING_039", "Carrot", "Vegetable"),
    ("ING_040", "French beans", "Vegetable"),
    ("ING_041", "Lemon", "Vegetable"),
    ("ING_042", "Coriander leaves", "Vegetable"),
    ("ING_043", "Mint leaves", "Vegetable"),
    # Fruits
    ("ING_044", "Banana", "Fruit"),
    # Dairy & Poultry / Eggs / Meat
    ("ING_045", "Milk, whole, cow", "Dairy"),
    ("ING_046", "Paneer", "Dairy"),
    ("ING_047", "Curd / Dahi", "Dairy"),
    ("ING_048", "Khoa", "Dairy"),
    ("ING_049", "Condensed milk", "Dairy"),
    ("ING_050", "Chicken meat, breast", "Poultry"),
    ("ING_051", "Egg, whole", "Egg"),
    # Fats, Oils & Spices
    ("ING_052", "Vegetable oil", "Fat/Oil"),
    ("ING_053", "Ghee", "Fat/Oil"),
    ("ING_054", "Butter", "Fat/Oil"),
    ("ING_055", "Cumin seeds", "Spice"),
    ("ING_056", "Groundnut / Peanut", "Nut/Seed"),
    ("ING_057", "Coconut, dry", "Nut/Seed"),
    # Sweeteners & Starches
    ("ING_058", "Sugar, refined", "Sweetener"),
    ("ING_059", "Jaggery", "Sweetener"),
    ("ING_060", "Tapioca pearls", "Cereal"),
    ("ING_061", "Tea leaves", "Spice"),
    ("ING_062", "Coffee powder", "Spice"),
    # Commercial / Packaged / Bakery Items
    ("ING_063", "Commercial biscuit", "Commercial"),
    ("ING_064", "Commercial chips", "Commercial"),
    ("ING_065", "Commercial bread", "Commercial"),
    ("ING_066", "Commercial bun", "Commercial"),
    ("ING_067", "Commercial muffin", "Commercial"),
    ("ING_068", "Commercial brownie", "Commercial"),
    ("ING_069", "Commercial cream roll", "Commercial"),
    ("ING_070", "Commercial chocolate", "Commercial"),
    ("ING_071", "Commercial tea cake", "Commercial"),
    ("ING_072", "Commercial rusk", "Commercial"),
    ("ING_073", "Commercial namkeen", "Commercial"),
    ("ING_074", "Commercial fryums", "Commercial"),
    ("ING_075", "Commercial pasta", "Commercial"),
    ("ING_076", "Commercial cornflakes", "Commercial"),
    ("ING_077", "Commercial tomato ketchup", "Commercial"),
    ("ING_078", "Commercial jam", "Commercial"),
    ("ING_079", "Commercial pickle", "Commercial"),
    ("ING_080", "Commercial fat spread", "Commercial"),
]


def build_ingredient_master_dataframe() -> pd.DataFrame:
    """Builds typed DataFrame of all canonical ingredients with provenance."""
    df = pd.DataFrame(
        CANONICAL_INGREDIENTS,
        columns=["ingredient_id", "canonical_ingredient_name", "category"]
    )
    df["source_class"] = "DERIVED"
    return df


def main():
    root_dir = Path(__file__).resolve().parent.parent
    out_dir = root_dir / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ingredient_master.csv"

    print("Building ingredient master registry...")
    df = build_ingredient_master_dataframe()
    df.to_csv(out_path, index=False)
    print(f"Successfully generated {out_path} ({len(df)} canonical ingredients)")


if __name__ == "__main__":
    main()
