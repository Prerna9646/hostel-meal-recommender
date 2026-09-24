"""
test_explainability.py

Unit tests for ExplainabilityEngine and Why-Not Diagnostic (Phase 13).
Validates faithful score verification (exact capped rewards, no rounding distortion),
counterfactual exclusion audits, clinical citations, and fallback guidance.
"""

from pathlib import Path
import pytest
from src.recommender.profile import UserProfile
from src.recommender.engine import RecommendationEngine, MealRecommendation
from src.recommender.explainability import ExplainabilityEngine, MealExplanation


@pytest.fixture(scope="module")
def rec_engine():
    return RecommendationEngine()


@pytest.fixture(scope="module")
def exp_engine():
    return ExplainabilityEngine()


def test_faithful_score_verification(rec_engine, exp_engine):
    """
    Key test for Explainable AI (XAI) faithfulness:
    Verifies that the human-facing explanation reports the EXACT computed numbers,
    respecting caps (50 for protein, 25 for fibre) and summing identically to total score.
    """
    profile = UserProfile(age=20, sex="MALE", height_cm=170.0, weight_kg=65.0)
    rec = rec_engine.recommend_meal(profile, date_str="2026-10-01", slot_str="LUNCH")
    exp = exp_engine.explain_recommendation(rec, profile)

    assert exp.status == "SUCCESS"
    assert "Plain Rice" in exp.selected_dishes or "Chapati" in exp.selected_dishes

    comps = exp.score_explanation["components"]
    s_energy = comps["energy_proximity_score"]["score"]
    s_protein = comps["protein_reward"]["score"]
    s_fibre = comps["fibre_reward"]["score"]
    s_health = comps["clinical_health_modifiers"]["score"]

    # Verify caps
    assert s_protein <= 50.0
    assert s_fibre <= 25.0
    assert comps["energy_proximity_score"]["max_possible"] == 100.0

    # Verify exact sum faithfulness
    calculated_sum = round(s_energy + s_protein + s_fibre + s_health, 2)
    assert calculated_sum == exp.score_explanation["total_score"]
    assert calculated_sum == rec.total_score


def test_why_not_diagnostic_audit(rec_engine, exp_engine):
    """Verifies that every excluded dish is transparently audited with reason and citation."""
    profile_diab = UserProfile(
        age=20, sex="MALE", height_cm=170.0, weight_kg=65.0,
        dietary_preference="VEGETARIAN",
        health_conditions=["DIABETES"]
    )
    rec = rec_engine.recommend_meal(profile_diab, date_str="2026-10-01", slot_str="DINNER")
    exp = exp_engine.explain_recommendation(rec, profile_diab)

    # Custard must appear in why_not_audit
    assert "Custard" in exp.why_not_audit
    assert "HR_DIAB_001" in exp.why_not_audit["Custard"]
    assert "ICMR (2018)" in exp.why_not_audit["Custard"]


def test_fallback_explanation_guidance(exp_engine):
    """Verifies that depleted candidate pools generate actionable guidance rather than a blank error."""
    rec_fallback = MealRecommendation(
        status="NO_VALID_COMBINATION",
        slot="LUNCH",
        date="2026-10-15",
        diagnostic_message="Candidate pool depleted by stacked exclusions.",
        excluded_dishes={"Paneer Curry": ["DIET_FILTER"], "Pickle": ["HR_HTN_001"]}
    )
    profile = UserProfile(health_conditions=["HYPERTENSION"])
    exp = exp_engine.explain_recommendation(rec_fallback, profile)

    assert exp.status == "NO_VALID_COMBINATION"
    assert exp.selected_dishes == []
    assert exp.fallback_guidance is not None
    assert "canteen extras" in exp.fallback_guidance.lower()
    assert "Paneer Curry" in exp.why_not_audit
    assert "Pickle" in exp.why_not_audit


def test_clinical_justifications_grounding(rec_engine, exp_engine):
    profile_multi = UserProfile(
        age=22, sex="FEMALE", height_cm=160.0, weight_kg=55.0,
        health_conditions=["DIABETES", "HYPERTENSION", "PCOS"]
    )
    rec = rec_engine.recommend_meal(profile_multi, date_str="2026-10-01", slot_str="LUNCH")
    exp = exp_engine.explain_recommendation(rec, profile_multi)

    justs = " ".join(exp.clinical_justifications)
    assert "ICMR (2018)" in justs
    assert "IHG-IV (2019)" in justs
    assert "PCOS Guidelines (2023)" in justs
