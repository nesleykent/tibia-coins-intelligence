"""Independently verify launch-phase model coverage, splits and metrics.

    python scripts/45_verify_launch_models.py
"""
from __future__ import annotations

import gzip
import json
import pathlib
import pickle

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
MODEL_PATH = ROOT / "models" / "launch_phase_models.pkl.gz"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(actual: float, expected: float, label: str) -> None:
    if not np.isclose(actual, expected, rtol=1e-9, atol=1e-9):
        raise AssertionError(f"{label}: expected {expected}, found {actual}")


def main() -> None:
    registry = pd.read_csv(
        P / "launch_model_registry.csv",
        parse_dates=["created", "first", "last"],
    )
    holdout = pd.read_csv(
        P / "launch_model_holdout_predictions.csv",
        parse_dates=["date", "created"],
    )
    comparison = pd.read_csv(P / "launch_model_comparison.csv")
    latest = pd.read_csv(
        P / "latest_launch_predictions.csv",
        parse_dates=["as_of", "created"],
    )
    selection = pd.read_csv(P / "launch_model_estimator_selection.csv")
    results = json.loads((P / "launch_model_results.json").read_text())

    require(
        registry.world.nunique() == len(registry) == 21,
        "Registry must contain 21 unique training-eligible launch worlds",
    )
    require(
        set(registry.cohort) == {"train", "validation", "holdout"},
        "Launch registry must contain all three world-level cohorts",
    )
    require(
        registry.groupby("world", observed=True).cohort.nunique().max() == 1,
        "A launch world belongs to more than one cohort",
    )
    require(
        registry.groupby("pvp_type", observed=True).cohort.nunique().min() == 3,
        "Every PvP type must be represented in train, validation and holdout",
    )
    require(
        registry.groupby("pvp_type", observed=True).selected_estimator.nunique().max()
        == 1,
        "A PvP family has inconsistent estimator assignments",
    )
    require(
        set(registry.pvp_type)
        == {"Open PvP", "Optional PvP", "Retro Open PvP"},
        "Unexpected PvP family in launch models",
    )
    require(
        registry.loc[
            registry.pvp_type.eq("Retro Open PvP"),
            "low_sample_pvp_warning",
        ].astype(bool).all(),
        "Retro Open PvP must carry its low-sample warning",
    )

    selected = selection[selection.selected.astype(bool)]
    require(
        selected.pvp_type.nunique() == registry.pvp_type.nunique(),
        "Estimator selection must choose one model for every PvP type",
    )
    require(
        selected.set_index("pvp_type").candidate_estimator.to_dict()
        == registry.groupby("pvp_type", observed=True)
        .selected_estimator.first().to_dict(),
        "Estimator selection and registry disagree",
    )

    holdout_worlds = set(registry.query("cohort == 'holdout'").world)
    require(
        set(holdout.world) == holdout_worlds,
        "Holdout predictions do not contain exactly the held-out worlds",
    )
    require(
        holdout.date.min() >= pd.Timestamp(results["holdout_start"]),
        "A holdout prediction predates the declared holdout",
    )
    require(
        np.isfinite(
            holdout[
                [
                    "actual_change_pct",
                    "general_prediction_pct",
                    "launch_prediction_pct",
                ]
            ].to_numpy()
        ).all(),
        "Holdout predictions contain non-finite values",
    )
    require(
        holdout.age_days.between(0, results["max_age_days"]).all(),
        "A holdout row lies outside launch phase",
    )

    overall = comparison.query("scope == 'all'")
    require(len(overall) == 1, "Comparison must contain one overall row")
    overall = overall.iloc[0]
    actual = holdout.actual_change_pct.to_numpy()
    launch_error = holdout.launch_prediction_pct.to_numpy() - actual
    general_error = holdout.general_prediction_pct.to_numpy() - actual
    zero_error = -actual
    launch_rmse = float(np.sqrt(np.mean(launch_error**2)))
    general_rmse = float(np.sqrt(np.mean(general_error**2)))
    zero_rmse = float(np.sqrt(np.mean(zero_error**2)))
    close(launch_rmse, float(overall.launch_rmse_pct), "Launch RMSE")
    close(general_rmse, float(overall.general_rmse_pct), "General RMSE")
    close(zero_rmse, float(overall.zero_rmse_pct), "Zero RMSE")
    require(
        overall.better_model
        == min(
            {
                "launch": launch_rmse,
                "general": general_rmse,
                "zero": zero_rmse,
            },
            key={
                "launch": launch_rmse,
                "general": general_rmse,
                "zero": zero_rmse,
            }.get,
        ),
        "Reported holdout winner is incorrect",
    )

    for pvp_type, frame in holdout.groupby("pvp_type", observed=True):
        row = comparison.query(
            "scope == 'pvp_type' and scope_value == @pvp_type"
        )
        require(len(row) == 1, f"Missing comparison for {pvp_type}")
        row = row.iloc[0]
        pvp_launch_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        frame.launch_prediction_pct
                        - frame.actual_change_pct
                    )
                    ** 2
                )
            )
        )
        close(
            pvp_launch_rmse,
            float(row.launch_rmse_pct),
            f"{pvp_type} launch RMSE",
        )

    require(
        len(latest) == latest.world.nunique() == 18,
        "Latest launch predictions must contain 18 unique active worlds",
    )
    require(
        latest.age_days.between(0, results["max_age_days"]).all(),
        "A current prediction lies outside launch phase",
    )
    project_as_of = pd.Timestamp(results["active_as_of"])
    require(
        (
            (project_as_of - latest.as_of).dt.days
            == latest.stale_days.astype(int)
        ).all(),
        "Current launch prediction staleness is incorrect",
    )
    require(
        latest.stale_days.max() == results["max_prediction_staleness_days"],
        "Results metadata does not report maximum prediction staleness",
    )
    require(
        (
            latest.launch_low80_pct
            <= latest.launch_predicted_change_pct
        ).all()
        and (
            latest.launch_predicted_change_pct
            <= latest.launch_high80_pct
        ).all(),
        "A launch prediction lies outside its own interval",
    )

    with gzip.open(MODEL_PATH, "rb") as handle:
        artifact = pickle.load(handle)
    require(
        set(artifact["models"]) == set(registry.pvp_type),
        "Artifact must contain exactly one model per launch PvP type",
    )
    require(
        artifact["pvp_never_pooled"] is True,
        "Artifact must guarantee PvP isolation",
    )
    require(
        artifact["max_age_days"] == results["max_age_days"] == 540,
        "Launch phase cutoff must be 540 days",
    )
    require(
        results["active_launch_worlds"] == 18
        and results["training_eligible_worlds"] == 21,
        "Results metadata does not match output coverage",
    )

    print(
        "[LAUNCH MODEL VERIFY] PASS — "
        f"{len(registry)} training worlds, {len(latest)} active worlds, "
        f"{registry.pvp_type.nunique()} PvP-specific models"
    )
    print(
        f"  untouched cohort/date holdout: launch {launch_rmse:.3f}% vs "
        f"general {general_rmse:.3f}% vs zero {zero_rmse:.3f}% — "
        f"winner: {overall.better_model}"
    )


if __name__ == "__main__":
    main()
