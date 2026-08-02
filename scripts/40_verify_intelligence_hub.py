"""Verify the unified interactive intelligence workspace.

    python scripts/40_verify_intelligence_hub.py
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
HUB = ROOT / "reports" / "intelligence_hub.html"
ENTRY = ROOT / "index.html"


def main() -> None:
    assert HUB.exists(), "missing reports/intelligence_hub.html"
    assert ENTRY.exists(), "missing root index.html"
    html = HUB.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")

    prefix = "const EMBEDDED = "
    start = html.index(prefix) + len(prefix)
    end = html.index(";\nconst DATA_FILES", start)
    payload = json.loads(html[start:end])

    worlds = pd.read_csv(P / "world_summary.csv")
    panel = pd.read_csv(P / "panel_daily.csv")
    index = pd.read_csv(P / "market_index.csv")
    predictions = pd.read_csv(P / "latest_predictions.csv")
    specific_predictions = pd.read_csv(P / "latest_specific_predictions.csv")
    model_registry = pd.read_csv(P / "specific_model_registry.csv")
    model_comparison = pd.read_csv(P / "specific_model_comparison.csv")
    model_sensitivity = pd.read_csv(P / "specific_model_sensitivity.csv")
    launch_predictions = pd.read_csv(P / "latest_launch_predictions.csv")
    launch_registry = pd.read_csv(P / "launch_model_registry.csv")
    launch_comparison = pd.read_csv(P / "launch_model_comparison.csv")
    forecasts = pd.read_csv(P / "forecasts_sa.csv")
    strategy = pd.read_csv(P / "strategy_holdout.csv")
    figures = json.loads((ROOT / "figures" / "manifest.json").read_text())

    assert "__DATA__" not in html
    assert "<script src=" not in html, "hub must remain self-contained"
    assert len(payload["worlds"]) == len(worlds) == 93
    assert len(payload["worldSeries"]) == panel.price_gp.notna().sum()
    valid_index = index.index_valid.astype(bool) & index.ew_price.notna()
    assert len(payload["marketIndex"]) == valid_index.sum()
    assert len(payload["predictions"]) == len(predictions)
    assert len(payload["specificPredictions"]) == len(specific_predictions)
    assert len(payload["modelRegistry"]) == len(model_registry)
    assert len(payload["modelComparison"]) == len(model_comparison)
    assert len(payload["modelSensitivity"]) == len(model_sensitivity)
    assert len(payload["launchPredictions"]) == len(launch_predictions)
    assert len(payload["launchRegistry"]) == len(launch_registry)
    assert len(payload["launchComparison"]) == len(launch_comparison)
    assert len(payload["forecasts"]) == len(forecasts)
    assert len(payload["strategy"]) == len(strategy)
    assert len(payload["figures"]) == len(figures) == 34
    assert {row["world"] for row in payload["worlds"]} == set(worlds.world)
    assert {row["world"] for row in payload["predictions"]} == set(predictions.world)
    assert {row["world"] for row in payload["specificPredictions"]} == set(
        specific_predictions.world
    )
    assert {row["world"] for row in payload["modelRegistry"]} == set(
        model_registry.world
    )
    assert {row["world"] for row in payload["launchPredictions"]} == set(
        launch_predictions.world
    )

    for view in (
        "overview",
        "worlds",
        "forecasts",
        "models",
        "strategy",
        "emission",
        "library",
    ):
        assert f'id="view-{view}"' in html
        assert f'data-view="{view}"' in html

    for feature in (
        "function showView(",
        "function renderOverviewChart(",
        "function renderWorldChart(",
        "function renderForecastChart(",
        "function renderModels(",
        "function renderModelChart(",
        "function renderModelDetail(",
        "function renderLaunchModels(",
        "function renderStrategy(",
        "function renderLibrary(",
        "function openExhibit(",
        "function updateURL(",
        "async function copyView(",
        "async function refreshProjectData(",
    ):
        assert feature in html, f"missing interactive feature: {feature}"

    for source in (
        "../data/processed/market_index.csv",
        "../data/processed/world_summary.csv",
        "../data/processed/panel_daily.csv",
        "../data/processed/forecasts_sa.csv",
        "../data/processed/latest_predictions.csv",
        "../data/processed/latest_specific_predictions.csv",
        "../data/processed/specific_model_registry.csv",
        "../data/processed/specific_model_comparison.csv",
        "../data/processed/specific_model_sensitivity.csv",
        "../data/processed/latest_launch_predictions.csv",
        "../data/processed/launch_model_registry.csv",
        "../data/processed/launch_model_comparison.csv",
        "../data/processed/strategy_holdout.csv",
    ):
        assert source in html, f"missing live data source: {source}"

    iframe_tag = html[html.index('<iframe id="emissionFrame"'):html.index(
        "</iframe>", html.index('<iframe id="emissionFrame"')
    )]
    assert 'src=' not in iframe_tag, (
        "the emission iframe must remain lazy until its view opens"
    )
    assert '$("#emissionFrame").src="gold_emission_dashboard.html"' in html
    assert 'href="tibia_coin_market_report.pdf"' in html
    assert 'data-mode="price">Price (GP)</button>' in html
    assert 'data-mode="return">Return (%)</button>' in html
    assert 'id="worldStart" type="date"' in html
    assert 'id="worldEnd" type="date"' in html
    assert '$("#worldStart").value=$("#overviewStart").value' in html
    assert '$("#overviewStart").value=$("#worldStart").value' in html
    assert 'const start=$("#worldStart").value,end=$("#worldEnd").value' in html
    assert "Actual daily market price in GP per Tibia Coin." in html
    assert "comparisonDates=[...new Set(data.worldSeries.map(row=>row.date))].sort()" in html
    assert "missing history is left blank" in html
    assert "const linePath=key=>" in html
    assert "each series is rebased to 100" not in html
    assert "Interactive rebased world comparison" not in html
    assert "direct GP drops" in html
    assert "GP means gold pieces; Tibia Coins are labeled TC throughout." in html
    assert "What the data says" in html
    assert "See the numbers and technical explanation" in html
    assert "Do not keep extra TC expecting easy profit" in html
    assert "More hunting did not reliably move the TC price" in html
    assert 'class="claim-details"' in html
    assert "reports/intelligence_hub.html" in entry
    assert 'meta http-equiv="refresh"' in entry

    print(
        f"[INTELLIGENCE VERIFY] passed: {len(worlds)} worlds, "
        f"{panel.price_gp.notna().sum():,} price rows, {len(predictions)} predictions, "
        f"{model_registry.group_id.nunique()} specific models, "
        f"{launch_registry.pvp_type.nunique()} launch models, "
        f"{len(forecasts)} scenario forecasts, {len(figures)} interactive exhibits"
    )


if __name__ == "__main__":
    main()
