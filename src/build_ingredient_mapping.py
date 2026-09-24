"""
build_ingredient_mapping.py

Generates ingredient_mapping_final.csv and ingredient_nutrition_final.csv.
Reads canonical taxonomy from ingredient_master.csv and mappings from config/ingredient_mappings.yaml.
Extracts nutrient payloads from ifct_2017_clean.csv or cited external references.
Propagates NaN for unavailable commercial foods (never treats missing as zero).
"""

from pathlib import Path
import pandas as pd
import numpy as np
import yaml


EXTERNAL_NUTRITION_PAYLOADS = {
    "USDA_FDC_169655": {
        "food_group": "Sugars",
        "energy_kcal_per_100g": 387.0,
        "protein_g_per_100g": 0.0,
        "fat_g_per_100g": 0.0,
        "carbohydrate_g_per_100g": 99.96,
        "fibre_g_per_100g": 0.0,
        "potassium_mg_per_100g": 2.0,
        "sodium_mg_per_100g": 1.0,
        "calcium_mg_per_100g": 1.0,
        "iron_mg_per_100g": 0.05,
    },
    "USDA_FDC_173410": {
        "food_group": "Dairy",
        "energy_kcal_per_100g": 717.0,
        "protein_g_per_100g": 0.85,
        "fat_g_per_100g": 81.11,
        "carbohydrate_g_per_100g": 0.06,
        "fibre_g_per_100g": 0.0,
        "potassium_mg_per_100g": 24.0,
        "sodium_mg_per_100g": 643.0,
        "calcium_mg_per_100g": 24.0,
        "iron_mg_per_100g": 0.02,
    },
    "USDA_FDC_173449": {
        "food_group": "Dairy",
        "energy_kcal_per_100g": 321.0,
        "protein_g_per_100g": 7.91,
        "fat_g_per_100g": 8.70,
        "carbohydrate_g_per_100g": 54.40,
        "fibre_g_per_100g": 0.0,
        "potassium_mg_per_100g": 371.0,
        "sodium_mg_per_100g": 127.0,
        "calcium_mg_per_100g": 284.0,
        "iron_mg_per_100g": 0.19,
    },
    "USDA_FDC_172685": {
        "food_group": "Cereal",
        "energy_kcal_per_100g": 265.0,
        "protein_g_per_100g": 8.85,
        "fat_g_per_100g": 3.20,
        "carbohydrate_g_per_100g": 49.10,
        "fibre_g_per_100g": 2.70,
        "potassium_mg_per_100g": 115.0,
        "sodium_mg_per_100g": 491.0,
        "calcium_mg_per_100g": 260.0,
        "iron_mg_per_100g": 3.60,
    },
    "PROJECT_CULINARY_ASSUMPTION": {
        "food_group": "Spice",
        "energy_kcal_per_100g": 0.0,
        "protein_g_per_100g": 0.0,
        "fat_g_per_100g": 0.0,
        "carbohydrate_g_per_100g": 0.0,
        "fibre_g_per_100g": 0.0,
        "potassium_mg_per_100g": 0.0,
        "sodium_mg_per_100g": 0.0,
        "calcium_mg_per_100g": 0.0,
        "iron_mg_per_100g": 0.0,
    }
}


def build_mapping_datasets(root_dir: Path):
    clean_ifct = pd.read_csv(root_dir / "data" / "processed" / "ifct_2017_clean.csv")
    ifct_dict = clean_ifct.set_index("ifct_code").to_dict(orient="index")

    cfg_path = root_dir / "config" / "ingredient_mappings.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    mappings = cfg["mappings"]

    mapping_rows = []
    nutrition_rows = []

    for m in mappings:
        ing = m["ingredient"]
        norm_ing = ing.lower().replace(",", "").replace("/", " ").strip()
        code = str(m.get("ifct_code", "")).strip()
        status = m["mapping_status"]
        m_type = m["mapping_type"]
        conf = float(m["confidence"])
        src_type = m["source_type"]
        src_ref = m["source_reference"]
        notes = m.get("notes", "")

        ifct_name = ifct_dict[code]["food_name"] if code and code in ifct_dict else ""

        mapping_rows.append({
            "ingredient": ing,
            "normalized_ingredient": norm_ing,
            "ifct_code": code,
            "ifct_name": ifct_name,
            "mapping_status": status,
            "mapping_type": m_type,
            "confidence": conf,
            "source_type": src_type,
            "source_reference": src_ref,
            "notes": notes
        })

        # Build nutrition row
        nut_row = {
            "ingredient": ing,
            "ifct_code": code,
            "ifct_name": ifct_name,
            "food_group": "",
            "energy_kcal_per_100g": np.nan,
            "protein_g_per_100g": np.nan,
            "fat_g_per_100g": np.nan,
            "carbohydrate_g_per_100g": np.nan,
            "fibre_g_per_100g": np.nan,
            "potassium_mg_per_100g": np.nan,
            "sodium_mg_per_100g": np.nan,
            "calcium_mg_per_100g": np.nan,
            "iron_mg_per_100g": np.nan,
            "data_source": src_type,
            "source_reference": src_ref,
            "data_status": status,
            "notes": notes
        }

        if code and code in ifct_dict:
            row_data = ifct_dict[code]
            nut_row["food_group"] = row_data["food_group"]
            for col in ["energy_kcal_per_100g", "protein_g_per_100g", "fat_g_per_100g",
                        "carbohydrate_g_per_100g", "fibre_g_per_100g", "potassium_mg_per_100g",
                        "sodium_mg_per_100g", "calcium_mg_per_100g", "iron_mg_per_100g"]:
                nut_row[col] = row_data[col]
            nut_row["data_source"] = "IFCT_2017"
        elif src_ref in EXTERNAL_NUTRITION_PAYLOADS:
            payload = EXTERNAL_NUTRITION_PAYLOADS[src_ref]
            nut_row.update(payload)
            nut_row["data_source"] = "EXTERNAL_REFERENCE"
            nut_row["data_status"] = "VERIFIED" if "USDA" in src_ref else "ESTIMATED"
        else:
            nut_row["data_source"] = "UNAVAILABLE"
            nut_row["data_status"] = "UNAVAILABLE"

        nutrition_rows.append(nut_row)

    df_mapping = pd.DataFrame(mapping_rows)
    df_nutrition = pd.DataFrame(nutrition_rows)

    out_dir = root_dir / "data" / "processed"
    df_mapping.to_csv(out_dir / "ingredient_mapping_final.csv", index=False)
    df_nutrition.to_csv(out_dir / "ingredient_nutrition_final.csv", index=False)
    print(f"Generated {out_dir / 'ingredient_mapping_final.csv'} ({len(df_mapping)} rows)")
    print(f"Generated {out_dir / 'ingredient_nutrition_final.csv'} ({len(df_nutrition)} rows)")


if __name__ == "__main__":
    build_mapping_datasets(Path(__file__).resolve().parent.parent)
