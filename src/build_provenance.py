"""
build_provenance.py

Generates metadata catalog tables in data/metadata/:
1. source_registry.csv: Formal bibliographic registry of all authoritative data sources.
2. data_provenance.csv: Column-level lineage and transformation tracking.
3. data_dictionary.csv: Exhaustive schema documentation for all 10 project datasets.
4. limitations.csv: Catalogued methodological and empirical limitations.
"""

from pathlib import Path
import pandas as pd


SOURCE_REGISTRY_DATA = [
    {
        "source_id": "SRC_IFCT2017_PUB",
        "source_name": "Indian Food Composition Tables 2017 (Print Publication)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://www.nin.res.in",
        "description": "Longvah, T., Ananthan, R., Bhaskarachary, K., & Venkaiah, K. (2017). Indian Food Composition Tables. National Institute of Nutrition (ICMR), Hyderabad. ISBN: 978-93-84570-00-5.",
        "used_for": "Primary nutritional densities, macronutrient mass fractions, and mineral analysis",
        "access_date": "2026-09-24",
        "notes": "Official comprehensive national food composition database for Indian foods"
    },
    {
        "source_id": "SRC_IFCT2017_REPO",
        "source_name": "IFCT 2017 Machine-Readable Dataset (nodef/ifct2017)",
        "source_type": "DATASET_REPOSITORY",
        "url": "https://github.com/nodef/ifct2017",
        "description": "Digitized comma-separated values distribution of IFCT 2017 tables (542 foods x 421 columns).",
        "used_for": "Raw data input for ifct_2017_original.csv",
        "access_date": "2026-09-24",
        "notes": "Supplied as project raw input; reconciled 542 rows against printed 528 food tables"
    },
    {
        "source_id": "SRC_ATWATER_FAO2003",
        "source_name": "FAO Food Energy Analysis and Conversion Factors (2003)",
        "source_type": "TECHNICAL_STANDARD",
        "url": "https://www.fao.org/4/y5022e/y5022e00.htm",
        "description": "FAO. (2003). Food energy - methods of analysis and conversion factors. FAO Food and Nutrition Paper 77, Rome. Chapter 3: Calculation of energy content of foods (fat = 9.0 kcal/g / 37 kJ/g).",
        "used_for": "Deriving energy for Group T edible oils and fats with raw 0 kJ defect",
        "access_date": "2026-09-24",
        "notes": "Authoritative international Atwater general energy factor standard"
    },
    {
        "source_id": "SRC_USDA_FDC",
        "source_name": "USDA FoodData Central (Selected Reference Foods)",
        "source_type": "EXTERNAL_DATABASE",
        "url": "https://fdc.nal.usda.gov",
        "description": "United States Department of Agriculture Agricultural Research Service FoodData Central (FDC IDs: 169655 Granulated sugar; 173410 Salted butter; 173449 Condensed milk; 172685 White bread).",
        "used_for": "Per-item external reference nutrient payloads for commercial items absent from IFCT",
        "access_date": "2026-09-24",
        "notes": "Used strictly on a per-item cited basis, never as an ungrounded default"
    },
    {
        "source_id": "SRC_HOSTEL_MENU",
        "source_name": "Institutional Hostel Mess Menu (October 2026)",
        "source_type": "INSTITUTIONAL_DATA",
        "url": "LOCAL_WORKSPACE:mess_menu.csv",
        "description": "Real operational mess menu spanning 31 days (October 1 to October 31, 2026) across 624 service rows.",
        "used_for": "Daily meal scheduling, meal slots, and candidate dish availability",
        "access_date": "2026-09-24",
        "notes": "Authoritative institutional schedule of served dishes"
    },
    {
        "source_id": "SRC_PROJECT_PORTIONS",
        "source_name": "Project Standardized Raw Portion Model",
        "source_type": "PROJECT_ASSUMPTION",
        "url": "LOCAL_CONFIG:config/dish_templates.yaml",
        "description": "Standardized raw-ingredient-gram issuance weights per single student serving (e.g., 30g atta/chapati, 50g raw rice, 30g pulse/dal, 5g cooking fat).",
        "used_for": "Decomposing 132 canonical dishes into raw ingredient gram quantities",
        "access_date": "2026-09-24",
        "notes": "Explicitly classified as modeling assumptions, not measured institutional recipes"
    },
    {
        "source_id": "SRC_MISRA_2009",
        "source_name": "Asian Indian Obesity Consensus Guidelines (Misra et al., 2009)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://pubmed.ncbi.nlm.nih.gov/19582986/",
        "description": "Misra, A., Chowbey, P., Makkar, B. M., Vikram, N. K., Wasir, J. S., Chadha, D., et al. (2009). Consensus statement for diagnosis of obesity, abdominal obesity and the metabolic syndrome for Asian Indians. JAPI, 57(2), 163-170.",
        "used_for": "Asian Indian BMI cut-offs (<18.5 Underweight, 18.5-22.9 Normal, 23.0-24.9 Overweight, >=25.0 Obese)",
        "access_date": "2026-09-24",
        "notes": "Authoritative national clinical consensus addressing lower BMI threshold for adiposity-related cardiometabolic risk in Asian Indians"
    },
    {
        "source_id": "SRC_WHO_2000",
        "source_name": "WHO International BMI Classification (2000 / 2004)",
        "source_type": "TECHNICAL_STANDARD",
        "url": "https://www.who.int/publications/i/item/9241208945",
        "description": "WHO. (2000). Obesity: preventing and managing the global epidemic. WHO Technical Report Series 894; WHO Expert Consultation. (2004). Appropriate body-mass index for Asian populations. Lancet, 363(9403), 157-163.",
        "used_for": "International reference BMI cut-offs (<18.5, 18.5-24.9, 25.0-29.9, >=30.0)",
        "access_date": "2026-09-24",
        "notes": "Global comparative benchmark standard"
    },
    {
        "source_id": "SRC_ICMR_NIN_2020",
        "source_name": "Nutrient Requirements for Indians: Recommended Dietary Allowances and Estimated Average Requirements (ICMR-NIN 2020)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://www.nin.res.in",
        "description": "ICMR-National Institute of Nutrition. (2020). Nutrient Requirements for Indians: A Report of the Expert Group. Hyderabad: ICMR-NIN. Reference weights: Men 65kg, Women 55kg. Protein: 0.83 g/kg/d; Fibre: 30g/2000kcal; Calcium: 1000mg/d; Iron: Men 19mg/d, Women 29mg/d; Sodium: 2000mg/d; Potassium: 3500mg/d.",
        "used_for": "Personalized daily nutritional targets, macronutrient distributions, mineral requirements, and PAL energy calculations",
        "access_date": "2026-09-24",
        "notes": "National statutory dietary guideline for Indian population"
    },
    {
        "source_id": "SRC_MIFFLIN_1990",
        "source_name": "Mifflin-St Jeor Resting Energy Expenditure Equation (1990)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://pubmed.ncbi.nlm.nih.gov/2305711/",
        "description": "Mifflin, M. D., St Jeor, S. T., Hill, L. A., Scott, B. J., Daugherty, S. A., & Koh, Y. O. (1990). A new predictive equation for resting energy expenditure in healthy individuals. The American Journal of Clinical Nutrition, 51(2), 241-247.",
        "used_for": "Basal Metabolic Rate (BMR) prediction from student weight, height, age, and sex",
        "access_date": "2026-09-24",
        "notes": "Clinically established as the most reliable resting metabolic rate predictive equation"
    },
    {
        "source_id": "SRC_ICMR_DIAB_2018",
        "source_name": "ICMR Guidelines for Management of Type 2 Diabetes (2018)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://www.icmr.gov.in",
        "description": "Indian Council of Medical Research. (2018). ICMR Guidelines for Management of Type 2 Diabetes. New Delhi: ICMR. Medical Nutrition Therapy (MNT): free sugar restriction, deep-fried food elimination, complex carbohydrate prioritization.",
        "used_for": "Clinical dietary constraint rules for diabetic students (dessert exclusion, fried snack penalty)",
        "access_date": "2026-09-24",
        "notes": "Authoritative national clinical management guideline"
    },
    {
        "source_id": "SRC_IHG_IV_2019",
        "source_name": "Indian Hypertension Guidelines-IV (IHG-IV 2019)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://www.japi.org",
        "description": "Association of Physicians of India. (2019). Indian Hypertension Guidelines-IV. JAPI. Dietary sodium reduction (<2000mg/d), avoidance of preserved high-salt pickles and packaged snacks, adequate potassium promotion.",
        "used_for": "Clinical dietary constraint rules for hypertensive students (pickle exclusion, packaged snack penalty)",
        "access_date": "2026-09-24",
        "notes": "National clinical consensus for hypertension management"
    },
    {
        "source_id": "SRC_PCOS_2023",
        "source_name": "International Evidence-based Guideline for Assessment and Management of PCOS (2023)",
        "source_type": "PRIMARY_LITERATURE",
        "url": "https://doi.org/10.1016/j.fertnstert.2023.07.025",
        "description": "Teede, H. J., et al. (2023). Recommendations from the 2023 international evidence-based guideline for the assessment and management of polycystic ovary syndrome. Fertility and Sterility, 120(4), 767-793.",
        "used_for": "Dietary rules for PCOS (simple sugar restriction, refuting arbitrary dairy elimination)",
        "access_date": "2026-09-24",
        "notes": "Global multi-society clinical guideline for PCOS"
    }
]

PROVENANCE_DATA = [
    {"dataset": "ifct_2017_clean.csv", "column_or_value": "energy_kcal_per_100g", "source_type": "IFCT_DERIVED", "source": "SRC_IFCT2017_REPO", "source_url": "https://github.com/nodef/ifct2017", "method": "enerc (kJ) / 4.184; Group T fatce * 9.0 kcal/g", "notes": "Converted from kJ to kcal; oils resolved via FAO 2003 Atwater factor"},
    {"dataset": "ifct_2017_clean.csv", "column_or_value": "calcium_mg_per_100g", "source_type": "IFCT_DERIVED", "source": "SRC_IFCT2017_REPO", "source_url": "https://github.com/nodef/ifct2017", "method": "ca (g) * 1000.0", "notes": "Converted from g/100g to mg/100g"},
    {"dataset": "ifct_2017_clean.csv", "column_or_value": "dietary_tag", "source_type": "IFCT_DERIVED", "source": "SRC_IFCT2017_REPO", "source_url": "https://github.com/nodef/ifct2017", "method": "Derived from tags string", "notes": "Mapped to VEGETARIAN (328), EGGETARIAN (15), NON_VEG (199)"},
    {"dataset": "ingredient_master.csv", "column_or_value": "canonical_ingredient_name", "source_type": "DERIVED", "source": "SRC_HOSTEL_MENU", "source_url": "LOCAL_WORKSPACE:mess_menu.csv", "method": "Culinary decomposition of 153 menu dishes", "notes": "80 canonical raw ingredients"},
    {"dataset": "dish_ingredients_final.csv", "column_or_value": "quantity_g", "source_type": "PROJECT_ASSUMPTION", "source": "SRC_PROJECT_PORTIONS", "source_url": "LOCAL_CONFIG:config/dish_templates.yaml", "method": "Standardized raw-ingredient-gram issuance per single serving", "notes": "No cooked weight; 5g oil uniform assumption"},
    {"dataset": "dish_nutrition_final.csv", "column_or_value": "energy_kcal", "source_type": "DERIVED", "source": "SRC_IFCT2017_PUB", "source_url": "https://www.nin.res.in", "method": "sum((quantity_g / 100) * energy_kcal_per_100g)", "notes": "Propagates NaN for INSUFFICIENT_DATA dishes"},
    {"dataset": "dish_nutrition_final.csv", "column_or_value": "sodium_mg", "source_type": "IFCT_DERIVED", "source": "SRC_IFCT2017_PUB", "source_url": "https://www.nin.res.in", "method": "sum((quantity_g / 100) * sodium_mg_per_100g)", "notes": "Strict lower bound: natural food sodium only; excludes added table salt"},
    {"dataset": "mess_menu_final.csv", "column_or_value": "normalized_meal", "source_type": "DERIVED", "source": "SRC_HOSTEL_MENU", "source_url": "LOCAL_WORKSPACE:mess_menu.csv", "method": "Canonical slot normalization; Girls Hostel -> E_TEA (scope=GIRLS_HOSTEL)", "notes": "4 canonical slots"},
    {"dataset": "dish_classification_final.csv", "column_or_value": "plate_role", "source_type": "PROJECT_DESIGN_CHOICE", "source": "SRC_PROJECT_PORTIONS", "source_url": "LOCAL_CONFIG:config/dish_templates.yaml", "method": "Plate grammar role taxonomy (STAPLE, DAL_PROTEIN, etc.)", "notes": "8 plate grammar roles"},
    {"dataset": "bmi_rules.csv", "column_or_value": "min_bmi,max_bmi", "source_type": "PRIMARY_LITERATURE", "source": "SRC_MISRA_2009", "source_url": "https://pubmed.ncbi.nlm.nih.gov/19582986/", "method": "Consensus cut-offs (<18.5, 18.5-22.9, 23.0-24.9, >=25.0)", "notes": "Official Asian Indian consensus guideline"},
    {"dataset": "rda_targets.csv", "column_or_value": "energy_kcal,protein_g,minerals", "source_type": "PRIMARY_LITERATURE", "source": "SRC_ICMR_NIN_2020", "source_url": "https://www.nin.res.in", "method": "ICMR-NIN 2020 reference tables", "notes": "Official adult RDA and PAL reference matrix"},
    {"dataset": "health_rules.csv", "column_or_value": "action,status", "source_type": "PRIMARY_LITERATURE", "source": "SRC_ICMR_DIAB_2018", "source_url": "https://www.icmr.gov.in", "method": "Clinical guidelines filter engine; ungrounded rules DISABLED_UNSOURCED", "notes": "16 clinical rules (11 active, 5 disabled)"},
    {"dataset": "canteen_extras.csv", "column_or_value": "price_inr,energy_kcal", "source_type": "DERIVED", "source": "SRC_IFCT2017_PUB", "source_url": "https://www.nin.res.in", "method": "Budget knapsack optimization using strictly verified IFCT nutrient items", "notes": "8 verified canteen items with verified non-NaN nutrition"}
]

LIMITATIONS_DATA = [
    {
        "limitation_id": "LIM_001",
        "limitation": "Omission of Cooking Moisture Retention Factors",
        "affected_component": "Dish Nutrition Aggregation",
        "reason": "IFCT 2017 records raw edible portion densities; institution-specific water evaporation and cooking yields vary by simmer duration.",
        "impact": "Dish serving weights reflect raw commodity inputs rather than cooked wet plate mass.",
        "mitigation": "Strict raw-ingredient-gram basis maintained across all dishes; avoids synthetic yield errors.",
        "paper_wording": "Nutritional calculations were modeled strictly on a raw-ingredient-gram basis per serving. While cooking alters water content, raw commodity aggregation avoids unvalidated yield assumptions."
    },
    {
        "limitation_id": "LIM_002",
        "limitation": "Sodium Underestimation (Lower Bound Only)",
        "affected_component": "Micronutrient Profiling & Hypertension Rules",
        "reason": "Hostel kitchen culinary salt addition (NaCl) is unstandardized and unrecorded in menu text.",
        "impact": "Reported sodium represents intrinsic biological sodium only, underestimating actual sodium intake.",
        "mitigation": "Sodium is explicitly badged as a strict lower bound in the UI; sodium-based penalty scoring is disabled.",
        "paper_wording": "Sodium calculations reflect natural biological ingredient content only. Added cooking salt could not be measured, so sodium values represent a strict lower bound."
    },
    {
        "limitation_id": "LIM_003",
        "limitation": "Standardized Serving Weight Assumptions",
        "affected_component": "Dish Portions",
        "reason": "Actual ladle and katori portions served to students fluctuate with cafeteria server discretion.",
        "impact": "Absolute caloric intake per student may vary by +/- 15% based on physical serving size.",
        "mitigation": "All portions are version-controlled in YAML and classified as PROJECT_ASSUMPTION; sensitivity analysis planned.",
        "paper_wording": "Where exact institutional ladle measures were unavailable, standardized portion weights were established as modeling assumptions and not treated as measured recipe data."
    },
    {
        "limitation_id": "LIM_004",
        "limitation": "Absence of Generic IFCT Profiles for Packaged Snacks",
        "affected_component": "Canteen & Evening Tea Nutrition",
        "reason": "IFCT 2017 is an agricultural database that does not analyze ultra-processed branded commercial products (chips, biscuits).",
        "impact": "17 commercial canteen snacks cannot be scored for macronutrient proximity.",
        "mitigation": "Packaged items propagate NaN and carry INSUFFICIENT_DATA badges, showing availability without corrupting nutrition scores.",
        "paper_wording": "Commercial packaged bakery snacks lacking generic IFCT records were classified as INSUFFICIENT_DATA and excluded from numeric ranking to avoid arbitrary nutrient guessing."
    },
    {
        "limitation_id": "LIM_005",
        "limitation": "Unverified Statistical Spread in Repository Companion Columns",
        "affected_component": "Nutritional Confidence Intervals",
        "reason": "The digitized nodef/ifct2017 repository titles analytical variance columns as _e without specifying SD vs SE.",
        "impact": "Confidence interval bands cannot be reliably computed without risking false statistical precision.",
        "mitigation": "Companion _e columns are classified as UNVERIFIED_STATISTICAL_SPREAD and omitted from scoring.",
        "paper_wording": "Companion variance columns in the digitized repository were flagged as unverified statistical spread and excluded from interval claims."
    },
    {
        "limitation_id": "LIM_006",
        "limitation": "Absence of Core Pulse/Protein in Institutional Sunday Special Lunch",
        "affected_component": "Plate Grammar Assembly & Lunch Scheduling",
        "reason": "Real institutional mess schedules a celebratory Sunday lunch (Veg Biryani + Dum Aloo + Mix Raita + Salad + Chapati) that completely omits a standalone legume, pulse, or dal curry (DAL_PROTEIN).",
        "impact": "Plate grammar strictly requires a DAL_PROTEIN core for lunch, causing all 5 personas to encounter a NO_VALID_COMBINATION fallback on all 4 Sundays (explaining the 96.8% success rate and 0.0% CVR).",
        "mitigation": "Recommender triggers graceful fallback state diagnosing the structural protein deficit and recommending canteen protein addition (Boiled Egg or Curd) or kitchen substitution.",
        "paper_wording": "Institutional menus occasionally feature composite celebratory meals that lack foundational macro-components (e.g. absence of a dedicated pulse core in Sunday biryani lunches). Rather than relaxing nutritional grammar to force an incomplete thali, the system activates a formal fallback state, diagnosing the structural protein deficit and recommending targeted canteen supplementation."
    },
    {
        "limitation_id": "LIM_007",
        "limitation": "Institutional Single-Portion Ceiling for High-PAL Varsity Athletes",
        "affected_component": "Energy Target Alignment for High-Activity Personas",
        "reason": "Institutional mess portion issuance is calibrated for sedentary university students (~2,100 kcal/day across 4 slots), delivering an empirical average of ~1,391 kcal/day in single portions.",
        "impact": "For a varsity athlete requiring ~3,700 kcal/day (PAL 2.20 + underweight surplus), purchasing 1-2 canteen extras cannot bridge a ~2,100 kcal structural deficit.",
        "mitigation": "System honestly reports the structural issuance ceiling rather than falsifying single-portion nutritional density; recommends multi-serving staple quotas (4-6 chapatis / double rice) at issuance counters.",
        "paper_wording": "Standard single-serving institutional issuance cannot satisfy the energetic requirements of high-PAL varsity athletes requiring >3,500 kcal/day. The system explicitly discloses this structural deficit, demonstrating that athletic nutritional support requires multi-serving staple scaling at the counter rather than reliance on discretionary snacks alone."
    }
]

DATA_DICTIONARY_DATA = [
    # 1. ifct_2017_clean.csv (16 columns)
    {"dataset": "ifct_2017_clean.csv", "column": "ifct_code", "description": "Unique alphanumeric food identifier from IFCT 2017", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "A001-T014", "notes": "Primary Key"},
    {"dataset": "ifct_2017_clean.csv", "column": "food_name", "description": "Standardized English food name", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "String", "notes": "From IFCT name"},
    {"dataset": "ifct_2017_clean.csv", "column": "scientific_name", "description": "Binomial botanical / zoological name", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "String", "notes": "From IFCT scie"},
    {"dataset": "ifct_2017_clean.csv", "column": "food_group", "description": "NIN-ICMR biological food group classification", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "20 groups (A-T)", "notes": "From IFCT grup"},
    {"dataset": "ifct_2017_clean.csv", "column": "dietary_tag", "description": "Dietary lifestyle classification", "unit": "dimensionless", "source_type": "IFCT_DERIVED", "allowed_values": "VEGETARIAN, EGGETARIAN, NON_VEG", "notes": "Derived from tags"},
    {"dataset": "ifct_2017_clean.csv", "column": "energy_kcal_per_100g", "description": "Metabolizable energy density", "unit": "kcal/100g", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "kJ / 4.184; oils via Atwater fat factor 9 kcal/g"},
    {"dataset": "ifct_2017_clean.csv", "column": "protein_g_per_100g", "description": "Total protein content", "unit": "g/100g", "source_type": "IFCT_DIRECT", "allowed_values": ">= 0.0", "notes": "Kjeldahl crude protein"},
    {"dataset": "ifct_2017_clean.csv", "column": "fat_g_per_100g", "description": "Total crude fat content", "unit": "g/100g", "source_type": "IFCT_DIRECT", "allowed_values": ">= 0.0", "notes": "Mixed solvent extraction"},
    {"dataset": "ifct_2017_clean.csv", "column": "carbohydrate_g_per_100g", "description": "Available carbohydrates by difference", "unit": "g/100g", "source_type": "IFCT_DIRECT", "allowed_values": ">= 0.0", "notes": "Excludes dietary fibre"},
    {"dataset": "ifct_2017_clean.csv", "column": "fibre_g_per_100g", "description": "Total dietary fibre", "unit": "g/100g", "source_type": "IFCT_DIRECT", "allowed_values": ">= 0.0", "notes": "Enzymatic-gravimetric method"},
    {"dataset": "ifct_2017_clean.csv", "column": "calcium_mg_per_100g", "description": "Elemental calcium content", "unit": "mg/100g", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "Converted from g/100g * 1000"},
    {"dataset": "ifct_2017_clean.csv", "column": "iron_mg_per_100g", "description": "Elemental iron content", "unit": "mg/100g", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "Converted from g/100g * 1000"},
    {"dataset": "ifct_2017_clean.csv", "column": "potassium_mg_per_100g", "description": "Elemental potassium content", "unit": "mg/100g", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "Converted from g/100g * 1000"},
    {"dataset": "ifct_2017_clean.csv", "column": "sodium_mg_per_100g", "description": "Elemental sodium content", "unit": "mg/100g", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "Converted from g/100g * 1000"},
    {"dataset": "ifct_2017_clean.csv", "column": "water_g_per_100g", "description": "Moisture content", "unit": "g/100g", "source_type": "IFCT_DIRECT", "allowed_values": ">= 0.0", "notes": "Moisture by drying"},
    {"dataset": "ifct_2017_clean.csv", "column": "source_class", "description": "Data provenance classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "IFCT_DERIVED", "notes": "Provenance tracking"},

    # 2. ingredient_master.csv (4 columns)
    {"dataset": "ingredient_master.csv", "column": "ingredient_id", "description": "Unique canonical ingredient identifier (ING_001 - ING_080)", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "ING_XXX", "notes": "Primary Key"},
    {"dataset": "ingredient_master.csv", "column": "canonical_ingredient_name", "description": "Standardized canonical commodity name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Unique commodity label"},
    {"dataset": "ingredient_master.csv", "column": "category", "description": "Domain food category", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "Cereal, Pulse, Vegetable, Fruit, Dairy, Poultry, Egg, Fat/Oil, Spice, Nut/Seed, Sweetener, Commercial", "notes": "Taxonomy"},
    {"dataset": "ingredient_master.csv", "column": "source_class", "description": "Data provenance classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "DERIVED", "notes": "Provenance tracking"},

    # 3. ingredient_mapping_final.csv (10 columns)
    {"dataset": "ingredient_mapping_final.csv", "column": "ingredient", "description": "Canonical ingredient name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Foreign Key to ingredient_master"},
    {"dataset": "ingredient_mapping_final.csv", "column": "normalized_ingredient", "description": "Normalized lowercase tokenized string", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Search key"},
    {"dataset": "ingredient_mapping_final.csv", "column": "ifct_code", "description": "Target IFCT 2017 food code", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "A001-T014 or empty", "notes": "Foreign Key to clean IFCT"},
    {"dataset": "ingredient_mapping_final.csv", "column": "ifct_name", "description": "Matching food name from IFCT", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "String or empty", "notes": "IFCT name"},
    {"dataset": "ingredient_mapping_final.csv", "column": "mapping_status", "description": "Validation level of the mapping", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "VERIFIED, APPROXIMATE, UNMAPPED", "notes": "Quality badge"},
    {"dataset": "ingredient_mapping_final.csv", "column": "mapping_type", "description": "Semantic relationship type", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "DIRECT, SYNONYM, VARIETY, FOOD_FORM, INGREDIENT_FORM, EXTERNAL, UNAVAILABLE", "notes": "Ontology link"},
    {"dataset": "ingredient_mapping_final.csv", "column": "confidence", "description": "Mapping confidence score", "unit": "score (0.0 - 1.0)", "source_type": "DERIVED", "allowed_values": "0.0 to 1.0", "notes": "Subjective/audit confidence"},
    {"dataset": "ingredient_mapping_final.csv", "column": "source_type", "description": "Source origin classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "IFCT_DIRECT, IFCT_DERIVED, EXTERNAL_REFERENCE, PROJECT_ASSUMPTION, UNAVAILABLE", "notes": "Contract class"},
    {"dataset": "ingredient_mapping_final.csv", "column": "source_reference", "description": "Exact citation identifier or document code", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "Citation string", "notes": "Traceability"},
    {"dataset": "ingredient_mapping_final.csv", "column": "notes", "description": "Qualitative explanatory notes on the mapping decision", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Audit notes"},

    # 4. ingredient_nutrition_final.csv (17 columns)
    {"dataset": "ingredient_nutrition_final.csv", "column": "ingredient", "description": "Canonical ingredient name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Primary Key"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "ifct_code", "description": "Linked IFCT code", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "A001-T014 or empty", "notes": "Foreign Key"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "ifct_name", "description": "Linked IFCT food name", "unit": "dimensionless", "source_type": "IFCT_DIRECT", "allowed_values": "String or empty", "notes": "Reference label"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "food_group", "description": "Nutritional food group", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Group"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "energy_kcal_per_100g", "description": "Energy density", "unit": "kcal/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "protein_g_per_100g", "description": "Protein density", "unit": "g/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "fat_g_per_100g", "description": "Fat density", "unit": "g/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "carbohydrate_g_per_100g", "description": "Carbohydrate density", "unit": "g/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "fibre_g_per_100g", "description": "Dietary fibre density", "unit": "g/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "potassium_mg_per_100g", "description": "Potassium density", "unit": "mg/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "sodium_mg_per_100g", "description": "Sodium density", "unit": "mg/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "calcium_mg_per_100g", "description": "Calcium density", "unit": "mg/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "iron_mg_per_100g", "description": "Iron density", "unit": "mg/100g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for UNAVAILABLE"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "data_source", "description": "Authoritative database providing data", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "IFCT_2017, EXTERNAL_REFERENCE, UNAVAILABLE", "notes": "Provenance"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "source_reference", "description": "Bibliographic reference code", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "Citation string", "notes": "Citation"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "data_status", "description": "Validation status", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "VERIFIED, APPROXIMATE, ESTIMATED, UNAVAILABLE", "notes": "Status"},
    {"dataset": "ingredient_nutrition_final.csv", "column": "notes", "description": "Explanatory notes", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Notes"},

    # 5. dish_ingredients_final.csv (9 columns)
    {"dataset": "dish_ingredients_final.csv", "column": "dish", "description": "Canonical dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "132 canonical dishes", "notes": "Composite Key"},
    {"dataset": "dish_ingredients_final.csv", "column": "ingredient", "description": "Canonical ingredient name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "80 canonical ingredients", "notes": "Composite Key"},
    {"dataset": "dish_ingredients_final.csv", "column": "quantity_g", "description": "Raw ingredient weight per single serving", "unit": "g", "source_type": "PROJECT_ASSUMPTION", "allowed_values": "> 0.0", "notes": "Raw commodity weight"},
    {"dataset": "dish_ingredients_final.csv", "column": "quantity_basis", "description": "Basis of measurement", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "RAW_INGREDIENT_GRAM_PER_SERVING", "notes": "No cooked weight"},
    {"dataset": "dish_ingredients_final.csv", "column": "source_type", "description": "Source provenance classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PROJECT_ASSUMPTION", "notes": "Modeling assumption"},
    {"dataset": "dish_ingredients_final.csv", "column": "source_reference", "description": "Reference catalog identifier", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PROJECT_PORTION_ASSUMPTIONS", "notes": "Citation"},
    {"dataset": "dish_ingredients_final.csv", "column": "mapping_status", "description": "Ingredient mapping status", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "VERIFIED, APPROXIMATE, UNMAPPED", "notes": "Propagated status"},
    {"dataset": "dish_ingredients_final.csv", "column": "confidence", "description": "Mapping confidence score", "unit": "score (0.0 - 1.0)", "source_type": "DERIVED", "allowed_values": "0.0 to 1.0", "notes": "Confidence"},
    {"dataset": "dish_ingredients_final.csv", "column": "notes", "description": "Culinary role of the ingredient in the dish", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Recipe explanation"},

    # 6. portion_assumptions.csv (8 columns)
    {"dataset": "portion_assumptions.csv", "column": "dish", "description": "Canonical dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Dish"},
    {"dataset": "portion_assumptions.csv", "column": "ingredient", "description": "Canonical ingredient name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Ingredient"},
    {"dataset": "portion_assumptions.csv", "column": "quantity_g", "description": "Raw portion quantity", "unit": "g", "source_type": "PROJECT_ASSUMPTION", "allowed_values": "> 0.0", "notes": "Grams"},
    {"dataset": "portion_assumptions.csv", "column": "basis", "description": "Portion basis", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "RAW_INGREDIENT_GRAM_PER_SERVING", "notes": "Raw basis"},
    {"dataset": "portion_assumptions.csv", "column": "source", "description": "Assumption source reference", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PROJECT_PORTION_ASSUMPTIONS", "notes": "Source"},
    {"dataset": "portion_assumptions.csv", "column": "source_type", "description": "Provenance classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PROJECT_ASSUMPTION", "notes": "Class"},
    {"dataset": "portion_assumptions.csv", "column": "reason", "description": "Culinary modeling rationale", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Reason"},
    {"dataset": "portion_assumptions.csv", "column": "notes", "description": "Additional descriptive notes", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Notes"},

    # 7. dish_nutrition_final.csv (14 columns)
    {"dataset": "dish_nutrition_final.csv", "column": "dish", "description": "Canonical dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "132 canonical dishes", "notes": "Primary Key"},
    {"dataset": "dish_nutrition_final.csv", "column": "serving_size_g", "description": "Total raw ingredient weight per single serving", "unit": "g", "source_type": "PROJECT_ASSUMPTION", "allowed_values": "> 0.0", "notes": "Raw commodity sum"},
    {"dataset": "dish_nutrition_final.csv", "column": "ingredient_count", "description": "Number of distinct ingredients", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 1", "notes": "Count"},
    {"dataset": "dish_nutrition_final.csv", "column": "data_coverage_percent", "description": "Percentage of ingredients mapped", "unit": "%", "source_type": "DERIVED", "allowed_values": "0.0 - 100.0", "notes": "Coverage"},
    {"dataset": "dish_nutrition_final.csv", "column": "calculation_status", "description": "Completeness classification status", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "COMPLETE_IFCT, ASSUMPTION_INCLUDED, EXTERNAL_DATA_INCLUDED, PARTIAL_IFCT, INSUFFICIENT_DATA", "notes": "Badge"},
    {"dataset": "dish_nutrition_final.csv", "column": "energy_kcal", "description": "Serving energy", "unit": "kcal", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "NaN for INSUFFICIENT_DATA"},
    {"dataset": "dish_nutrition_final.csv", "column": "protein_g", "description": "Serving protein", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Protein"},
    {"dataset": "dish_nutrition_final.csv", "column": "fat_g", "description": "Serving fat", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Fat"},
    {"dataset": "dish_nutrition_final.csv", "column": "carbohydrate_g", "description": "Serving carbohydrate", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Carbohydrate"},
    {"dataset": "dish_nutrition_final.csv", "column": "fibre_g", "description": "Serving dietary fibre", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Fibre"},
    {"dataset": "dish_nutrition_final.csv", "column": "potassium_mg", "description": "Serving potassium", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Potassium"},
    {"dataset": "dish_nutrition_final.csv", "column": "sodium_mg", "description": "Serving sodium (intrinsic biological only)", "unit": "mg", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Strict lower bound"},
    {"dataset": "dish_nutrition_final.csv", "column": "calcium_mg", "description": "Serving calcium", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Calcium"},
    {"dataset": "dish_nutrition_final.csv", "column": "iron_mg", "description": "Serving iron", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0 or NaN", "notes": "Iron"},

    # 8. dish_nutrition_coverage.csv (8 columns)
    {"dataset": "dish_nutrition_coverage.csv", "column": "dish", "description": "Canonical dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Primary Key"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "total_ingredients", "description": "Total ingredients in recipe", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 1", "notes": "Count"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "mapped_ingredients", "description": "Count of mapped ingredients", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 0", "notes": "Mapped"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "unmapped_ingredients", "description": "Count of unmapped ingredients", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 0", "notes": "Unmapped"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "ifct_coverage_percent", "description": "Coverage percentage", "unit": "%", "source_type": "DERIVED", "allowed_values": "0.0 - 100.0", "notes": "Coverage"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "assumption_count", "description": "Count of approximate assumptions", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 0", "notes": "Assumptions"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "external_data_count", "description": "Count of external reference items", "unit": "count", "source_type": "DERIVED", "allowed_values": ">= 0", "notes": "External"},
    {"dataset": "dish_nutrition_coverage.csv", "column": "calculation_status", "description": "Status badge", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "COMPLETE_IFCT, ASSUMPTION_INCLUDED, EXTERNAL_DATA_INCLUDED, PARTIAL_IFCT, INSUFFICIENT_DATA", "notes": "Status"},

    # 9. mess_menu_final.csv (10 columns)
    {"dataset": "mess_menu_final.csv", "column": "menu_row_id", "description": "Synthetic primary key for normalized menu entries", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "1 - 635", "notes": "Primary Key"},
    {"dataset": "mess_menu_final.csv", "column": "original_date", "description": "Pristine raw date string from mess_menu.csv", "unit": "dimensionless", "source_type": "INSTITUTIONAL_DATA", "allowed_values": "String", "notes": "Provenance"},
    {"dataset": "mess_menu_final.csv", "column": "normalized_date", "description": "Standardized ISO calendar date", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "2026-10-01 to 2026-10-31", "notes": "ISO YYYY-MM-DD"},
    {"dataset": "mess_menu_final.csv", "column": "original_meal", "description": "Pristine raw meal slot string from mess_menu.csv", "unit": "dimensionless", "source_type": "INSTITUTIONAL_DATA", "allowed_values": "Lunch, Breakfast, Dinner, E-Tea, Girls Hostel, Dessert", "notes": "Provenance"},
    {"dataset": "mess_menu_final.csv", "column": "normalized_meal", "description": "Standardized operational meal slot", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "BREAKFAST, LUNCH, DINNER, E_TEA", "notes": "Operational slot"},
    {"dataset": "mess_menu_final.csv", "column": "hostel_scope", "description": "Dining facility applicability scope", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "COMMON, GIRLS_HOSTEL", "notes": "Facility filter"},
    {"dataset": "mess_menu_final.csv", "column": "original_dish", "description": "Pristine raw dish string from mess_menu.csv", "unit": "dimensionless", "source_type": "INSTITUTIONAL_DATA", "allowed_values": "String", "notes": "Provenance"},
    {"dataset": "mess_menu_final.csv", "column": "canonical_dish", "description": "Canonical culinary dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "132 canonical dishes", "notes": "Foreign Key to dish_nutrition"},
    {"dataset": "mess_menu_final.csv", "column": "is_dessert_flag", "description": "Boolean flag indicating dessert course", "unit": "boolean", "source_type": "DERIVED", "allowed_values": "True, False", "notes": "Dinner dessert indicator"},
    {"dataset": "mess_menu_final.csv", "column": "provenance_notes", "description": "Transformation and derivation notes", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Row provenance"},

    # 10. dish_classification_final.csv (5 columns)
    {"dataset": "dish_classification_final.csv", "column": "canonical_dish", "description": "Canonical culinary dish name", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "132 canonical dishes", "notes": "Primary Key"},
    {"dataset": "dish_classification_final.csv", "column": "plate_role", "description": "Domain dietary plate grammar role", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "STAPLE, DAL_PROTEIN, DRY_SABZI, GRAVY_SABZI, SNACK, BEVERAGE, DESSERT, ACCOMPANIMENT", "notes": "Plate grammar"},
    {"dataset": "dish_classification_final.csv", "column": "dietary_tag", "description": "Dietary lifestyle classification derived from ingredients", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "VEGETARIAN, EGGETARIAN, NON_VEG", "notes": "Conservative inheritance"},
    {"dataset": "dish_classification_final.csv", "column": "allowed_slots", "description": "Comma-separated list of operational slots where dish appears", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "Subsets of BREAKFAST, LUNCH, DINNER, E_TEA", "notes": "Scheduling filter"},
    {"dataset": "dish_classification_final.csv", "column": "source_class", "description": "Data provenance classification", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PROJECT_DESIGN_CHOICE", "notes": "Design choice"},

    # 11. bmi_rules.csv (7 columns)
    {"dataset": "bmi_rules.csv", "column": "standard", "description": "Authoritative clinical classification standard", "unit": "dimensionless", "source_type": "PRIMARY_LITERATURE", "allowed_values": "ASIAN_INDIAN_MISRA2009, WHO_INTERNATIONAL", "notes": "Classification guideline"},
    {"dataset": "bmi_rules.csv", "column": "category", "description": "Weight status category name", "unit": "dimensionless", "source_type": "PRIMARY_LITERATURE", "allowed_values": "UNDERWEIGHT, NORMAL, OVERWEIGHT, OBESE", "notes": "Risk tier"},
    {"dataset": "bmi_rules.csv", "column": "min_bmi", "description": "Inclusive lower BMI boundary for category", "unit": "kg/m^2", "source_type": "PRIMARY_LITERATURE", "allowed_values": ">= 0.0", "notes": "Lower cutoff"},
    {"dataset": "bmi_rules.csv", "column": "max_bmi", "description": "Inclusive upper BMI boundary for category", "unit": "kg/m^2", "source_type": "PRIMARY_LITERATURE", "allowed_values": "<= 100.0", "notes": "Upper cutoff"},
    {"dataset": "bmi_rules.csv", "column": "source_id", "description": "Foreign key to source_registry.csv", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "SRC_MISRA_2009, SRC_WHO_2000", "notes": "Source FK"},
    {"dataset": "bmi_rules.csv", "column": "citation", "description": "Formal bibliographic citation for cutoff", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Citation"},
    {"dataset": "bmi_rules.csv", "column": "notes", "description": "Clinical cardiometabolic risk interpretation", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Clinical note"},

    # 12. rda_targets.csv (15 columns)
    {"dataset": "rda_targets.csv", "column": "sex", "description": "Biological sex", "unit": "dimensionless", "source_type": "PRIMARY_LITERATURE", "allowed_values": "MALE, FEMALE", "notes": "Sex"},
    {"dataset": "rda_targets.csv", "column": "reference_weight_kg", "description": "Reference body weight for adult Indian", "unit": "kg", "source_type": "PRIMARY_LITERATURE", "allowed_values": "55.0, 65.0", "notes": "ICMR-NIN 2020 reference weight"},
    {"dataset": "rda_targets.csv", "column": "activity_level", "description": "Physical activity level category", "unit": "dimensionless", "source_type": "PRIMARY_LITERATURE", "allowed_values": "SEDENTARY, MODERATE, HEAVY", "notes": "Activity category"},
    {"dataset": "rda_targets.csv", "column": "pal", "description": "Physical activity level multiplier", "unit": "ratio", "source_type": "PRIMARY_LITERATURE", "allowed_values": "1.40, 1.75, 2.20", "notes": "PAL factor"},
    {"dataset": "rda_targets.csv", "column": "energy_kcal", "description": "Daily Total Energy Expenditure recommendation", "unit": "kcal", "source_type": "PRIMARY_LITERATURE", "allowed_values": "> 0.0", "notes": "TEE"},
    {"dataset": "rda_targets.csv", "column": "protein_g", "description": "Daily Recommended Dietary Allowance for protein", "unit": "g", "source_type": "PRIMARY_LITERATURE", "allowed_values": "> 0.0", "notes": "RDA protein"},
    {"dataset": "rda_targets.csv", "column": "fat_g", "description": "Daily fat intake target (25% total energy)", "unit": "g", "source_type": "DERIVED", "allowed_values": "> 0.0", "notes": "25% of kcal"},
    {"dataset": "rda_targets.csv", "column": "carbohydrate_g", "description": "Daily carbohydrate intake target", "unit": "g", "source_type": "DERIVED", "allowed_values": "> 0.0", "notes": "Remainder of kcal"},
    {"dataset": "rda_targets.csv", "column": "fibre_g", "description": "Daily dietary fibre recommendation (30g/2000kcal)", "unit": "g", "source_type": "PRIMARY_LITERATURE", "allowed_values": "> 0.0", "notes": "Safe intake"},
    {"dataset": "rda_targets.csv", "column": "calcium_mg", "description": "Daily Recommended Dietary Allowance for calcium", "unit": "mg", "source_type": "PRIMARY_LITERATURE", "allowed_values": "1000.0", "notes": "Adult RDA"},
    {"dataset": "rda_targets.csv", "column": "iron_mg", "description": "Daily Recommended Dietary Allowance for iron", "unit": "mg", "source_type": "PRIMARY_LITERATURE", "allowed_values": "19.0, 29.0", "notes": "Sex differentiated"},
    {"dataset": "rda_targets.csv", "column": "potassium_mg", "description": "Daily adequate intake for potassium", "unit": "mg", "source_type": "PRIMARY_LITERATURE", "allowed_values": "3500.0", "notes": "AI"},
    {"dataset": "rda_targets.csv", "column": "sodium_max_mg", "description": "Daily safe upper limit for sodium intake", "unit": "mg", "source_type": "PRIMARY_LITERATURE", "allowed_values": "2000.0", "notes": "Safe limit"},
    {"dataset": "rda_targets.csv", "column": "source_id", "description": "Foreign key to source_registry.csv", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "SRC_ICMR_NIN_2020", "notes": "Source FK"},
    {"dataset": "rda_targets.csv", "column": "notes", "description": "Descriptive reference annotation", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Report notes"},

    # 13. health_rules.csv (12 columns)
    {"dataset": "health_rules.csv", "column": "rule_id", "description": "Unique identifier for clinical health rule", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "HR_DIAB_*, HR_HTN_*, HR_PCOS_*, HR_OBES_*", "notes": "Primary Key"},
    {"dataset": "health_rules.csv", "column": "condition", "description": "Clinical health condition targeted", "unit": "dimensionless", "source_type": "PRIMARY_LITERATURE", "allowed_values": "DIABETES, HYPERTENSION, PCOS, OBESITY", "notes": "Condition"},
    {"dataset": "health_rules.csv", "column": "rule_type", "description": "Enforcement severity type", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "HARD_CONSTRAINT, SOFT_PENALTY, PROMOTION", "notes": "Severity"},
    {"dataset": "health_rules.csv", "column": "target_attribute", "description": "Evaluated dish attribute", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "plate_role, canonical_dish, ingredient, glycemic_index, sodium_mg, carbohydrate_g", "notes": "Attribute"},
    {"dataset": "health_rules.csv", "column": "operator", "description": "Comparison operator", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "EQUALS, IN, CONTAINS, LESS_THAN", "notes": "Operator"},
    {"dataset": "health_rules.csv", "column": "threshold_or_value", "description": "Comparison threshold or match value", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "String or float", "notes": "Value"},
    {"dataset": "health_rules.csv", "column": "action", "description": "Recommender action executed on match", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "EXCLUDE, PENALIZE_SCORE, BOOST_SCORE", "notes": "Action"},
    {"dataset": "health_rules.csv", "column": "status", "description": "Active operational status", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "ACTIVE_VERIFIED, DISABLED_UNSOURCED", "notes": "Integrity filter"},
    {"dataset": "health_rules.csv", "column": "provenance_type", "description": "Clinical evidence tier", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "PRIMARY_LITERATURE, NEEDS_SOURCE", "notes": "Provenance tier"},
    {"dataset": "health_rules.csv", "column": "source_id", "description": "Foreign key to source_registry.csv", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "SRC_*, NEEDS_SOURCE", "notes": "Source FK"},
    {"dataset": "health_rules.csv", "column": "citation", "description": "Formal bibliographic citation", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String or UNGROUNDED", "notes": "Citation"},
    {"dataset": "health_rules.csv", "column": "rationale", "description": "Clinical medical nutrition rationale", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Clinical justification"},

    # 14. canteen_extras.csv (15 columns)
    {"dataset": "canteen_extras.csv", "column": "dish", "description": "Canonical dish name of canteen extra", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Primary Key"},
    {"dataset": "canteen_extras.csv", "column": "plate_role", "description": "Plate grammar role", "unit": "dimensionless", "source_type": "PROJECT_DESIGN_CHOICE", "allowed_values": "DAL_PROTEIN, ACCOMPANIMENT, BEVERAGE, STAPLE", "notes": "Role"},
    {"dataset": "canteen_extras.csv", "column": "dietary_tag", "description": "Dietary classification tag", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "VEGETARIAN, EGGETARIAN, NON_VEG", "notes": "Diet"},
    {"dataset": "canteen_extras.csv", "column": "price_inr", "description": "Retail canteen purchase price", "unit": "INR", "source_type": "INSTITUTIONAL_DATA", "allowed_values": "> 0.0", "notes": "Price"},
    {"dataset": "canteen_extras.csv", "column": "energy_kcal", "description": "Serving energy", "unit": "kcal", "source_type": "DERIVED", "allowed_values": "> 0.0", "notes": "Verified IFCT energy"},
    {"dataset": "canteen_extras.csv", "column": "protein_g", "description": "Serving protein", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Protein"},
    {"dataset": "canteen_extras.csv", "column": "fat_g", "description": "Serving fat", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Fat"},
    {"dataset": "canteen_extras.csv", "column": "carbohydrate_g", "description": "Serving carbohydrate", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Carbohydrate"},
    {"dataset": "canteen_extras.csv", "column": "fibre_g", "description": "Serving dietary fibre", "unit": "g", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Fibre"},
    {"dataset": "canteen_extras.csv", "column": "calcium_mg", "description": "Serving calcium", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Calcium"},
    {"dataset": "canteen_extras.csv", "column": "iron_mg", "description": "Serving iron", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Iron"},
    {"dataset": "canteen_extras.csv", "column": "potassium_mg", "description": "Serving potassium", "unit": "mg", "source_type": "DERIVED", "allowed_values": ">= 0.0", "notes": "Potassium"},
    {"dataset": "canteen_extras.csv", "column": "sodium_mg", "description": "Serving sodium (natural biological only)", "unit": "mg", "source_type": "IFCT_DERIVED", "allowed_values": ">= 0.0", "notes": "Sodium"},
    {"dataset": "canteen_extras.csv", "column": "calculation_status", "description": "Nutritional calculation verification badge", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "COMPLETE_IFCT, ASSUMPTION_INCLUDED", "notes": "Strict non-NaN status"},
    {"dataset": "canteen_extras.csv", "column": "notes", "description": "Culinary and nutritional description", "unit": "dimensionless", "source_type": "DERIVED", "allowed_values": "String", "notes": "Item description"}
]


def build_metadata_tables(root_dir: Path):
    meta_dir = root_dir / "data" / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(SOURCE_REGISTRY_DATA).to_csv(meta_dir / "source_registry.csv", index=False)
    pd.DataFrame(PROVENANCE_DATA).to_csv(meta_dir / "data_provenance.csv", index=False)
    pd.DataFrame(LIMITATIONS_DATA).to_csv(meta_dir / "limitations.csv", index=False)
    pd.DataFrame(DATA_DICTIONARY_DATA).to_csv(meta_dir / "data_dictionary.csv", index=False)

    print(f"Generated {meta_dir / 'source_registry.csv'} ({len(SOURCE_REGISTRY_DATA)} sources)")
    print(f"Generated {meta_dir / 'data_provenance.csv'} ({len(PROVENANCE_DATA)} provenance records)")
    print(f"Generated {meta_dir / 'limitations.csv'} ({len(LIMITATIONS_DATA)} catalogued limitations)")
    print(f"Generated {meta_dir / 'data_dictionary.csv'} ({len(DATA_DICTIONARY_DATA)} dictionary entries)")


if __name__ == "__main__":
    build_metadata_tables(Path(__file__).resolve().parent.parent)
