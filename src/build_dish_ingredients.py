"""
build_dish_ingredients.py

Decomposes all 132 canonical hostel mess dishes into raw ingredient gram quantities per serving.
Reads recipes and portion rules from config/dish_templates.yaml.
Integrates mapping metadata from data/processed/ingredient_mapping_final.csv.
Outputs data/rules/portion_assumptions.csv and data/processed/dish_ingredients_final.csv.
"""

from pathlib import Path
import pandas as pd
import yaml


def build_dish_ingredient_tables(root_dir: Path):
    templates_path = root_dir / "config" / "dish_templates.yaml"
    mapping_path = root_dir / "data" / "processed" / "ingredient_mapping_final.csv"

    with open(templates_path, "r", encoding="utf-8") as f:
        tmpl_cfg = yaml.safe_load(f)
    dishes_data = tmpl_cfg["dishes"]

    mapping_df = pd.read_csv(mapping_path)
    mapping_dict = mapping_df.set_index("ingredient").to_dict(orient="index")

    portion_rows = []
    dish_ing_rows = []

    for dish, ing_list in dishes_data.items():
        for item in ing_list:
            ing = item["ingredient"]
            qty = float(item["quantity_g"])
            reason = item.get("reason", "Standard institutional raw ingredient portion assumption")

            meta = mapping_dict.get(ing, {})
            m_status = meta.get("mapping_status", "UNMAPPED")
            conf = meta.get("confidence", 0.0)
            ing_notes = meta.get("notes", "")

            # 1. Portion assumptions audit record
            portion_rows.append({
                "dish": dish,
                "ingredient": ing,
                "quantity_g": qty,
                "basis": "RAW_INGREDIENT_GRAM_PER_SERVING",
                "source": "PROJECT_PORTION_ASSUMPTIONS",
                "source_type": "PROJECT_ASSUMPTION",
                "reason": reason,
                "notes": ing_notes
            })

            # 2. Processed dish ingredients record
            dish_ing_rows.append({
                "dish": dish,
                "ingredient": ing,
                "quantity_g": qty,
                "quantity_basis": "RAW_INGREDIENT_GRAM_PER_SERVING",
                "source_type": "PROJECT_ASSUMPTION",
                "source_reference": "PROJECT_PORTION_ASSUMPTIONS",
                "mapping_status": m_status,
                "confidence": conf,
                "notes": reason
            })

    df_portions = pd.DataFrame(portion_rows)
    df_dish_ings = pd.DataFrame(dish_ing_rows)

    rules_dir = root_dir / "data" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    df_portions.to_csv(rules_dir / "portion_assumptions.csv", index=False)

    proc_dir = root_dir / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    df_dish_ings.to_csv(proc_dir / "dish_ingredients_final.csv", index=False)

    print(f"Generated {rules_dir / 'portion_assumptions.csv'} ({len(df_portions)} rows across {len(dishes_data)} dishes)")
    print(f"Generated {proc_dir / 'dish_ingredients_final.csv'} ({len(df_dish_ings)} rows)")


if __name__ == "__main__":
    build_dish_ingredient_tables(Path(__file__).resolve().parent.parent)
