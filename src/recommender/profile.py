"""
profile.py

User profile and anthropometric modeling for hostel students.
Computes BMI, classifies weight status using Asian Indian (Misra et al., 2009)
and WHO international cut-offs, and validates dietary preferences.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any


VALID_SEXES = {"MALE", "FEMALE"}
VALID_DIETS = {"VEGETARIAN", "EGGETARIAN", "NON_VEG"}
VALID_HOSTELS = {"COMMON", "GIRLS_HOSTEL"}
VALID_ACTIVITIES = {"SEDENTARY", "LIGHT", "MODERATE", "HEAVY"}
VALID_CONDITIONS = {"NONE", "DIABETES", "HYPERTENSION", "PCOS", "OBESITY"}


@dataclass
class UserProfile:
    student_id: str = "STU_DEFAULT"
    age: int = 20
    sex: str = "MALE"
    height_cm: float = 170.0
    weight_kg: float = 65.0
    dietary_preference: str = "VEGETARIAN"
    hostel_type: str = "COMMON"
    activity_level: str = "SEDENTARY"
    health_conditions: List[str] = field(default_factory=lambda: ["NONE"])
    canteen_budget_inr: float = 0.0

    def __post_init__(self):
        self.sex = str(self.sex).strip().upper()
        self.dietary_preference = str(self.dietary_preference).strip().upper()
        self.hostel_type = str(self.hostel_type).strip().upper()
        self.activity_level = str(self.activity_level).strip().upper()
        self.health_conditions = [str(c).strip().upper() for c in self.health_conditions] or ["NONE"]

        if self.sex not in VALID_SEXES:
            raise ValueError(f"Invalid sex '{self.sex}'. Allowed: {VALID_SEXES}")
        if self.dietary_preference not in VALID_DIETS:
            raise ValueError(f"Invalid diet '{self.dietary_preference}'. Allowed: {VALID_DIETS}")
        if self.hostel_type not in VALID_HOSTELS:
            raise ValueError(f"Invalid hostel '{self.hostel_type}'. Allowed: {VALID_HOSTELS}")
        if self.activity_level not in VALID_ACTIVITIES:
            raise ValueError(f"Invalid activity '{self.activity_level}'. Allowed: {VALID_ACTIVITIES}")

        unknown_conds = set(self.health_conditions) - VALID_CONDITIONS
        if unknown_conds:
            raise ValueError(f"Unknown health conditions: {unknown_conds}. Allowed: {VALID_CONDITIONS}")

        if not (15 <= self.age <= 65):
            raise ValueError(f"Age {self.age} out of expected hostel range [15, 65]")
        if not (120.0 <= self.height_cm <= 230.0):
            raise ValueError(f"Height {self.height_cm} cm out of realistic range [120, 230]")
        if not (30.0 <= self.weight_kg <= 200.0):
            raise ValueError(f"Weight {self.weight_kg} kg out of realistic range [30, 200]")
        if self.canteen_budget_inr < 0.0:
            raise ValueError(f"Canteen budget cannot be negative: {self.canteen_budget_inr}")

        if self.sex == "MALE" and self.hostel_type == "GIRLS_HOSTEL":
            raise ValueError("Incompatible profile: Male student cannot be assigned to GIRLS_HOSTEL")
        if self.sex == "MALE" and "PCOS" in self.health_conditions:
            raise ValueError("Incompatible profile: PCOS applies to female physiology only")

    @property
    def height_m(self) -> float:
        return self.height_cm / 100.0

    @property
    def bmi(self) -> float:
        return round(self.weight_kg / (self.height_m ** 2), 2)

    @property
    def bmi_category_asian(self) -> str:
        """Asian Indian classification from Misra et al. (2009) JAPI consensus."""
        val = self.bmi
        if val < 18.5:
            return "UNDERWEIGHT"
        elif val < 23.0:
            return "NORMAL"
        elif val < 25.0:
            return "OVERWEIGHT"
        else:
            return "OBESE"

    @property
    def bmi_category_who(self) -> str:
        """Standard international WHO (2000) classification."""
        val = self.bmi
        if val < 18.5:
            return "UNDERWEIGHT"
        elif val < 25.0:
            return "NORMAL"
        elif val < 30.0:
            return "OVERWEIGHT"
        else:
            return "OBESE"

    @property
    def healthy_weight_range_asian_kg(self) -> Tuple[float, float]:
        """Healthy weight range (BMI 18.5 to 22.9 kg/m2) for Asian Indians."""
        h_sq = self.height_m ** 2
        return (round(18.5 * h_sq, 1), round(22.9 * h_sq, 1))

    def allows_dish_diet(self, dish_dietary_tag: str) -> bool:
        """Checks if a dish's dietary tag is permitted under user's preference."""
        tag = str(dish_dietary_tag).strip().upper()
        if self.dietary_preference == "VEGETARIAN":
            return tag == "VEGETARIAN"
        elif self.dietary_preference == "EGGETARIAN":
            return tag in {"VEGETARIAN", "EGGETARIAN"}
        elif self.dietary_preference == "NON_VEG":
            return tag in {"VEGETARIAN", "EGGETARIAN", "NON_VEG"}
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "age": self.age,
            "sex": self.sex,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "bmi_category_asian": self.bmi_category_asian,
            "bmi_category_who": self.bmi_category_who,
            "healthy_weight_range_asian_kg": self.healthy_weight_range_asian_kg,
            "dietary_preference": self.dietary_preference,
            "hostel_type": self.hostel_type,
            "activity_level": self.activity_level,
            "health_conditions": self.health_conditions,
            "canteen_budget_inr": self.canteen_budget_inr,
            "bmi_source_citation": "Misra et al. (2009) JAPI 57:163-170 (SRC_MISRA_2009)"
        }
