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
    assert len(payload["forecasts"]) == len(forecasts)
    assert len(payload["strategy"]) == len(strategy)
    assert len(payload["figures"]) == len(figures) == 34
    assert {row["world"] for row in payload["worlds"]} == set(worlds.world)
    assert {row["world"] for row in payload["predictions"]} == set(predictions.world)

    for view in ("overview", "worlds", "forecasts", "strategy", "emission", "library"):
        assert f'id="view-{view}"' in html
        assert f'data-view="{view}"' in html

    for feature in (
        "function showView(",
        "function renderOverviewChart(",
        "function renderWorldChart(",
        "function renderForecastChart(",
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
    assert "reports/intelligence_hub.html" in entry
    assert 'meta http-equiv="refresh"' in entry

    print(
        f"[INTELLIGENCE VERIFY] passed: {len(worlds)} worlds, "
        f"{panel.price_gp.notna().sum():,} price rows, {len(predictions)} predictions, "
        f"{len(forecasts)} scenario forecasts, {len(figures)} interactive exhibits"
    )


if __name__ == "__main__":
    main()
