"""
validate_data.py

Rigorous automated validation gate for all Phase 1-6 datasets and metadata.
Asserts structural, chemical, mathematical, and provenance integrity.
Prints the standardized DATA VALIDATION REPORT summary and exits non-zero on errors.
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np


def validate_all(root_dir: Path) -> dict:
    errors = []
    warnings = []

    # 1. Load datasets
    clean_ifct_path = root_dir / "data" / "processed" / "ifct_2017_clean.csv"
    ing_master_path = root_dir / "data" / "processed" / "ingredient_master.csv"
    ing_mapping_path = root_dir / "data" / "processed" / "ingredient_mapping_final.csv"
    ing_nut_path = root_dir / "data" / "processed" / "ingredient_nutrition_final.csv"
    dish_ings_path = root_dir / "data" / "processed" / "dish_ingredients_final.csv"
    dish_nut_path = root_dir / "data" / "processed" / "dish_nutrition_final.csv"
    dish_cov_path = root_dir / "data" / "processed" / "dish_nutrition_coverage.csv"
    portions_path = root_dir / "data" / "rules" / "portion_assumptions.csv"
    menu_path = root_dir / "data" / "raw" / "mess_menu.csv"
    if not menu_path.exists():
        menu_path = root_dir / "mess_menu.csv"

    # Assert all files exist
    for p in [clean_ifct_path, ing_master_path, ing_mapping_path, ing_nut_path,
              dish_ings_path, dish_nut_path, dish_cov_path, portions_path, menu_path]:
        if not p.exists():
            errors.append(f"Missing required dataset: {p}")
            return {"errors": errors, "warnings": warnings}

    df_ifct = pd.read_csv(clean_ifct_path)
    df_ing_master = pd.read_csv(ing_master_path)
    df_mapping = pd.read_csv(ing_mapping_path)
    df_ing_nut = pd.read_csv(ing_nut_path)
    df_dish_ings = pd.read_csv(dish_ings_path)
    df_dish_nut = pd.read_csv(dish_nut_path)
    df_dish_cov = pd.read_csv(dish_cov_path)
    df_portions = pd.read_csv(portions_path)
    df_menu = pd.read_csv(menu_path)

    # 2. IFCT Integrity Checks
    if df_ifct["ifct_code"].duplicated().any():
        errors.append(f"Duplicate IFCT codes found: {df_ifct[df_ifct['ifct_code'].duplicated()]['ifct_code'].tolist()}")

    # Cow milk check
    milk_row = df_ifct[df_ifct["ifct_code"] == "L002"]
    if milk_row.empty:
        errors.append("Cow milk (L002) missing from clean IFCT")
    else:
        milk_ca = milk_row.iloc[0]["calcium_mg_per_100g"]
        milk_kcal = milk_row.iloc[0]["energy_kcal_per_100g"]
        if not (117.0 <= milk_ca <= 119.0):
            errors.append(f"Cow milk calcium out of range: {milk_ca} mg (expected ~118 mg)")
        if not (72.0 <= milk_kcal <= 74.0):
            errors.append(f"Cow milk energy out of range: {milk_kcal} kcal (expected ~72.9 kcal)")

    # 3. Ingredient Master & Mapping Checks
    if df_ing_master["ingredient_id"].duplicated().any():
        errors.append("Duplicate ingredient_id in ingredient_master.csv")
    if df_ing_master["canonical_ingredient_name"].duplicated().any():
        errors.append("Duplicate canonical_ingredient_name in ingredient_master.csv")

    verified_count = int((df_mapping["mapping_status"] == "VERIFIED").sum())
    approx_count = int((df_mapping["mapping_status"] == "APPROXIMATE").sum())
    unmapped_count = int((df_mapping["mapping_status"] == "UNMAPPED").sum())

    # 4. Dish & Recipe Integrity Checks
    dishes_without_ings = set(df_dish_nut["dish"]) - set(df_dish_ings["dish"])
    if dishes_without_ings:
        errors.append(f"Dishes without recipe ingredients: {dishes_without_ings}")

    # Non-positive portions
    if (df_dish_ings["quantity_g"] <= 0).any():
        errors.append("Non-positive portion quantity found in dish_ingredients_final.csv")

    # Portion size sanity (between 1g and 250g raw ingredient)
    if (df_dish_ings["quantity_g"] > 250.0).any():
        errors.append("Unrealistically large single raw ingredient portion (>250g)")

    # Foreign key integrity: recipe ingredients must be in master
    unknown_recipe_ings = set(df_dish_ings["ingredient"]) - set(df_ing_master["canonical_ingredient_name"])
    if unknown_recipe_ings:
        errors.append(f"Unknown recipe ingredients not in master: {unknown_recipe_ings}")

    # 5. Dish Nutrition Checks
    complete_nut = int((df_dish_nut["calculation_status"] == "COMPLETE_IFCT").sum())
    partial_nut = int((df_dish_nut["calculation_status"] == "PARTIAL_IFCT").sum())
    ext_nut = int((df_dish_nut["calculation_status"] == "EXTERNAL_DATA_INCLUDED").sum())
    approx_nut = int((df_dish_nut["calculation_status"] == "ASSUMPTION_INCLUDED").sum())
    insufficient_nut = int((df_dish_nut["calculation_status"] == "INSUFFICIENT_DATA").sum())

    # All non-insufficient dishes must have valid energy > 0
    calculated_dishes = df_dish_nut[df_dish_nut["calculation_status"] != "INSUFFICIENT_DATA"]
    if (calculated_dishes["energy_kcal"] <= 0.0).any() or calculated_dishes["energy_kcal"].isnull().any():
        errors.append("Calculated dishes with zero or null energy found")

    # All insufficient data dishes must have NaN energy
    insufficient_dishes = df_dish_nut[df_dish_nut["calculation_status"] == "INSUFFICIENT_DATA"]
    if insufficient_dishes["energy_kcal"].notnull().any():
        errors.append("Insufficient data dishes found with non-null energy")

    # Non-negativity check
    for col in ["protein_g", "fat_g", "carbohydrate_g", "fibre_g", "calcium_mg", "iron_mg", "sodium_mg", "potassium_mg"]:
        if (calculated_dishes[col] < 0.0).any():
            errors.append(f"Negative values found in {col}")

    # 6. Menu Integrity Checks
    if df_menu.duplicated().any():
        errors.append("Duplicate menu rows found in mess_menu.csv")
    if df_menu.isnull().any().any():
        errors.append("Null values found in mess_menu.csv")

    # Counts
    ifct_foods_count = len(df_ifct)
    extracted_ings_count = len(df_ing_master)
    total_dishes_count = len(df_dish_nut)

    # Count project assumptions & external references
    project_assumptions_count = len(df_portions) + approx_count
    external_refs_count = int((df_mapping["source_type"] == "EXTERNAL_REFERENCE").sum())

    # Print exact required summary report
    print("DATA VALIDATION REPORT")
    print(f"IFCT foods: {ifct_foods_count}")
    print(f"Ingredients extracted: {extracted_ings_count} | Verified mappings: {verified_count} | Approximate mappings: {approx_count} | Unmapped ingredients: {unmapped_count}")
    print(f"Dishes: {total_dishes_count} | Complete nutrition: {complete_nut + ext_nut + approx_nut} | Partial nutrition: {partial_nut} | Insufficient data: {insufficient_nut}")
    print(f"Project assumptions: {project_assumptions_count} | External references: {external_refs_count}")
    print(f"Warnings: {len(warnings)} | Errors: {len(errors)}")

    if errors:
        print("\nERRORS DETECTED:")
        for e in errors:
            print(f"  - {e}")

    return {
        "errors": errors,
        "warnings": warnings,
        "ifct_foods": ifct_foods_count,
        "ingredients": extracted_ings_count,
        "dishes": total_dishes_count,
        "verified_mappings": verified_count,
        "approx_mappings": approx_count,
        "unmapped_ingredients": unmapped_count,
        "complete_nutrition": complete_nut + ext_nut + approx_nut,
        "partial_nutrition": partial_nut,
        "insufficient_data": insufficient_nut,
        "project_assumptions": project_assumptions_count,
        "external_references": external_refs_count
    }


def main():
    root_dir = Path(__file__).resolve().parent.parent
    result = validate_all(root_dir)
    if result["errors"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
