"""
build_menu_dataset.py

Normalizes the raw mess menu dataset and classifies all 132 canonical dishes.
1. Normalizes dates to ISO YYYY-MM-DD.
2. Normalizes meal slots to BREAKFAST, LUNCH, DINNER, E_TEA.
3. Resolves Girls Hostel into facility schedule (hostel_scope='GIRLS_HOSTEL', normalized_meal='E_TEA').
4. Decomposes 11 compound menu rows into individual course rows.
5. Classifies all 132 canonical dishes into plate grammar roles and dietary tags.
Outputs data/processed/mess_menu_final.csv and data/processed/dish_classification_final.csv.
"""

from pathlib import Path
import pandas as pd
import yaml


PLATE_ROLES = {
    # Staples (18)
    "Chapati": "STAPLE", "Plain Rice": "STAPLE", "Jeera Rice": "STAPLE", "Veg Fried Rice": "STAPLE",
    "Veg Biryani": "STAPLE", "Poori": "STAPLE", "Stuffed Paratha": "STAPLE", "Poha": "STAPLE",
    "Khichdi": "STAPLE", "Sweet Dalia": "STAPLE", "Besan Chilla": "STAPLE", "Chole Bhature": "STAPLE",
    "Poori Aloo Chana": "STAPLE", "Pav Bhaji": "STAPLE", "Bread": "STAPLE", "Sandwich": "STAPLE",
    "Pink Sauce Pasta": "STAPLE", "Cornflakes": "STAPLE",
    # Dal & Protein Core (28)
    "Yellow Dal Tadka": "DAL_PROTEIN", "Chana Dal Tadka": "DAL_PROTEIN", "Chana Toor Dal": "DAL_PROTEIN",
    "Moong Dal": "DAL_PROTEIN", "Moong Sabut": "DAL_PROTEIN", "Malka Masoor": "DAL_PROTEIN",
    "Sabut Masoor": "DAL_PROTEIN", "Lobiya Dal": "DAL_PROTEIN", "Rajmah": "DAL_PROTEIN",
    "Black Chana": "DAL_PROTEIN", "White Chana": "DAL_PROTEIN", "Dal Makhani": "DAL_PROTEIN",
    "Black Dal Tadka": "DAL_PROTEIN", "Dhaba Dal": "DAL_PROTEIN", "Dal Maratha": "DAL_PROTEIN",
    "Dal Palak": "DAL_PROTEIN", "Mix Dal Amritsari": "DAL_PROTEIN", "Panchmail Dal": "DAL_PROTEIN",
    "Aloo Onion Kadhi": "DAL_PROTEIN", "Kadhi Pakora": "DAL_PROTEIN", "Amritsari Badi": "DAL_PROTEIN",
    "Boiled Egg": "DAL_PROTEIN", "Egg Curry": "DAL_PROTEIN", "Egg Bhurji": "DAL_PROTEIN",
    "Omelette": "DAL_PROTEIN", "Chicken Curry": "DAL_PROTEIN", "Butter Chicken": "DAL_PROTEIN",
    "Chicken Kolhapuri": "DAL_PROTEIN",
    # Gravy Sabzi / Curries (13)
    "Matar Paneer": "GRAVY_SABZI", "Kadhai Paneer": "GRAVY_SABZI", "Paneer Butter Masala": "GRAVY_SABZI",
    "Paneer Do Pyaza": "GRAVY_SABZI", "Paneer Kolhapuri": "GRAVY_SABZI", "Paneer Lababdar": "GRAVY_SABZI",
    "Paneer Chettinad": "GRAVY_SABZI", "Dum Aloo": "GRAVY_SABZI", "Dahi Aloo": "GRAVY_SABZI",
    "Veg Kofta Curry": "GRAVY_SABZI", "Veg Korma": "GRAVY_SABZI", "Nutry Masala": "GRAVY_SABZI",
    "Nutry Matar": "GRAVY_SABZI",
    # Dry Sabzi (19)
    "Aloo": "DRY_SABZI", "Aloo Bhaji": "DRY_SABZI", "Aloo Matar": "DRY_SABZI", "Aloo Capsicum": "DRY_SABZI",
    "Aloo Cabbage Matar": "DRY_SABZI", "Jeera Aloo": "DRY_SABZI", "Masala Aloo": "DRY_SABZI",
    "Gobhi Matar": "DRY_SABZI", "Gobhi Adraki": "DRY_SABZI", "Ghiya Masala": "DRY_SABZI",
    "Khata Mitha Kaddu": "DRY_SABZI", "Green Peas Masala": "DRY_SABZI", "Corn Peas Masala": "DRY_SABZI",
    "Palak Corn": "DRY_SABZI", "Mix Veg": "DRY_SABZI", "Kadhai Veg": "DRY_SABZI", "Veg Jaipuri": "DRY_SABZI",
    "Veg Jalfrazi": "DRY_SABZI", "Veg Manchurian": "DRY_SABZI",
    # Snacks (19)
    "Samosa": "SNACK", "Aloo Bonda": "SNACK", "Bread Pakora": "SNACK", "Mix Pakora": "SNACK",
    "Crispy Dal Kachori": "SNACK", "Mathi": "SNACK", "Namak Pare": "SNACK", "Jhal Muri": "SNACK",
    "Namkeen Seviyan": "SNACK", "Biscuit": "SNACK", "Chips": "SNACK", "Muffin": "SNACK",
    "Brownie": "SNACK", "Cream Roll": "SNACK", "Danish Bun": "SNACK", "Tea Cake": "SNACK",
    "Rusk": "SNACK", "Namkeen": "SNACK", "Fryums": "SNACK",
    # Desserts (11)
    "Gulab Jamun": "DESSERT", "Besan Ka Halwa": "DESSERT", "Halwa": "DESSERT", "Sabudana Kheer": "DESSERT",
    "Kesari Kheer": "DESSERT", "Vermicelli Payasam": "DESSERT", "Vermicelli Pudding with Condensed Milk": "DESSERT",
    "Coconut Laddu": "DESSERT", "Custard": "DESSERT", "Chocolate": "DESSERT", "Chocolate Pie": "DESSERT",
    # Beverages (4)
    "Milk": "BEVERAGE", "Tea": "BEVERAGE", "Coffee": "BEVERAGE", "Chaas": "BEVERAGE",
    # Accompaniments & Salads (20)
    "Green Salad": "ACCOMPANIMENT", "Cucumber Salad": "ACCOMPANIMENT", "Beetroot Cucumber Salad": "ACCOMPANIMENT",
    "Kachumber Salad": "ACCOMPANIMENT", "Chana Peanut Salad": "ACCOMPANIMENT", "Onion": "ACCOMPANIMENT",
    "Tomato": "ACCOMPANIMENT", "Green Chilli": "ACCOMPANIMENT", "Sirca Onion": "ACCOMPANIMENT",
    "Chutney": "ACCOMPANIMENT", "Plain Curd": "ACCOMPANIMENT", "Boondi Raita": "ACCOMPANIMENT",
    "Mix Raita": "ACCOMPANIMENT", "Jeera Raita": "ACCOMPANIMENT", "Mint Raita": "ACCOMPANIMENT",
    "Pickle": "ACCOMPANIMENT", "Tomato Ketchup": "ACCOMPANIMENT", "Jam": "ACCOMPANIMENT",
    "Fat Spread": "ACCOMPANIMENT", "Banana": "ACCOMPANIMENT"
}


def build_normalized_menu(menu_path: Path, synonyms_cfg: dict) -> pd.DataFrame:
    raw_menu = pd.read_csv(menu_path)
    c_map = synonyms_cfg.get("canonical_dish_mappings", {})
    s_map = synonyms_cfg.get("spelling_normalisations", {})
    comp = synonyms_cfg.get("compound_dish_decompositions", {})

    normalized_rows = []
    row_id = 1

    for _, row in raw_menu.iterrows():
        orig_date = str(row["date"]).strip()
        orig_meal = str(row["meal"]).strip()
        orig_dish = str(row["dish"]).strip()
        norm_date = pd.to_datetime(orig_date).strftime("%Y-%m-%d")

        if orig_meal == "Girls Hostel":
            norm_meal, scope, is_dessert = "E_TEA", "GIRLS_HOSTEL", False
        elif orig_meal == "E-Tea":
            norm_meal, scope, is_dessert = "E_TEA", "COMMON", False
        elif orig_meal == "Dessert":
            norm_meal, scope, is_dessert = "DINNER", "COMMON", True
        else:
            norm_meal, scope, is_dessert = orig_meal.upper(), "COMMON", False

        if orig_dish in comp:
            p_dish = comp[orig_dish]["primary_dish"]
            s_dish = comp[orig_dish]["secondary_dish"]
            for dish_name, split_type in [(p_dish, "COMPOUND_SPLIT_PRIMARY"), (s_dish, "COMPOUND_SPLIT_SECONDARY")]:
                normalized_rows.append({
                    "menu_row_id": row_id,
                    "original_date": orig_date,
                    "normalized_date": norm_date,
                    "original_meal": orig_meal,
                    "normalized_meal": norm_meal,
                    "hostel_scope": scope,
                    "original_dish": orig_dish,
                    "canonical_dish": dish_name,
                    "is_dessert_flag": is_dessert,
                    "provenance_notes": split_type
                })
                row_id += 1
        else:
            canon = c_map.get(orig_dish, s_map.get(orig_dish, orig_dish))
            prov = "CANONICAL_MAPPING" if orig_dish in c_map else ("SPELLING_NORMALISATION" if orig_dish in s_map else "DIRECT_MENU_ITEM")
            if is_dessert:
                prov += "_DESSERT_ATTACHED_TO_DINNER"
            normalized_rows.append({
                "menu_row_id": row_id,
                "original_date": orig_date,
                "normalized_date": norm_date,
                "original_meal": orig_meal,
                "normalized_meal": norm_meal,
                "hostel_scope": scope,
                "original_dish": orig_dish,
                "canonical_dish": canon,
                "is_dessert_flag": is_dessert,
                "provenance_notes": prov
            })
            row_id += 1

    return pd.DataFrame(normalized_rows)


def build_dish_classification(norm_menu: pd.DataFrame, dish_ings_path: Path) -> pd.DataFrame:
    dish_ings = pd.read_csv(dish_ings_path)
    all_dishes = sorted(norm_menu["canonical_dish"].unique())

    slot_map = norm_menu.groupby("canonical_dish")["normalized_meal"].unique().apply(lambda s: ",".join(sorted(list(set(s))))).to_dict()

    class_rows = []
    for dish in all_dishes:
        ings = set(dish_ings[dish_ings["dish"] == dish]["ingredient"])
        role = PLATE_ROLES.get(dish, "ACCOMPANIMENT")

        # Dietary tag inheritance
        if any("Chicken" in ing for ing in ings):
            tag = "NON_VEG"
        elif any("Egg" in ing for ing in ings):
            tag = "EGGETARIAN"
        else:
            tag = "VEGETARIAN"

        class_rows.append({
            "canonical_dish": dish,
            "plate_role": role,
            "dietary_tag": tag,
            "allowed_slots": slot_map.get(dish, "LUNCH,DINNER"),
            "source_class": "PROJECT_DESIGN_CHOICE"
        })

    return pd.DataFrame(class_rows)


def main():
    root_dir = Path(__file__).resolve().parent.parent
    menu_path = root_dir / "data" / "raw" / "mess_menu.csv"
    if not menu_path.exists():
        menu_path = root_dir / "mess_menu.csv"

    cfg_path = root_dir / "config" / "dish_synonyms.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        synonyms_cfg = yaml.safe_load(f)

    print("Building normalized mess menu...")
    norm_menu = build_normalized_menu(menu_path, synonyms_cfg)

    dish_ings_path = root_dir / "data" / "processed" / "dish_ingredients_final.csv"
    print("Building dish classification dataset...")
    dish_class = build_dish_classification(norm_menu, dish_ings_path)

    out_dir = root_dir / "data" / "processed"
    norm_menu.to_csv(out_dir / "mess_menu_final.csv", index=False)
    dish_class.to_csv(out_dir / "dish_classification_final.csv", index=False)

    print(f"Generated {out_dir / 'mess_menu_final.csv'} ({len(norm_menu)} rows)")
    print(f"Generated {out_dir / 'dish_classification_final.csv'} ({len(dish_class)} canonical dishes)")


if __name__ == "__main__":
    main()
