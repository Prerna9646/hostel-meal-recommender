"""
app.py

Streamlit Web Interface for Explainable AI-Based Meal Recommendation.
Grounding: IFCT 2017 & ICMR-NIN 2020 Guidelines.
Features: Interactive student profiling, Asian Indian BMI classification,
constraint-satisfying meal assembly, faithful score decomposition,
user-friendly explainability, and canteen budget optimization.
"""

from pathlib import Path
import streamlit as st
import pandas as pd

from src.recommender.profile import UserProfile
from src.recommender.targets import compute_daily_targets, compute_slot_targets
from src.recommender.engine import RecommendationEngine
from src.recommender.explainability import ExplainabilityEngine
from src.recommender.canteen import CanteenOptimizer


st.set_page_config(page_title="Hostel Meal Recommender (IFCT 2017)", layout="wide")

# UI Chrome Sanitization: Hide Deploy button and footer branding; preserve appearance-mode menu
st.markdown(
    """
    <style>
    /* Hide Streamlit Deploy button across all Streamlit versions */
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    .stDeployButton,
    [data-testid="stDeployButton"] {
        display: none !important;
    }
    /* Hide footer branding on page and inside hamburger menu popover */
    footer,
    [data-testid="stFooter"],
    [data-testid="stMainMenuList"] + div,
    [data-testid="stMainMenuList"] ~ div,
    div:has(> .stMenuVersionCopyButton),
    .stMenuVersionCopyButton,
    [class*="enqxyix15"],
    [class*="enqxyix16"],
    [class*="enqxyix18"] {
        display: none !important;
        visibility: hidden !important;
    }
    /* Suppress developer chrome in hamburger menu (Rerun, Clear Cache, Print, Screen recording)
       while preserving Settings (Light / Dark / System appearance modes) intact */
    [data-testid="stMainMenuItem-rerun"],
    [data-testid="stMainMenuItem-autoRerun"],
    [data-testid="stMainMenuItem-clearCache"],
    [data-testid="stMainMenuItem-recordScreencast"],
    [data-testid="stMainMenuItem-print"],
    [data-testid="stMainMenuItem-about"],
    [data-testid="stMainMenuDivider"] {
        display: none !important;
    }
    /* Metric Cards: clean typography & prevent text collision / horizontal overflow */
    [data-testid="stMetricValue"] {
        overflow: hidden !important;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 1.25rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMetricLabel"] > div {
        font-size: 0.85rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    /* Sidebar specific metric styling */
    [data-testid="stSidebar"] [data-testid="stMetricValue"] > div {
        font-size: 1.05rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] > div {
        font-size: 0.82rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def format_why_not_reason(raw: str, profile: UserProfile) -> tuple[str, str]:
    """Translates internal audit strings to warm, student-friendly explanations with technical trace."""
    cleaned = raw.replace("EXCLUDED:", "").strip()
    if "DIET_FILTER" in raw:
        pref = profile.dietary_preference.replace("_", " ").title()
        return f"Not included — contains ingredients outside your {pref} preference.", cleaned
    if any(k in raw for k in ("HR_DIAB", "DIABETES")):
        return "Not included — high in simple sugars/sweets (managed for diabetes).", cleaned
    if any(k in raw for k in ("HR_HTN", "HYPERTENSION")):
        return "Not included — high-salt preserved item (managed for blood pressure).", cleaned
    if any(k in raw for k in ("HR_PCOS", "PCOS")):
        return "Not included — simple sugars restricted for PCOS metabolic balance.", cleaned
    if any(k in raw for k in ("HR_OBES", "OBESITY")):
        return "Not included — energy-dense item restricted for weight management.", cleaned
    if "INSUFFICIENT_DATA" in raw:
        return "Not included — packaged/commercial item without verified laboratory nutrition data.", cleaned
    if "SUBOPTIMAL" in raw:
        return "Not included — other available combinations achieved a closer match to your targets.", cleaned
    return "Not included — excluded per menu constraints.", cleaned


@st.cache_resource
def load_engines():
    rec_engine = RecommendationEngine()
    exp_engine = ExplainabilityEngine()
    can_optimizer = CanteenOptimizer()
    return rec_engine, exp_engine, can_optimizer


rec_engine, exp_engine, can_optimizer = load_engines()

# Exact Header & Subtitle
st.title("Explainable AI Meal Recommender for Hostel Students")
st.caption("Personalised, health-aware plate recommendations grounded in IFCT 2017 & ICMR-NIN 2020 guidelines")

# Sidebar: Student Profile
st.sidebar.header("1. Student Profile & Anthropometrics")
age = st.sidebar.slider("Age (years)", 17, 30, 20)
sex = st.sidebar.selectbox("Biological Sex", ["FEMALE", "MALE"])
ht = st.sidebar.number_input("Height (cm)", 130.0, 210.0, 165.0, step=0.5)
wt = st.sidebar.number_input("Weight (kg)", 35.0, 150.0, 60.0, step=0.5)
diet = st.sidebar.selectbox("Dietary Lifestyle", ["VEGETARIAN", "EGGETARIAN", "NON_VEG"])
act = st.sidebar.selectbox("Activity Level (PAL)", ["SEDENTARY", "LIGHT", "MODERATE", "HEAVY"])

# Dynamic health conditions: exclude PCOS for male physiology
health_options = (
    ["NONE", "DIABETES", "HYPERTENSION", "OBESITY"]
    if sex == "MALE"
    else ["NONE", "DIABETES", "HYPERTENSION", "PCOS", "OBESITY"]
)
conds = st.sidebar.multiselect("Health Conditions", health_options, default=["NONE"])

# Graceful sanitization if user switches sex to MALE with PCOS active
if sex == "MALE" and "PCOS" in conds:
    st.sidebar.warning("ℹ️ Note: PCOS applies to female physiology only and has been excluded from this profile.")
    conds = [c for c in conds if c != "PCOS"]
    if not conds:
        conds = ["NONE"]

budget = st.sidebar.number_input("Canteen Extras Budget (₹)", 0.0, 100.0, 0.0, step=5.0)
hostel = "GIRLS_HOSTEL" if sex == "FEMALE" else "COMMON"

try:
    profile = UserProfile(
        age=age, sex=sex, height_cm=ht, weight_kg=wt,
        dietary_preference=diet, hostel_type=hostel,
        activity_level=act, health_conditions=conds or ["NONE"],
        canteen_budget_inr=budget
    )
except ValueError as e:
    st.sidebar.error(f"⚠️ Profile Notice: {e}")
    st.stop()

# Display Anthropometrics Badge (2x2 layout avoiding clipping on narrow sidebar widths)
col_bmi1, col_bmi2 = st.sidebar.columns(2)
col_bmi1.metric("BMI", f"{profile.bmi}")
w_min, w_max = profile.healthy_weight_range_asian_kg
col_bmi2.metric("Healthy Wt (kg)", f"{w_min} – {w_max}")

col_bmi3, col_bmi4 = st.sidebar.columns(2)
col_bmi3.metric("Asian Status", profile.bmi_category_asian)
col_bmi4.metric("WHO Status", profile.bmi_category_who)

# Main Interface: Date and Slot Selection
st.subheader("2. Institutional Menu Query")
col_date, col_slot = st.columns(2)
date_str = col_date.selectbox("Menu Date (October 2026)", [f"2026-10-{d:02d}" for d in range(1, 32)])
slot_str = col_slot.selectbox("Operational Meal Slot", ["BREAKFAST", "LUNCH", "E_TEA", "DINNER"], index=1)

# Live Autonomous Recommendation on State Change (No Manual Trigger)
daily_targets = compute_daily_targets(profile)
slot_targets = compute_slot_targets(daily_targets, slot_str)
rec = rec_engine.recommend_meal(profile, date_str, slot_str)
exp = exp_engine.explain_recommendation(rec, profile)
canteen_rec = can_optimizer.optimize_extras(rec, profile, slot_targets)

# Display Recommendation
st.markdown("---")
if rec.status == "SUCCESS":
    st.success(f"**{exp.headline}**")
    cols_macro = st.columns(4)
    totals = rec.nutritional_totals
    t_targets = rec.target_nutrients

    cols_macro[0].metric("Energy", f"{totals['energy_kcal']} kcal", f"Target: {t_targets['target_energy_kcal']} kcal")
    cols_macro[1].metric("Protein", f"{totals['protein_g']} g", f"Target: {t_targets['protein_g']} g")
    cols_macro[2].metric("Dietary Fibre", f"{totals['fibre_g']} g", f"Target: {t_targets['fibre_g']} g")
    cols_macro[3].metric("Natural Sodium", f"{totals['sodium_mg']} mg", "Lower bound (salt unmeasured)")

    # Plate Composition Table
    with st.expander("🍽️ View Recommended Plate Composition & Plate Roles", expanded=True):
        plate_rows = []
        for d in rec.selected_dishes:
            d_class = rec_engine.class_df.loc[d]
            d_nutr = rec_engine.nutr_df.loc[d]
            plate_rows.append({
                "Dish Name": d,
                "Plate Role": d_class["plate_role"],
                "Dietary Tag": d_class["dietary_tag"],
                "Energy (kcal)": d_nutr["energy_kcal"],
                "Protein (g)": d_nutr["protein_g"],
                "Fibre (g)": d_nutr["fibre_g"]
            })
        st.dataframe(pd.DataFrame(plate_rows), width="stretch")

    # Canteen Extras Card
    if budget > 0:
        st.subheader("🛒 Canteen Extras & Budget Optimization")
        if canteen_rec.selected_extras:
            st.info(f"**Canteen Purchases:** " + " | ".join(canteen_rec.gap_closure_notes))
            st.write(f"Total Spent: ₹{canteen_rec.total_cost_inr} | Remaining Balance: ₹{canteen_rec.remaining_budget_inr}")
            st.metric("Combined Energy (Plate + Canteen)", f"{canteen_rec.combined_totals['energy_kcal']} kcal")
            st.metric("Combined Protein (Plate + Canteen)", f"{canteen_rec.combined_totals['protein_g']} g")
        else:
            st.write("No compliant canteen extras needed or affordable within budget.")
else:
    st.error(f"**Status: {rec.status}**")
    st.warning(f"**Diagnostic Explanation:** {exp.fallback_guidance}")

# Explainable AI & Why-Not Diagnostics
st.markdown("---")
st.subheader("3. Why This Meal Was Recommended (Transparency & Scoring)")

with st.expander("📊 How Your Meal Score Was Calculated", expanded=True):
    if rec.status == "SUCCESS":
        sb = exp.score_explanation["components"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Energy Match", f"{sb['energy_proximity_score']['score']} / 100", f"{sb['energy_proximity_score']['percent_met']}% met")
        c2.metric("Protein Score", f"{sb['protein_reward']['score']} / 50", f"{sb['protein_reward']['percent_met']}% met")
        c3.metric("Fibre Score", f"{sb['fibre_reward']['score']} / 25", f"{sb['fibre_reward']['percent_met']}% met")
        c4.metric("Health Bonus", f"{sb['clinical_health_modifiers']['score']:+.1f} pts")
        st.caption(f"**Overall Meal Score:** {exp.score_explanation['total_score']} points (sum of exact components)")

    if exp.clinical_justifications:
        st.markdown("**Active Guidelines Applied to Your Plate:**")
        for j in exp.clinical_justifications:
            st.markdown(f"- {j}")

with st.expander("🍽️ Why Other Menu Items Weren't Selected", expanded=False):
    st.write("Here is why other dishes served on today's menu were left off your recommended plate:")
    if exp.why_not_audit:
        for dish, raw_reason in exp.why_not_audit.items():
            user_text, tech_text = format_why_not_reason(raw_reason, profile)
            st.markdown(f"• **{dish}**: {user_text}")
    else:
        st.write("All candidate items on today's menu were incorporated into your plate.")
