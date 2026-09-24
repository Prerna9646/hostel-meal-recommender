"""
targets.py

Computes personalized daily and meal-slot nutritional targets.
Uses Mifflin-St Jeor equation for BMR, ICMR-NIN (2020) physical activity levels (PAL),
and ICMR-NIN (2020) adult Recommended Dietary Allowances (RDA) for macronutrients and minerals.
"""

from dataclasses import dataclass
from typing import Dict, Any
from src.recommender.profile import UserProfile


PAL_FACTORS = {
    "SEDENTARY": 1.40,
    "LIGHT": 1.55,
    "MODERATE": 1.75,
    "HEAVY": 2.20
}

SLOT_ENERGY_FRACTIONS = {
    "BREAKFAST": 0.25,
    "LUNCH": 0.35,
    "E_TEA": 0.10,
    "DINNER": 0.30
}


@dataclass
class DailyNutrientTargets:
    bmr_kcal: float
    pal: float
    tdee_kcal: float
    target_energy_kcal: float
    protein_g: float
    fat_g: float
    carbohydrate_g: float
    fibre_g: float
    calcium_mg: float
    iron_mg: float
    potassium_mg: float
    sodium_max_mg: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in self.__dict__.items()}


@dataclass
class SlotNutrientTargets:
    slot: str
    energy_fraction: float
    target_energy_kcal: float
    protein_g: float
    fat_g: float
    carbohydrate_g: float
    fibre_g: float
    calcium_mg: float
    iron_mg: float
    potassium_mg: float
    sodium_max_mg: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in self.__dict__.items()}


def compute_bmr(profile: UserProfile) -> float:
    """Mifflin-St Jeor (1990) BMR equation."""
    base = (10.0 * profile.weight_kg) + (6.25 * profile.height_cm) - (5.0 * profile.age)
    bmr = base + 5.0 if profile.sex == "MALE" else base - 161.0
    return round(bmr, 2)


def compute_daily_targets(profile: UserProfile) -> DailyNutrientTargets:
    """Derives daily nutrient targets personalized to profile and Asian BMI category."""
    bmr = compute_bmr(profile)
    pal = PAL_FACTORS.get(profile.activity_level, 1.40)
    tdee = round(bmr * pal, 2)

    # Goal adjustment for weight management
    cat = profile.bmi_category_asian
    if cat in {"OVERWEIGHT", "OBESE"} or "OBESITY" in profile.health_conditions:
        min_safe = 1500.0 if profile.sex == "MALE" else 1200.0
        target_kcal = max(min_safe, round(tdee - 400.0, 2))
    elif cat == "UNDERWEIGHT":
        target_kcal = round(tdee + 400.0, 2)
    else:
        target_kcal = tdee

    # Macronutrient derivations (ICMR-NIN 2020)
    # Protein: 0.83 g/kg for sedentary/light; 1.2 g/kg for moderate/heavy
    prot_rate = 1.20 if profile.activity_level in {"MODERATE", "HEAVY"} else 0.83
    protein_g = round(profile.weight_kg * prot_rate, 2)

    # Fat: 25% of total calories (Atwater 9 kcal/g)
    fat_g = round((target_kcal * 0.25) / 9.0, 2)

    # Carbs: Remainder of energy (Atwater 4 kcal/g)
    carb_kcal = target_kcal - (protein_g * 4.0 + fat_g * 9.0)
    carb_g = round(max(50.0, carb_kcal / 4.0), 2)

    # Fibre: ICMR-NIN 2020 (30g per 2000 kcal)
    fibre_g = round(target_kcal * (30.0 / 2000.0), 2)

    # Minerals: ICMR-NIN 2020
    calcium_mg = 1000.0
    iron_mg = 29.0 if profile.sex == "FEMALE" else 19.0
    potassium_mg = 3500.0
    sodium_max_mg = 2000.0

    return DailyNutrientTargets(
        bmr_kcal=bmr,
        pal=pal,
        tdee_kcal=tdee,
        target_energy_kcal=target_kcal,
        protein_g=protein_g,
        fat_g=fat_g,
        carbohydrate_g=carb_g,
        fibre_g=fibre_g,
        calcium_mg=calcium_mg,
        iron_mg=iron_mg,
        potassium_mg=potassium_mg,
        sodium_max_mg=sodium_max_mg
    )


def compute_slot_targets(daily: DailyNutrientTargets, slot: str) -> SlotNutrientTargets:
    """Allocates daily nutrient targets into operational meal slots."""
    norm_slot = str(slot).strip().upper()
    if norm_slot not in SLOT_ENERGY_FRACTIONS:
        raise ValueError(f"Unknown slot '{norm_slot}'. Allowed: {list(SLOT_ENERGY_FRACTIONS.keys())}")

    frac = SLOT_ENERGY_FRACTIONS[norm_slot]
    return SlotNutrientTargets(
        slot=norm_slot,
        energy_fraction=frac,
        target_energy_kcal=round(daily.target_energy_kcal * frac, 2),
        protein_g=round(daily.protein_g * frac, 2),
        fat_g=round(daily.fat_g * frac, 2),
        carbohydrate_g=round(daily.carbohydrate_g * frac, 2),
        fibre_g=round(daily.fibre_g * frac, 2),
        calcium_mg=round(daily.calcium_mg * frac, 2),
        iron_mg=round(daily.iron_mg * frac, 2),
        potassium_mg=round(daily.potassium_mg * frac, 2),
        sodium_max_mg=round(daily.sodium_max_mg * frac, 2)
    )
