"""
health_rules.py

Clinical health rules engine for condition-specific dietary constraints.
Applies active verified rules from ICMR (2018), IHG-IV (2019), PCOS Guidelines (2023),
and Misra et al. (2009). Strictly segregates and disables ungrounded/NEEDS_SOURCE rules.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd


class HealthRuleEngine:
    def __init__(self, rules_csv_path: Path = None):
        if rules_csv_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            rules_csv_path = root / "data" / "rules" / "health_rules.csv"

        self.df = pd.read_csv(rules_csv_path)
        self.active_rules = self.df[self.df["status"] == "ACTIVE_VERIFIED"].copy()
        self.disabled_rules = self.df[self.df["status"] == "DISABLED_UNSOURCED"].copy()

    def evaluate_hard_constraints(
        self,
        dish_name: str,
        plate_role: str,
        user_conditions: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Evaluates whether a dish is prohibited by any active clinical hard constraint.
        Returns (is_allowed, list_of_rejection_reasons).
        """
        conds = {c.strip().upper() for c in user_conditions if c.strip().upper() != "NONE"}
        if not conds:
            return True, []

        reasons = []
        is_allowed = True

        for _, rule in self.active_rules[self.active_rules["rule_type"] == "HARD_CONSTRAINT"].iterrows():
            if rule["condition"] not in conds:
                continue

            attr = rule["target_attribute"]
            op = rule["operator"]
            val = str(rule["threshold_or_value"]).strip()

            target_val = plate_role if attr == "plate_role" else dish_name

            matched = False
            if op == "EQUALS" and target_val.upper() == val.upper():
                matched = True
            elif op == "IN" and target_val.upper() in [x.strip().upper() for x in val.split(",")]:
                matched = True

            if matched:
                is_allowed = False
                reasons.append(f"[{rule['rule_id']}] {rule['condition']}: {rule['rationale']} ({rule['citation']})")

        return is_allowed, reasons

    def calculate_soft_adjustments(
        self,
        dish_name: str,
        plate_role: str,
        user_conditions: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Calculates score modifiers (penalties / promotions) from soft clinical guidelines.
        Returns (score_delta, list_of_adjustment_notes).
        """
        conds = {c.strip().upper() for c in user_conditions if c.strip().upper() != "NONE"}
        if not conds:
            return 0.0, []

        delta = 0.0
        notes = []

        active_soft = self.active_rules[self.active_rules["rule_type"].isin(["SOFT_PENALTY", "PROMOTION"])]
        for _, rule in active_soft.iterrows():
            if rule["condition"] not in conds:
                continue

            attr = rule["target_attribute"]
            op = rule["operator"]
            val = str(rule["threshold_or_value"]).strip()
            target_val = plate_role if attr == "plate_role" else dish_name

            matched = False
            if op == "EQUALS" and target_val.upper() == val.upper():
                matched = True
            elif op == "IN" and target_val.upper() in [x.strip().upper() for x in val.split(",")]:
                matched = True

            if matched:
                if rule["rule_type"] == "SOFT_PENALTY":
                    delta -= 15.0
                    notes.append(f"Penalty -15: [{rule['rule_id']}] {rule['rationale']}")
                elif rule["rule_type"] == "PROMOTION":
                    delta += 10.0
                    notes.append(f"Bonus +10: [{rule['rule_id']}] {rule['rationale']}")

        return round(delta, 1), notes

    def get_disabled_rules_summary(self) -> List[Dict[str, str]]:
        """Returns metadata for all ungrounded rules disabled for research integrity."""
        return self.disabled_rules[[
            "rule_id", "condition", "target_attribute", "threshold_or_value",
            "provenance_type", "rationale"
        ]].to_dict(orient="records")
