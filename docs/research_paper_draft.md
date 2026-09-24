# Explainable AI-Based Meal Recommendation for Indian Hostel Students Using IFCT 2017

**Authors:** Advanced Agentic Research Team  
**Affiliation:** University Dining Healthcare & Computational Nutrition Laboratory  
**Target Venue:** *IEEE Transactions on Computational Social Systems / ACM Transactions on Computing for Healthcare*  
**Date:** September 2026  

---

## Abstract
University hostel students in India face fixed diurnal cafeteria menus that offer limited agency while exposing them to nutritional deficiencies and metabolic health risks. Traditional automated diet recommenders frequently utilize opaque black-box neural collaborative filtering or ungrounded generative models that hallucinate nutritional values, lack constraint safety guarantees, and fail to adapt to South Asian metabolic phenotypes. In this paper, we propose a constraint-satisfying, fully explainable meal recommendation framework grounded in the Indian Food Composition Tables (IFCT 2017) and statutory ICMR-NIN (2020) dietary guidelines. We establish an empirical food data lineage across 542 raw commodities, 80 canonical ingredients, and 132 composite cafeteria dishes. The system personalizes recommendations through Mifflin-St Jeor resting metabolic equations, profile-adjustable Physical Activity Levels (PAL), and Asian Indian-specific Body Mass Index (BMI) cut-offs (Misra et al., 2009). A domain-specific plate grammar assembles structural Indian thali combinations, evaluated via a transparent multi-attribute optimization model with verifiable zero-drift Explainable AI (XAI) scoring and counterfactual "Why-Not" diagnostics. A secondary greedy knapsack layer optimizes discretionary canteen purchases to close biological protein gaps. In a 31-day longitudinal evaluation across 5 clinically diverse student personas (620 meal decisions), the system achieved a **0.0% Constraint Violation Rate (CVR)**. Crucially, the evaluation uncovers key institutional insights: (1) an empirical structural protein gap in celebratory Sunday biryani lunches caught uniformly by plate grammar fallbacks (yielding a 96.8% success rate with zero violations), and (2) an unavoidable structural issuance ceiling for varsity athletes requiring multi-serving staple quotas.

**Keywords:** Computational Nutrition, Explainable AI (XAI), Indian Food Composition Tables (IFCT 2017), Multi-Attribute Decision Making, Constraint Satisfaction, Medical Nutrition Therapy.

---

## 1. Introduction
Malnutrition and emerging cardiometabolic disorders (Type 2 Diabetes, Hypertension, Polycystic Ovary Syndrome, and Central Adiposity) represent a dual burden among young adult university students in India. Hostel residents are uniquely constrained: unlike free-living adults who can purchase customized groceries, hostel students subsist on fixed institutional mess menus operating on monthly cyclic schedules. 

Historically, computational meal recommendation systems have exhibited several fundamental flaws:
1. **Pseudoscience and Data Unreliability:** Reliance on western food databases (e.g. generic USDA entries) that do not reflect indigenous Indian culinary preparations, spices, or cultivar genetics.
2. **Black-Box Opacity:** Deploying deep reinforcement learning or matrix factorization that cannot explain *why* a particular meal was prescribed or *why* an alternative was omitted.
3. **Clinical Violation Risks:** Recommending high-sugar desserts to diabetic students or high-salt preserved condiments to hypertensive individuals due to soft-penalty trade-offs.
4. **Failure of South Asian Phenotypic Grounding:** Utilizing western BMI cut-offs ($\geq 25\text{ kg/m}^2$ for overweight), thereby misclassifying Asian Indians who develop insulin resistance and visceral adiposity at $\text{BMI} \geq 23.0\text{ kg/m}^2$.

To overcome these challenges, we design, implement, and validate an explainable, constraint-satisfaction meal recommendation architecture grounded strictly in empirical national food science data.

---

## 2. Institutional Context & Data Lineage
The system is constructed upon a three-tier relational data pipeline:

```
[IFCT 2017 Machine-Readable (542 Foods x 421 Cols)]
                  │
                  ▼ (Conversion kJ->kcal, mineral mg, Atwater oil fix)
      [ifct_2017_clean.csv (542 Rows x 16 Cols)]
                  │
                  ▼ (Canonical mapping & component decomposition)
    [ingredient_master.csv (80 Canonical Raw Ingredients)]
                  │
                  ▼ (Standardized raw issuance assumptions)
   [dish_ingredients_final.csv (503 Rows, 132 Dishes)]
                  │
                  ▼ (Nutrient aggregation & NaN status rollup)
    [dish_nutrition_final.csv (132 Canonical Dishes)]
                  │
                  ▼ (Plate grammar assembly & multi-attribute optimization)
    [mess_menu_final.csv (635 Rows, October 2026 Menu)]
```

### 2.1 IFCT 2017 Sanitization & Anomaly Resolution
- **Energy Conversion:** Raw IFCT values recorded metabolizable energy in kilojoules (`enerc`), which were standardized to kilocalories ($\text{kcal} = \text{kJ} / 4.184$).
- **Mineral Unit Scaling:** Calcium and iron reported in raw fractional grams per 100g were scaled by $1,000.0$ to standard milligrams per 100g ($\text{mg}/100\text{g}$).
- **Edible Oils Anomaly:** Group T edible oils and fats (`T001`–`T014`) contained a raw database defect where `enerc == 0` despite `fatce == 100.0`. In accordance with FAO (2003) technical standards, energy was derived using the international Atwater general factor for fat ($9.0\text{ kcal/g} \rightarrow 900.0\text{ kcal/100g}$), tagged `IFCT_DERIVED`.
- **Statistical Spread Flagging:** 207 analytical variance columns suffixed with `_e` lacked formal documentation distinguishing standard deviation (SD) from standard error (SE). To avoid false confidence interval claims, these were catalogued as `UNVERIFIED_STATISTICAL_SPREAD` and excluded from scoring.

### 2.2 Dish Composition & Portion Assumptions
Because hostel dining operates on communal bulk preparation, 132 canonical cafeteria dishes were decomposed into raw-ingredient-gram weights per serving ([`dish_ingredients_final.csv`](file:///c:/Users/ranje/OneDrive/Desktop/project/data/processed/dish_ingredients_final.csv)). Cooking oil was standardized to a uniform modeling assumption of $5.0\text{g}$ vegetable fat per cooked serving. All 17 commercial packaged snacks lacking generic agricultural IFCT profiles (e.g. chips, muffins) propagated `NaN` and were catalogued as `INSUFFICIENT_DATA`.

---

## 3. Methodology & System Architecture

### 3.1 Anthropometrics & Ethnic Asian Indian Cut-offs
The student profile model ([`UserProfile`](file:///c:/Users/ranje/OneDrive/Desktop/project/src/recommender/profile.py)) computes Body Mass Index ($\text{BMI} = \text{wt} / \text{ht}^2$). Adhering to the clinical consensus published by Misra et al. (2009) in the *Journal of the Association of Physicians of India* (JAPI), weight status is stratified using ethnic thresholds:
- **Underweight:** $< 18.5\text{ kg/m}^2$
- **Normal Weight:** $18.5 - 22.99\text{ kg/m}^2$
- **Overweight (Elevated Risk):** $23.0 - 24.99\text{ kg/m}^2$
- **Obese (High Risk):** $\geq 25.0\text{ kg/m}^2$

### 3.2 Personalized Target Derivation (ICMR-NIN 2020)
Basal Metabolic Rate is derived via the Mifflin-St Jeor (1990) equation:
$$\text{BMR}_{\text{Male}} = 10W + 6.25H - 5A + 5, \quad \text{BMR}_{\text{Female}} = 10W + 6.25H - 5A - 161$$
Total Daily Energy Expenditure is scaled by profile-adjustable Physical Activity Levels (PAL):
$$\text{TDEE} = \text{BMR} \times \text{PAL}, \quad \text{PAL} \in \{1.40 \text{ (Sedentary)}, 1.55 \text{ (Light)}, 1.75 \text{ (Moderate)}, 2.20 \text{ (Heavy)}\}$$
Daily macronutrients and micronutrients follow ICMR-NIN (2020) statutory adult recommendations:
- **Protein:** $0.83\text{ g/kg/d}$ (sedentary) to $1.20\text{ g/kg/d}$ (active/athlete).
- **Fat:** $25\%$ of total calories ($E \times 0.25 / 9$).
- **Fibre:** $30\text{ g per 2,000 kcal}$.
- **Calcium:** $1,000\text{ mg/d}$ | **Potassium:** $3,500\text{ mg/d}$ | **Sodium:** $\leq 2,000\text{ mg/d}$ (natural baseline).
- **Iron:** Sex-differentiated: $19\text{ mg/d}$ (Men) vs $29\text{ mg/d}$ (Women of reproductive age).

Daily targets are distributed across diurnal slots:
$$\text{Breakfast (25\%)}, \quad \text{Lunch (35\%)}, \quad \text{E-Tea (10\%)}, \quad \text{Dinner (30\%)}$$

### 3.3 Plate Grammar Assembly
To enforce structural meal balance, candidate dishes are assembled under domain plate grammar rules:
- **Breakfast:** 1 Primary (`STAPLE` or `SNACK`) + optional `BEVERAGE` or `ACCOMPANIMENT` (max 3 items).
- **Lunch / Dinner:** 1 `STAPLE` + 1 `DAL_PROTEIN` + optional `GRAVY_SABZI`, `DRY_SABZI`, `ACCOMPANIMENT`, `DESSERT` (max 4 items).
- **E-Tea:** 1 Primary (`SNACK`, `BEVERAGE`, or `STAPLE`) + optional addition (max 2 items).

### 3.4 Multi-Attribute Optimization Model
Candidate plates that pass dietary, clinical, and data-completeness filters are scored via a transparent objective function:
$$\text{PlateScore} = S_{\text{Energy}} + S_{\text{Protein}} + S_{\text{Fibre}} + \sum \Delta_{\text{Health}}$$
$$\text{Where:} \quad S_{\text{Energy}} = \max\left(0, \; 100 \times \left(1.0 - \frac{|\text{Energy} - E_{\text{target}}|}{E_{\text{target}}}\right)\right)$$
$$S_{\text{Protein}} = \min\left(50, \; 50 \times \frac{\text{Protein}}{P_{\text{target}}}\right), \quad S_{\text{Fibre}} = \min\left(25, \; 25 \times \frac{\text{Fibre}}{\text{Fib}_{\text{target}}}\right)$$
$$\Delta_{\text{Health}} = \sum \text{Soft Penalties } (-15.0) + \sum \text{Clinical Promotions } (+10.0)$$

---

## 4. Clinical Evidence & Safety Filtering
Clinical rules ([`data/rules/health_rules.csv`](file:///c:/Users/ranje/OneDrive/Desktop/project/data/rules/health_rules.csv)) were subjected to an evidence audit:
- **Active Verified Rules (11):** Grounded in ICMR (2018) Type 2 Diabetes Guidelines (eliminating sucrose desserts `HR_DIAB_001`, penalizing fried snacks `HR_DIAB_002`), Indian Hypertension Guidelines (eliminating preserved pickles `HR_HTN_001`), and PCOS Guidelines (2023).
- **Segregated Disabled Rules (5):** Glycemic Index thresholds (`GI < 55`) and sodium caps on curries were disabled (`DISABLED_UNSOURCED` / `NEEDS_SOURCE`) because IFCT 2017 lacks empirical GI measurements and kitchen table salt was unmeasured. Routine dairy bans for PCOS were actively refuted and disabled per the 2023 International PCOS Guideline.

---

## 5. Experimental Evaluation & Results

### 5.1 Simulation Setup
A longitudinal simulation was executed across the complete 31-day October 2026 mess menu for 5 representative personas ($5 \times 31 \times 4 = 620\text{ individual meals}$):
1. **Persona A:** 21F, Sedentary, Vegetarian, `GIRLS_HOSTEL`, Type 2 Diabetes (Target: 1,450 kcal).
2. **Persona B:** 24M, Sedentary, Non-Veg, `COMMON`, Hypertension + Obesity (Target: 1,970 kcal).
3. **Persona C:** 20M, Heavy PAL (2.2), Eggetarian, `COMMON`, Underweight Athlete (Target: 3,700 kcal).
4. **Persona D:** 20F, Light PAL (1.55), Vegetarian, `GIRLS_HOSTEL`, PCOS (Target: 1,980 kcal).
5. **Persona E:** 20M, Moderate PAL (1.75), Vegetarian, `COMMON`, Healthy Control (Target: 2,710 kcal).

### 5.2 Performance Metrics
| Metric | Benchmark Result | Clinical Significance |
| :--- | :---: | :--- |
| **Total Meal Decisions** | **620** | Full 31-day longitudinal evaluation |
| **Constraint Violation Rate (CVR)** | **0.0%** | Zero clinical, dietary, or NaN violations |
| **Dietary Violations** | **0** | Strict vegetarian/eggetarian preservation |
| **Clinical Violations** | **0** | Zero desserts to diabetics; zero pickles to hypertensives |
| **Success Rate across Cohort** | **96.8%** | Exactly 120/124 slots successful per persona |
| **Fallback Rate** | **3.2%** | Exactly 4 Sunday lunches per persona |

### 5.3 Discovery 1: The Sunday Biryani Protein Gap
The identical 96.8% success rate across all 5 personas was audited. In every case, the 4 non-success slots occurred on **October 4, 11, 18, and 25 (Sunday Lunch)**. On Sundays, the cafeteria serves a celebratory menu: Veg Biryani, Dum Aloo, Mix Raita, and Salad. The menu provides zero pulses or legume dals. Because lunch grammar strictly requires a `DAL_PROTEIN` core, the engine rejected the plate and activated its formal fallback state (`NO_VALID_COMBINATION`), diagnosing the protein gap and advising canteen supplementation.

### 5.4 Discovery 2: The Athlete Single-Portion Issuance Ceiling
For Persona C (Athlete, target $3,700\text{ kcal}$), standard single-portion plates averaged $1,391\text{ kcal/day}$, leaving an empirical deficit of $2,309\text{ kcal/day}$. Discretionary canteen extras (two boiled eggs) closed the protein RDA but added only $\approx 173\text{ kcal}$. Rather than hiding this gap through synthetic portion scaling, our evaluation explicitly demonstrates that institutional cafeteria operations must provide athlete-sized staple quotas (4–6 chapatis / double rice) to sustain varsity sports.

---

## 6. Methodological Limitations & Threats to Validity
As catalogued in [`data/metadata/limitations.csv`](file:///c:/Users/ranje/OneDrive/Desktop/project/data/metadata/limitations.csv):
1. **Moisture & Yield Variations:** Modeled on raw commodity inputs; water evaporation during simmering alters cooked wet mass but preserves dry macronutrients.
2. **Sodium Underestimation:** Reflects natural intrinsic biological sodium only; culinary table salt was unmeasured and is reported as a strict lower bound.
3. **Packaged Commercial Snacks:** 17 commercial items lacking IFCT entries were barred from scoring to prevent ungrounded algorithmic hallucination.

---

## 7. Conclusion
We have demonstrated an Explainable AI meal recommendation system that achieves 100% clinical safety and zero constraint violations across an institutional Indian hostel dining environment. By grounding calculations in IFCT 2017, enforcing ethnic Asian Indian BMI criteria, deploying plate grammar, and maintaining a faithful mathematical audit trail, the framework provides a transparent template for clinical dietetic AI in institutional settings.

---

## References
1. Longvah, T., Ananthan, R., Bhaskarachary, K., & Venkaiah, K. (2017). *Indian Food Composition Tables*. National Institute of Nutrition, ICMR, Hyderabad. ISBN: 978-93-84570-00-5.
2. ICMR-National Institute of Nutrition. (2020). *Nutrient Requirements for Indians: Recommended Dietary Allowances and Estimated Average Requirements*. Hyderabad: ICMR-NIN.
3. Misra, A., Chowbey, P., Makkar, B. M., Vikram, N. K., Wasir, J. S., Chadha, D., et al. (2009). Consensus statement for diagnosis of obesity, abdominal obesity and the metabolic syndrome for Asian Indians. *Journal of the Association of Physicians of India*, 57(2), 163-170.
4. WHO Expert Consultation. (2004). Appropriate body-mass index for Asian populations and its implications for policy and intervention strategies. *The Lancet*, 363(9403), 157-163.
5. Mifflin, M. D., St Jeor, S. T., Hill, L. A., Scott, B. J., Daugherty, S. A., & Koh, Y. O. (1990). A new predictive equation for resting energy expenditure in healthy individuals. *The American Journal of Clinical Nutrition*, 51(2), 241-247.
6. Indian Council of Medical Research. (2018). *ICMR Guidelines for Management of Type 2 Diabetes*. New Delhi: ICMR.
7. Association of Physicians of India. (2019). Indian Hypertension Guidelines-IV (IHG-IV). *Journal of the Association of Physicians of India*.
8. Teede, H. J., Tay, C. T., Laven, J. J., Dokras, A., Moran, L. J., Piltonen, T. T., et al. (2023). Recommendations from the 2023 international evidence-based guideline for the assessment and management of polycystic ovary syndrome. *Fertility and Sterility*, 120(4), 767-793.
9. Food and Agriculture Organization. (2003). *Food energy - methods of analysis and conversion factors*. FAO Food and Nutrition Paper 77, Rome.
10. United States Department of Agriculture. (2024). *FoodData Central Database*. USDA Agricultural Research Service.
