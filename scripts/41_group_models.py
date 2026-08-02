"""Fit hierarchical group-specific relative-value models and compare them with the general model.

The existing production model is deliberately pooled across every converged world. This stage
adds a second family of models whose scope follows the requested market structure:

    PvP x BattlEye cohort x region
        -> if fewer than MIN_GROUP_WORLDS, pool regions
    PvP x BattlEye cohort
        -> if still fewer than MIN_GROUP_WORLDS, pool BattlEye cohorts
    PvP

PvP types are never mixed. A final PvP-only cohort is therefore fitted even when the number of
worlds remains below the preferred minimum; that condition is recorded as a low-sample warning.
BattlEye "green" means protected since release, while "yellow" means protection was retrofitted.

Validation is date-based. The first 70% of dates train a sensitivity comparison, the next 15%
validate the pooling threshold, and the final 15% remain untouched until the general-versus-
specific holdout comparison. Seven dates are purged between estimation and evaluation windows.

Outputs:
    data/processed/specific_model_registry.csv
    data/processed/specific_model_estimator_selection.csv
    data/processed/specific_model_sensitivity.csv
    data/processed/specific_model_comparison.csv
    data/processed/specific_model_holdout_predictions.csv
    data/processed/latest_specific_predictions.csv
    data/processed/specific_model_results.json
    models/specific_models.pkl.gz

    python scripts/41_group_models.py
"""
from __future__ import annotations

import gzip
import json
import pathlib
import pickle
import re
import runpy
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
MODEL_PATH = ROOT / "models" / "specific_models.pkl.gz"
RNG = 12345
HORIZON = 7
MIN_GROUP_WORLDS = 5
SENSITIVITY_THRESHOLDS = (4, 5, 6)
CV_TREES = 120
FINAL_TREES = 250
GENERAL_HOLDOUT_TREES = 400
MIN_TRAIN_ROWS = 250
MIN_LINEAR_ROWS = 30

base = runpy.run_path(str(ROOT / "scripts" / "30_model_artifact.py"))
FEATURES = base["FEATURES"]
THRESHOLD = float(base["THR"])
build_panel = base["build_panel"]


def slug(value: str) -> str:
    """Stable identifier safe for CSVs, URLs and artifact dictionaries."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def random_forest(n_estimators: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimators,
        min_samples_leaf=40,
        max_features=0.6,
        random_state=RNG,
        n_jobs=-1,
    )


def model_for_sample(
    n_rows: int,
    n_estimators: int,
    *,
    estimator: str | None = None,
) -> tuple[RegressorMixin, str]:
    """Use shrinkage instead of a high-variance forest for a forced tiny PvP cohort."""
    selected = estimator or (
        "ridge_low_sample" if n_rows < MIN_TRAIN_ROWS else "random_forest"
    )
    if selected == "ridge_low_sample":
        return (
            make_pipeline(StandardScaler(), Ridge(alpha=25.0)),
            "ridge_low_sample",
        )
    if selected == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0)), "ridge"
    if selected == "random_forest":
        return random_forest(n_estimators), "random_forest"
    raise ValueError(f"Unsupported estimator {selected}")


def eligible_metadata() -> pd.DataFrame:
    worlds = pd.read_csv(P / "world_summary.csv")
    worlds = worlds[worlds["converged"].astype(bool)].copy()
    # Tibia's green/yellow labels describe whether protection existed at world release.
    worlds["battleye_color"] = np.where(
        worlds["battleye_date"].astype(str).str.lower().eq("release"),
        "green",
        "yellow",
    )
    keep = [
        "world",
        "pvp_type",
        "battleye_color",
        "region",
        "battleye_date",
        "n_obs",
    ]
    return worlds[keep].sort_values("world").reset_index(drop=True)


def build_registry(min_group_worlds: int) -> pd.DataFrame:
    """Assign one scoring model to each world while retaining its full training pool."""
    worlds = eligible_metadata()
    exact_counts = worlds.groupby(
        ["pvp_type", "battleye_color", "region"], observed=True
    ).size()
    battleye_counts = worlds.groupby(
        ["pvp_type", "battleye_color"], observed=True
    ).size()
    pvp_counts = worlds.groupby("pvp_type", observed=True).size()

    rows: list[dict] = []
    for row in worlds.itertuples(index=False):
        exact_n = int(exact_counts.loc[(row.pvp_type, row.battleye_color, row.region)])
        battleye_n = int(battleye_counts.loc[(row.pvp_type, row.battleye_color)])
        pvp_n = int(pvp_counts.loc[row.pvp_type])

        if exact_n >= min_group_worlds:
            level = "pvp_battleye_region"
            group_id = "__".join(
                [slug(row.pvp_type), row.battleye_color, slug(row.region)]
            )
            model_battleye = row.battleye_color
            model_region = row.region
            model_worlds = exact_n
            fallback_reason = "Exact segment meets the preferred minimum"
        elif battleye_n >= min_group_worlds:
            level = "pvp_battleye"
            group_id = "__".join([slug(row.pvp_type), row.battleye_color, "all-regions"])
            model_battleye = row.battleye_color
            model_region = None
            model_worlds = battleye_n
            fallback_reason = (
                f"Exact segment has {exact_n} worlds; pooled across regions"
            )
        else:
            level = "pvp"
            group_id = "__".join([slug(row.pvp_type), "all-battleye", "all-regions"])
            model_battleye = None
            model_region = None
            model_worlds = pvp_n
            fallback_reason = (
                f"PvP × BattlEye segment has {battleye_n} worlds; pooled across "
                "regions and BattlEye cohorts"
            )

        rows.append(
            {
                "world": row.world,
                "pvp_type": row.pvp_type,
                "battleye_color": row.battleye_color,
                "region": row.region,
                "group_level": level,
                "group_id": group_id,
                "model_pvp_type": row.pvp_type,
                "model_battleye_color": model_battleye,
                "model_region": model_region,
                "exact_worlds": exact_n,
                "pvp_battleye_worlds": battleye_n,
                "model_worlds": model_worlds,
                "preferred_min_worlds": min_group_worlds,
                "low_sample_warning": bool(model_worlds < min_group_worlds),
                "fallback_reason": fallback_reason,
            }
        )

    registry = pd.DataFrame(rows)
    assigned = registry.groupby("group_id", observed=True).world.transform("size")
    registry["assigned_worlds"] = assigned.astype(int)
    return registry.sort_values(
        ["pvp_type", "battleye_color", "region", "world"]
    ).reset_index(drop=True)


def model_specs(registry: pd.DataFrame) -> list[dict]:
    cols = [
        "group_id",
        "group_level",
        "model_pvp_type",
        "model_battleye_color",
        "model_region",
        "model_worlds",
        "low_sample_warning",
    ]
    return registry[cols].drop_duplicates("group_id").to_dict("records")


def rows_for_spec(frame: pd.DataFrame, spec: dict) -> pd.Series:
    mask = frame["pvp_type"].eq(spec["model_pvp_type"])
    if pd.notna(spec["model_battleye_color"]):
        mask &= frame["battleye_color"].eq(spec["model_battleye_color"])
    if pd.notna(spec["model_region"]):
        mask &= frame["region"].eq(spec["model_region"])
    return mask


def fit_specific_models(
    train: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    n_estimators: int,
    estimator_by_group: dict[str, str] | None = None,
) -> tuple[dict[str, RegressorMixin], list[dict]]:
    models: dict[str, RegressorMixin] = {}
    diagnostics: list[dict] = []
    for spec in model_specs(registry):
        scoped = train[rows_for_spec(train, spec)]
        if len(scoped) < MIN_LINEAR_ROWS:
            raise RuntimeError(
                f"{spec['group_id']} has only {len(scoped)} training rows; "
                f"minimum is {MIN_LINEAR_ROWS}"
            )
        requested = (
            estimator_by_group.get(spec["group_id"])
            if estimator_by_group is not None
            else None
        )
        model, estimator = model_for_sample(
            len(scoped), n_estimators, estimator=requested
        )
        model.fit(
            scoped[FEATURES].to_numpy(), scoped["y"].to_numpy()
        )
        models[spec["group_id"]] = model
        diagnostics.append(
            {
                **spec,
                "n_train": int(len(scoped)),
                "train_worlds": int(scoped["world"].nunique()),
                "estimator": estimator,
            }
        )
    return models, diagnostics


def select_group_estimators(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    registry: pd.DataFrame,
) -> tuple[dict[str, str], pd.DataFrame]:
    """Choose each group's estimator before the final holdout is opened."""
    selected: dict[str, str] = {}
    rows: list[dict] = []
    for spec in model_specs(registry):
        scoped_train = train[rows_for_spec(train, spec)]
        assigned_worlds = set(
            registry.loc[registry.group_id.eq(spec["group_id"]), "world"]
        )
        scoped_validation = validation[
            validation.world.isin(assigned_worlds)
        ]
        if len(scoped_train) < MIN_LINEAR_ROWS or scoped_validation.empty:
            raise RuntimeError(
                f"Cannot select estimator for {spec['group_id']}: "
                f"{len(scoped_train)} training and {len(scoped_validation)} "
                "validation rows"
            )
        candidates = ["ridge"]
        if len(scoped_train) >= MIN_TRAIN_ROWS:
            candidates.append("random_forest")
        candidate_rows = []
        for estimator in candidates:
            model, fitted_name = model_for_sample(
                len(scoped_train), CV_TREES, estimator=estimator
            )
            model.fit(
                scoped_train[FEATURES].to_numpy(),
                scoped_train["y"].to_numpy(),
            )
            prediction = model.predict(
                scoped_validation[FEATURES].to_numpy()
            )
            rmse = float(
                np.sqrt(
                    np.mean((prediction - scoped_validation["y"].to_numpy()) ** 2)
                )
            )
            candidate_rows.append(
                {
                    **spec,
                    "candidate_estimator": fitted_name,
                    "n_train": int(len(scoped_train)),
                    "n_validation": int(len(scoped_validation)),
                    "validation_rmse_pct": rmse * 100,
                }
            )
        best = min(candidate_rows, key=lambda item: item["validation_rmse_pct"])
        selected[spec["group_id"]] = best["candidate_estimator"]
        for candidate in candidate_rows:
            candidate["selected"] = (
                candidate["candidate_estimator"]
                == best["candidate_estimator"]
            )
        rows.extend(candidate_rows)
    return selected, pd.DataFrame(rows)


def score_specific(
    frame: pd.DataFrame,
    registry: pd.DataFrame,
    models: dict[str, RegressorMixin],
) -> pd.DataFrame:
    scored = frame.merge(
        registry[
            [
                "world",
                "group_id",
                "group_level",
                "model_worlds",
                "low_sample_warning",
                "fallback_reason",
            ]
        ],
        on="world",
        how="left",
        validate="many_to_one",
    )
    scored["specific_prediction"] = np.nan
    for group_id, idx in scored.groupby("group_id", observed=True).groups.items():
        model = models.get(group_id)
        if model is None:
            raise RuntimeError(f"Missing fitted model for {group_id}")
        scored.loc[idx, "specific_prediction"] = model.predict(
            scored.loc[idx, FEATURES].to_numpy()
        )
    if scored["specific_prediction"].isna().any():
        missing = scored.loc[scored.specific_prediction.isna(), "world"].unique()
        raise RuntimeError(f"Specific predictions missing for {missing.tolist()}")
    return scored


def newey_west_t(values: pd.Series, lags: int) -> tuple[float, float]:
    x = values.dropna().to_numpy(dtype=float)
    if len(x) < 20:
        return np.nan, np.nan
    centered = x - x.mean()
    variance = float(np.dot(centered, centered) / len(x))
    for lag in range(1, min(lags, len(x) - 1) + 1):
        weight = 1 - lag / (lags + 1)
        covariance = float(
            np.dot(centered[lag:], centered[:-lag]) / len(x)
        )
        variance += 2 * weight * covariance
    if variance <= 0:
        return np.nan, np.nan
    statistic = float(x.mean() / np.sqrt(variance / len(x)))
    p_value = float(2 * (1 - stats.norm.cdf(abs(statistic))))
    return statistic, p_value


def comparison_metrics(
    frame: pd.DataFrame,
    *,
    scope: str,
    scope_value: str,
) -> dict:
    y = frame["y"].to_numpy()
    general = frame["general_prediction"].to_numpy()
    specific = frame["specific_prediction"].to_numpy()
    general_error = general - y
    specific_error = specific - y
    general_rmse = float(np.sqrt(np.mean(general_error**2)))
    specific_rmse = float(np.sqrt(np.mean(specific_error**2)))
    daily = (
        pd.DataFrame(
            {
                "date": frame["date"].to_numpy(),
                "general_sq": general_error**2,
                "specific_sq": specific_error**2,
            }
        )
        .groupby("date", observed=True)[["general_sq", "specific_sq"]]
        .mean()
    )
    dm_t, dm_p = newey_west_t(
        daily["general_sq"] - daily["specific_sq"], HORIZON - 1
    )
    denominator = float(np.sum(y**2))
    return {
        "scope": scope,
        "scope_value": scope_value,
        "n_test": int(len(frame)),
        "n_dates": int(frame["date"].nunique()),
        "n_worlds": int(frame["world"].nunique()),
        "general_rmse_pct": general_rmse * 100,
        "specific_rmse_pct": specific_rmse * 100,
        "specific_improvement_pct": (
            (general_rmse - specific_rmse) / general_rmse * 100
            if general_rmse
            else np.nan
        ),
        "general_mae_pct": float(np.mean(np.abs(general_error)) * 100),
        "specific_mae_pct": float(np.mean(np.abs(specific_error)) * 100),
        "general_r2_oos": (
            float(1 - np.sum(general_error**2) / denominator)
            if denominator
            else np.nan
        ),
        "specific_r2_oos": (
            float(1 - np.sum(specific_error**2) / denominator)
            if denominator
            else np.nan
        ),
        "general_direction_accuracy": float(
            np.mean(np.sign(general) == np.sign(y))
        ),
        "specific_direction_accuracy": float(
            np.mean(np.sign(specific) == np.sign(y))
        ),
        "dm_t_specific_vs_general": dm_t,
        "dm_p_specific_vs_general": dm_p,
        "better_model": "specific" if specific_rmse < general_rmse else "general",
    }


def comparison_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = [comparison_metrics(scored, scope="all", scope_value="All eligible worlds")]
    for pvp_type, group in scored.groupby("pvp_type", observed=True):
        rows.append(
            comparison_metrics(group, scope="pvp_type", scope_value=pvp_type)
        )
    for group_id, group in scored.groupby("group_id", observed=True):
        rows.append(
            comparison_metrics(group, scope="model_group", scope_value=group_id)
        )
    return pd.DataFrame(rows)


def split_frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dates = np.sort(panel["date"].unique())
    validation_start = int(len(dates) * 0.70)
    holdout_start = int(len(dates) * 0.85)
    train_end = max(1, validation_start - HORIZON)
    pre_holdout_end = max(validation_start + 1, holdout_start - HORIZON)
    return {
        "train": panel[panel.date < dates[train_end]].copy(),
        "validation": panel[
            (panel.date >= dates[validation_start])
            & (panel.date < dates[holdout_start])
        ].copy(),
        "pre_holdout": panel[panel.date < dates[pre_holdout_end]].copy(),
        "holdout": panel[panel.date >= dates[holdout_start]].copy(),
        "validation_start": pd.Timestamp(dates[validation_start]),
        "holdout_start": pd.Timestamp(dates[holdout_start]),
    }


def main() -> None:
    metadata = eligible_metadata()
    panel = build_panel().merge(
        metadata[
            ["world", "pvp_type", "battleye_color", "region", "battleye_date"]
        ],
        on="world",
        how="left",
        validate="many_to_one",
    )
    fit_panel = panel.dropna(subset=FEATURES + ["y"]).copy()
    frames = split_frames(fit_panel)

    print(
        f"[GROUP MODELS] {fit_panel.world.nunique()} worlds, "
        f"{len(fit_panel):,} complete world-days"
    )
    print(
        f"  validation from {frames['validation_start'].date()} | "
        f"untouched holdout from {frames['holdout_start'].date()}"
    )

    # The preferred minimum is set ex ante. Nearby thresholds are reported as a sensitivity
    # check rather than selected on the holdout.
    general_validation_model = random_forest(CV_TREES).fit(
        frames["train"][FEATURES].to_numpy(), frames["train"]["y"].to_numpy()
    )
    general_validation = general_validation_model.predict(
        frames["validation"][FEATURES].to_numpy()
    )
    sensitivity_rows: list[dict] = []
    for min_worlds in SENSITIVITY_THRESHOLDS:
        registry = build_registry(min_worlds)
        models, _ = fit_specific_models(
            frames["train"], registry, n_estimators=CV_TREES
        )
        scored = score_specific(frames["validation"], registry, models)
        scored["general_prediction"] = general_validation
        metric = comparison_metrics(
            scored, scope="validation_threshold", scope_value=str(min_worlds)
        )
        distribution = registry.groupby("group_level", observed=True).world.count()
        metric.update(
            {
                "min_group_worlds": min_worlds,
                "n_models": int(registry.group_id.nunique()),
                "n_exact_worlds": int(
                    distribution.get("pvp_battleye_region", 0)
                ),
                "n_region_pooled_worlds": int(
                    distribution.get("pvp_battleye", 0)
                ),
                "n_pvp_pooled_worlds": int(distribution.get("pvp", 0)),
            }
        )
        sensitivity_rows.append(metric)
        print(
            f"  sensitivity min={min_worlds}: "
            f"specific RMSE {metric['specific_rmse_pct']:.3f}% vs "
            f"general {metric['general_rmse_pct']:.3f}%"
        )
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(P / "specific_model_sensitivity.csv", index=False)

    registry = build_registry(MIN_GROUP_WORLDS)
    estimator_by_group, estimator_selection = select_group_estimators(
        frames["train"], frames["validation"], registry
    )
    estimator_selection.to_csv(
        P / "specific_model_estimator_selection.csv", index=False
    )
    registry["selected_estimator"] = registry["group_id"].map(
        estimator_by_group
    )
    registry.to_csv(P / "specific_model_registry.csv", index=False)
    estimator_counts = registry[
        ["group_id", "selected_estimator"]
    ].drop_duplicates().selected_estimator.value_counts()
    print(
        "  selected estimators: "
        + ", ".join(
            f"{name}={count}" for name, count in estimator_counts.items()
        )
    )

    # Final comparison: neither model sees the last 15% of dates.
    general_holdout_model = random_forest(GENERAL_HOLDOUT_TREES).fit(
        frames["pre_holdout"][FEATURES].to_numpy(),
        frames["pre_holdout"]["y"].to_numpy(),
    )
    holdout_models, holdout_model_diagnostics = fit_specific_models(
        frames["pre_holdout"],
        registry,
        n_estimators=FINAL_TREES,
        estimator_by_group=estimator_by_group,
    )
    holdout_scored = score_specific(frames["holdout"], registry, holdout_models)
    holdout_scored["general_prediction"] = general_holdout_model.predict(
        frames["holdout"][FEATURES].to_numpy()
    )
    comparison = comparison_table(holdout_scored)
    comparison.to_csv(P / "specific_model_comparison.csv", index=False)

    holdout_output = holdout_scored[
        [
            "world",
            "date",
            "pvp_type",
            "battleye_color",
            "region",
            "group_level",
            "group_id",
            "y",
            "general_prediction",
            "specific_prediction",
        ]
    ].copy()
    holdout_output["actual_change_pct"] = holdout_output.pop("y") * 100
    holdout_output["general_prediction_pct"] = (
        holdout_output.pop("general_prediction") * 100
    )
    holdout_output["specific_prediction_pct"] = (
        holdout_output.pop("specific_prediction") * 100
    )
    holdout_output["specific_minus_general_pct"] = (
        holdout_output["specific_prediction_pct"]
        - holdout_output["general_prediction_pct"]
    )
    holdout_output.to_csv(
        P / "specific_model_holdout_predictions.csv", index=False
    )

    overall = comparison.query("scope == 'all'").iloc[0]
    print(
        f"[HOLDOUT] general RMSE {overall.general_rmse_pct:.3f}% | "
        f"specific {overall.specific_rmse_pct:.3f}% | "
        f"improvement {overall.specific_improvement_pct:+.2f}% | "
        f"DM p={overall.dm_p_specific_vs_general:.4f}"
    )

    # Group-calibrated 80% intervals use residuals from the untouched evaluation period.
    holdout_scored["specific_abs_error"] = (
        holdout_scored["specific_prediction"] - holdout_scored["y"]
    ).abs()
    overall_halfwidth = float(
        holdout_scored["specific_abs_error"].quantile(0.80)
    )
    interval_halfwidth = (
        holdout_scored.groupby("group_id", observed=True)["specific_abs_error"]
        .quantile(0.80)
        .to_dict()
    )

    # Refit each specific model on every target-bearing row, then score the latest features.
    production_models, production_diagnostics = fit_specific_models(
        fit_panel,
        registry,
        n_estimators=FINAL_TREES,
        estimator_by_group=estimator_by_group,
    )
    latest = (
        panel.dropna(subset=FEATURES)
        .sort_values("date")
        .groupby("world", observed=True)
        .tail(1)
        .copy()
    )
    latest_scored = score_specific(latest, registry, production_models)
    general_latest = pd.read_csv(P / "latest_predictions.csv").rename(
        columns={
            "predicted_change_pct": "general_predicted_change_pct",
            "low80_pct": "general_low80_pct",
            "high80_pct": "general_high80_pct",
        }
    )
    latest_scored = latest_scored.merge(
        general_latest[
            [
                "world",
                "as_of",
                "general_predicted_change_pct",
                "general_low80_pct",
                "general_high80_pct",
            ]
        ],
        on="world",
        how="left",
        validate="one_to_one",
    )
    latest_scored["specific_predicted_change_pct"] = (
        latest_scored["specific_prediction"] * 100
    )
    latest_scored["specific_halfwidth_pct"] = latest_scored["group_id"].map(
        interval_halfwidth
    ).fillna(overall_halfwidth) * 100
    latest_scored["specific_low80_pct"] = (
        latest_scored["specific_predicted_change_pct"]
        - latest_scored["specific_halfwidth_pct"]
    )
    latest_scored["specific_high80_pct"] = (
        latest_scored["specific_predicted_change_pct"]
        + latest_scored["specific_halfwidth_pct"]
    )
    latest_scored["specific_minus_general_pct"] = (
        latest_scored["specific_predicted_change_pct"]
        - latest_scored["general_predicted_change_pct"]
    )
    latest_scored["deviation_pct"] = latest_scored["dev_l"] * 100
    latest_scored["outside_band"] = latest_scored["outside"].astype(bool)
    latest_output = latest_scored[
        [
            "world",
            "as_of",
            "price_gp",
            "pvp_type",
            "battleye_color",
            "region",
            "group_level",
            "group_id",
            "model_worlds",
            "low_sample_warning",
            "fallback_reason",
            "deviation_pct",
            "outside_band",
            "general_predicted_change_pct",
            "general_low80_pct",
            "general_high80_pct",
            "specific_predicted_change_pct",
            "specific_low80_pct",
            "specific_high80_pct",
            "specific_minus_general_pct",
        ]
    ].sort_values("specific_predicted_change_pct")
    latest_output.to_csv(P / "latest_specific_predictions.csv", index=False)

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": (
            "Seven-day change in a world's log-price deviation from the "
            "cross-world mean"
        ),
        "hierarchy": [
            "PvP × BattlEye × region",
            "PvP × BattlEye, regions pooled",
            "PvP, regions and BattlEye cohorts pooled",
        ],
        "pvp_never_pooled": True,
        "battleye_definition": {
            "green": "battleye_date == release",
            "yellow": "BattlEye retrofitted after world release",
        },
        "preferred_min_worlds": MIN_GROUP_WORLDS,
        "sensitivity_thresholds": list(SENSITIVITY_THRESHOLDS),
        "eligible_worlds": int(registry.world.nunique()),
        "specific_models": int(registry.group_id.nunique()),
        "selected_estimators": {
            key: int(value) for key, value in estimator_counts.items()
        },
        "low_sample_models": int(
            registry.loc[registry.low_sample_warning, "group_id"].nunique()
        ),
        "validation_start": str(frames["validation_start"].date()),
        "holdout_start": str(frames["holdout_start"].date()),
        "holdout": {
            key: (
                value.item()
                if hasattr(value, "item")
                else value
            )
            for key, value in overall.to_dict().items()
        },
        "group_level_worlds": {
            key: int(value)
            for key, value in registry.groupby(
                "group_level", observed=True
            ).world.count().items()
        },
        "outputs": {
            "registry": "data/processed/specific_model_registry.csv",
            "estimator_selection": (
                "data/processed/specific_model_estimator_selection.csv"
            ),
            "sensitivity": "data/processed/specific_model_sensitivity.csv",
            "comparison": "data/processed/specific_model_comparison.csv",
            "holdout_predictions": (
                "data/processed/specific_model_holdout_predictions.csv"
            ),
            "latest_predictions": (
                "data/processed/latest_specific_predictions.csv"
            ),
            "artifact": "models/specific_models.pkl.gz",
        },
    }
    (P / "specific_model_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )

    artifact = {
        "version": 1,
        "generated_at": results["generated_at"],
        "target": results["target"],
        "horizon_days": HORIZON,
        "features": FEATURES,
        "band_threshold": THRESHOLD,
        "preferred_min_worlds": MIN_GROUP_WORLDS,
        "hierarchy": results["hierarchy"],
        "registry": registry.to_dict("records"),
        "models": production_models,
        "model_diagnostics": production_diagnostics,
        "holdout_model_diagnostics": holdout_model_diagnostics,
        "specific_interval_halfwidth": interval_halfwidth,
        "fallback_interval_halfwidth": overall_halfwidth,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(MODEL_PATH, "wb", compresslevel=6) as handle:
        pickle.dump(artifact, handle, protocol=pickle.HIGHEST_PROTOCOL)

    fundamentals_path = P / "fundamentals_results.json"
    fundamentals = (
        json.loads(fundamentals_path.read_text())
        if fundamentals_path.exists()
        else {}
    )
    fundamentals["group_specific_models"] = results
    fundamentals_path.write_text(
        json.dumps(fundamentals, indent=1, default=str), encoding="utf-8"
    )

    print(
        f"[GROUP MODELS] wrote {registry.group_id.nunique()} models "
        f"({MODEL_PATH.stat().st_size / 1e6:.1f} MB compressed), "
        f"{len(latest_output)} latest predictions"
    )


if __name__ == "__main__":
    main()
