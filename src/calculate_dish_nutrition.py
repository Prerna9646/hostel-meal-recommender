"""
calculate_dish_nutrition.py

Aggregates raw ingredient nutritional densities to compute dish-level nutrition.
Formula: contribution = (quantity_g / 100.0) * nutrient_per_100g.
Preserves missing data (NaN) without silently treating unmapped commercial foods as zero.
Outputs data/processed/dish_nutrition_final.csv and data/processed/dish_nutrition_coverage.csv.
"""

from pathlib import Path
import pandas as pd
import numpy as np


NUTRIENT_MAP = {
    "energy_kcal_per_100g": "energy_kcal",
    "protein_g_per_100g": "protein_g",
    "fat_g_per_100g": "fat_g",
    "carbohydrate_g_per_100g": "carbohydrate_g",
    "fibre_g_per_100g": "fibre_g",
    "potassium_mg_per_100g": "potassium_mg",
    "sodium_mg_per_100g": "sodium_mg",
    "calcium_mg_per_100g": "calcium_mg",
    "iron_mg_per_100g": "iron_mg",
}


def compute_dish_nutrition(root_dir: Path):
    dish_ings_path = root_dir / "data" / "processed" / "dish_ingredients_final.csv"
    ing_nut_path = root_dir / "data" / "processed" / "ingredient_nutrition_final.csv"

    dish_ings = pd.read_csv(dish_ings_path)
    ing_nut = pd.read_csv(ing_nut_path)

    merged = dish_ings.merge(ing_nut, on="ingredient", suffixes=("", "_nut"))

    nutrition_rows = []
    coverage_rows = []

    for dish, group in merged.groupby("dish", sort=True):
        tot_ings = len(group)
        unmapped = int((group["mapping_status"] == "UNMAPPED").sum())
        mapped = tot_ings - unmapped
        approx = int((group["mapping_status"] == "APPROXIMATE").sum())
        external = int((group["data_source"] == "EXTERNAL_REFERENCE").sum())

        tot_qty = group["quantity_g"].sum()

        if unmapped == tot_ings:
            calc_status = "INSUFFICIENT_DATA"
            coverage_pct = 0.0
        elif unmapped > 0:
            calc_status = "PARTIAL_IFCT"
            mapped_qty = group[group["mapping_status"] != "UNMAPPED"]["quantity_g"].sum()
            coverage_pct = round((mapped_qty / tot_qty) * 100.0, 1)
        elif external > 0:
            calc_status = "EXTERNAL_DATA_INCLUDED"
            coverage_pct = 100.0
        elif approx > 0:
            calc_status = "ASSUMPTION_INCLUDED"
            coverage_pct = 100.0
        else:
            calc_status = "COMPLETE_IFCT"
            coverage_pct = 100.0

        # Build coverage record
        coverage_rows.append({
            "dish": dish,
            "total_ingredients": tot_ings,
            "mapped_ingredients": mapped,
            "unmapped_ingredients": unmapped,
            "ifct_coverage_percent": coverage_pct,
            "assumption_count": approx,
            "external_data_count": external,
            "calculation_status": calc_status
        })

        # Build nutrition record
        nut_record = {
            "dish": dish,
            "serving_size_g": round(tot_qty, 1),
            "ingredient_count": tot_ings,
            "data_coverage_percent": coverage_pct,
            "calculation_status": calc_status
        }

        for in_col, out_col in NUTRIENT_MAP.items():
            if calc_status == "INSUFFICIENT_DATA":
                nut_record[out_col] = np.nan
            else:
                contrib = (group["quantity_g"] / 100.0) * group[in_col]
                if contrib.isnull().any():
                    nut_record[out_col] = np.nan
                else:
                    nut_record[out_col] = round(contrib.sum(), 2)

        nutrition_rows.append(nut_record)

    df_nutrition = pd.DataFrame(nutrition_rows)
    df_coverage = pd.DataFrame(coverage_rows)

    out_dir = root_dir / "data" / "processed"
    df_nutrition.to_csv(out_dir / "dish_nutrition_final.csv", index=False)
    df_coverage.to_csv(out_dir / "dish_nutrition_coverage.csv", index=False)

    print(f"Generated {out_dir / 'dish_nutrition_final.csv'} ({len(df_nutrition)} dishes)")
    print(f"Generated {out_dir / 'dish_nutrition_coverage.csv'} ({len(df_coverage)} coverage records)")


if __name__ == "__main__":
    compute_dish_nutrition(Path(__file__).resolve().parent.parent)
