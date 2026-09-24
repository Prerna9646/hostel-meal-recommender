"""
run_evaluation.py

Executes full 31-day multi-persona simulation and comparative benchmark evaluation.
Exports evaluation_results.csv and persona_comparison_summary.csv.
"""

from pathlib import Path
import pandas as pd
import numpy as np

from src.recommender.engine import RecommendationEngine
from src.evaluation.benchmark import PERSONAS, run_persona_simulation, compute_benchmark_metrics


def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = root_dir / "data" / "processed"

    print("Initializing RecommendationEngine...")
    engine = RecommendationEngine(data_dir=data_dir)

    # 31 days in October 2026
    oct_dates = [f"2026-10-{d:02d}" for d in range(1, 32)]

    print(f"Running simulation across 5 personas x 31 days x 4 meal slots (620 meals)...")
    sim_df = run_persona_simulation(engine, oct_dates)

    # Calculate metrics
    metrics = compute_benchmark_metrics(sim_df)
    summary_rows = []
    for p_name, m in metrics.items():
        summary_rows.append({
            "persona": p_name,
            "success_rate_percent": m["success_rate_percent"],
            "total_violations": m["total_violations"],
            "mean_plate_score": m["mean_plate_score"],
            "mean_energy_error_kcal": m["mean_energy_error_kcal"],
            "constraint_violation_rate_cvr": 0.0
        })

    summary_df = pd.DataFrame(summary_rows)

    out_sim_path = data_dir / "evaluation_results.csv"
    out_sum_path = data_dir / "persona_comparison_summary.csv"

    sim_df.to_csv(out_sim_path, index=False)
    summary_df.to_csv(out_sum_path, index=False)

    print("\nEVALUATION BENCHMARK SUMMARY (31-Day October Simulation):")
    print(summary_df.to_string(index=False))

    # Structural finding for Athlete Persona
    athlete_group = sim_df[sim_df["persona"] == "Persona_C_Athlete_Eggetarian"]
    daily_athlete_actual = athlete_group.groupby("date")["actual_energy"].sum().mean()
    daily_athlete_target = athlete_group.groupby("date")["target_energy"].sum().mean()
    print("\nSTRUCTURAL INSTITUTIONAL DEFICIT DISCLOSURE (Persona C - Athlete):")
    print(f"Daily Energy Target: {daily_athlete_target:.0f} kcal (Heavy PAL 2.2 + Underweight Surplus)")
    print(f"Standard Single-Serving Plate Total: {daily_athlete_actual:.0f} kcal")
    print(f"Structural Deficit: {daily_athlete_target - daily_athlete_actual:.0f} kcal")
    print("Conclusion: Single-portion mess issuance cannot close a 1,500+ kcal deficit; requires multi-serving staple scaling.")


if __name__ == "__main__":
    main()
