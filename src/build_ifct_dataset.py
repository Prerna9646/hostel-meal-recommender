"""
build_ifct_dataset.py

Cleans and standardizes the IFCT 2017 raw nutritional dataset.
Converts energy from kJ to kcal (using 1 kcal = 4.184 kJ) and minerals from g to mg.
Resolves Group T zero-energy anomaly using FAO (2003) Atwater 9 kcal/g factor.
Derives standard dietary tags (VEGETARIAN, EGGETARIAN, NON_VEG).
"""

from pathlib import Path
import pandas as pd
import numpy as np


KJ_TO_KCAL_FACTOR: float = 4.184
G_TO_MG_FACTOR: float = 1000.0
ATWATER_FAT_KCAL_PER_G: float = 9.0  # FAO (2003) / Atwater general factor


def derive_dietary_tag(raw_tag: str) -> str:
    """Classifies food items into VEGETARIAN, EGGETARIAN, or NON_VEG from IFCT tags."""
    if not isinstance(raw_tag, str):
        return "VEGETARIAN"
    t = raw_tag.lower()
    if "nonveg" in t and "eggetarian" in t and "vegetarian" not in t:
        return "EGGETARIAN"
    elif "nonveg" in t:
        return "NON_VEG"
    return "VEGETARIAN"


def clean_ifct(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Transforms raw IFCT 2017 DataFrame into standardized scientific units."""
    clean_df = pd.DataFrame()
    clean_df["ifct_code"] = raw_df["code"].astype(str).str.strip()
    clean_df["food_name"] = raw_df["name"].astype(str).str.strip()
    clean_df["scientific_name"] = raw_df["scie"].fillna("").astype(str).str.strip()
    clean_df["food_group"] = raw_df["grup"].astype(str).str.strip()
    clean_df["dietary_tag"] = raw_df["tags"].apply(derive_dietary_tag)

    # Standard energy conversion: enerc is in kJ per 100g -> convert to kcal
    energy_kcal = raw_df["enerc"] / KJ_TO_KCAL_FACTOR

    # Anomaly resolution: Group T (Edible Oils and Fats) has enerc == 0 in raw file
    # Derive energy using Atwater fat factor: fatce * 9.0 kcal/g
    is_oil_group = clean_df["ifct_code"].str.startswith("T")
    is_zero_enerc = raw_df["enerc"] == 0
    oil_mask = is_oil_group & is_zero_enerc
    energy_kcal[oil_mask] = raw_df.loc[oil_mask, "fatce"] * ATWATER_FAT_KCAL_PER_G
    clean_df["energy_kcal_per_100g"] = energy_kcal.round(2)

    # Macronutrients in g per 100g
    clean_df["protein_g_per_100g"] = raw_df["protcnt"].round(2)
    clean_df["fat_g_per_100g"] = raw_df["fatce"].round(2)
    clean_df["carbohydrate_g_per_100g"] = raw_df["choavldf"].round(2)
    clean_df["fibre_g_per_100g"] = raw_df["fibtg"].round(2)

    # Minerals in g per 100g -> convert to mg per 100g
    clean_df["calcium_mg_per_100g"] = (raw_df["ca"] * G_TO_MG_FACTOR).round(2)
    clean_df["iron_mg_per_100g"] = (raw_df["fe"] * G_TO_MG_FACTOR).round(2)
    clean_df["potassium_mg_per_100g"] = (raw_df["k"] * G_TO_MG_FACTOR).round(2)
    clean_df["sodium_mg_per_100g"] = (raw_df["na"] * G_TO_MG_FACTOR).round(2)

    # Moisture content
    clean_df["water_g_per_100g"] = raw_df["water"].round(2)

    # Provenance source class
    clean_df["source_class"] = "IFCT_DERIVED"

    return clean_df


def main():
    root_dir = Path(__file__).resolve().parent.parent
    raw_path = root_dir / "data" / "raw" / "ifct_2017_original.csv"
    if not raw_path.exists():
        raw_path = root_dir / "ifct_2017_original.csv"

    out_dir = root_dir / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ifct_2017_clean.csv"

    print(f"Reading raw IFCT data from: {raw_path}")
    raw_df = pd.read_csv(raw_path, low_memory=False)

    print("Executing unit conversions and cleaning transformations...")
    clean_df = clean_ifct(raw_df)

    clean_df.to_csv(out_path, index=False)
    print(f"Successfully generated {out_path} ({len(clean_df)} rows, {len(clean_df.columns)} columns)")


if __name__ == "__main__":
    main()
