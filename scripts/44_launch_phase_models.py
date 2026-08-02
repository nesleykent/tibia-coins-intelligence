"""Fit PvP-specific models for worlds in their launch phase.

Launch worlds are structurally different from mature worlds: they usually begin far from the
cross-world price level and converge over many months. This stage defines launch phase as the
first 540 days after creation (close to the observed 501-day median convergence time), models
each PvP type separately, and evaluates on later launch cohorts that are never seen in training.

The target is the seven-day change in the launch world's log-price deviation from the mature
61-world mean. The comparison model is the mature general model refitted without dates from the
launch holdout period. A zero-change baseline is reported as well.

Outputs:
    data/processed/launch_model_registry.csv
    data/processed/launch_model_estimator_selection.csv
    data/processed/launch_model_comparison.csv
    data/processed/launch_model_holdout_predictions.csv
    data/processed/latest_launch_predictions.csv
    data/processed/launch_model_results.json
    models/launch_phase_models.pkl.gz

    python scripts/44_launch_phase_models.py
"""
from __future__ import annotations

import gzip
import json
import pathlib
import pickle
import runpy
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
MODEL_PATH = ROOT / "models" / "launch_phase_models.pkl.gz"
GENERAL_MODEL_PATH = ROOT / "models" / "deviation_model.pkl"
RNG = 12345
HORIZON = 7
LAUNCH_MAX_AGE_DAYS = 540
MIN_MATURE_WORLDS = 10
MIN_WORLD_ROWS = 30
LOW_SAMPLE_WORLDS = 5

general_stage = runpy.run_path(str(ROOT / "scripts" / "30_model_artifact.py"))
GENERAL_FEATURES = general_stage["FEATURES"]
build_mature_panel = general_stage["build_panel"]
THRESHOLD = float(general_stage["THR"])

LAUNCH_FEATURES = GENERAL_FEATURES + [
    "age_days",
    "log_age_days",
    "days_observed",
    "log_days_observed",
    "first_observed_dev",
]

group_stage = runpy.run_path(str(ROOT / "scripts" / "41_group_models.py"))
newey_west_t = group_stage["newey_west_t"]


def launch_metadata() -> pd.DataFrame:
    worlds = pd.read_csv(
        P / "world_summary.csv",
        parse_dates=["created", "first", "last"],
    )
    metadata = pd.read_csv(P / "world_metadata.csv")[
        ["world", "game_world_type"]
    ]
    worlds = worlds.merge(metadata, on="world", how="left", validate="one_to_one")
    worlds = worlds[
        worlds["launch_in_window"].astype(bool)
        & worlds["game_world_type"].eq("regular")
    ].copy()
    worlds["battleye_color"] = np.where(
        worlds["battleye_date"].astype(str).str.lower().eq("release"),
        "green",
        "yellow",
    )
    return worlds[
        [
            "world",
            "created",
            "first",
            "last",
            "pvp_type",
            "battleye_color",
            "region",
            "n_obs",
        ]
    ].sort_values(["pvp_type", "created", "world"]).reset_index(drop=True)


def launch_panel(max_age_days: int = LAUNCH_MAX_AGE_DAYS) -> pd.DataFrame:
    panel = pd.read_csv(
        P / "panel_daily.csv",
        parse_dates=["date", "created"],
    )
    metadata = launch_metadata()
    launch_worlds = set(metadata["world"])

    mature = panel[
        panel["converged"].astype(bool) & panel["price_gp"].notna()
    ][["world", "date", "price_gp"]].copy()
    mature["logp"] = np.log(mature["price_gp"])
    mature_stats = (
        mature.groupby("date", observed=True)["logp"]
        .agg(mature_mean="mean", mature_count="size")
        .reset_index()
    )
    mature_stats.loc[
        mature_stats["mature_count"] < MIN_MATURE_WORLDS,
        "mature_mean",
    ] = np.nan

    frame = panel[
        panel["world"].isin(launch_worlds) & panel["price_gp"].notna()
    ][["world", "date", "created", "price_gp"]].copy()
    frame = frame.merge(
        metadata[
            ["world", "pvp_type", "battleye_color", "region", "first"]
        ],
        on="world",
        how="left",
        validate="many_to_one",
    )
    frame["age_days"] = (frame["date"] - frame["created"]).dt.days
    frame = frame[frame["age_days"].between(0, max_age_days)].copy()
    frame["logp"] = np.log(frame["price_gp"])
    frame = frame.merge(
        mature_stats,
        on="date",
        how="left",
        validate="many_to_one",
    )
    frame["dev"] = frame["logp"] - frame["mature_mean"]
    frame = frame.dropna(subset=["dev"]).sort_values(
        ["world", "date"]
    ).reset_index(drop=True)

    grouped = frame.groupby("world", observed=True)
    future_date = grouped["date"].shift(-HORIZON)
    frame["y"] = grouped["dev"].shift(-HORIZON) - frame["dev"]
    frame.loc[
        (future_date - frame["date"]).dt.days.ne(HORIZON),
        "y",
    ] = np.nan

    previous_date = grouped["date"].shift(1)
    frame["dev_l"] = grouped["dev"].shift(1)
    frame.loc[
        (frame["date"] - previous_date).dt.days.ne(1),
        "dev_l",
    ] = np.nan
    frame["absdev"] = frame["dev_l"].abs()
    frame["outside"] = (frame["absdev"] > THRESHOLD).astype(float)
    frame["dev_x_out"] = frame["dev_l"] * frame["outside"]
    frame["dev_sq"] = frame["dev_l"] * frame["absdev"]

    logp_lag1 = grouped["logp"].shift(1)
    logp_lag6 = grouped["logp"].shift(6)
    logp_lag22 = grouped["logp"].shift(22)
    date_lag6 = grouped["date"].shift(6)
    date_lag22 = grouped["date"].shift(22)
    frame["mom5"] = logp_lag1 - logp_lag6
    frame.loc[
        (previous_date - date_lag6).dt.days.ne(5),
        "mom5",
    ] = np.nan
    frame["mom21"] = logp_lag1 - logp_lag22
    frame.loc[
        (previous_date - date_lag22).dt.days.ne(21),
        "mom21",
    ] = np.nan

    daily_return = grouped["logp"].diff()
    daily_return.loc[
        grouped["date"].diff().dt.days.ne(1)
    ] = np.nan
    lagged_return = daily_return.groupby(frame["world"], observed=True).shift(1)
    frame["vol14"] = (
        lagged_return.groupby(frame["world"], observed=True)
        .rolling(14)
        .std()
        .reset_index(level=0, drop=True)
    )
    frame["dev_ma21"] = (
        frame["dev_l"]
        .groupby(frame["world"], observed=True)
        .rolling(21)
        .mean()
        .reset_index(level=0, drop=True)
    )
    frame["dev_sd21"] = (
        frame["dev_l"]
        .groupby(frame["world"], observed=True)
        .rolling(21)
        .std()
        .reset_index(level=0, drop=True)
    )

    mature_features = build_mature_panel().dropna(
        subset=["dev_l", "xw_disp"]
    )
    dispersion = (
        mature_features.groupby("date", observed=True)["xw_disp"]
        .first()
        .to_dict()
    )
    mature_deviation = {
        date: np.sort(group["dev_l"].to_numpy(dtype=float))
        for date, group in mature_features.groupby("date", observed=True)
    }
    frame["xw_disp"] = frame["date"].map(dispersion)
    frame["dev_rank"] = [
        (
            np.searchsorted(mature_deviation[date], value, side="right")
            / len(mature_deviation[date])
            if date in mature_deviation and pd.notna(value)
            else np.nan
        )
        for date, value in zip(frame["date"], frame["dev_l"], strict=True)
    ]

    frame["log_age_days"] = np.log1p(frame["age_days"])
    frame["days_observed"] = grouped.cumcount()
    frame["log_days_observed"] = np.log1p(frame["days_observed"])
    frame["first_observed_dev"] = grouped["dev"].transform("first")
    return frame


def cohort_registry(fit_panel: pd.DataFrame) -> pd.DataFrame:
    metadata = launch_metadata()
    complete = fit_panel.dropna(subset=LAUNCH_FEATURES + ["y"])
    counts = complete.groupby("world", observed=True).size()
    usable = metadata[metadata["world"].map(counts).fillna(0) >= MIN_WORLD_ROWS].copy()
    usable["complete_rows"] = usable["world"].map(counts).astype(int)
    usable["cohort"] = ""

    for _, indexes in usable.groupby("pvp_type", observed=True).groups.items():
        ordered = usable.loc[indexes].sort_values(["created", "world"]).index.tolist()
        n_worlds = len(ordered)
        n_holdout = max(1, int(np.floor(n_worlds * 0.30)))
        remaining = n_worlds - n_holdout
        n_validation = max(1, int(np.floor(remaining * 0.25)))
        if remaining - n_validation < 2:
            n_validation = max(1, remaining - 2)
        usable.loc[ordered[: remaining - n_validation], "cohort"] = "train"
        usable.loc[
            ordered[remaining - n_validation : remaining],
            "cohort",
        ] = "validation"
        usable.loc[ordered[remaining:], "cohort"] = "holdout"

    latest_date = pd.read_csv(P / "panel_daily.csv", usecols=["date"]).date.max()
    latest_date = pd.Timestamp(latest_date)
    usable["age_at_latest_days"] = (latest_date - usable["created"]).dt.days
    usable["currently_in_launch_phase"] = usable["age_at_latest_days"].between(
        0, LAUNCH_MAX_AGE_DAYS
    )
    usable["low_sample_pvp_warning"] = (
        usable.groupby("pvp_type", observed=True)["world"].transform("size")
        < LOW_SAMPLE_WORLDS
    )
    return usable.sort_values(
        ["pvp_type", "created", "world"]
    ).reset_index(drop=True)


def launch_estimator(name: str):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=20.0))
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=20,
            max_features=0.65,
            random_state=RNG,
            n_jobs=-1,
        )
    raise ValueError(f"Unsupported launch estimator {name}")


def fit_launch_models(
    frame: pd.DataFrame,
    estimator_by_pvp: dict[str, str],
) -> dict[str, object]:
    models: dict[str, object] = {}
    for pvp_type, estimator in estimator_by_pvp.items():
        scoped = frame[frame["pvp_type"].eq(pvp_type)].dropna(
            subset=LAUNCH_FEATURES + ["y"]
        )
        if scoped.empty:
            raise RuntimeError(f"No launch training rows for {pvp_type}")
        model = launch_estimator(estimator)
        model.fit(
            scoped[LAUNCH_FEATURES].to_numpy(),
            scoped["y"].to_numpy(),
        )
        models[pvp_type] = model
    return models


def score_launch(
    frame: pd.DataFrame,
    models: dict[str, object],
) -> pd.DataFrame:
    scored = frame.copy()
    scored["launch_prediction"] = np.nan
    for pvp_type, indexes in scored.groupby("pvp_type", observed=True).groups.items():
        model = models.get(pvp_type)
        if model is None:
            raise RuntimeError(f"Missing launch model for {pvp_type}")
        scored.loc[indexes, "launch_prediction"] = model.predict(
            scored.loc[indexes, LAUNCH_FEATURES].to_numpy()
        )
    if scored["launch_prediction"].isna().any():
        raise RuntimeError("Launch scoring produced missing predictions")
    return scored


def select_estimators(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    registry: pd.DataFrame,
) -> tuple[dict[str, str], pd.DataFrame]:
    selected: dict[str, str] = {}
    rows: list[dict] = []
    for pvp_type in sorted(registry["pvp_type"].unique()):
        scoped_train = train[train["pvp_type"].eq(pvp_type)].dropna(
            subset=LAUNCH_FEATURES + ["y"]
        )
        scoped_validation = validation[
            validation["pvp_type"].eq(pvp_type)
        ].dropna(subset=LAUNCH_FEATURES + ["y"])
        train_worlds = scoped_train["world"].nunique()
        candidates = ["ridge"]
        # Even a small-world launch cohort can have hundreds of daily rows. The forest is
        # allowed as a bounded alternative to a linear model, whose extrapolation can become
        # implausible when a new world begins far outside the historical feature range.
        if train_worlds >= 2 and len(scoped_train) >= 60:
            candidates.append("random_forest")
        candidate_rows: list[dict] = []
        for estimator in candidates:
            model = launch_estimator(estimator)
            model.fit(
                scoped_train[LAUNCH_FEATURES].to_numpy(),
                scoped_train["y"].to_numpy(),
            )
            prediction = model.predict(
                scoped_validation[LAUNCH_FEATURES].to_numpy()
            )
            rmse = float(
                np.sqrt(
                    np.mean(
                        (
                            prediction
                            - scoped_validation["y"].to_numpy()
                        )
                        ** 2
                    )
                )
            )
            candidate_rows.append(
                {
                    "pvp_type": pvp_type,
                    "candidate_estimator": estimator,
                    "train_worlds": int(train_worlds),
                    "validation_worlds": int(
                        scoped_validation["world"].nunique()
                    ),
                    "n_train": int(len(scoped_train)),
                    "n_validation": int(len(scoped_validation)),
                    "validation_rmse_pct": rmse * 100,
                }
            )
        best = min(candidate_rows, key=lambda row: row["validation_rmse_pct"])
        selected[pvp_type] = best["candidate_estimator"]
        for candidate in candidate_rows:
            candidate["selected"] = (
                candidate["candidate_estimator"]
                == best["candidate_estimator"]
            )
        rows.extend(candidate_rows)
    return selected, pd.DataFrame(rows)


def comparison_metrics(
    frame: pd.DataFrame,
    *,
    scope: str,
    scope_value: str,
) -> dict:
    actual = frame["y"].to_numpy(dtype=float)
    launch = frame["launch_prediction"].to_numpy(dtype=float)
    general = frame["general_prediction"].to_numpy(dtype=float)
    zero = np.zeros(len(frame))
    errors = {
        "launch": launch - actual,
        "general": general - actual,
        "zero": zero - actual,
    }
    rmse = {
        key: float(np.sqrt(np.mean(value**2)))
        for key, value in errors.items()
    }
    daily = pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "launch_sq": errors["launch"] ** 2,
            "general_sq": errors["general"] ** 2,
            "zero_sq": errors["zero"] ** 2,
        }
    ).groupby("date", observed=True).mean()
    general_t, general_p = newey_west_t(
        daily["general_sq"] - daily["launch_sq"],
        HORIZON - 1,
    )
    zero_t, zero_p = newey_west_t(
        daily["zero_sq"] - daily["launch_sq"],
        HORIZON - 1,
    )
    winner = min(rmse, key=rmse.get)
    return {
        "scope": scope,
        "scope_value": scope_value,
        "n_test": int(len(frame)),
        "n_dates": int(frame["date"].nunique()),
        "n_worlds": int(frame["world"].nunique()),
        "launch_rmse_pct": rmse["launch"] * 100,
        "general_rmse_pct": rmse["general"] * 100,
        "zero_rmse_pct": rmse["zero"] * 100,
        "launch_improvement_vs_general_pct": (
            (rmse["general"] - rmse["launch"]) / rmse["general"] * 100
        ),
        "launch_improvement_vs_zero_pct": (
            (rmse["zero"] - rmse["launch"]) / rmse["zero"] * 100
        ),
        "launch_mae_pct": float(np.mean(np.abs(errors["launch"])) * 100),
        "general_mae_pct": float(np.mean(np.abs(errors["general"])) * 100),
        "zero_mae_pct": float(np.mean(np.abs(errors["zero"])) * 100),
        "nw_t_launch_vs_general": general_t,
        "nw_p_launch_vs_general": general_p,
        "nw_t_launch_vs_zero": zero_t,
        "nw_p_launch_vs_zero": zero_p,
        "better_model": winner,
    }


def main() -> None:
    panel = launch_panel()
    fit_panel = panel.dropna(subset=LAUNCH_FEATURES + ["y"]).copy()
    registry = cohort_registry(panel)
    registry.to_csv(P / "launch_model_registry.csv", index=False)

    cohort_map = registry.set_index("world")["cohort"]
    fit_panel["cohort"] = fit_panel["world"].map(cohort_map)
    validation_worlds = set(registry.query("cohort == 'validation'")["world"])
    holdout_worlds = set(registry.query("cohort == 'holdout'")["world"])
    dates = np.sort(fit_panel["date"].unique())
    validation_start = pd.Timestamp(dates[int(len(dates) * 0.70)])
    holdout_start = pd.Timestamp(dates[int(len(dates) * 0.85)])

    selection_train = fit_panel[
        fit_panel["cohort"].eq("train")
        & (fit_panel["date"] < validation_start - pd.Timedelta(days=HORIZON))
    ]
    validation = fit_panel[
        fit_panel["cohort"].eq("validation")
        & (fit_panel["date"] >= validation_start)
        & (fit_panel["date"] < holdout_start)
    ]
    estimator_by_pvp, selection = select_estimators(
        selection_train,
        validation,
        registry,
    )
    selection.to_csv(
        P / "launch_model_estimator_selection.csv",
        index=False,
    )
    registry["selected_estimator"] = registry["pvp_type"].map(estimator_by_pvp)
    registry.to_csv(P / "launch_model_registry.csv", index=False)

    pre_holdout = fit_panel[
        ~fit_panel["world"].isin(holdout_worlds)
        & (fit_panel["date"] < holdout_start - pd.Timedelta(days=HORIZON))
    ]
    holdout = fit_panel[
        fit_panel["world"].isin(holdout_worlds)
        & (fit_panel["date"] >= holdout_start)
    ].copy()
    holdout_models = fit_launch_models(pre_holdout, estimator_by_pvp)
    holdout = score_launch(holdout, holdout_models)

    mature = build_mature_panel().dropna(subset=GENERAL_FEATURES + ["y"])
    mature_train = mature[
        mature["date"] < holdout_start - pd.Timedelta(days=HORIZON)
    ]
    general_holdout = RandomForestRegressor(
        n_estimators=400,
        min_samples_leaf=40,
        max_features=0.6,
        random_state=RNG,
        n_jobs=-1,
    ).fit(
        mature_train[GENERAL_FEATURES].to_numpy(),
        mature_train["y"].to_numpy(),
    )
    holdout["general_prediction"] = general_holdout.predict(
        holdout[GENERAL_FEATURES].to_numpy()
    )

    comparison_rows = [
        comparison_metrics(
            holdout,
            scope="all",
            scope_value="All launch holdout worlds",
        )
    ]
    for pvp_type, group in holdout.groupby("pvp_type", observed=True):
        comparison_rows.append(
            comparison_metrics(
                group,
                scope="pvp_type",
                scope_value=pvp_type,
            )
        )
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(P / "launch_model_comparison.csv", index=False)

    holdout_output = holdout[
        [
            "world",
            "date",
            "created",
            "age_days",
            "pvp_type",
            "battleye_color",
            "region",
            "y",
            "general_prediction",
            "launch_prediction",
        ]
    ].copy()
    holdout_output["actual_change_pct"] = holdout_output.pop("y") * 100
    holdout_output["general_prediction_pct"] = (
        holdout_output.pop("general_prediction") * 100
    )
    holdout_output["launch_prediction_pct"] = (
        holdout_output.pop("launch_prediction") * 100
    )
    holdout_output["launch_minus_general_pct"] = (
        holdout_output["launch_prediction_pct"]
        - holdout_output["general_prediction_pct"]
    )
    holdout_output.to_csv(
        P / "launch_model_holdout_predictions.csv",
        index=False,
    )

    holdout["launch_abs_error"] = (
        holdout["launch_prediction"] - holdout["y"]
    ).abs()
    overall_halfwidth = float(holdout["launch_abs_error"].quantile(0.80))
    pvp_halfwidth = (
        holdout.groupby("pvp_type", observed=True)["launch_abs_error"]
        .quantile(0.80)
        .to_dict()
    )

    production_models = fit_launch_models(fit_panel, estimator_by_pvp)
    current_date = pd.read_csv(
        P / "panel_daily.csv",
        usecols=["date"],
        parse_dates=["date"],
    )["date"].max()
    active_worlds = set(
        launch_metadata()
        .loc[
            lambda frame: (current_date - frame["created"]).dt.days.between(
                0, LAUNCH_MAX_AGE_DAYS
            ),
            "world",
        ]
    )
    latest = (
        panel.dropna(subset=LAUNCH_FEATURES)
        .sort_values("date")
        .groupby("world", observed=True)
        .tail(1)
        .copy()
    )
    latest = latest[latest["world"].isin(active_worlds)].copy()
    latest = score_launch(latest, production_models)

    with open(GENERAL_MODEL_PATH, "rb") as handle:
        general_artifact = pickle.load(handle)
    latest["general_prediction"] = general_artifact["model"].predict(
        latest[GENERAL_FEATURES].to_numpy()
    )
    general_halfwidth = float(
        general_artifact["conformal_halfwidth"]["0.2"]
    )
    latest["launch_halfwidth"] = (
        latest["pvp_type"].map(pvp_halfwidth).fillna(overall_halfwidth)
    )
    latest["general_predicted_change_pct"] = latest["general_prediction"] * 100
    latest["general_low80_pct"] = (
        latest["general_prediction"] - general_halfwidth
    ) * 100
    latest["general_high80_pct"] = (
        latest["general_prediction"] + general_halfwidth
    ) * 100
    latest["launch_predicted_change_pct"] = latest["launch_prediction"] * 100
    latest["launch_low80_pct"] = (
        latest["launch_prediction"] - latest["launch_halfwidth"]
    ) * 100
    latest["launch_high80_pct"] = (
        latest["launch_prediction"] + latest["launch_halfwidth"]
    ) * 100
    latest["launch_minus_general_pct"] = (
        latest["launch_predicted_change_pct"]
        - latest["general_predicted_change_pct"]
    )
    latest["deviation_pct"] = latest["dev_l"] * 100
    latest["selected_estimator"] = latest["pvp_type"].map(estimator_by_pvp)
    training_world_counts = registry.groupby(
        "pvp_type", observed=True
    )["world"].nunique()
    latest["model_worlds"] = latest["pvp_type"].map(training_world_counts)
    latest["low_sample_warning"] = latest["model_worlds"] < LOW_SAMPLE_WORLDS
    latest["stale_days"] = (current_date - latest["date"]).dt.days
    latest_output = latest[
        [
            "world",
            "date",
            "created",
            "age_days",
            "price_gp",
            "pvp_type",
            "battleye_color",
            "region",
            "model_worlds",
            "selected_estimator",
            "low_sample_warning",
            "stale_days",
            "deviation_pct",
            "general_predicted_change_pct",
            "general_low80_pct",
            "general_high80_pct",
            "launch_predicted_change_pct",
            "launch_low80_pct",
            "launch_high80_pct",
            "launch_minus_general_pct",
        ]
    ].rename(columns={"date": "as_of"}).sort_values(
        "launch_predicted_change_pct"
    )
    latest_output.to_csv(P / "latest_launch_predictions.csv", index=False)

    overall = comparison.query("scope == 'all'").iloc[0]
    convergence = json.loads((P / "results.json").read_text())["young"]
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "definition": (
            f"Regular worlds created inside the sample, from age 0 through "
            f"{LAUNCH_MAX_AGE_DAYS} days"
        ),
        "max_age_days": LAUNCH_MAX_AGE_DAYS,
        "observed_median_convergence_days": int(
            convergence["median_days_to_within_5pct"]
        ),
        "target": (
            "Seven-day change in a launch world's log-price deviation from "
            "the mature converged-world mean"
        ),
        "pvp_never_pooled": True,
        "battleye_not_split": (
            "Launch cohorts are overwhelmingly green; BattlEye separation "
            "is not identified"
        ),
        "launch_worlds_observed": int(len(launch_metadata())),
        "training_eligible_worlds": int(registry["world"].nunique()),
        "active_launch_worlds": int(latest_output["world"].nunique()),
        "active_as_of": str(pd.Timestamp(latest_output["as_of"].max()).date()),
        "max_prediction_staleness_days": int(latest_output["stale_days"].max()),
        "validation_start": str(pd.Timestamp(validation_start).date()),
        "holdout_start": str(pd.Timestamp(holdout_start).date()),
        "cohort_worlds": {
            key: int(value)
            for key, value in registry.groupby(
                "cohort", observed=True
            )["world"].nunique().items()
        },
        "pvp_worlds": {
            key: int(value)
            for key, value in registry.groupby(
                "pvp_type", observed=True
            )["world"].nunique().items()
        },
        "selected_estimators": estimator_by_pvp,
        "holdout": {
            key: value.item() if hasattr(value, "item") else value
            for key, value in overall.to_dict().items()
        },
        "outputs": {
            "registry": "data/processed/launch_model_registry.csv",
            "estimator_selection": (
                "data/processed/launch_model_estimator_selection.csv"
            ),
            "comparison": "data/processed/launch_model_comparison.csv",
            "holdout_predictions": (
                "data/processed/launch_model_holdout_predictions.csv"
            ),
            "latest_predictions": (
                "data/processed/latest_launch_predictions.csv"
            ),
            "artifact": "models/launch_phase_models.pkl.gz",
        },
    }
    (P / "launch_model_results.json").write_text(
        json.dumps(results, indent=2, default=str),
        encoding="utf-8",
    )

    artifact = {
        "version": 1,
        "generated_at": results["generated_at"],
        "definition": results["definition"],
        "target": results["target"],
        "horizon_days": HORIZON,
        "max_age_days": LAUNCH_MAX_AGE_DAYS,
        "features": LAUNCH_FEATURES,
        "general_features": GENERAL_FEATURES,
        "pvp_never_pooled": True,
        "registry": registry.to_dict("records"),
        "selected_estimators": estimator_by_pvp,
        "models": production_models,
        "launch_interval_halfwidth": pvp_halfwidth,
        "fallback_interval_halfwidth": overall_halfwidth,
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(MODEL_PATH, "wb", compresslevel=6) as handle:
        pickle.dump(artifact, handle, protocol=pickle.HIGHEST_PROTOCOL)

    fundamentals_path = P / "fundamentals_results.json"
    fundamentals = json.loads(fundamentals_path.read_text())
    fundamentals["launch_phase_models"] = results
    fundamentals_path.write_text(
        json.dumps(fundamentals, indent=1, default=str),
        encoding="utf-8",
    )

    print(
        f"[LAUNCH MODELS] {len(registry)} training-eligible worlds, "
        f"{len(latest_output)} active launch worlds, "
        f"holdout from {holdout_start.date()}"
    )
    print(
        "  selected: "
        + ", ".join(
            f"{pvp}={estimator}"
            for pvp, estimator in estimator_by_pvp.items()
        )
    )
    print(
        f"[HOLDOUT] launch {overall.launch_rmse_pct:.3f}% | "
        f"general {overall.general_rmse_pct:.3f}% | "
        f"zero {overall.zero_rmse_pct:.3f}% | "
        f"winner {overall.better_model}"
    )
    print(
        f"[LAUNCH MODELS] wrote {MODEL_PATH.relative_to(ROOT)} "
        f"({MODEL_PATH.stat().st_size / 1e6:.1f} MB)"
    )


if __name__ == "__main__":
    main()
