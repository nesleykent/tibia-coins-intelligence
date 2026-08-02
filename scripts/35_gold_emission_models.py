"""Compare kill-count and monetary-emission variables on equivalent samples.

The regressions are descriptive/predictive, not causal. They use world and date fixed effects,
activity controls, a lagged dependent variable, and Cameron-Gelbach-Miller two-way clustered
standard errors by world and date.

    python scripts/35_gold_emission_models.py
"""
from __future__ import annotations

import json
import pathlib
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning)


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
HORIZONS = (1, 7, 30)
LAGS = (1, 7, 14, 30, 60, 90)
MA_WINDOWS = (7, 14, 30, 60, 90)
COVERAGE_THRESHOLDS = (0.80, 0.90, 0.95)

SERIES = {
    "kill_count": "total_kills",
    "direct_coin": "direct_coin_gp",
    "potential_max": "potential_total_gp_max",
    "realized_25": "realized_estimate_gp_25",
    "realized_50": "realized_estimate_gp_50",
    "realized_75": "realized_estimate_gp_75",
    "realized_100": "realized_estimate_gp_100",
}


def group_demean(values: np.ndarray, codes: np.ndarray) -> None:
    count = np.bincount(codes)
    for column in range(values.shape[1]):
        total = np.bincount(codes, weights=values[:, column])
        mean = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
        values[:, column] -= mean[codes]


def two_way_within(values: np.ndarray, world: np.ndarray, date: np.ndarray) -> np.ndarray:
    transformed = values.astype(float, copy=True)
    for _ in range(100):
        previous = transformed.copy()
        group_demean(transformed, world)
        group_demean(transformed, date)
        if np.max(np.abs(transformed - previous)) < 1e-10:
            break
    return transformed


def cluster_meat(score: np.ndarray, codes: np.ndarray) -> np.ndarray:
    grouped = np.zeros((codes.max() + 1, score.shape[1]))
    np.add.at(grouped, codes, score)
    return grouped.T @ grouped


def fe_model(frame: pd.DataFrame, y: str, x: str, controls: list[str]) -> dict | None:
    columns = [y, x, *controls]
    data = frame[["world", "date", *columns]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 500 or data.world.nunique() < 5 or data.date.nunique() < 10:
        return None
    world_codes, worlds = pd.factorize(data.world, sort=True)
    date_codes, dates = pd.factorize(data.date, sort=True)
    within = two_way_within(data[columns].to_numpy(float), world_codes, date_codes)
    yv, X = within[:, 0], within[:, 1:]
    keep = X.std(axis=0) > 1e-12
    if not keep[0]:
        return None
    X = X[:, keep]
    names = np.array([x, *controls])[keep]
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ yv
    residual = yv - X @ beta
    score = X * residual[:, None]
    world_meat = cluster_meat(score, world_codes)
    date_meat = cluster_meat(score, date_codes)
    observation_meat = score.T @ score
    n, k = len(data), X.shape[1]
    world_groups, date_groups = len(worlds), len(dates)
    common_correction = (n - 1) / max(n - k, 1)
    world_correction = world_groups / max(world_groups - 1, 1) * common_correction
    date_correction = date_groups / max(date_groups - 1, 1) * common_correction
    observation_correction = n / max(n - k, 1)
    covariance_two_way = xtx_inv @ (
        world_correction * world_meat
        + date_correction * date_meat
        - observation_correction * observation_meat
    ) @ xtx_inv
    covariance_world = xtx_inv @ (world_correction * world_meat) @ xtx_inv
    covariance_date = xtx_inv @ (date_correction * date_meat) @ xtx_inv
    raw_variance = np.diag(covariance_two_way)
    # Finite samples can make the two-way inclusion-exclusion diagonal non-positive.
    # A conservative floor at the larger one-way clustered variance avoids reporting an
    # imaginary or spuriously tiny standard error while preserving two-way clustering.
    variance_floor = np.maximum(
        np.diag(covariance_world), np.diag(covariance_date)
    )
    variance = np.maximum(raw_variance, variance_floor)
    floor_applied = variance > raw_variance + 1e-18
    se = np.sqrt(np.clip(variance, 0, None))
    index = int(np.where(names == x)[0][0])
    coefficient = beta[index]
    stderr = se[index]
    ss_total = np.sum(yv**2)
    r2 = 1 - np.sum(residual**2) / ss_total if ss_total > 0 else np.nan
    return {
        "coefficient": float(coefficient),
        "std_error_two_way": float(stderr),
        "t_stat": float(coefficient / stderr) if stderr > 0 else np.nan,
        "p_value": float(2 * stats.norm.sf(abs(coefficient / stderr)))
        if stderr > 0
        else np.nan,
        "r2_within": float(r2),
        "cluster_variance_floor_applied": bool(floor_applied[index]),
        "n": int(len(data)),
        "n_worlds": int(len(worlds)),
        "n_dates": int(len(dates)),
        "date_start": str(pd.Timestamp(data.date.min()).date()),
        "date_end": str(pd.Timestamp(data.date.max()).date()),
    }


def prepare() -> pd.DataFrame:
    emissions = pd.read_csv(P / "gold_emission_daily.csv", parse_dates=["date"])
    prices = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])[
        ["world", "date", "price_gp", "converged"]
    ].rename(columns={"converged": "price_converged"})
    data = (
        emissions.merge(prices, on=["world", "date"], how="inner")
        .sort_values(["world", "date"])
        .reset_index(drop=True)
    )
    data = data[data.price_converged & ~data.low_quality_flag].copy()
    group = data.groupby("world", observed=True)
    data["log_price"] = np.log(data.price_gp)
    data["return_1d"] = group.log_price.diff()
    data["lagged_return_1d"] = group.return_1d.shift(1)
    data["log_online"] = np.log1p(data.players_online_avg)
    data["online_growth"] = group.log_online.diff()
    for name, column in SERIES.items():
        data[f"log_{name}"] = np.log1p(data[column])
        data[f"growth_{name}"] = group[f"log_{name}"].diff()
    data["log_potential_with_bosses"] = np.log1p(
        data.potential_total_gp_max_with_bosses
    )
    data["growth_potential_with_bosses"] = group.log_potential_with_bosses.diff()
    for horizon in HORIZONS:
        data[f"forward_return_{horizon}d"] = (
            group.log_price.shift(-horizon) - data.log_price
        )
    return data


def lag_and_ma_models(data: pd.DataFrame) -> pd.DataFrame:
    group = data.groupby("world", observed=True)
    rows: list[dict] = []
    controls = ["lagged_return_1d", "online_growth_lag"]
    for lag in LAGS:
        data["online_growth_lag"] = group.online_growth.shift(lag)
        exposures = []
        for name in SERIES:
            column = f"x_{name}_lag{lag}"
            data[column] = group[f"growth_{name}"].shift(lag)
            exposures.append(column)
        common = [
            *exposures,
            "lagged_return_1d",
            "online_growth_lag",
            *[f"forward_return_{horizon}d" for horizon in HORIZONS],
        ]
        for horizon in HORIZONS:
            sample = data.dropna(
                subset=[*exposures, *controls, f"forward_return_{horizon}d"]
            )
            for name, exposure in zip(SERIES, exposures):
                result = fe_model(
                    sample, f"forward_return_{horizon}d", exposure, controls
                )
                if result:
                    rows.append(
                        {
                            "model_type": "shock_lag",
                            "series": name,
                            "horizon_days": horizon,
                            "lag_or_window_days": lag,
                            **result,
                        }
                    )

    for window in MA_WINDOWS:
        data["online_growth_lag"] = group.online_growth.shift(1)
        exposures = []
        for name in SERIES:
            column = f"x_{name}_ma{window}"
            data[column] = (
                group[SERIES[name]]
                .rolling(window, min_periods=max(3, window // 2))
                .mean()
                .reset_index(level=0, drop=True)
                .groupby(data.world, observed=True)
                .shift(1)
            )
            data[column] = np.log1p(data[column])
            exposures.append(column)
        for horizon in HORIZONS:
            sample = data.dropna(
                subset=[*exposures, *controls, f"forward_return_{horizon}d"]
            )
            for name, exposure in zip(SERIES, exposures):
                result = fe_model(
                    sample, f"forward_return_{horizon}d", exposure, controls
                )
                if result:
                    rows.append(
                        {
                            "model_type": "moving_average_level",
                            "series": name,
                            "horizon_days": horizon,
                            "lag_or_window_days": window,
                            **result,
                        }
                    )
    return pd.DataFrame(rows)


def level_models(data: pd.DataFrame) -> pd.DataFrame:
    group = data.groupby("world", observed=True)
    data = data.copy()
    data["log_cumulative_realized_50"] = np.log1p(
        data.cumulative_realized_estimate_gp_50
    )
    data["log_cumulative_kills"] = np.log1p(group.total_kills.cumsum())
    rows = []
    for name, exposure in {
        "kill_count_cumulative": "log_cumulative_kills",
        "realized_50_cumulative": "log_cumulative_realized_50",
    }.items():
        result = fe_model(data, "log_price", exposure, ["log_online"])
        if result:
            rows.append(
                {
                    "model_type": "cumulative_index_level",
                    "series": name,
                    "horizon_days": 0,
                    "lag_or_window_days": 0,
                    **result,
                }
            )
    return pd.DataFrame(rows)


def oos_models(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group = data.groupby("world", observed=True)
    for name in SERIES:
        data[f"oos_{name}_lag1"] = group[f"growth_{name}"].shift(1)
        data[f"oos_{name}_lag7"] = group[f"growth_{name}"].shift(7)
        data[f"oos_{name}_lag30"] = group[f"growth_{name}"].shift(30)
    dates = np.sort(data.date.unique())
    cutoff = dates[int(len(dates) * 0.70)]
    world_dummies = pd.get_dummies(data.world, prefix="world", drop_first=True, dtype=float)
    base = pd.concat([data.reset_index(drop=True), world_dummies.reset_index(drop=True)], axis=1)
    dummy_columns = list(world_dummies.columns)

    for horizon in HORIZONS:
        common_numeric = [
            "lagged_return_1d",
            "online_growth",
            *[
                f"oos_{name}_lag{lag}"
                for name in SERIES
                for lag in (1, 7, 30)
            ],
        ]
        sample = base.dropna(
            subset=[f"forward_return_{horizon}d", *common_numeric]
        ).copy()
        train_mask = sample.date < cutoff
        test_mask = sample.date >= cutoff
        if train_mask.sum() < 500 or test_mask.sum() < 100:
            continue
        y_train = sample.loc[train_mask, f"forward_return_{horizon}d"].to_numpy()
        y_test = sample.loc[test_mask, f"forward_return_{horizon}d"].to_numpy()
        baseline_rmse = float(np.sqrt(np.mean(y_test**2)))
        for name in SERIES:
            numeric = [
                f"oos_{name}_lag1",
                f"oos_{name}_lag7",
                f"oos_{name}_lag30",
                "lagged_return_1d",
                "online_growth",
            ]
            train_numeric = sample.loc[train_mask, numeric].to_numpy(float)
            test_numeric = sample.loc[test_mask, numeric].to_numpy(float)
            mean = train_numeric.mean(axis=0)
            scale = train_numeric.std(axis=0)
            scale[scale < 1e-12] = 1
            train_numeric = (train_numeric - mean) / scale
            test_numeric = (test_numeric - mean) / scale
            X_train = np.column_stack(
                [
                    np.ones(train_mask.sum()),
                    train_numeric,
                    sample.loc[train_mask, dummy_columns].to_numpy(float),
                ]
            )
            X_test = np.column_stack(
                [
                    np.ones(test_mask.sum()),
                    test_numeric,
                    sample.loc[test_mask, dummy_columns].to_numpy(float),
                ]
            )
            ridge = np.eye(X_train.shape[1]) * 1e-6
            ridge[0, 0] = 0
            beta = np.linalg.solve(X_train.T @ X_train + ridge, X_train.T @ y_train)
            prediction = X_test @ beta
            rmse = float(np.sqrt(np.mean((y_test - prediction) ** 2)))
            rows.append(
                {
                    "series": name,
                    "horizon_days": horizon,
                    "cutoff_date": str(pd.Timestamp(cutoff).date()),
                    "train_n": int(train_mask.sum()),
                    "test_n": int(test_mask.sum()),
                    "random_walk_rmse": baseline_rmse,
                    "model_rmse": rmse,
                    "rmse_improvement_pct": 1 - rmse / baseline_rmse,
                    "model_mae": float(np.mean(np.abs(y_test - prediction))),
                    "direction_accuracy": float(
                        np.mean(np.sign(prediction) == np.sign(y_test))
                    ),
                }
            )
    return pd.DataFrame(rows)


def sensitivity_models(data: pd.DataFrame) -> pd.DataFrame:
    group = data.groupby("world", observed=True)
    candidates = {
        "kill_count": "growth_kill_count",
        "direct_coin": "growth_direct_coin",
        "realized_50": "growth_realized_50",
        "potential_max": "growth_potential_max",
        "potential_with_bosses": "growth_potential_with_bosses",
    }
    for exposure in candidates.values():
        data[f"{exposure}_lag7"] = group[exposure].shift(7)
    data["online_growth_lag"] = group.online_growth.shift(7)
    rows = []
    for threshold in COVERAGE_THRESHOLDS:
        sample = data[data.coverage_deaths_pct_nonboss >= threshold]
        common = [
            f"{exposure}_lag7" for exposure in candidates.values()
        ] + ["forward_return_7d", "lagged_return_1d", "online_growth_lag"]
        sample = sample.dropna(subset=common)
        for name, exposure in candidates.items():
            result = fe_model(
                sample,
                "forward_return_7d",
                f"{exposure}_lag7",
                ["lagged_return_1d", "online_growth_lag"],
            )
            if result:
                rows.append(
                    {
                        "coverage_threshold": threshold,
                        "series": name,
                        "bosses_included": name == "potential_with_bosses",
                        **result,
                    }
                )
    return pd.DataFrame(rows)


def validation_tables(data: pd.DataFrame) -> pd.DataFrame:
    creatures = pd.read_csv(P / "creature_gold_value.csv")
    emissions = pd.read_csv(P / "gold_emission_daily.csv")
    rows = []
    for _, row in creatures.nlargest(
        20, "expected_total_potential_gp_per_kill"
    ).iterrows():
        rows.append(
            {
                "check": "extreme_expected_value",
                "entity": row.canonical_name,
                "value": row.expected_total_potential_gp_per_kill,
                "unit": "GP per kill",
                "context": (
                    f"{row.coverage_category}; {row.loot_samples:.0f} source samples; "
                    f"{row.loot_confidence} confidence"
                ),
            }
        )
    for metric in ("top_emission_creature_share", "top_kill_creature_share"):
        rows.append(
            {
                "check": metric,
                "entity": "world-day distribution",
                "value": emissions[metric].quantile(0.99),
                "unit": "99th percentile share",
                "context": f"median={emissions[metric].median():.4f}",
            }
        )
    activity = (
        data.groupby("world", observed=True)
        .agg(
            online=("players_online_avg", "mean"),
            emission=("realized_estimate_gp_50", "mean"),
            coverage=("coverage_deaths_pct_nonboss", "mean"),
        )
        .reset_index()
    )
    activity["emission_per_online"] = activity.emission / activity.online
    for _, row in activity.nlargest(10, "emission_per_online").iterrows():
        rows.append(
            {
                "check": "world_emission_per_activity",
                "entity": row.world,
                "value": row.emission_per_online,
                "unit": "estimated GP per average online player-day",
                "context": f"mean online={row.online:.1f}; mean coverage={row.coverage:.1%}",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    data = prepare()
    lag_models = lag_and_ma_models(data)
    levels = level_models(data)
    comparison = pd.concat([lag_models, levels], ignore_index=True)
    oos = oos_models(data)
    sensitivity = sensitivity_models(data)
    validation = validation_tables(data)

    lag_models.to_csv(P / "gold_emission_lag_results.csv", index=False)
    comparison.to_csv(P / "gold_emission_model_comparison.csv", index=False)
    oos.to_csv(P / "gold_emission_oos.csv", index=False)
    sensitivity.to_csv(P / "gold_emission_sensitivity.csv", index=False)
    validation.to_csv(P / "gold_emission_validation.csv", index=False)

    headline = comparison[
        (comparison.model_type == "shock_lag")
        & (comparison.horizon_days.isin([1, 7, 30]))
        & (comparison.lag_or_window_days == comparison.horizon_days)
        & (comparison.series.isin(["kill_count", "direct_coin", "potential_max", "realized_50"]))
    ].copy()
    results = {
        "sample": {
            "n": int(len(data)),
            "worlds": int(data.world.nunique()),
            "start": str(data.date.min().date()),
            "end": str(data.date.max().date()),
            "quality_filter": "coverage >= 80%, non-partial date, converged price worlds",
        },
        "specification": {
            "fixed_effects": ["world", "date"],
            "clustered_standard_errors": ["world", "date"],
            "controls": ["lagged one-day return", "online-player growth"],
            "horizons_days": list(HORIZONS),
            "lags_days": list(LAGS),
            "moving_average_windows_days": list(MA_WINDOWS),
            "claim_scope": "descriptive temporal association and out-of-sample prediction; not causal",
        },
        "headline_models": headline.to_dict("records"),
        "oos": oos.to_dict("records"),
        "best_oos_rmse_improvement_pct": float(oos.rmse_improvement_pct.max()),
        "worst_oos_rmse_improvement_pct": float(oos.rmse_improvement_pct.min()),
        "n_model_rows": int(len(comparison)),
        "n_sensitivity_rows": int(len(sensitivity)),
    }
    (P / "gold_emission_results.json").write_text(
        json.dumps(results, indent=1, default=str)
    )
    fundamentals_path = P / "fundamentals_results.json"
    if fundamentals_path.exists():
        fundamentals = json.loads(fundamentals_path.read_text())
        fundamentals["gold_emission"] = results
        fundamentals_path.write_text(json.dumps(fundamentals, indent=1, default=str))
    print(
        f"[GOLD MODELS] {len(comparison):,} equivalent FE models; "
        f"{len(oos):,} out-of-sample comparisons; {len(sensitivity):,} sensitivities"
    )
    print(headline[[
        "series", "horizon_days", "coefficient", "std_error_two_way",
        "p_value", "r2_within", "n"
    ]].round(6).to_string(index=False))
    print(
        f"OOS RMSE improvement range vs random walk: "
        f"{oos.rmse_improvement_pct.min():+.2%} to "
        f"{oos.rmse_improvement_pct.max():+.2%}"
    )


if __name__ == "__main__":
    main()
