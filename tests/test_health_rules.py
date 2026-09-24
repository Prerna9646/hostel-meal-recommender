"""
test_health_rules.py

Unit tests for clinical health rules engine (Phase 11).
Validates condition-specific hard exclusions, soft penalties, promotions,
and strict disabling of ungrounded/NEEDS_SOURCE rules (GI thresholds, dairy bans, keto caps).
"""

from pathlib import Path
import pandas as pd
import pytest
from src.recommender.health_rules import HealthRuleEngine


@pytest.fixture(scope="module")
def engine():
    return HealthRuleEngine()


def test_health_rules_csv_structure(engine):
    assert len(engine.df) == 16, f"Expected 16 rules, found {len(engine.df)}"
    assert len(engine.active_rules) == 11
    assert len(engine.disabled_rules) == 5

    conditions = set(engine.df["condition"].unique())
    assert conditions == {"DIABETES", "HYPERTENSION", "PCOS", "OBESITY"}


def test_disabled_unsourced_rules(engine):
    """Verifies ungrounded rules are tagged NEEDS_SOURCE and disabled from active execution."""
    disabled_ids = set(engine.disabled_rules["rule_id"])
    expected_disabled = {"HR_DIAB_004", "HR_HTN_004", "HR_PCOS_003", "HR_PCOS_004", "HR_OBES_004"}
    assert disabled_ids == expected_disabled

    for _, r in engine.disabled_rules.iterrows():
        assert r["status"] == "DISABLED_UNSOURCED"
        assert r["provenance_type"] == "NEEDS_SOURCE"
        assert r["source_id"] == "NEEDS_SOURCE"
        assert "NEEDS_SOURCE" in r["citation"]

    # Active rules must not contain any of the disabled IDs
    active_ids = set(engine.active_rules["rule_id"])
    assert not active_ids.intersection(expected_disabled)


def test_diabetes_hard_constraints(engine):
    # Desserts prohibited
    allowed, reasons = engine.evaluate_hard_constraints("Gulab Jamun", "DESSERT", ["DIABETES"])
    assert allowed is False
    assert any("HR_DIAB_001" in r for r in reasons)

    # Staples allowed
    allowed, reasons = engine.evaluate_hard_constraints("Chapati", "STAPLE", ["DIABETES"])
    assert allowed is True
    assert reasons == []


def test_hypertension_hard_constraints(engine):
    # High-salt preserved pickle prohibited
    allowed, reasons = engine.evaluate_hard_constraints("Pickle", "ACCOMPANIMENT", ["HYPERTENSION"])
    assert allowed is False
    assert any("HR_HTN_001" in r for r in reasons)

    # Plain curd allowed
    allowed, reasons = engine.evaluate_hard_constraints("Plain Curd", "ACCOMPANIMENT", ["HYPERTENSION"])
    assert allowed is True
    assert reasons == []


def test_pcos_hard_constraints_and_dairy_preservation(engine):
    # Desserts prohibited
    allowed, reasons = engine.evaluate_hard_constraints("Chocolate Pie", "DESSERT", ["PCOS"])
    assert allowed is False
    assert any("HR_PCOS_001" in r for r in reasons)

    # Milk beverage must NOT be prohibited by active rules (dairy ban is DISABLED_UNSOURCED)
    allowed, reasons = engine.evaluate_hard_constraints("Milk", "BEVERAGE", ["PCOS"])
    assert allowed is True
    assert reasons == []


def test_obesity_hard_constraints(engine):
    allowed, reasons = engine.evaluate_hard_constraints("Halwa", "DESSERT", ["OBESITY"])
    assert allowed is False
    assert any("HR_OBES_001" in r for r in reasons)

    allowed, reasons = engine.evaluate_hard_constraints("Jeera Rice", "STAPLE", ["OBESITY"])
    assert allowed is True


def test_soft_adjustments(engine):
    # Diabetic snack penalty
    delta, notes = engine.calculate_soft_adjustments("Samosa", "SNACK", ["DIABETES"])
    assert delta == -15.0
    assert any("HR_DIAB_002" in n for n in notes)

    # Hypertensive snack penalty and banana promotion
    delta, notes = engine.calculate_soft_adjustments("Chips", "SNACK", ["HYPERTENSION"])
    assert delta == -15.0
    assert any("HR_HTN_002" in n for n in notes)

    delta_ban, notes_ban = engine.calculate_soft_adjustments("Banana", "ACCOMPANIMENT", ["HYPERTENSION"])
    assert delta_ban == 10.0
    assert any("HR_HTN_003" in n for n in notes_ban)

    # Obese salad promotion
    delta_sal, notes_sal = engine.calculate_soft_adjustments("Green Salad", "ACCOMPANIMENT", ["OBESITY"])
    assert delta_sal == 10.0
    assert any("HR_OBES_003" in n for n in notes_sal)


def test_unaffected_profile_none(engine):
    allowed, reasons = engine.evaluate_hard_constraints("Gulab Jamun", "DESSERT", ["NONE"])
    assert allowed is True
    assert reasons == []

    delta, notes = engine.calculate_soft_adjustments("Gulab Jamun", "DESSERT", ["NONE"])
    assert delta == 0.0
    assert notes == []
