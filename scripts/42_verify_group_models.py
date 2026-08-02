"""Independently verify the hierarchical group-specific model outputs.

This check intentionally consumes the published CSV/JSON/artifact files instead of
calling the model-building helpers. It validates coverage, pooling order, PvP
isolation, reported holdout metrics and deployable artifact completeness.

    python scripts/42_verify_group_models.py
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
MODEL_PATH = ROOT / "models" / "specific_models.pkl.gz"
MIN_WORLDS = 5


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(actual: float, expected: float, label: str) -> None:
    if not np.isclose(actual, expected, rtol=1e-9, atol=1e-9):
        raise AssertionError(f"{label}: expected {expected}, found {actual}")


def main() -> None:
    registry = pd.read_csv(P / "specific_model_registry.csv")
    holdout = pd.read_csv(
        P / "specific_model_holdout_predictions.csv",
        parse_dates=["date"],
    )
    comparison = pd.read_csv(P / "specific_model_comparison.csv")
    sensitivity = pd.read_csv(P / "specific_model_sensitivity.csv")
    latest = pd.read_csv(P / "latest_specific_predictions.csv")
    results = json.loads((P / "specific_model_results.json").read_text())

    require(len(registry) == 61, "Registry must contain the 61 eligible worlds")
    require(registry.world.nunique() == 61, "Each world must appear exactly once")
    require(not registry.isna().all(axis=1).any(), "Registry contains empty rows")
    require(
        registry.groupby("group_id").selected_estimator.nunique().max() == 1,
        "A group has inconsistent estimator assignments",
    )

    exact_counts = registry.groupby(
        ["pvp_type", "battleye_color", "region"], observed=True
    ).world.size()
    battleye_counts = registry.groupby(
        ["pvp_type", "battleye_color"], observed=True
    ).world.size()
    pvp_counts = registry.groupby("pvp_type", observed=True).world.size()

    for row in registry.itertuples(index=False):
        exact_n = int(exact_counts.loc[(row.pvp_type, row.battleye_color, row.region)])
        battleye_n = int(
            battleye_counts.loc[(row.pvp_type, row.battleye_color)]
        )
        pvp_n = int(pvp_counts.loc[row.pvp_type])
        require(
            row.model_pvp_type == row.pvp_type,
            f"{row.world}: model crosses PvP types",
        )
        if exact_n >= MIN_WORLDS:
            expected_level = "pvp_battleye_region"
            require(
                row.model_battleye_color == row.battleye_color
                and row.model_region == row.region
                and int(row.model_worlds) == exact_n,
                f"{row.world}: exact group scope is incorrect",
            )
        elif battleye_n >= MIN_WORLDS:
            expected_level = "pvp_battleye"
            require(
                row.model_battleye_color == row.battleye_color
                and pd.isna(row.model_region)
                and int(row.model_worlds) == battleye_n,
                f"{row.world}: region pooling is incorrect",
            )
        else:
            expected_level = "pvp"
            require(
                pd.isna(row.model_battleye_color)
                and pd.isna(row.model_region)
                and int(row.model_worlds) == pvp_n,
                f"{row.world}: BattlEye pooling is incorrect",
            )
        require(
            row.group_level == expected_level,
            f"{row.world}: expected {expected_level}, found {row.group_level}",
        )
        require(
            bool(row.low_sample_warning) == (int(row.model_worlds) < MIN_WORLDS),
            f"{row.world}: low-sample warning is inconsistent",
        )

    registry_map = registry.set_index("world")
    holdout_registry = holdout.world.map(registry_map.group_id)
    require(
        holdout_registry.eq(holdout.group_id).all(),
        "Holdout rows do not match registry assignments",
    )
    require(
        holdout.world.nunique() == 61 and holdout.date.nunique() > 100,
        "Holdout coverage is incomplete",
    )
    require(
        np.isfinite(
            holdout[
                [
                    "actual_change_pct",
                    "general_prediction_pct",
                    "specific_prediction_pct",
                ]
            ].to_numpy()
        ).all(),
        "Holdout predictions contain non-finite values",
    )

    overall = comparison.query("scope == 'all'")
    require(len(overall) == 1, "Comparison must have exactly one overall row")
    overall = overall.iloc[0]
    general_error = (
        holdout.general_prediction_pct - holdout.actual_change_pct
    ).to_numpy()
    specific_error = (
        holdout.specific_prediction_pct - holdout.actual_change_pct
    ).to_numpy()
    general_rmse = float(np.sqrt(np.mean(general_error**2)))
    specific_rmse = float(np.sqrt(np.mean(specific_error**2)))
    close(general_rmse, float(overall.general_rmse_pct), "General RMSE")
    close(specific_rmse, float(overall.specific_rmse_pct), "Specific RMSE")
    close(
        (general_rmse - specific_rmse) / general_rmse * 100,
        float(overall.specific_improvement_pct),
        "Specific improvement",
    )
    require(
        overall.better_model
        == ("specific" if specific_rmse < general_rmse else "general"),
        "Reported holdout winner is incorrect",
    )

    for pvp_type, frame in holdout.groupby("pvp_type", observed=True):
        row = comparison.query(
            "scope == 'pvp_type' and scope_value == @pvp_type"
        )
        require(len(row) == 1, f"Missing comparison for {pvp_type}")
        row = row.iloc[0]
        g_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        frame.general_prediction_pct
                        - frame.actual_change_pct
                    )
                    ** 2
                )
            )
        )
        s_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        frame.specific_prediction_pct
                        - frame.actual_change_pct
                    )
                    ** 2
                )
            )
        )
        close(g_rmse, float(row.general_rmse_pct), f"{pvp_type} general RMSE")
        close(s_rmse, float(row.specific_rmse_pct), f"{pvp_type} specific RMSE")

    require(
        latest.world.nunique() == 61 and len(latest) == 61,
        "Latest predictions must contain one row per eligible world",
    )
    require(
        latest.group_id.eq(latest.world.map(registry_map.group_id)).all(),
        "Latest predictions do not match registry assignments",
    )
    latest_numeric = latest[
        [
            "general_predicted_change_pct",
            "specific_predicted_change_pct",
            "specific_low80_pct",
            "specific_high80_pct",
        ]
    ].to_numpy()
    require(
        np.isfinite(latest_numeric).all(),
        "Latest predictions contain non-finite values",
    )
    require(
        (latest.specific_low80_pct <= latest.specific_predicted_change_pct).all()
        and (
            latest.specific_predicted_change_pct
            <= latest.specific_high80_pct
        ).all(),
        "A specific prediction lies outside its own interval",
    )

    require(
        set(sensitivity.min_group_worlds.astype(int)) == {4, 5, 6},
        "Sensitivity thresholds must be 4, 5 and 6",
    )
    sensitivity_total = sensitivity[
        [
            "n_exact_worlds",
            "n_region_pooled_worlds",
            "n_pvp_pooled_worlds",
        ]
    ].sum(axis=1)
    require(
        sensitivity_total.eq(61).all(),
        "Sensitivity pooling buckets must cover all eligible worlds",
    )

    with gzip.open(MODEL_PATH, "rb") as handle:
        artifact = pickle.load(handle)
    group_ids = set(registry.group_id)
    require(
        set(artifact["models"]) == group_ids,
        "Deployable artifact does not contain every registered model",
    )
    require(
        artifact["preferred_min_worlds"] == MIN_WORLDS,
        "Artifact minimum-world threshold is incorrect",
    )
    require(
        results["pvp_never_pooled"] is True,
        "Results metadata must guarantee PvP isolation",
    )
    require(
        results["eligible_worlds"] == 61
        and results["specific_models"] == registry.group_id.nunique(),
        "Results metadata does not match registry coverage",
    )

    levels = registry.groupby("group_level", observed=True).world.size().to_dict()
    print(
        "[GROUP MODEL VERIFY] PASS — "
        f"{registry.world.nunique()} worlds, {registry.group_id.nunique()} models; "
        f"exact={levels.get('pvp_battleye_region', 0)}, "
        f"region-pooled={levels.get('pvp_battleye', 0)}, "
        f"PvP-pooled={levels.get('pvp', 0)}"
    )
    print(
        f"  untouched holdout: general {general_rmse:.3f}% vs "
        f"specific {specific_rmse:.3f}% — winner: {overall.better_model}"
    )


if __name__ == "__main__":
    main()
