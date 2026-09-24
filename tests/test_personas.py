"""
test_personas.py

Unit tests for Multi-Persona Simulation and Comparative Evaluation (Phase 15).
Validates 0% Constraint Violation Rate (CVR) across 620 simulated meals,
strict condition adherence, and honest reporting of high-PAL portion ceilings.
"""

from pathlib import Path
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def eval_df():
    path = Path(__file__).resolve().parent.parent / "data" / "processed" / "evaluation_results.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def summary_df():
    path = Path(__file__).resolve().parent.parent / "data" / "processed" / "persona_comparison_summary.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


def test_simulation_dataset_completeness(eval_df):
    """Verifies that 620 total meal decisions were evaluated (5 personas x 31 days x 4 slots)."""
    assert len(eval_df) == 620
    assert eval_df["persona"].nunique() == 5
    assert eval_df["date"].nunique() == 31
    assert set(eval_df["slot"].unique()) == {"BREAKFAST", "LUNCH", "E_TEA", "DINNER"}


def test_zero_constraint_violations_across_all_personas(eval_df, summary_df):
    """
    Key academic claim: Constraint Satisfaction ensures 0.0% Constraint Violation Rate (CVR).
    Zero clinical violations, zero diet violations, zero unmapped commercial items served.
    """
    assert eval_df["clinical_violations"].sum() == 0
    assert eval_df["diet_violations"].sum() == 0
    assert eval_df["insufficient_data_violations"].sum() == 0
    assert (summary_df["total_violations"] == 0).all()
    assert (summary_df["constraint_violation_rate_cvr"] == 0.0).all()


def test_persona_a_diabetic_clinical_adherence(eval_df):
    diab_df = eval_df[eval_df["persona"] == "Persona_A_Diabetic_Female"]
    assert len(diab_df) == 124
    assert diab_df["clinical_violations"].sum() == 0
    assert diab_df["diet_violations"].sum() == 0


def test_persona_b_hypertensive_clinical_adherence(eval_df):
    htn_df = eval_df[eval_df["persona"] == "Persona_B_Hypertensive_Male"]
    assert len(htn_df) == 124
    assert htn_df["clinical_violations"].sum() == 0


def test_athlete_structural_energy_disclosure(eval_df):
    """
    Validates research honesty: single-serving institutional issuance cannot close
    a 2,000+ kcal deficit for a heavy-PAL varsity athlete requiring ~3,700 kcal.
    """
    ath_df = eval_df[eval_df["persona"] == "Persona_C_Athlete_Eggetarian"]
    daily_actual = ath_df.groupby("date")["actual_energy"].sum().mean()
    daily_target = ath_df.groupby("date")["target_energy"].sum().mean()

    # The actual energy is capped by single-portion size (~1,300-1,500 kcal)
    assert daily_actual < 2000.0
    assert daily_target > 3500.0
    assert (daily_target - daily_actual) > 1500.0
