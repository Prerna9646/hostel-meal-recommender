"""
test_ui.py

Sanity and integration tests for the Streamlit UI (Phase 16).
Validates that the app script compiles cleanly, engine dependencies instantiate without error,
UI execution flows run seamlessly across test dates, and UI cleanup invariants hold.
"""

from pathlib import Path
import py_compile
import pytest
from src.recommender.profile import UserProfile
from src.recommender.engine import RecommendationEngine
from src.recommender.explainability import ExplainabilityEngine
from src.recommender.canteen import CanteenOptimizer
from src.evaluation.benchmark import PERSONAS


def test_app_syntax():
    app_path = Path(__file__).resolve().parent.parent / "app.py"
    assert app_path.exists(), "app.py does not exist"
    # Compiles without raising SyntaxError
    py_compile.compile(str(app_path), doraise=True)


def test_ui_cleanups():
    """Validates that UI cleanup rules are enforced in app.py."""
    app_path = Path(__file__).resolve().parent.parent / "app.py"
    code = app_path.read_text(encoding="utf-8")

    # 1. Literature registry and technical audit removed from student view
    assert "source_registry.csv" not in code, "Academic source registry should not be in app.py"
    assert "Scientific Literature Registry" not in code, "Literature registry section should be removed"
    assert "Technical Rule Audit" not in code, "Technical Rule Audit should be removed from visible UI"

    # 2. Exact Title and Subtitle
    assert 'Explainable AI Meal Recommender for Hostel Students' in code
    assert 'Personalised, health-aware plate recommendations grounded in IFCT 2017 & ICMR-NIN 2020 guidelines' in code

    # 3. Persona Preset selector removed (students directly customize profile)
    assert "Load Test Persona Preset" not in code, "Preset selector should be removed from visible UI"

    # 4. Residence Scope standalone widget removed
    assert 'st.sidebar.selectbox("Residence Scope"' not in code, "Residence Scope widget should be removed"

    # 5. Streamlit chrome suppression: footer branding, deploy button, and developer menu items hidden; #MainMenu intact
    assert ".stAppDeployButton" in code, "CSS should suppress stAppDeployButton"
    assert "footer" in code, "CSS should suppress footer"
    assert "stMainMenuItem-rerun" in code, "CSS should suppress Rerun"
    assert "stMainMenuItem-clearCache" in code, "CSS should suppress Clear Cache"
    assert "stMainMenuItem-print" in code, "CSS should suppress Print"
    assert "stMainMenuItem-recordScreencast" in code, "CSS should suppress Screen recording"
    assert "stMainMenuList" in code, "CSS should suppress Made with Streamlit version footer inside hamburger menu"
    assert "#MainMenu {" not in code, "CSS should not hide #MainMenu container so appearance/theme menu remains accessible"

    # 6. No manual autoplay or run button; live silent rerun
    assert "st.button" not in code, "No manual execution button in app.py; reactive live rerun preserved"

    # 7. Metric card layout: 2x2 grid to prevent truncation
    assert 'st.sidebar.columns(4)' not in code, "Sidebar should not cram 4 metrics into one row"
    assert 'st.sidebar.columns(2)' in code, "Sidebar should use 2-column layout to prevent truncation"

    # 8. PCOS dynamic exclusion for male physiology
    assert 'health_options' in code, "Should dynamically restrict health options based on sex"
    assert 'PCOS applies to female physiology only' in code, "Should handle PCOS on male profile gracefully"


def test_why_not_translation_logic():
    """Tests the display-layer translation of raw audit strings to user-friendly messages."""
    app_path = Path(__file__).resolve().parent.parent / "app.py"
    code = app_path.read_text(encoding="utf-8")

    # Extract format_why_not_reason definition
    fn_code = code[code.index("def format_why_not_reason"):code.index("@st.cache_resource")]
    scope = {"UserProfile": UserProfile}
    exec(fn_code, scope)
    format_fn = scope["format_why_not_reason"]

    profile = PERSONAS["Persona_A_Diabetic_Female"]

    # Diet filter translation
    user_txt, tech_txt = format_fn("EXCLUDED: DIET_FILTER: NON_VEG dish violates VEGETARIAN preference", profile)
    assert "Vegetarian" in user_txt
    assert "DIET_FILTER" in tech_txt

    # Insufficient data translation
    user_txt, tech_txt = format_fn("EXCLUDED: INSUFFICIENT_DATA: Commercial unmapped item cannot be scored", profile)
    assert "laboratory nutrition data" in user_txt
    assert "INSUFFICIENT_DATA" in tech_txt

    # Diabetes constraint translation
    user_txt, tech_txt = format_fn("EXCLUDED: [HR_DIAB_001] DIABETES: Prohibit concentrated sweets (ICMR 2018)", profile)
    assert "diabetes" in user_txt
    assert "HR_DIAB_001" in tech_txt

    # Hypertension constraint translation
    user_txt, tech_txt = format_fn("EXCLUDED: [HR_HTN_001] HYPERTENSION: Eliminate pickles (IHG-IV 2019)", profile)
    assert "blood pressure" in user_txt
    assert "HR_HTN_001" in tech_txt

    # Suboptimal score translation
    user_txt, tech_txt = format_fn("SUBOPTIMAL_SCORE", profile)
    assert "closer match" in user_txt


def test_app_pipeline_integration():
    """Simulates the backend data flow of app.py for all 5 personas."""
    rec_engine = RecommendationEngine()
    exp_engine = ExplainabilityEngine()
    can_optimizer = CanteenOptimizer()

    test_date = "2026-10-01"
    test_slot = "LUNCH"

    for p_name, profile in PERSONAS.items():
        rec = rec_engine.recommend_meal(profile, test_date, test_slot)
        exp = exp_engine.explain_recommendation(rec, profile)
        assert rec.status == "SUCCESS"
        assert exp.headline != ""
        assert len(rec.selected_dishes) >= 2
