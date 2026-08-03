"""Verify the monetary-emission reconstruction and its report inputs.

    python scripts/37_verify_gold_emission.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "gold_emission_report_artifact.json"
DASHBOARD = ROOT / "reports" / "gold_emission_dashboard.html"

REQUIRED = [
    "creature_loot_items.csv",
    "creature_gold_value.csv",
    "gold_emission_daily.csv",
    "gold_emission_quality.csv",
    "gold_emission_quality.json",
    "gold_emission_model_comparison.csv",
    "gold_emission_lag_results.csv",
    "gold_emission_oos.csv",
    "gold_emission_sensitivity.csv",
    "gold_emission_validation.csv",
    "gold_emission_results.json",
]


def close(left, right, tolerance=1e-8) -> bool:
    return bool(np.allclose(left, right, rtol=tolerance, atol=tolerance, equal_nan=True))


def main() -> None:
    missing = [name for name in REQUIRED if not (P / name).exists()]
    assert not missing, f"missing outputs: {missing}"
    assert REPORT.exists(), "missing report artifact"
    assert DASHBOARD.exists(), "missing interactive dashboard"

    items = pd.read_csv(P / "creature_loot_items.csv")
    creatures = pd.read_csv(P / "creature_gold_value.csv")
    daily = pd.read_csv(P / "gold_emission_daily.csv", parse_dates=["date"])
    models = pd.read_csv(P / "gold_emission_model_comparison.csv")
    oos = pd.read_csv(P / "gold_emission_oos.csv")
    sensitivity = pd.read_csv(P / "gold_emission_sensitivity.csv")
    quality = json.loads((P / "gold_emission_quality.json").read_text())
    artifact = json.loads(REPORT.read_text())
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    assert "Direct GP drops" in dashboard
    assert "Potential GP maximum" in dashboard
    assert "Realized GP estimate" not in dashboard
    assert "GP means Tibia gold pieces. TC means Tibia Coins" in dashboard
    assert "Direct coins" not in dashboard

    assert creatures.creature_id.is_unique
    assert not daily.duplicated(["world", "date"]).any()
    assert daily.world.nunique() == quality["worlds"]
    assert len(daily) == quality["world_days"]
    assert items.drop_probability.between(0, 1).all()
    assert (items.expected_quantity_per_kill >= 0).all()
    assert (items.npc_sell_value_max_gp >= 0).all()
    assert close(
        items.expected_direct_coin_gp_per_kill,
        items.expected_quantity_per_kill * items.nominal_coin_value_gp,
    )
    assert close(
        items.expected_npc_sale_gp_per_kill,
        items.expected_quantity_per_kill * items.npc_sell_value_max_gp,
    )

    assert close(
        daily.potential_total_gp_max,
        daily.direct_coin_gp + daily.npc_potential_gp_max,
    )
    assert close(
        daily.realized_estimate_gp_50,
        daily.direct_coin_gp + 0.5 * daily.npc_potential_gp_max,
    )
    assert close(
        daily.potential_total_gp_max_with_bosses,
        daily.potential_total_gp_max + daily.boss_potential_total_gp_max,
    )
    assert daily.coverage_deaths_pct_nonboss.between(0, 1).all()
    assert daily.coverage_deaths_pct_all.between(0, 1).all()
    assert (
        daily.low_quality_flag
        == (
            (daily.coverage_deaths_pct_nonboss < quality["daily_coverage_threshold"])
            | daily.partial_date_flag
        )
    ).all()
    for _, group in daily.groupby("world", observed=True):
        ordered = group.sort_values("date")
        for column in (
            "cumulative_direct_coin_gp",
            "cumulative_potential_total_gp_max",
            "cumulative_realized_estimate_gp_50",
        ):
            assert (ordered[column].diff().dropna() >= -1e-6).all(), column

    assert not models.duplicated(
        ["model_type", "series", "horizon_days", "lag_or_window_days"]
    ).any()
    assert np.isfinite(
        models[["coefficient", "std_error_two_way", "p_value", "r2_within"]]
    ).all().all()
    sample_counts = models.groupby(
        ["model_type", "horizon_days", "lag_or_window_days"], observed=True
    ).n.nunique()
    assert sample_counts.max() == 1, "series were not compared on identical samples"
    assert set(oos.series) == {
        "kill_count",
        "direct_coin",
        "potential_max",
        "realized_25",
        "realized_50",
        "realized_75",
        "realized_100",
    }
    assert oos.rmse_improvement_pct.between(-1, 1).all()
    assert len(sensitivity) == 15

    assert artifact["surface"] == "report"
    assert artifact["snapshot"]["status"] == "ready"
    datasets = artifact["snapshot"]["datasets"]
    assert len(datasets) <= 50
    assert all(isinstance(rows, list) and len(rows) <= 2000 for rows in datasets.values())
    assert artifact["manifest"]["blocks"][0]["body"].strip() == (
        "# " + artifact["manifest"]["title"]
    )
    assert any(block["type"] == "chart" for block in artifact["manifest"]["blocks"])
    assert all(
        table.get("defaultSort", {}).get("field") in {
            column["field"] for column in table["columns"]
        }
        for table in artifact["manifest"]["tables"]
    )
    assert "__DATA__" not in dashboard
    assert f'"worldDays":{len(daily)}' in dashboard
    assert "const EMBEDDED =" in dashboard
    assert 'id="worldSelect"' in dashboard
    assert 'id="dateStart"' in dashboard and 'id="dateEnd"' in dashboard
    assert 'id="scenarioSelect"' not in dashboard
    assert 'id="lineChart"' in dashboard
    assert 'id="tcPriceToggle"' in dashboard
    assert "TC price (GP/TC)" in dashboard
    assert 'direct: "#4E79A7"' in dashboard
    assert 'potential: "#F28E2B"' in dashboard
    assert 'tcPrice: "#59A14F"' in dashboard
    assert "priceSchema" in dashboard and "priceRows" in dashboard
    assert "creatureValueSchema" in dashboard and "creatureValues" in dashboard
    assert 'params.set("tcPrice", "1")' in dashboard
    assert 'id="creatureDetail"' in dashboard
    assert "day-detail-mode" in dashboard
    assert "← Back to Gold Emission" in dashboard
    assert 'data-detail-date=' in dashboard
    assert "async function openCreatureDetail(date, trigger = null, pushRoute = true)" in dashboard
    assert "function renderCreatureDetail(world, date, rows, sourceUrl)" in dashboard
    assert "tibiamaps/tibia-kill-stats/main/data/" in dashboard
    assert "function enhanceSortableTables(root = document)" in dashboard
    assert 'class="sort-button"' in dashboard
    assert 'id="fileInput"' in dashboard
    assert "<script src=" not in dashboard, "dashboard must remain self-contained"
    assert "async function refreshProjectCSV()" in dashboard
    assert 'fetch("../data/processed/gold_emission_daily.csv", { cache: "no-store" })' in dashboard
    assert 'if (!["http:", "https:"].includes(location.protocol)) return;' in dashboard
    assert 'sourceMeta = { ...sourceMeta, mode: "fallback" };' in dashboard
    assert "void refreshProjectCSV();" in dashboard
    assert "function isoDate(value)" in dashboard
    assert "function isoTimestamp(value)" in dashboard
    assert 'id="worldBreakdown"' in dashboard
    assert "function renderWorldBreakdown(rows)" in dashboard
    assert "What generated potential GP in" in dashboard
    assert "Largest creature source on one day" in dashboard
    assert "Days needing extra caution" in dashboard
    assert 'Intl.DateTimeFormat("en-US"' not in dashboard
    assert 'toLocaleString("en-US")' not in dashboard
    invalid_guard = dashboard.index(
        'if ($("#dateStart").value > $("#dateEnd").value)'
    )
    invalid_return = dashboard.index("return;", invalid_guard)
    invalid_block = dashboard[invalid_guard:invalid_return]
    assert "filtered = []" in invalid_block
    for renderer in (
        "updateMetrics(filtered)",
        "renderChart(filtered)",
        "renderComposition(filtered)",
        "renderQuality(filtered)",
        "renderTable(filtered)",
    ):
        assert renderer in invalid_block, f"invalid date range leaves stale {renderer}"

    print(
        f"[GOLD VERIFY] passed: {len(creatures):,} creatures, {len(items):,} loot rows, "
        f"{len(daily):,} world-days, {len(models):,} FE models, "
        f"{sum(len(rows) for rows in datasets.values()):,} report rows, dashboard ready"
    )


if __name__ == "__main__":
    main()
