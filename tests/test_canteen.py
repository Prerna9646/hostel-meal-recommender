"""
test_canteen.py

Unit tests for Canteen Extras & Budget Optimization Layer (Phase 14).
Validates catalog data purity (strictly non-NaN verified IFCT nutrition),
dietary filtering on extras, gap-directed knapsack selection, and budget arithmetic.
"""

from pathlib import Path
import pandas as pd
import pytest
from src.recommender.profile import UserProfile
from src.recommender.engine import RecommendationEngine
from src.recommender.targets import compute_daily_targets, compute_slot_targets
from src.recommender.canteen import CanteenOptimizer, CanteenRecommendation


@pytest.fixture(scope="module")
def optimizer():
    return CanteenOptimizer()


@pytest.fixture(scope="module")
def rec_engine():
    return RecommendationEngine()


def test_canteen_extras_catalog_purity(optimizer):
    """Enforces research integrity: extras catalog must have zero NaN or INSUFFICIENT_DATA items."""
    df = optimizer.df
    assert len(df) == 8, f"Expected 8 canonical canteen extras, found {len(df)}"

    assert not df["energy_kcal"].isna().any(), "Found NaN energy in canteen extras catalog"
    assert not df["protein_g"].isna().any(), "Found NaN protein in canteen extras catalog"
    assert not df["fat_g"].isna().any(), "Found NaN fat in canteen extras catalog"
    assert not (df["calculation_status"] == "INSUFFICIENT_DATA").any(), "INSUFFICIENT_DATA dish present in extras"
    assert (df["price_inr"] > 0.0).all(), "Prices must be positive"


def test_no_budget_returns_no_extras(optimizer, rec_engine):
    profile = UserProfile(canteen_budget_inr=0.0)
    rec = rec_engine.recommend_meal(profile, date_str="2026-10-01", slot_str="LUNCH")
    daily = compute_daily_targets(profile)
    slot = compute_slot_targets(daily, "LUNCH")

    canteen_rec = optimizer.optimize_extras(rec, profile, slot)
    assert canteen_rec.status == "NO_BUDGET"
    assert len(canteen_rec.selected_extras) == 0
    assert canteen_rec.remaining_budget_inr == 0.0


def test_protein_gap_closure_eggetarian(optimizer, rec_engine):
    """An eggetarian student with budget selects Boiled Egg to close protein gap."""
    profile_egg = UserProfile(
        dietary_preference="EGGETARIAN",
        canteen_budget_inr=20.0,
        activity_level="HEAVY"  # High protein target
    )
    rec = rec_engine.recommend_meal(profile_egg, date_str="2026-10-01", slot_str="LUNCH")
    daily = compute_daily_targets(profile_egg)
    slot = compute_slot_targets(daily, "LUNCH")

    canteen_rec = optimizer.optimize_extras(rec, profile_egg, slot)
    assert canteen_rec.status == "SUCCESS"
    selected_dishes = [item["dish"] for item in canteen_rec.selected_extras]
    assert "Boiled Egg" in selected_dishes
    assert canteen_rec.remaining_budget_inr >= 0.0
    assert canteen_rec.combined_totals["protein_g"] > rec.nutritional_totals["protein_g"]


def test_vegetarian_dietary_restriction_on_extras(optimizer, rec_engine):
    """Vegetarian student with budget must NEVER be recommended Boiled Egg or Omelette."""
    profile_veg = UserProfile(
        dietary_preference="VEGETARIAN",
        canteen_budget_inr=50.0
    )
    rec = rec_engine.recommend_meal(profile_veg, date_str="2026-10-01", slot_str="LUNCH")
    daily = compute_daily_targets(profile_veg)
    slot = compute_slot_targets(daily, "LUNCH")

    canteen_rec = optimizer.optimize_extras(rec, profile_veg, slot)
    assert canteen_rec.status == "SUCCESS"
    for item in canteen_rec.selected_extras:
        assert item["dietary_tag"] == "VEGETARIAN"
        assert item["dish"] not in {"Boiled Egg", "Omelette"}


def test_budget_clamping_and_balance(optimizer, rec_engine):
    """Student with ₹10 budget cannot afford ₹15 or ₹25 items; selects ₹10 item."""
    profile = UserProfile(
        dietary_preference="VEGETARIAN",
        canteen_budget_inr=10.0
    )
    rec = rec_engine.recommend_meal(profile, date_str="2026-10-01", slot_str="LUNCH")
    daily = compute_daily_targets(profile)
    slot = compute_slot_targets(daily, "LUNCH")

    canteen_rec = optimizer.optimize_extras(rec, profile, slot)
    assert canteen_rec.status == "SUCCESS"
    assert canteen_rec.total_cost_inr <= 10.0
    assert canteen_rec.remaining_budget_inr == round(10.0 - canteen_rec.total_cost_inr, 1)
    for item in canteen_rec.selected_extras:
        assert item["price_inr"] <= 10.0
