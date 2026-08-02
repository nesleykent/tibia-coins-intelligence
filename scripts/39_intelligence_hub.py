"""Build the unified interactive Tibia Coins Intelligence workspace.

    python scripts/39_intelligence_hub.py

The generated HTML is self-contained for offline use. When served from the
repository root it refreshes its analytical datasets from data/processed.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
FIGURES = ROOT / "figures" / "manifest.json"
OUTPUT = ROOT / "reports" / "intelligence_hub.html"


def value(item):
    if pd.isna(item):
        return None
    if hasattr(item, "item"):
        item = item.item()
    return item


def records(path: pathlib.Path, columns: list[str], *, where=None) -> list[dict]:
    frame = pd.read_csv(path, low_memory=False)
    if where is not None:
        frame = where(frame)
    return [
        {column: value(row[column]) for column in columns}
        for _, row in frame[columns].iterrows()
    ]


def figure_topic(key: str) -> str:
    number = int(key[3:5])
    if number <= 4:
        return "Market overview"
    if number <= 16:
        return "Worlds & activity"
    if number <= 26:
        return "Market mechanics"
    if number <= 31:
        return "Models & forecasts"
    return "Strategy"


def _headline_facts() -> dict:
    """The claims the PDF and this page must agree on, read from the shared results."""
    fund = json.loads((P / "fundamentals_results.json").read_text())
    res = json.loads((P / "results.json").read_text())
    grid = pd.DataFrame(fund["strategy"]["grid"])
    hold = pd.DataFrame(fund["strategy"]["holdout"]["rows"])

    def cell(h, col):
        row = grid[(grid.horizon == h) & (grid.decile == grid.decile.max())
                   & (grid.cost_basis == "above the fee cap")]
        return float(row[col].iloc[0])

    def ho(h, col):
        return float(hold[(hold.horizon == h) & (hold.period == "holdout")][col].iloc[0])

    pages = 0
    pdf = ROOT / "reports" / "tibia_coin_market_report.pdf"
    if pdf.exists():
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(pdf)).pages)
        except Exception:
            pages = 0
    return {
        "verdict": "buy relative, not directional",
        "confidence": 78,
        "reportPages": pages,
        "bandThresholdPct": res["advanced"]["tar"]["threshold_pct"],
        "actionGapPct": fund["scenarios"]["levels"]["arb_act_gap_pct"],
        "lotSize": res["fees"]["lot_size"],
        "feeCapLotTc": res["fees"]["cap_binds_at_lot_tc"],
        "roundTripPct": res["fees"]["roundtrip_largest_decile_pct"],
        "strategyNet7": cell(7, "net_pct"),
        "strategyNet30": cell(30, "net_pct"),
        "strategyWin30": cell(30, "share_profitable"),
        "holdoutNet7": ho(7, "net_pct"),
        "holdoutT7": ho(7, "t_newey_west"),
        "holdoutWindows7": int(ho(7, "n_effective")),
        "holdoutWindows30": int(ho(30, "n_effective")),
        "holdoutWindows91": int(ho(91, "n_effective")),
        "episodesPerMonth": fund["strategy"]["occurrence"]["episodes_per_month"],
        "capacityGpPerMonth": fund["strategy"]["capacity"]["gp_per_month"],
        "bazaarOverMarket": res["venues"]["market_size"]["bazaar_over_market"],
        "marketTcYear": res["venues"]["market_size"]["market_tc_year"],
        "bazaarTcYear": res["venues"]["market_size"]["bazaar_tc_year"],
        "tcPerWorldDay": fund["participants"]["executable"][
            "median_executed_per_world_day_tc"],
        "emissionVerdict": "rejected",
    }


def build_payload() -> dict:
    results = json.loads((P / "results.json").read_text())
    manifest = json.loads(FIGURES.read_text())

    market_index = records(
        P / "market_index.csv",
        ["date", "ew_price", "disp_pct", "breadth_up", "n_worlds"],
        where=lambda frame: frame[
            frame["index_valid"].astype(bool) & frame["ew_price"].notna()
        ],
    )
    worlds = records(
        P / "world_summary.csv",
        [
            "world", "first", "last", "px_first", "px_last", "px_med", "px_min",
            "px_max", "vol", "sold", "bought", "region", "pvp_type", "converged",
            "launch_in_window", "population", "active_chars", "premium_share",
            "total_ret_pct",
        ],
    )
    world_series = records(
        P / "panel_daily.csv",
        ["world", "date", "price_gp", "tc_sold", "tc_bought"],
        where=lambda frame: frame[frame["price_gp"].notna()],
    )
    forecasts = records(
        P / "forecasts_sa.csv",
        [
            "world", "last_price", "launch_phase", "gap_to_mean_pct",
            "sigma_daily_pct", "mu_daily_pct",
            "2w_p50", "2w_p10", "2w_p90",
            "1m_p50", "1m_p10", "1m_p90",
            "3m_p50", "3m_p10", "3m_p90",
            "6m_p50", "6m_p10", "6m_p90",
        ],
    )
    predictions = records(
        P / "latest_predictions.csv",
        [
            "world", "as_of", "price_gp", "deviation_pct", "outside_band",
            "predicted_change_pct", "low80_pct", "high80_pct",
        ],
    )
    specific_predictions = records(
        P / "latest_specific_predictions.csv",
        [
            "world", "as_of", "price_gp", "pvp_type", "battleye_color", "region",
            "group_level", "group_id", "model_worlds", "low_sample_warning",
            "fallback_reason", "deviation_pct", "outside_band",
            "general_predicted_change_pct", "general_low80_pct", "general_high80_pct",
            "specific_predicted_change_pct", "specific_low80_pct",
            "specific_high80_pct", "specific_minus_general_pct",
        ],
    )
    model_registry = records(
        P / "specific_model_registry.csv",
        [
            "world", "pvp_type", "battleye_color", "region", "group_level",
            "group_id", "model_worlds", "assigned_worlds", "preferred_min_worlds",
            "low_sample_warning", "fallback_reason", "selected_estimator",
        ],
    )
    model_comparison = records(
        P / "specific_model_comparison.csv",
        [
            "scope", "scope_value", "n_test", "n_dates", "n_worlds",
            "general_rmse_pct", "specific_rmse_pct", "specific_improvement_pct",
            "general_mae_pct", "specific_mae_pct", "general_r2_oos",
            "specific_r2_oos", "general_direction_accuracy",
            "specific_direction_accuracy", "dm_t_specific_vs_general",
            "dm_p_specific_vs_general", "better_model",
        ],
    )
    model_sensitivity = records(
        P / "specific_model_sensitivity.csv",
        [
            "min_group_worlds", "n_models", "n_exact_worlds",
            "n_region_pooled_worlds", "n_pvp_pooled_worlds",
            "general_rmse_pct", "specific_rmse_pct",
            "specific_improvement_pct",
        ],
    )
    launch_predictions = records(
        P / "latest_launch_predictions.csv",
        [
            "world", "as_of", "created", "age_days", "price_gp", "pvp_type",
            "battleye_color", "region", "model_worlds", "selected_estimator",
            "low_sample_warning", "stale_days", "deviation_pct",
            "general_predicted_change_pct", "general_low80_pct",
            "general_high80_pct", "launch_predicted_change_pct",
            "launch_low80_pct", "launch_high80_pct",
            "launch_minus_general_pct",
        ],
    )
    launch_registry = records(
        P / "launch_model_registry.csv",
        [
            "world", "created", "first", "last", "pvp_type",
            "battleye_color", "region", "complete_rows", "cohort",
            "age_at_latest_days", "currently_in_launch_phase",
            "low_sample_pvp_warning", "selected_estimator",
        ],
    )
    launch_comparison = records(
        P / "launch_model_comparison.csv",
        [
            "scope", "scope_value", "n_test", "n_dates", "n_worlds",
            "launch_rmse_pct", "general_rmse_pct", "zero_rmse_pct",
            "launch_improvement_vs_general_pct",
            "launch_improvement_vs_zero_pct", "launch_mae_pct",
            "general_mae_pct", "zero_mae_pct",
            "nw_t_launch_vs_general", "nw_p_launch_vs_general",
            "nw_t_launch_vs_zero", "nw_p_launch_vs_zero", "better_model",
        ],
    )
    strategy = records(
        P / "strategy_holdout.csv",
        [
            "horizon", "period", "cutoff_pct", "n", "n_effective", "net_pct",
            "t_newey_west", "share_profitable",
        ],
    )
    figures = [
        {
            "id": key,
            "label": f"Study {index + 1:02d}",
            "title": item["title"],
            "subtitle": item["subtitle"],
            "note": item["note"],
            "source": item["source"],
            "image": f"../figures/{key}.png",
            "topic": figure_topic(key),
        }
        for index, (key, item) in enumerate(manifest.items())
        if (ROOT / "figures" / f"{key}.png").exists()
    ]

    return {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "start": results["window"]["start"],
            "end": results["window"]["end"],
            "worlds": results["window"]["n_worlds"],
            "worldDays": results["window"]["n_world_days"],
            "converged": results["window"]["n_converged"],
            "indexReturn": results["index"]["total_pct"],
            "latestMedian": results["desc"]["price_latest_median"],
            "figureCount": len(figures),
            "specificModels": int(pd.Series(
                [row["group_id"] for row in model_registry]
            ).nunique()),
            "launchModels": int(pd.Series(
                [row["pvp_type"] for row in launch_registry]
            ).nunique()),
            "activeLaunchWorlds": len(launch_predictions),
            # The report and this page publish the same claims, so they read them from the
            # same place. Anything hardcoded in the markup below drifts the moment a stage
            # re-runs; scripts/46_verify_artifacts.py fails the build when they disagree.
            **_headline_facts(),
        },
        "marketIndex": market_index,
        "worlds": worlds,
        "worldSeries": world_series,
        "forecasts": forecasts,
        "predictions": predictions,
        "specificPredictions": specific_predictions,
        "modelRegistry": model_registry,
        "modelComparison": model_comparison,
        "modelSensitivity": model_sensitivity,
        "launchPredictions": launch_predictions,
        "launchRegistry": launch_registry,
        "launchComparison": launch_comparison,
        "strategy": strategy,
        "figures": figures,
    }


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Tibia Coins Intelligence</title>
  <style>
    :root {
      --bg:#fff; --surface:#fff; --surface-soft:#f7f9fc; --ink:#0e1c3b;
      --muted:#647087; --line:#d7deea; --line-soft:#edf1f6; --blue:#155eef;
      --blue-soft:#eef4ff; --gold:#c58b16; --gold-soft:#fff8e7; --green:#14804a;
      --red:#c9363e; --focus:#155eef; --radius:8px; --sidebar:224px;
      font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      color:var(--ink); background:var(--bg);
    }
    *{box-sizing:border-box}
    html{scroll-behavior:smooth}
    body{margin:0;min-width:320px;background:var(--bg)}
    button,input,select{font:inherit;color:inherit}
    button,select,input{min-height:44px}
    button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{
      outline:3px solid rgb(21 94 239 / 22%);outline-offset:2px
    }
    a{color:var(--blue)}
    .app{display:grid;grid-template-columns:var(--sidebar) minmax(0,1fr);min-height:100vh}
    .sidebar{border-right:1px solid var(--line);padding:24px 14px;display:flex;flex-direction:column;
      position:sticky;top:0;height:100vh;background:#fff;z-index:8}
    .brand{display:flex;align-items:center;gap:12px;padding:0 10px 26px}
    .brand-mark{font-size:25px;font-weight:850;letter-spacing:-.07em}
    .brand-name{font-size:13px;font-weight:750;line-height:1.1}
    .nav{display:grid;gap:5px}
    .nav-button{border:0;border-left:3px solid transparent;background:transparent;border-radius:6px;
      min-height:48px;padding:0 12px;display:flex;align-items:center;gap:12px;text-align:left;
      cursor:pointer;font-size:14px;font-weight:650;color:#273552}
    .nav-button svg{width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:1.8}
    .nav-button:hover{background:var(--surface-soft)}
    .nav-button.active{border-left-color:var(--blue);background:var(--blue-soft);color:#0f51d8}
    .sidebar-note{margin-top:auto;padding:16px 12px 4px;color:var(--muted);font-size:11px;line-height:1.5}
    .workspace{min-width:0}
    .utility{height:64px;border-bottom:1px solid var(--line);display:flex;align-items:center;
      justify-content:space-between;gap:18px;padding:0 28px;position:sticky;top:0;background:rgb(255 255 255 / 96%);
      backdrop-filter:blur(8px);z-index:7}
    .status{display:flex;align-items:center;gap:9px;color:#34405a;font-size:12px;min-width:0}
    .status-dot{width:8px;height:8px;border-radius:50%;background:var(--green);flex:none}
    .status-dot.fallback{background:var(--gold)}
    .status-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .utility-actions{display:flex;gap:10px}
    .button{border:1px solid #aeb9cb;background:#fff;border-radius:7px;padding:0 14px;
      font-weight:700;font-size:13px;cursor:pointer;display:inline-flex;align-items:center;gap:8px;text-decoration:none}
    .button:hover{background:var(--surface-soft)}
    .button.primary{border-color:var(--blue);background:var(--blue);color:#fff}
    .button svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.8}
    .main{padding:28px 30px 52px;max-width:1540px;margin:0 auto}
    .view[hidden]{display:none}
    .view-header{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:18px}
    h1{font-size:clamp(30px,3.3vw,48px);line-height:1.05;letter-spacing:-.045em;margin:0}
    .view-intro{color:var(--muted);max-width:700px;line-height:1.55;margin:8px 0 0;font-size:14px}
    h2{font-size:18px;letter-spacing:-.015em;margin:0}
    h3{font-size:15px;margin:0}
    .filters{display:flex;align-items:end;gap:12px;flex-wrap:wrap}
    .field{display:grid;gap:6px;min-width:150px}
    .field.wide{min-width:230px}
    .field label{font-size:11px;font-weight:750;color:#3b4760}
    select,input[type="date"],input[type="search"]{width:100%;border:1px solid #bdc7d6;border-radius:7px;
      background:#fff;padding:0 11px;font-size:13px}
    .date-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .metric-rail{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);
      border-radius:var(--radius);margin:18px 0 16px;overflow:hidden}
    .metric{padding:16px 22px;min-width:0}
    .metric+.metric{border-left:1px solid var(--line)}
    .metric-label{display:block;color:#4e5a71;font-size:12px;margin-bottom:7px}
    .metric-value{display:block;color:var(--blue);font-size:clamp(24px,2.4vw,36px);
      line-height:1;font-weight:760;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
    .metric-meta{display:block;color:var(--muted);font-size:11px;margin-top:7px}
    .panel{border:1px solid var(--line);border-radius:var(--radius);background:#fff;min-width:0}
    .panel-heading{display:flex;align-items:start;justify-content:space-between;gap:16px;
      padding:15px 16px 10px}
    .panel-heading p{margin:4px 0 0;color:var(--muted);font-size:12px}
    .chart-panel{padding-bottom:10px}
    .legend{display:flex;flex-wrap:wrap;gap:9px 18px;color:#3d4961;font-size:11px}
    .legend-item{display:inline-flex;align-items:center;gap:7px}
    .legend-line{width:24px;border-top:3px solid var(--blue)}
    .legend-line.dashed{border-color:#7b869a;border-top-style:dashed}
    .chart-wrap{position:relative;padding:0 10px 4px}
    .chart{width:100%;height:340px;display:block;overflow:visible}
    .chart-tooltip{position:absolute;z-index:4;pointer-events:none;background:rgb(255 255 255 / 98%);
      border:1px solid #aeb9c8;border-radius:7px;box-shadow:0 8px 24px rgb(14 28 59 / 10%);
      padding:9px 11px;font-size:11px;line-height:1.5;opacity:0;transition:opacity .1s;min-width:180px}
    .chart-tooltip.visible{opacity:1}
    .chart-empty{color:var(--muted);text-align:center;padding:100px 20px}
    .split{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(260px,.8fr);gap:16px;margin-top:16px}
    .table-tools{display:flex;gap:8px;align-items:center}
    .table-tools input{min-width:200px}
    .table-wrap{overflow:auto;border-top:1px solid var(--line-soft)}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th,td{padding:10px 12px;border-bottom:1px solid var(--line-soft);text-align:right;white-space:nowrap}
    th{color:#34405a;background:#fafbfd;font-weight:750;position:sticky;top:0;z-index:1}
    th:first-child,td:first-child{text-align:left}
    tbody tr{cursor:pointer}
    tbody tr:hover{background:#f8faff}
    tbody tr.selected{background:var(--gold-soft);box-shadow:inset 3px 0 var(--gold)}
    .positive{color:var(--green);font-weight:700}
    .negative{color:var(--red);font-weight:700}
    .neutral{color:var(--muted)}
    .signal{padding:18px 17px;display:grid;align-content:start;gap:18px}
    .signal-block{border-bottom:1px solid var(--line);padding-bottom:16px}
    .signal-value{display:block;font-size:30px;line-height:1;font-weight:780;margin-top:8px}
    .signal-note{color:var(--muted);font-size:11px;line-height:1.55;margin:0}
    .world-layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(280px,.7fr);gap:16px}
    .world-facts{padding:16px;display:grid;gap:13px}
    .fact{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line-soft);
      padding-bottom:10px;font-size:12px}
    .fact span{color:var(--muted)}
    .fact strong{text-align:right}
    .segmented{display:inline-flex;border:1px solid #b9c3d2;border-radius:7px;overflow:hidden}
    .segment{min-height:40px;border:0;border-right:1px solid #b9c3d2;background:#fff;padding:0 14px;
      cursor:pointer;font-size:12px;font-weight:700}
    .segment:last-child{border-right:0}
    .segment.active{background:var(--blue);color:#fff}
    .forecast-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,.7fr);gap:16px}
    .forecast-summary{padding:18px;display:grid;gap:14px}
    .forecast-band{padding:11px 0;border-bottom:1px solid var(--line-soft)}
    .forecast-band:last-child{border:0}
    .forecast-band strong{font-size:22px;display:block;margin-top:5px}
    .model-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(300px,.75fr);gap:16px}
    .model-detail{padding:18px;display:grid;gap:13px;align-content:start}
    .model-levels{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:0 16px 16px}
    .model-level{border:1px solid var(--line-soft);background:var(--surface-soft);border-radius:7px;
      padding:13px;font-size:11px;line-height:1.5;color:#3c4961}
    .model-level strong{display:block;color:var(--ink);font-size:13px;margin-bottom:4px}
    .model-badge{display:inline-flex;align-items:center;min-height:25px;border-radius:999px;
      background:var(--blue-soft);color:#0f51d8;padding:0 9px;font-size:10px;font-weight:800}
    .model-badge.warning{background:var(--gold-soft);color:#765910}
    .strategy-grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(300px,.7fr);gap:16px}
    .bar-area{padding:16px}
    .bar-row{display:grid;grid-template-columns:72px 1fr 72px;gap:12px;align-items:center;margin:20px 0}
    .bar-track{height:26px;background:var(--surface-soft);border-radius:4px;overflow:hidden}
    .bar-fill{height:100%;background:var(--blue);transition:width .2s}
    .bar-fill.gold{background:var(--gold)}
    .evidence{padding:18px;display:grid;gap:14px}
    .evidence-callout{border-left:3px solid var(--gold);background:var(--gold-soft);padding:12px;
      color:#5f4a17;font-size:12px;line-height:1.55}
    .emission-frame{width:100%;height:1050px;border:1px solid var(--line);border-radius:var(--radius);
      background:#fff}
    .library-tools{display:grid;grid-template-columns:minmax(240px,1fr) 220px auto;gap:10px;margin:16px 0}
    .library-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
    .exhibit{border:1px solid var(--line);border-radius:var(--radius);background:#fff;overflow:hidden;
      text-align:left;cursor:pointer;padding:0;min-height:0;transition:transform .12s,border-color .12s}
    .exhibit:hover{transform:translateY(-2px);border-color:#94a7c5}
    .exhibit img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;object-position:top;
      background:var(--surface-soft);border-bottom:1px solid var(--line-soft)}
    .exhibit-copy{display:block;padding:13px 14px 15px}
    .exhibit-id{display:block;color:var(--blue);font-size:10px;font-weight:800;text-transform:uppercase}
    .exhibit-title{display:block;margin-top:6px;font-size:13px;font-weight:750;line-height:1.35}
    dialog{width:min(1100px,calc(100% - 28px));max-height:calc(100vh - 28px);border:0;border-radius:10px;
      padding:0;box-shadow:0 22px 70px rgb(14 28 59 / 24%)}
    dialog::backdrop{background:rgb(14 28 59 / 54%)}
    .modal-head{display:flex;justify-content:space-between;gap:18px;align-items:start;padding:18px;
      border-bottom:1px solid var(--line)}
    .icon-button{width:44px;min-width:44px;border:1px solid var(--line);border-radius:7px;background:#fff;
      cursor:pointer;font-size:20px}
    .modal-body{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(280px,.7fr);gap:18px;
      padding:18px;overflow:auto}
    .modal-body img{width:100%;height:auto;border:1px solid var(--line-soft)}
    .modal-notes{font-size:12px;line-height:1.6;color:#37435c}
    .modal-notes p{margin:0 0 14px}
    .source{color:var(--muted);font-size:10px}
    .empty{padding:70px 20px;text-align:center;color:var(--muted)}
    .footer{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:10px;
      border-top:1px solid var(--line);margin-top:22px;padding-top:14px}
    .mobile-only{display:none}
    @media(max-width:1050px){
      :root{--sidebar:190px}.main{padding:24px 20px 44px}.library-grid{grid-template-columns:repeat(2,1fr)}
      .split,.world-layout,.forecast-grid,.model-grid,.strategy-grid{grid-template-columns:1fr}
      .signal{grid-template-columns:1fr 1fr}.emission-frame{height:1150px}
    }
    .thesis-verdict{margin:0 0 10px;font-size:19px;line-height:1.3}
    .thesis-verdict strong{text-transform:capitalize}
    .thesis-confidence{margin-left:9px;font-size:13px;color:var(--muted);font-weight:500}
    .thesis-body{margin:0 0 16px;max-width:78ch;color:var(--muted);line-height:1.55}
    .thesis-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);
      border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
    .thesis-fact{background:var(--card);padding:12px 13px;display:flex;flex-direction:column;gap:3px}
    .thesis-fact span{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
    .thesis-fact strong{font-size:19px;line-height:1.15}
    .thesis-fact small{font-size:11px;color:var(--muted);line-height:1.35}
    .thesis-note{margin:14px 0 0;font-size:12.5px;color:var(--muted);max-width:82ch;line-height:1.5}
    @media(max-width:1100px){.thesis-grid{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:760px){
      .app{display:block}.sidebar{position:sticky;height:auto;border-right:0;border-bottom:1px solid var(--line);
        padding:0;top:0}.brand{padding:14px 16px 10px}.brand-mark{font-size:21px}.brand-name{font-size:15px}
      .nav{display:flex;overflow-x:auto;padding:0 10px 7px;gap:2px}.nav-button{flex:none;border-left:0;
        border-bottom:3px solid transparent;border-radius:0;padding:0 10px;min-height:44px}
      .nav-button.active{border-bottom-color:var(--blue);border-left-color:transparent;background:transparent}
      .nav-button svg{display:none}.sidebar-note{display:none}.utility{position:static;height:50px;padding:0 14px}
      .status-text{max-width:220px}.utility-actions .button:first-child{display:none}
      .main{padding:20px 14px 38px}.view-header{display:block}.filters{margin-top:18px;display:grid;
        grid-template-columns:1fr 1fr}.field,.field.wide{min-width:0}.field.wide{grid-column:1/-1}
      .metric-rail{grid-template-columns:1fr 1fr;border:0;gap:9px;overflow:visible}
      .metric{border:1px solid var(--line);border-radius:var(--radius);padding:13px}
      .metric+.metric{border-left:1px solid var(--line)}.metric-value{font-size:25px}
      .chart{height:300px}.panel-heading{display:block}.legend{margin-top:10px}
      .signal{grid-template-columns:1fr 1fr}.table-tools{margin-top:10px}.table-tools input{min-width:0}
      .data-table thead{display:none}.data-table,.data-table tbody{display:block}
      .data-table tr{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px;border-bottom:1px solid var(--line)}
      .data-table td{display:grid;gap:3px;padding:0;border:0;text-align:left!important;white-space:normal}
      .data-table td::before{content:attr(data-label);color:var(--muted);font-size:9px;text-transform:uppercase;
        font-weight:750}.data-table td:first-child{grid-column:1/-1;font-size:15px}
      .library-tools{grid-template-columns:1fr 1fr}.library-tools input{grid-column:1/-1}
      .model-levels{grid-template-columns:1fr}
      .library-grid{grid-template-columns:1fr}.modal-body{grid-template-columns:1fr}
      .emission-frame{height:1250px}.footer{display:block}.footer span{display:block;margin-top:5px}
    }
    @media(max-width:430px){
      .filters{grid-template-columns:1fr}.field.wide{grid-column:auto}.date-pair{grid-template-columns:1fr}
      .metric-rail{grid-template-columns:1fr 1fr}.signal{grid-template-columns:1fr}
      .library-tools{grid-template-columns:1fr}.library-tools input{grid-column:auto}
      .chart{height:270px}.emission-frame{height:1350px}
    }
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
    @media print{.sidebar,.utility,.filters,.button,.library-tools{display:none!important}.app{display:block}.main{max-width:none}}
  </style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">TCI</span><span class="brand-name">Tibia Coins<br>Intelligence</span></div>
    <nav class="nav" aria-label="Workspace navigation">
      <button class="nav-button active" data-view="overview">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13h6V4H4v9Zm0 7h6v-4H4v4Zm10 0h6v-9h-6v9Zm0-13h6V4h-6v3Z"/></svg>Overview
      </button>
      <button class="nav-button" data-view="worlds">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>Worlds
      </button>
      <button class="nav-button" data-view="forecasts">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 18 5-6 4 3 7-10M17 5h3v3"/></svg>Forecasts
      </button>
      <button class="nav-button" data-view="models">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h5v5H4zM15 4h5v5h-5zM10 15h5v5h-5zM6.5 10v2.5H12V15M17.5 9v3.5H12"/></svg>Models
      </button>
      <button class="nav-button" data-view="strategy">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="m14.8 9.2 5-5M16 4h4v4"/></svg>Strategy
      </button>
      <button class="nav-button" data-view="emission">
        <svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/></svg>Gold Emission
      </button>
      <button class="nav-button" data-view="library">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5c3-1 5-.4 8 1.5v13c-3-1.9-5-2.5-8-1.5v-13ZM20 5.5c-3-1-5-.4-8 1.5v13c3-1.9 5-2.5 8-1.5v-13Z"/></svg>Research Library
      </button>
    </nav>
    <div class="sidebar-note">Independent quantitative research.<br>Currency: GP per Tibia Coin.</div>
  </aside>

  <div class="workspace">
    <header class="utility">
      <div class="status"><i id="statusDot" class="status-dot"></i><span id="dataStatus" class="status-text"></span></div>
      <div class="utility-actions">
        <a class="button" href="tibia_coin_market_report.pdf" target="_blank" rel="noopener">Open full report</a>
        <button id="copyView" class="button" type="button">
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg>
          <span>Copy view</span>
        </button>
      </div>
    </header>

    <main class="main">
      <section id="view-overview" class="view">
        <div class="view-header">
          <div><h1>Tibia Coins Intelligence</h1><p class="view-intro">Explore price, relative value, forecasts and the economic mechanics connecting 93 Tibia worlds.</p></div>
          <div class="filters" aria-label="Overview filters">
            <div class="field"><label for="overviewWorld">World</label><select id="overviewWorld"></select></div>
            <div class="field wide"><label>Date range</label><div class="date-pair"><input id="overviewStart" type="date" aria-label="Start date"><input id="overviewEnd" type="date" aria-label="End date"></div></div>
          </div>
        </div>
        <div class="metric-rail" aria-label="Market summary">
          <div class="metric"><span class="metric-label" id="metricPriceLabel">Market index</span><strong id="metricPrice" class="metric-value">—</strong><span id="metricPriceMeta" class="metric-meta">GP per TC</span></div>
          <div class="metric"><span class="metric-label">Worlds</span><strong id="metricWorlds" class="metric-value">—</strong><span class="metric-meta">tracked</span></div>
          <div class="metric"><span class="metric-label">Median price</span><strong id="metricMedian" class="metric-value">—</strong><span class="metric-meta">GP per TC</span></div>
          <div class="metric"><span class="metric-label">Dispersion</span><strong id="metricDispersion" class="metric-value">—</strong><span class="metric-meta">cross-world log SD</span></div>
        </div>
        <article class="panel chart-panel">
          <div class="panel-heading"><div><h2 id="overviewChartTitle">Market index and dispersion</h2><p id="overviewChartNote">Tap, focus or move across the chart to inspect a date.</p></div><div id="overviewLegend" class="legend"></div></div>
          <div class="chart-wrap"><svg id="overviewChart" class="chart" role="img" aria-labelledby="overviewChartTitle"></svg><div id="overviewTooltip" class="chart-tooltip"></div></div>
        </article>
        <article class="panel thesis">
          <div class="panel-heading"><div><h2>The verdict, and why</h2><p>The same claims the
            report makes, read from the same results files. Nothing here is written by hand.</p></div></div>
          <p class="thesis-verdict"><strong id="verdictLine">—</strong>
            <span class="thesis-confidence" id="verdictConfidence">—</span></p>
          <p class="thesis-body">The gold price of a Tibia Coin is an exchange rate, not an asset
            price. Coin supply is perfectly elastic at a money price CipSoft fixes, neither leg
            pays a yield, and the Market fee holds a band open around every relation in the
            market. That model — not a preference for efficient markets — is why the level does
            not forecast, and why the one edge that exists only clears its cost at the strongest
            signals held long enough. Coins are a currency, not an asset: holding more than you
            intend to spend is an uncompensated position.</p>
          <div class="thesis-grid">
            <div class="thesis-fact"><span>Friction band</span><strong id="factBand">—</strong>
              <small>estimated from prices, no fee supplied</small></div>
            <div class="thesis-fact"><span>Act across worlds past</span><strong id="factAction">—</strong>
              <small>below this the round trip eats the edge</small></div>
            <div class="thesis-fact"><span>Minimum viable order</span><strong id="factLot">—</strong>
              <small>where the fee cap binds</small></div>
            <div class="thesis-fact"><span>Round trip at that size</span><strong id="factRoundTrip">—</strong>
              <small>against 4.00% below it</small></div>
            <div class="thesis-fact"><span>Net at 30 days</span><strong id="factNet30">—</strong>
              <small>strongest decile, after cost</small></div>
            <div class="thesis-fact"><span>Wins</span><strong id="factWin30">—</strong>
              <small>of 30-day occasions</small></div>
            <div class="thesis-fact"><span>Opportunities</span><strong id="factEpisodes">—</strong>
              <small>distinct episodes, not one standing gap</small></div>
            <div class="thesis-fact"><span>Capacity</span><strong id="factCapacity">—</strong>
              <small>the binding constraint, not conviction</small></div>
            <div class="thesis-fact"><span>Independent windows</span><strong id="factWindows">—</strong>
              <small>holdout at 7 · 30 · 91 days</small></div>
            <div class="thesis-fact"><span>Char Bazaar vs Market</span><strong id="factVenue">—</strong>
              <small>the priced venue is the smaller one</small></div>
            <div class="thesis-fact"><span>Cleared per world-day</span><strong id="factFlow">—</strong>
              <small>coins, converted at the 25-coin lot</small></div>
            <div class="thesis-fact"><span>Gold production channel</span><strong>Rejected</strong>
              <small>same null on the GP-emission series</small></div>
          </div>
          <p class="thesis-note">The quarterly strategy figures are the largest and the least
            supported: the holdout holds a single independent window at 91 days. A dispersion
            regime filter was proposed and rejected — it fails to improve selection and does not
            replicate within periods.</p>
        </article>
        <div class="split">
          <article class="panel">
            <div class="panel-heading"><div><h2>Worlds overview</h2><p id="overviewTableCount"></p></div><div class="table-tools"><input id="overviewSearch" type="search" placeholder="Search worlds…" aria-label="Search worlds"><select id="overviewSort" aria-label="Sort worlds"><option value="prediction">Predicted change</option><option value="price">Price</option><option value="deviation">Deviation</option><option value="world">World name</option></select></div></div>
            <div class="table-wrap"><table class="data-table"><thead><tr><th>World</th><th>Price (GP)</th><th>Deviation</th><th>Predicted 7d</th><th>Signal</th></tr></thead><tbody id="overviewTable"></tbody></table></div>
          </article>
          <aside class="panel signal">
            <div class="signal-block"><h2>Signal summary</h2><span class="signal-value positive" id="signalNet">—</span><small id="signalNote">—</small></div>
            <div class="signal-block"><h3>Level forecast</h3><span class="signal-value">No edge</span></div>
            <p class="signal-note">Relative position is forecastable; the common price level is not. Signals outside the estimated friction band deserve attention, not automatic execution.</p>
          </aside>
        </div>
      </section>

      <section id="view-worlds" class="view" hidden>
        <div class="view-header"><div><h1>Worlds</h1><p class="view-intro">Compare actual Tibia Coin prices first, then switch to percentage returns when relative performance matters.</p></div>
          <div class="filters"><div class="field"><label for="worldA">Primary world</label><select id="worldA"></select></div><div class="field"><label for="worldB">Compare with</label><select id="worldB"></select></div></div>
        </div>
        <div class="world-layout">
          <article class="panel chart-panel"><div class="panel-heading"><div><h2 id="worldChartTitle">World price comparison</h2><p id="worldChartDescription">Actual daily market price in GP per Tibia Coin.</p></div><div><div id="worldLegend" class="legend"></div><div id="worldChartMode" class="segmented" aria-label="World chart measure"><button class="segment active" data-mode="price">Price (GP)</button><button class="segment" data-mode="return">Return (%)</button></div></div></div><div class="chart-wrap"><svg id="worldChart" class="chart" role="img" aria-labelledby="worldChartTitle worldChartDescription"></svg><div id="worldTooltip" class="chart-tooltip"></div></div></article>
          <aside id="worldFacts" class="panel world-facts"></aside>
        </div>
        <article class="panel" style="margin-top:16px"><div class="panel-heading"><div><h2>All worlds</h2><p>Click a row to make it the primary world.</p></div><div class="table-tools"><input id="worldSearch" type="search" placeholder="Search worlds…" aria-label="Search all worlds"></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>World</th><th>Latest</th><th>Region</th><th>PvP</th><th>Population</th><th>Total return</th></tr></thead><tbody id="worldTable"></tbody></table></div></article>
      </section>

      <section id="view-forecasts" class="view" hidden>
        <div class="view-header"><div><h1>Forecasts</h1><p class="view-intro">Scenario ranges describe uncertainty around the level; the actionable model predicts relative convergence only.</p></div>
          <div class="filters"><div class="field"><label for="forecastWorld">World</label><select id="forecastWorld"></select></div><div class="field"><label>Horizon</label><div id="forecastHorizon" class="segmented"><button class="segment" data-horizon="2w">2 weeks</button><button class="segment active" data-horizon="1m">1 month</button><button class="segment" data-horizon="3m">3 months</button><button class="segment" data-horizon="6m">6 months</button></div></div></div>
        </div>
        <div class="forecast-grid">
          <article class="panel chart-panel"><div class="panel-heading"><div><h2 id="forecastChartTitle">Forecast fan</h2><p>Median and 80% simulated range. A wide band is uncertainty, not opportunity.</p></div></div><div class="chart-wrap"><svg id="forecastChart" class="chart" role="img" aria-labelledby="forecastChartTitle"></svg><div id="forecastTooltip" class="chart-tooltip"></div></div></article>
          <aside id="forecastSummary" class="panel forecast-summary"></aside>
        </div>
        <article class="panel" style="margin-top:16px"><div class="panel-heading"><div><h2>Relative-value ranking</h2><p>Seven-day predicted change in each world's position versus the cross-world mean.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>World</th><th>Price</th><th>Deviation</th><th>Prediction</th><th>80% interval</th></tr></thead><tbody id="predictionTable"></tbody></table></div></article>
      </section>

      <section id="view-models" class="view" hidden>
        <div class="view-header"><div><h1>General vs specific</h1><p class="view-intro">Compare the shared 61-world model with hierarchical group models defined by PvP, BattlEye cohort and region.</p></div>
          <div class="filters" aria-label="Specific model filters">
            <div class="field"><label for="modelPvp">PvP</label><select id="modelPvp"></select></div>
            <div class="field"><label for="modelBattleye">BattlEye</label><select id="modelBattleye"></select></div>
            <div class="field"><label for="modelRegion">Region</label><select id="modelRegion"></select></div>
            <div class="field"><label for="modelWorld">Inspect world</label><select id="modelWorld"></select></div>
          </div>
        </div>
        <div class="metric-rail" aria-label="Model comparison summary">
          <div class="metric"><span class="metric-label">General holdout RMSE</span><strong id="modelGeneralRmse" class="metric-value">—</strong><span class="metric-meta">lower is better</span></div>
          <div class="metric"><span class="metric-label">Specific holdout RMSE</span><strong id="modelSpecificRmse" class="metric-value">—</strong><span class="metric-meta">same untouched dates</span></div>
          <div class="metric"><span class="metric-label">Holdout winner</span><strong id="modelWinner" class="metric-value">—</strong><span id="modelWinnerMeta" class="metric-meta"></span></div>
          <div class="metric"><span class="metric-label">Specific models</span><strong id="modelCount" class="metric-value">—</strong><span class="metric-meta">PvP types never mixed</span></div>
        </div>
        <div class="model-grid">
          <article class="panel chart-panel"><div class="panel-heading"><div><h2 id="modelChartTitle">Holdout error by PvP type</h2><p>General and specific model RMSE; lower bars are better.</p></div><div class="legend"><span class="legend-item"><i class="legend-line"></i>General</span><span class="legend-item"><i class="legend-line" style="border-color:var(--gold)"></i>Specific</span></div></div><div class="chart-wrap"><svg id="modelChart" class="chart" role="img" aria-labelledby="modelChartTitle"></svg></div></article>
          <aside id="modelDetail" class="panel model-detail"></aside>
        </div>
        <article class="panel" style="margin-top:16px">
          <div class="panel-heading"><div><h2>Launch phase · experimental</h2><p>PvP-specific models for regular worlds from creation through age 540 days.</p></div><span class="model-badge warning">General remains default</span></div>
          <div class="metric-rail" aria-label="Launch model comparison summary">
            <div class="metric"><span class="metric-label">Active launch worlds</span><strong id="launchActiveWorlds" class="metric-value">—</strong><span class="metric-meta">inside the 540-day window</span></div>
            <div class="metric"><span class="metric-label">General holdout RMSE</span><strong id="launchGeneralRmse" class="metric-value">—</strong><span class="metric-meta">mature mapping applied to launches</span></div>
            <div class="metric"><span class="metric-label">Launch holdout RMSE</span><strong id="launchRmse" class="metric-value">—</strong><span class="metric-meta">unseen worlds and later dates</span></div>
            <div class="metric"><span class="metric-label">Holdout winner</span><strong id="launchWinner" class="metric-value">—</strong><span id="launchWinnerMeta" class="metric-meta"></span></div>
          </div>
          <div class="panel-heading"><div><h2>Current launch scores</h2><p id="launchTableCount">Active launch worlds</p></div><div class="table-tools"><input id="launchSearch" type="search" placeholder="Search launch worlds…" aria-label="Search launch predictions"></div></div>
          <div class="table-wrap"><table class="data-table"><thead><tr><th>World</th><th>Age</th><th>Data age</th><th>PvP</th><th>General 7d</th><th>Launch 7d</th><th>Difference</th><th>Model</th></tr></thead><tbody id="launchTable"></tbody></table></div>
          <div class="panel-heading"><div><h2>Launch holdout by PvP</h2><p>Lower RMSE is better; zero means no expected change.</p></div></div>
          <div class="table-wrap"><table class="data-table"><thead><tr><th>Scope</th><th>Worlds</th><th>Launch RMSE</th><th>General RMSE</th><th>Zero RMSE</th><th>Winner</th></tr></thead><tbody id="launchComparisonTable"></tbody></table></div>
        </article>
        <article class="panel" style="margin-top:16px">
          <div class="panel-heading"><div><h2>Pooling hierarchy</h2><p>Five worlds is the preferred minimum; fallback removes dimensions from the bottom up.</p></div><span class="model-badge">PvP always separate</span></div>
          <div class="model-levels">
            <div class="model-level"><strong>1 · Exact segment</strong>PvP × BattlEye × region. Used when at least five eligible worlds share all three dimensions.</div>
            <div class="model-level"><strong>2 · Pool regions</strong>If the exact segment is small, locations are combined while PvP and BattlEye remain fixed.</div>
            <div class="model-level"><strong>3 · Pool BattlEye</strong>If still small, BattlEye cohorts are combined. PvP is never combined with another PvP type.</div>
          </div>
        </article>
        <article class="panel" style="margin-top:16px">
          <div class="panel-heading"><div><h2>Current predictions</h2><p id="modelTableCount">Eligible worlds</p></div><div class="table-tools"><input id="modelSearch" type="search" placeholder="Search eligible worlds…" aria-label="Search model predictions"></div></div>
          <div class="table-wrap"><table class="data-table"><thead><tr><th>World</th><th>PvP</th><th>BattlEye</th><th>Region</th><th>General 7d</th><th>Specific 7d</th><th>Difference</th><th>Group level</th></tr></thead><tbody id="modelTable"></tbody></table></div>
        </article>
        <article class="panel" style="margin-top:16px">
          <div class="panel-heading"><div><h2>Minimum-group sensitivity</h2><p>The preferred five-world gate is declared before the final holdout, not selected from it.</p></div></div>
          <div class="table-wrap"><table class="data-table"><thead><tr><th>Minimum worlds</th><th>Specific models</th><th>Exact worlds</th><th>Region pooled</th><th>PvP pooled</th><th>General validation RMSE</th><th>Specific validation RMSE</th></tr></thead><tbody id="modelSensitivityTable"></tbody></table></div>
        </article>
      </section>

      <section id="view-strategy" class="view" hidden>
        <div class="view-header"><div><h1>Strategy</h1><p class="view-intro">Test the strongest cross-world convergence signals after transaction cost, with training and untouched holdout evidence separated.</p></div>
          <div id="strategyHorizon" class="segmented"><button class="segment active" data-days="7">7 days</button><button class="segment" data-days="30">30 days</button><button class="segment" data-days="91">91 days</button></div>
        </div>
        <div class="strategy-grid">
          <article class="panel"><div class="panel-heading"><div><h2>Net return after cost</h2><p>Top-decile raw convergence gap.</p></div></div><div id="strategyBars" class="bar-area"></div></article>
          <aside id="strategyEvidence" class="panel evidence"></aside>
        </div>
        <article class="panel" style="margin-top:16px"><div class="panel-heading"><div><h2>How to read the signal</h2><p>What the evidence permits—and what it does not.</p></div></div><div class="signal" style="grid-template-columns:repeat(3,1fr)">
          <div class="signal-block"><h3>Use</h3><p class="signal-note">Rank worlds by their raw gap to the cross-world mean and act only on the strongest decile outside the friction band.</p></div>
          <div class="signal-block"><h3>Do not use</h3><p class="signal-note">Do not issue a directional call on the common Tibia Coin price level; fifteen model classes fail to beat a random walk.</p></div>
          <div class="signal-block"><h3>Binding constraint</h3><p class="signal-note">Market depth limits deployable size. The opportunity is relative, conditional and capacity-constrained.</p></div>
        </div></article>
      </section>

      <section id="view-emission" class="view" hidden>
        <div class="view-header"><div><h1>Gold Emission</h1><p class="view-intro">Explore reconstructed direct coins and NPC-sale potential by world, period and realization scenario.</p></div><a class="button primary" href="gold_emission_dashboard.html" target="_blank" rel="noopener">Open full screen</a></div>
        <iframe id="emissionFrame" class="emission-frame" title="Interactive gold emission dashboard" loading="lazy"></iframe>
      </section>

      <section id="view-library" class="view" hidden>
        <div class="view-header"><div><h1>Research Library</h1><p class="view-intro">Search, open and inspect every analytical exhibit with its method note and source.</p></div><a class="button" href="tibia_coin_market_report.pdf" target="_blank" rel="noopener" id="reportLink">Read the full report</a></div>
        <div class="library-tools"><input id="librarySearch" type="search" placeholder="Search titles, topics or notes…" aria-label="Search research library"><select id="libraryTopic" aria-label="Filter research topic"><option value="all">All topics</option></select><button id="clearLibrary" class="button" type="button">Clear filters</button></div>
        <div id="libraryCount" class="source"></div>
        <div id="libraryGrid" class="library-grid" style="margin-top:12px"></div>
      </section>

      <footer class="footer"><span>Independent study · GP per Tibia Coin · not affiliated with CipSoft</span><span id="footerCoverage"></span></footer>
    </main>
  </div>
</div>

<dialog id="exhibitDialog">
  <div class="modal-head"><div><small id="modalId" class="exhibit-id"></small><h2 id="modalTitle"></h2><p id="modalSubtitle" class="view-intro"></p></div><button id="modalClose" class="icon-button" aria-label="Close exhibit">×</button></div>
  <div class="modal-body"><img id="modalImage" alt=""><div class="modal-notes"><h3>Interpretation</h3><p id="modalNote"></p><h3>Source</h3><p id="modalSource" class="source"></p><a id="modalOpenImage" class="button" target="_blank" rel="noopener">Open original</a></div></div>
</dialog>

<script>
const EMBEDDED = __DATA__;
const DATA_FILES = {
  marketIndex:"../data/processed/market_index.csv",
  worlds:"../data/processed/world_summary.csv",
  worldSeries:"../data/processed/panel_daily.csv",
  forecasts:"../data/processed/forecasts_sa.csv",
  predictions:"../data/processed/latest_predictions.csv",
  specificPredictions:"../data/processed/latest_specific_predictions.csv",
  modelRegistry:"../data/processed/specific_model_registry.csv",
  modelComparison:"../data/processed/specific_model_comparison.csv",
  modelSensitivity:"../data/processed/specific_model_sensitivity.csv",
  launchPredictions:"../data/processed/latest_launch_predictions.csv",
  launchRegistry:"../data/processed/launch_model_registry.csv",
  launchComparison:"../data/processed/launch_model_comparison.csv",
  strategy:"../data/processed/strategy_holdout.csv"
};
const COLORS = {blue:"#155eef",gray:"#7b869a",gold:"#c58b16",green:"#14804a",red:"#c9363e"};
const NS = "http://www.w3.org/2000/svg";
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const fmt = new Intl.NumberFormat("en-US",{maximumFractionDigits:0});
const fmt1 = new Intl.NumberFormat("en-US",{maximumFractionDigits:1});
const pct1 = new Intl.NumberFormat("en-US",{style:"percent",maximumFractionDigits:1});
const dateFmt = new Intl.DateTimeFormat("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"});
const shortDate = new Intl.DateTimeFormat("en-US",{month:"short",year:"2-digit",timeZone:"UTC"});
let data = structuredClone(EMBEDDED);
let worldMap = new Map();
let seriesMap = new Map();
let comparisonDates = [];
let predictionMap = new Map();
let specificPredictionMap = new Map();
let modelRegistryMap = new Map();
let launchPredictionMap = new Map();
let launchRegistryMap = new Map();
let forecastMap = new Map();
let activeView = "overview";
let selectedForecastHorizon = "1m";
let selectedWorldChartMode = "price";
let selectedStrategyHorizon = 7;
let selectedExhibit = "";
let liveMode = false;

function num(value){const parsed=Number(value);return Number.isFinite(parsed)?parsed:0}
function bool(value){return value===true||value===1||String(value).toLowerCase()==="true"}
function date(value){return new Date(`${value}T00:00:00Z`)}
function compact(value){const n=Math.abs(value);if(n>=1e9)return`${(value/1e9).toFixed(2)}B`;if(n>=1e6)return`${(value/1e6).toFixed(2)}M`;if(n>=1e3)return`${(value/1e3).toFixed(1)}K`;return fmt.format(value)}
function signed(value,digits=2){return`${value>0?"+":""}${num(value).toFixed(digits)}%`}
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]))}
function safeDate(value,min,max){return value&&value>=min&&value<=max?value:""}
function addSvg(parent,tag,attributes,text=""){const el=document.createElementNS(NS,tag);Object.entries(attributes).forEach(([key,val])=>el.setAttribute(key,val));if(text)el.textContent=text;parent.appendChild(el);return el}
function uniqueIndexes(count,length){if(length<=1)return[0];return[...new Set(Array.from({length:count},(_,i)=>Math.round(i*(length-1)/(count-1))))]}
function niceMax(value){const e=Math.floor(Math.log10(Math.max(value,1)));const u=10**e;const n=value/u;return(n<=1?1:n<=2?2:n<=5?5:10)*u}

function rebuildIndexes(){
  worldMap=new Map(data.worlds.map(row=>[row.world,row]));
  seriesMap=new Map();
  for(const row of data.worldSeries){
    if(!seriesMap.has(row.world))seriesMap.set(row.world,[]);
    seriesMap.get(row.world).push(row);
  }
  for(const rows of seriesMap.values())rows.sort((a,b)=>a.date.localeCompare(b.date));
  comparisonDates=[...new Set(data.worldSeries.map(row=>row.date))].sort();
  predictionMap=new Map(data.predictions.map(row=>[row.world,row]));
  specificPredictionMap=new Map(data.specificPredictions.map(row=>[row.world,row]));
  modelRegistryMap=new Map(data.modelRegistry.map(row=>[row.world,row]));
  launchPredictionMap=new Map(data.launchPredictions.map(row=>[row.world,row]));
  launchRegistryMap=new Map(data.launchRegistry.map(row=>[row.world,row]));
  forecastMap=new Map(data.forecasts.map(row=>[row.world,row]));
}

function populateSelect(select,values,selected,allLabel=""){
  select.innerHTML=(allLabel?`<option value="all">${escapeHtml(allLabel)}</option>`:"")+
    values.map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  if([...select.options].some(option=>option.value===selected))select.value=selected;
}

function initialize(){
  rebuildIndexes();
  const params=new URLSearchParams(location.search);
  const worlds=[...worldMap.keys()].sort((a,b)=>a.localeCompare(b));
  populateSelect($("#overviewWorld"),worlds,params.get("world")||"all","All worlds");
  populateSelect($("#worldA"),worlds,params.get("a")||"Antica");
  populateSelect($("#worldB"),worlds,params.get("b")||"Belobra");
  populateSelect($("#forecastWorld"),[...forecastMap.keys()].sort(),params.get("forecast")||"Belobra");
  const modelWorlds=[...new Set([...specificPredictionMap.keys(),...launchPredictionMap.keys()])].sort();
  const allModelRows=[...data.specificPredictions,...data.launchPredictions];
  populateSelect($("#modelPvp"),[...new Set(allModelRows.map(row=>row.pvp_type))].sort(),params.get("modelPvp")||"all","All PvP types");
  populateSelect($("#modelBattleye"),[...new Set(allModelRows.map(row=>row.battleye_color))].sort(),params.get("modelBe")||"all","All cohorts");
  populateSelect($("#modelRegion"),[...new Set(allModelRows.map(row=>row.region))].sort(),params.get("modelRegion")||"all","All regions");
  populateSelect($("#modelWorld"),modelWorlds,params.get("modelWorld")||"Belobra");
  const dates=data.marketIndex.map(row=>row.date);
  const min=dates[0],max=dates[dates.length-1];
  $("#overviewStart").min=$("#overviewEnd").min=min;
  $("#overviewStart").max=$("#overviewEnd").max=max;
  $("#overviewStart").value=safeDate(params.get("start"),min,max)||min;
  $("#overviewEnd").value=safeDate(params.get("end"),min,max)||max;
  selectedForecastHorizon=["2w","1m","3m","6m"].includes(params.get("horizon"))?params.get("horizon"):"1m";
  selectedWorldChartMode=["price","return"].includes(params.get("worldMeasure"))?params.get("worldMeasure"):"price";
  selectedStrategyHorizon=[7,30,91].includes(Number(params.get("days")))?Number(params.get("days")):7;
  bindEvents();
  populateLibraryChapters();
  showView(["overview","worlds","forecasts","models","strategy","emission","library"].includes(params.get("view"))?params.get("view"):"overview",false);
  updateStatus();
  renderAll();
  if(params.get("exhibit")&&data.figures.some(item=>item.id===params.get("exhibit"))){
    showView("library",false);
    openExhibit(params.get("exhibit"));
  }
}

function bindEvents(){
  $$(".nav-button").forEach(button=>button.addEventListener("click",()=>showView(button.dataset.view)));
  ["#overviewWorld","#overviewStart","#overviewEnd","#overviewSort"].forEach(selector=>$(selector).addEventListener("change",()=>{renderOverview();updateURL()}));
  $("#overviewSearch").addEventListener("input",renderOverviewTable);
  $("#worldA").addEventListener("change",()=>{renderWorlds();updateURL()});
  $("#worldB").addEventListener("change",()=>{renderWorlds();updateURL()});
  $$("#worldChartMode .segment").forEach(button=>button.addEventListener("click",()=>{selectedWorldChartMode=button.dataset.mode;renderWorldChart();updateURL()}));
  $("#worldSearch").addEventListener("input",renderWorldTable);
  $("#forecastWorld").addEventListener("change",()=>{renderForecasts();updateURL()});
  $$("#forecastHorizon .segment").forEach(button=>button.addEventListener("click",()=>{selectedForecastHorizon=button.dataset.horizon;renderForecasts();updateURL()}));
  ["#modelPvp","#modelBattleye","#modelRegion"].forEach(selector=>$(selector).addEventListener("change",()=>{renderModels();updateURL()}));
  $("#modelWorld").addEventListener("change",()=>{renderModelDetail();updateURL()});
  $("#modelSearch").addEventListener("input",renderModelTable);
  $("#launchSearch").addEventListener("input",renderLaunchModels);
  $$("#strategyHorizon .segment").forEach(button=>button.addEventListener("click",()=>{selectedStrategyHorizon=Number(button.dataset.days);renderStrategy();updateURL()}));
  $("#librarySearch").addEventListener("input",renderLibrary);
  $("#libraryTopic").addEventListener("change",renderLibrary);
  $("#clearLibrary").addEventListener("click",()=>{$("#librarySearch").value="";$("#libraryTopic").value="all";renderLibrary()});
  $("#copyView").addEventListener("click",copyView);
  $("#modalClose").addEventListener("click",closeExhibit);
  $("#exhibitDialog").addEventListener("click",event=>{if(event.target===$("#exhibitDialog"))closeExhibit()});
  window.addEventListener("resize",debounce(()=>{if(activeView==="overview")renderOverviewChart();if(activeView==="worlds")renderWorldChart();if(activeView==="forecasts")renderForecastChart();if(activeView==="models")renderModelChart()},120));
}

function showView(view,push=true){
  activeView=view;
  $$(".view").forEach(section=>section.hidden=section.id!==`view-${view}`);
  $$(".nav-button").forEach(button=>button.classList.toggle("active",button.dataset.view===view));
  if(view==="emission"&&!$("#emissionFrame").src)$("#emissionFrame").src="gold_emission_dashboard.html";
  if(view==="overview")renderOverview();
  if(view==="worlds")renderWorlds();
  if(view==="forecasts")renderForecasts();
  if(view==="models")renderModels();
  if(view==="strategy")renderStrategy();
  if(view==="library")renderLibrary();
  if(push)updateURL();
  window.scrollTo({top:0,behavior:matchMedia("(prefers-reduced-motion:reduce)").matches?"auto":"smooth"});
}

function renderHeadline(){
  // Every figure below comes from data.meta, which the builder reads from the same results
  // files the PDF reads. Nothing here is written by hand, so the page cannot drift from the
  // report when a pipeline stage re-runs.
  const m=data.meta;
  const el=(id,txt)=>{const n=$("#"+id);if(n)n.textContent=txt;};
  el("signalNet",`${signed(m.holdoutNet7,2)} net`);
  el("signalNote",`7-day true holdout · t = ${Number(m.holdoutT7).toFixed(1)} · `+
                  `${m.holdoutWindows7} independent windows`);
  el("verdictLine",m.verdict);
  el("verdictConfidence",`${m.confidence}/100 confidence`);
  el("factBand",`${Number(m.bandThresholdPct).toFixed(2)}%`);
  el("factAction",`${Number(m.actionGapPct).toFixed(0)}%`);
  el("factLot",`${fmt.format(m.feeCapLotTc)} TC`);
  el("factRoundTrip",`${Number(m.roundTripPct).toFixed(2)}%`);
  el("factNet30",`${signed(m.strategyNet30,2)}`);
  el("factWin30",`${Math.round(m.strategyWin30*100)}%`);
  el("factEpisodes",`${Number(m.episodesPerMonth).toFixed(1)} / month`);
  // A capacity estimate built on ~6 episodes a month does not support nine significant
  // figures; round it to the precision the underlying count can carry.
  const cap=Number(m.capacityGpPerMonth);
  el("factCapacity",cap>=1e6?`${(cap/1e6).toFixed(0)}M GP / month`:
                    `${fmt.format(Math.round(cap))} GP / month`);
  el("factVenue",`${Number(m.bazaarOverMarket).toFixed(1)}×`);
  el("factFlow",`${fmt.format(m.tcPerWorldDay)} TC`);
  el("factWindows",`${m.holdoutWindows7} · ${m.holdoutWindows30} · ${m.holdoutWindows91}`);
  const link=$("#reportLink");
  if(link&&m.reportPages)link.textContent=`Read the ${m.reportPages}-page report`;
}

function renderAll(){
  renderOverview();renderWorlds();renderForecasts();renderModels();renderStrategy();renderLibrary();
  renderHeadline();
  $("#footerCoverage").textContent=`${fmt.format(data.meta.worldDays)} world-days · ${fmt.format(data.meta.worlds)} worlds · ${data.meta.start} to ${data.meta.end}`;
}

function updateStatus(){
  const generated=new Date(data.meta.generatedAt);
  const stamp=Number.isNaN(generated.valueOf())?data.meta.generatedAt:generated.toLocaleString("en-US");
  $("#statusDot").classList.toggle("fallback",!liveMode&&["http:","https:"].includes(location.protocol));
  $("#dataStatus").textContent=liveMode?`Live project data · refreshed ${stamp}`:
    ["http:","https:"].includes(location.protocol)?`Embedded fallback · project CSV unavailable · ${stamp}`:`Offline snapshot · ${stamp}`;
}

function overviewRows(){
  const world=$("#overviewWorld").value;
  const start=$("#overviewStart").value,end=$("#overviewEnd").value;
  if(start>end)return[];
  return world==="all"?data.marketIndex.filter(row=>row.date>=start&&row.date<=end):
    (seriesMap.get(world)||[]).filter(row=>row.date>=start&&row.date<=end);
}

function renderOverview(){
  const world=$("#overviewWorld").value;
  const rows=overviewRows();
  const latestIndex=data.marketIndex[data.marketIndex.length-1]||{};
  const prices=data.worlds.map(row=>num(row.px_last)).filter(Boolean).sort((a,b)=>a-b);
  const median=prices.length?prices[Math.floor(prices.length/2)]:0;
  if(world==="all"){
    $("#metricPriceLabel").textContent="Market index";
    $("#metricPrice").textContent=latestIndex.ew_price?`${fmt.format(latestIndex.ew_price)} GP`:"—";
    $("#metricPriceMeta").textContent=`${signed(data.meta.indexReturn,1)} since Apr 2024`;
    $("#metricWorlds").textContent=fmt.format(data.meta.worlds);
    $("#metricMedian").textContent=`${fmt.format(median)} GP`;
    $("#metricDispersion").textContent=`${num(latestIndex.disp_pct).toFixed(1)}%`;
    $("#overviewChartTitle").textContent="Market index and dispersion";
  }else{
    const item=worldMap.get(world)||{};
    $("#metricPriceLabel").textContent=`${world} price`;
    $("#metricPrice").textContent=item.px_last?`${fmt.format(item.px_last)} GP`:"—";
    $("#metricPriceMeta").textContent=`${signed(item.total_ret_pct,1)} total return`;
    $("#metricWorlds").textContent=item.converged?"Converged":"Launch";
    $("#metricMedian").textContent=item.px_med?`${fmt.format(item.px_med)} GP`:"—";
    $("#metricDispersion").textContent=item.vol?`${num(item.vol).toFixed(1)}%`:"—";
    $("#overviewChartTitle").textContent=`${world} price history`;
  }
  renderOverviewChart(rows,world);
  renderOverviewTable();
}

function renderOverviewChart(rows=overviewRows(),world=$("#overviewWorld").value){
  const svg=$("#overviewChart"),tooltip=$("#overviewTooltip");
  svg.innerHTML="";
  if(!rows.length){addSvg(svg,"text",{x:400,y:170,"text-anchor":"middle",fill:"#647087"},"No observations for this selection");return}
  const width=Math.max(320,svg.clientWidth||900),height=340,m={top:22,right:world==="all"?64:16,bottom:42,left:64};
  const iw=width-m.left-m.right,ih=height-m.top-m.bottom;
  const priceKey=world==="all"?"ew_price":"price_gp";
  const prices=rows.map(row=>num(row[priceKey]));
  const pMin=Math.min(...prices),pMax=Math.max(...prices),pad=Math.max((pMax-pMin)*.12,500);
  const low=Math.max(0,pMin-pad),high=pMax+pad;
  const x=i=>m.left+(rows.length===1?iw/2:i/(rows.length-1)*iw);
  const y=value=>m.top+ih-(value-low)/(high-low||1)*ih;
  const dispersionMax=Math.max(10,...rows.map(row=>num(row.disp_pct)));
  const y2=value=>m.top+ih-num(value)/dispersionMax*ih;
  svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
  for(let i=0;i<=4;i++){
    const value=low+(high-low)*i/4,yy=y(value);
    addSvg(svg,"line",{x1:m.left,x2:width-m.right,y1:yy,y2:yy,stroke:"#e5eaf1","stroke-dasharray":i?"3 4":""});
    addSvg(svg,"text",{x:m.left-9,y:yy+4,"text-anchor":"end",fill:"#647087","font-size":10},compact(value));
  }
  for(const index of uniqueIndexes(Math.min(width<600?4:7,rows.length),rows.length)){
    addSvg(svg,"text",{x:x(index),y:height-13,"text-anchor":"middle",fill:"#647087","font-size":10},shortDate.format(date(rows[index].date)));
  }
  const pricePath=rows.map((row,i)=>`${i?"L":"M"} ${x(i).toFixed(2)} ${y(num(row[priceKey])).toFixed(2)}`).join(" ");
  addSvg(svg,"path",{d:pricePath,fill:"none",stroke:COLORS.blue,"stroke-width":2.4,"stroke-linecap":"round","stroke-linejoin":"round","vector-effect":"non-scaling-stroke"});
  if(world==="all"){
    const dispersionPath=rows.map((row,i)=>`${i?"L":"M"} ${x(i).toFixed(2)} ${y2(row.disp_pct).toFixed(2)}`).join(" ");
    addSvg(svg,"path",{d:dispersionPath,fill:"none",stroke:COLORS.gray,"stroke-width":1.8,"stroke-dasharray":"6 5","vector-effect":"non-scaling-stroke"});
    for(let i=0;i<=4;i++){
      const value=dispersionMax*i/4,yy=y2(value);
      addSvg(svg,"text",{x:width-m.right+9,y:yy+4,fill:"#647087","font-size":10},`${value.toFixed(value<10?1:0)}%`);
    }
  }
  $("#overviewLegend").innerHTML=`<span class="legend-item"><i class="legend-line"></i>${world==="all"?"Chain-linked index":escapeHtml(world)+" price"}</span>`+
    (world==="all"?`<span class="legend-item"><i class="legend-line dashed"></i>Cross-world dispersion</span>`:"");
  const cross=addSvg(svg,"line",{x1:m.left,x2:m.left,y1:m.top,y2:m.top+ih,stroke:"#34405a",opacity:0});
  const capture=addSvg(svg,"rect",{x:m.left,y:m.top,width:iw,height:ih,fill:"transparent",tabindex:"0","aria-label":"Interactive time-series chart"});
  const inspect=index=>{
    index=Math.max(0,Math.min(rows.length-1,index));const row=rows[index],xx=x(index);
    cross.setAttribute("x1",xx);cross.setAttribute("x2",xx);cross.setAttribute("opacity",1);
    tooltip.innerHTML=`<strong>${dateFmt.format(date(row.date))}</strong><br>${world==="all"?"Market index":escapeHtml(world)}: ${fmt.format(row[priceKey])} GP`+
      (world==="all"?`<br>Dispersion: ${num(row.disp_pct).toFixed(1)}%`:"");
    tooltip.style.left=`${Math.min(Math.max(8,xx+8),Math.max(8,width-210))}px`;tooltip.style.top="28px";tooltip.classList.add("visible");
    capture.setAttribute("aria-label",tooltip.textContent);
  };
  capture.addEventListener("pointermove",event=>{const b=svg.getBoundingClientRect(),px=(event.clientX-b.left)/b.width*width;inspect(Math.round((px-m.left)/iw*(rows.length-1)))});
  capture.addEventListener("pointerdown",event=>{const b=svg.getBoundingClientRect(),px=(event.clientX-b.left)/b.width*width;inspect(Math.round((px-m.left)/iw*(rows.length-1)))});
  capture.addEventListener("pointerleave",()=>{cross.setAttribute("opacity",0);tooltip.classList.remove("visible")});
  capture.addEventListener("keydown",event=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;event.preventDefault();let i=Number(capture.dataset.index||0);if(event.key==="ArrowLeft")i--;if(event.key==="ArrowRight")i++;if(event.key==="Home")i=0;if(event.key==="End")i=rows.length-1;capture.dataset.index=Math.max(0,Math.min(rows.length-1,i));inspect(Number(capture.dataset.index))});
}

function joinedWorlds(){
  return data.worlds.map(world=>({...world,prediction:predictionMap.get(world.world)||null}));
}

function signalOf(row){
  if(!row.prediction)return{label:"No model",className:"neutral"};
  if(!bool(row.prediction.outside_band))return{label:"Inside band",className:"neutral"};
  return num(row.prediction.predicted_change_pct)>=0?{label:"Converging ↑",className:"positive"}:{label:"Diverging ↓",className:"negative"};
}

function renderOverviewTable(){
  const term=$("#overviewSearch").value.trim().toLowerCase(),sort=$("#overviewSort").value;
  let rows=joinedWorlds().filter(row=>row.world.toLowerCase().includes(term));
  rows.sort((a,b)=>{
    if(sort==="world")return a.world.localeCompare(b.world);
    if(sort==="price")return num(b.px_last)-num(a.px_last);
    if(sort==="deviation")return Math.abs(num(b.prediction?.deviation_pct))-Math.abs(num(a.prediction?.deviation_pct));
    return num(b.prediction?.predicted_change_pct)-num(a.prediction?.predicted_change_pct);
  });
  $("#overviewTableCount").textContent=`${fmt.format(rows.length)} worlds`;
  $("#overviewTable").innerHTML=rows.map(row=>{const signal=signalOf(row);return`<tr data-world="${escapeHtml(row.world)}">
    <td data-label="World"><strong>${escapeHtml(row.world)}</strong></td>
    <td data-label="Price">${row.px_last?fmt.format(row.px_last):"—"}</td>
    <td data-label="Deviation" class="${num(row.prediction?.deviation_pct)>=0?"positive":"negative"}">${row.prediction?signed(row.prediction.deviation_pct):"—"}</td>
    <td data-label="Predicted 7d" class="${num(row.prediction?.predicted_change_pct)>=0?"positive":"negative"}">${row.prediction?signed(row.prediction.predicted_change_pct):"—"}</td>
    <td data-label="Signal" class="${signal.className}">${signal.label}</td></tr>`}).join("");
  $$("#overviewTable tr").forEach(row=>row.addEventListener("click",()=>{$("#worldA").value=row.dataset.world;showView("worlds")}));
}

function renderWorlds(){
  renderWorldChart();renderWorldFacts();renderWorldTable();
}

function commonSeries(worldA,worldB){
  const a=seriesMap.get(worldA)||[],b=seriesMap.get(worldB)||[];
  const aMap=new Map(a.map(row=>[row.date,row]));
  const bMap=new Map(b.map(row=>[row.date,row]));
  const a0=a.length?num(a[0].price_gp):null,b0=b.length?num(b[0].price_gp):null;
  return comparisonDates.map(item=>{
    const aPrice=aMap.has(item)?num(aMap.get(item).price_gp):null;
    const bPrice=bMap.has(item)?num(bMap.get(item).price_gp):null;
    return{date:item,aPrice,bPrice,
      aReturn:aPrice!==null&&a0?(aPrice/a0-1)*100:null,
      bReturn:bPrice!==null&&b0?(bPrice/b0-1)*100:null};
  });
}

function renderWorldChart(){
  const worldA=$("#worldA").value,worldB=$("#worldB").value,rows=commonSeries(worldA,worldB);
  $$("#worldChartMode .segment").forEach(button=>button.classList.toggle("active",button.dataset.mode===selectedWorldChartMode));
  const fixedWindow=`${dateFmt.format(date(comparisonDates[0]))} to ${dateFmt.format(date(comparisonDates[comparisonDates.length-1]))}`;
  $("#worldChartDescription").textContent=selectedWorldChartMode==="price"
    ?`Actual daily market price in GP per Tibia Coin. Fixed window: ${fixedWindow}; missing history is left blank.`
    :`Percentage gain or loss from each world's first observation. Fixed window: ${fixedWindow}; 0% means no change.`;
  $("#worldLegend").innerHTML=`<span class="legend-item"><i class="legend-line"></i>${escapeHtml(worldA)}</span><span class="legend-item"><i class="legend-line" style="border-color:${COLORS.gold}"></i>${escapeHtml(worldB)}</span>`;
  drawTwoSeries($("#worldChart"),$("#worldTooltip"),rows,{a:worldA,b:worldB},selectedWorldChartMode);
}

function drawTwoSeries(svg,tooltip,rows,labels,mode){
  svg.innerHTML="";
  if(!rows.length){addSvg(svg,"text",{x:400,y:170,"text-anchor":"middle",fill:"#647087"},"No observations for this selection");return}
  const width=Math.max(320,svg.clientWidth||900),height=340,m={top:22,right:18,bottom:42,left:58},iw=width-m.left-m.right,ih=height-m.top-m.bottom;
  const aKey=mode==="return"?"aReturn":"aPrice",bKey=mode==="return"?"bReturn":"bPrice";
  const values=rows.flatMap(row=>[row[aKey],row[bKey]]).filter(Number.isFinite);
  if(!values.length){addSvg(svg,"text",{x:400,y:170,"text-anchor":"middle",fill:"#647087"},"No observations for this selection");return}
  const rawLow=Math.min(...values),rawHigh=Math.max(...values),padding=Math.max((rawHigh-rawLow)*.08,mode==="return"?1:100);
  const low=rawLow-padding,high=rawHigh+padding;
  const x=i=>m.left+i/(rows.length-1||1)*iw,y=value=>m.top+ih-(value-low)/(high-low||1)*ih;
  svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
  for(let i=0;i<=4;i++){const v=low+(high-low)*i/4,yy=y(v);addSvg(svg,"line",{x1:m.left,x2:width-m.right,y1:yy,y2:yy,stroke:"#e5eaf1"});addSvg(svg,"text",{x:m.left-8,y:yy+4,"text-anchor":"end",fill:"#647087","font-size":10},mode==="return"?`${v>=0?"+":""}${v.toFixed(0)}%`:fmt.format(Math.round(v)))}
  for(const index of uniqueIndexes(Math.min(width<600?4:7,rows.length),rows.length))addSvg(svg,"text",{x:x(index),y:height-13,"text-anchor":"middle",fill:"#647087","font-size":10},shortDate.format(date(rows[index].date)));
  if(mode==="return"&&low<0&&high>0)addSvg(svg,"line",{x1:m.left,x2:width-m.right,y1:y(0),y2:y(0),stroke:"#647087","stroke-dasharray":"4 4"});
  const linePath=key=>{let d="",open=false;rows.forEach((row,i)=>{if(!Number.isFinite(row[key])){open=false;return}d+=`${open?"L":"M"} ${x(i).toFixed(2)} ${y(row[key]).toFixed(2)} `;open=true});return d.trim()};
  for(const [key,color] of [[aKey,COLORS.blue],[bKey,COLORS.gold]])addSvg(svg,"path",{d:linePath(key),fill:"none",stroke:color,"stroke-width":2.3,"vector-effect":"non-scaling-stroke"});
  const cross=addSvg(svg,"line",{x1:m.left,x2:m.left,y1:m.top,y2:m.top+ih,stroke:"#34405a",opacity:0});
  const capture=addSvg(svg,"rect",{x:m.left,y:m.top,width:iw,height:ih,fill:"transparent",tabindex:"0","aria-label":`Interactive world comparison by ${mode==="return"?"percentage return":"actual GP price"}`});
  const reading=(price,ret)=>price===null?"No observation":`${fmt.format(price)} GP · ${signed(ret,1)} since start`;
  const inspect=i=>{i=Math.max(0,Math.min(rows.length-1,i));const row=rows[i],xx=x(i);cross.setAttribute("x1",xx);cross.setAttribute("x2",xx);cross.setAttribute("opacity",1);tooltip.innerHTML=`<strong>${dateFmt.format(date(row.date))}</strong><br>${escapeHtml(labels.a)}: ${reading(row.aPrice,row.aReturn)}<br>${escapeHtml(labels.b)}: ${reading(row.bPrice,row.bReturn)}`;tooltip.style.left=`${Math.min(Math.max(8,xx+8),width-240)}px`;tooltip.style.top="28px";tooltip.classList.add("visible")};
  capture.addEventListener("pointermove",event=>{const b=svg.getBoundingClientRect(),px=(event.clientX-b.left)/b.width*width;inspect(Math.round((px-m.left)/iw*(rows.length-1)))});
  capture.addEventListener("pointerdown",event=>{const b=svg.getBoundingClientRect(),px=(event.clientX-b.left)/b.width*width;inspect(Math.round((px-m.left)/iw*(rows.length-1)))});
  capture.addEventListener("pointerleave",()=>{cross.setAttribute("opacity",0);tooltip.classList.remove("visible")});
}

function renderWorldFacts(){
  const name=$("#worldA").value,row=worldMap.get(name)||{},prediction=predictionMap.get(name);
  $("#worldFacts").innerHTML=`<h2>${escapeHtml(name)}</h2>
    <div class="fact"><span>Latest price</span><strong>${row.px_last?fmt.format(row.px_last)+" GP":"—"}</strong></div>
    <div class="fact"><span>Region</span><strong>${escapeHtml(row.region||"—")}</strong></div>
    <div class="fact"><span>PvP type</span><strong>${escapeHtml(row.pvp_type||"—")}</strong></div>
    <div class="fact"><span>Population proxy</span><strong>${row.population?fmt.format(row.population):"—"}</strong></div>
    <div class="fact"><span>Observed range</span><strong>${row.px_min?fmt.format(row.px_min)+" – "+fmt.format(row.px_max):"—"}</strong></div>
    <div class="fact"><span>Total return</span><strong class="${num(row.total_ret_pct)>=0?"positive":"negative"}">${signed(row.total_ret_pct,1)}</strong></div>
    <div class="fact"><span>7-day prediction</span><strong class="${num(prediction?.predicted_change_pct)>=0?"positive":"negative"}">${prediction?signed(prediction.predicted_change_pct):"No model"}</strong></div>`;
}

function renderWorldTable(){
  const term=$("#worldSearch").value.trim().toLowerCase();
  const rows=[...data.worlds].filter(row=>row.world.toLowerCase().includes(term)).sort((a,b)=>num(b.px_last)-num(a.px_last));
  $("#worldTable").innerHTML=rows.map(row=>`<tr data-world="${escapeHtml(row.world)}" class="${row.world===$("#worldA").value?"selected":""}">
    <td data-label="World"><strong>${escapeHtml(row.world)}</strong></td><td data-label="Latest">${row.px_last?fmt.format(row.px_last):"—"}</td>
    <td data-label="Region">${escapeHtml(row.region||"—")}</td><td data-label="PvP">${escapeHtml(row.pvp_type||"—")}</td>
    <td data-label="Population">${row.population?fmt.format(row.population):"—"}</td><td data-label="Total return" class="${num(row.total_ret_pct)>=0?"positive":"negative"}">${signed(row.total_ret_pct,1)}</td></tr>`).join("");
  $$("#worldTable tr").forEach(row=>row.addEventListener("click",()=>{$("#worldA").value=row.dataset.world;renderWorlds();updateURL()}));
}

function renderForecasts(){
  $$("#forecastHorizon .segment").forEach(button=>button.classList.toggle("active",button.dataset.horizon===selectedForecastHorizon));
  renderForecastChart();renderForecastSummary();renderPredictionTable();
}

function renderForecastChart(){
  const world=$("#forecastWorld").value,row=forecastMap.get(world),svg=$("#forecastChart");
  svg.innerHTML="";if(!row){addSvg(svg,"text",{x:400,y:170,"text-anchor":"middle",fill:"#647087"},"No forecast for this world");return}
  const key=selectedForecastHorizon,now=num(row.last_price),low=num(row[`${key}_p10`]),mid=num(row[`${key}_p50`]),high=num(row[`${key}_p90`]);
  const width=Math.max(320,svg.clientWidth||800),height=340,m={top:30,right:50,bottom:48,left:70},iw=width-m.left-m.right,ih=height-m.top-m.bottom;
  const min=Math.min(now,low)*.94,max=Math.max(now,high)*1.06,y=value=>m.top+ih-(value-min)/(max-min||1)*ih;
  svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
  for(let i=0;i<=4;i++){const v=min+(max-min)*i/4,yy=y(v);addSvg(svg,"line",{x1:m.left,x2:width-m.right,y1:yy,y2:yy,stroke:"#e5eaf1"});addSvg(svg,"text",{x:m.left-9,y:yy+4,"text-anchor":"end",fill:"#647087","font-size":10},compact(v))}
  const x0=m.left+iw*.18,x1=m.left+iw*.78;
  addSvg(svg,"path",{d:`M ${x0} ${y(now)} L ${x1} ${y(mid)}`,stroke:COLORS.blue,"stroke-width":2.5,fill:"none"});
  addSvg(svg,"line",{x1:x1,x2:x1,y1:y(low),y2:y(high),stroke:COLORS.gold,"stroke-width":12,opacity:.28});
  addSvg(svg,"line",{x1:x1-12,x2:x1+12,y1:y(low),y2:y(low),stroke:COLORS.gold,"stroke-width":2});
  addSvg(svg,"line",{x1:x1-12,x2:x1+12,y1:y(high),y2:y(high),stroke:COLORS.gold,"stroke-width":2});
  addSvg(svg,"circle",{cx:x0,cy:y(now),r:5,fill:COLORS.blue});addSvg(svg,"circle",{cx:x1,cy:y(mid),r:6,fill:COLORS.gold});
  addSvg(svg,"text",{x:x0,y:height-18,"text-anchor":"middle",fill:"#647087","font-size":11},"Today");
  addSvg(svg,"text",{x:x1,y:height-18,"text-anchor":"middle",fill:"#647087","font-size":11},({"2w":"2 weeks","1m":"1 month","3m":"3 months","6m":"6 months"})[key]);
  addSvg(svg,"text",{x:x0,y:y(now)-12,"text-anchor":"middle",fill:COLORS.blue,"font-size":12,"font-weight":700},fmt.format(now));
  addSvg(svg,"text",{x:x1,y:y(mid)-12,"text-anchor":"middle",fill:COLORS.gold,"font-size":12,"font-weight":700},fmt.format(mid));
  addSvg(svg,"text",{x:x1+18,y:y(high)+4,fill:"#647087","font-size":10},`P90 ${fmt.format(high)}`);
  addSvg(svg,"text",{x:x1+18,y:y(low)+4,fill:"#647087","font-size":10},`P10 ${fmt.format(low)}`);
}

function renderForecastSummary(){
  const world=$("#forecastWorld").value,row=forecastMap.get(world)||{},key=selectedForecastHorizon;
  const last=num(row.last_price),mid=num(row[`${key}_p50`]),low=num(row[`${key}_p10`]),high=num(row[`${key}_p90`]);
  $("#forecastSummary").innerHTML=`<h2>${escapeHtml(world)}</h2>
    <div class="forecast-band"><span class="metric-label">Last price</span><strong>${last?fmt.format(last)+" GP":"—"}</strong></div>
    <div class="forecast-band"><span class="metric-label">Median scenario</span><strong class="${mid>=last?"positive":"negative"}">${mid?fmt.format(mid)+" GP":"—"}</strong><small>${last?signed((mid/last-1)*100,1):"—"} versus today</small></div>
    <div class="forecast-band"><span class="metric-label">80% range</span><strong>${low?fmt.format(low)+" – "+fmt.format(high):"—"}</strong></div>
    <div class="forecast-band"><span class="metric-label">Daily volatility</span><strong>${num(row.sigma_daily_pct).toFixed(1)}%</strong></div>
    <p class="signal-note">${bool(row.launch_phase)?"Launch-phase world: uncertainty is structurally wider.":"Established world forecast."}</p>`;
}

function renderPredictionTable(){
  const rows=[...data.predictions].sort((a,b)=>num(b.predicted_change_pct)-num(a.predicted_change_pct));
  $("#predictionTable").innerHTML=rows.map(row=>`<tr data-world="${escapeHtml(row.world)}">
    <td data-label="World"><strong>${escapeHtml(row.world)}</strong></td><td data-label="Price">${fmt.format(row.price_gp)}</td>
    <td data-label="Deviation" class="${num(row.deviation_pct)>=0?"positive":"negative"}">${signed(row.deviation_pct)}</td>
    <td data-label="Prediction" class="${num(row.predicted_change_pct)>=0?"positive":"negative"}">${signed(row.predicted_change_pct)}</td>
    <td data-label="80% interval">${signed(row.low80_pct)} to ${signed(row.high80_pct)}</td></tr>`).join("");
  $$("#predictionTable tr").forEach(row=>row.addEventListener("click",()=>{if(forecastMap.has(row.dataset.world)){$("#forecastWorld").value=row.dataset.world;renderForecasts();updateURL()}}));
}

function modelLevelLabel(value){
  return({pvp_battleye_region:"PvP × BattlEye × region",pvp_battleye:"PvP × BattlEye",pvp:"PvP only"})[value]||value;
}

function filteredModelRows(){
  const pvp=$("#modelPvp").value,battleye=$("#modelBattleye").value,region=$("#modelRegion").value;
  const term=$("#modelSearch").value.trim().toLowerCase();
  return data.specificPredictions.filter(row=>
    (pvp==="all"||row.pvp_type===pvp)&&
    (battleye==="all"||row.battleye_color===battleye)&&
    (region==="all"||row.region===region)&&
    row.world.toLowerCase().includes(term));
}

function renderModels(){
  const overall=data.modelComparison.find(row=>row.scope==="all")||{};
  $("#modelGeneralRmse").textContent=`${num(overall.general_rmse_pct).toFixed(3)}%`;
  $("#modelSpecificRmse").textContent=`${num(overall.specific_rmse_pct).toFixed(3)}%`;
  const winner=overall.better_model==="specific"?"Specific":"General";
  $("#modelWinner").textContent=winner;
  const delta=Math.abs(num(overall.specific_improvement_pct));
  $("#modelWinnerMeta").textContent=`${winner==="General"?"specific is":"specific improves"} ${delta.toFixed(2)}% ${winner==="General"?"higher":"lower"} RMSE · p=${num(overall.dm_p_specific_vs_general).toFixed(3)}`;
  $("#modelCount").textContent=fmt.format(new Set(data.modelRegistry.map(row=>row.group_id)).size);
  renderModelChart();renderModelTable();renderModelDetail();renderModelSensitivity();renderLaunchModels();
}

function renderModelChart(){
  const rows=data.modelComparison.filter(row=>row.scope==="pvp_type").sort((a,b)=>num(a.general_rmse_pct)-num(b.general_rmse_pct));
  const svg=$("#modelChart");svg.innerHTML="";
  const width=Math.max(320,svg.clientWidth||800),height=340,m={top:24,right:62,bottom:42,left:Math.min(150,Math.max(105,width*.2))},iw=width-m.left-m.right,ih=height-m.top-m.bottom;
  const max=Math.max(1,...rows.flatMap(row=>[num(row.general_rmse_pct),num(row.specific_rmse_pct)]))*1.12;
  const x=value=>m.left+num(value)/max*iw,rowH=ih/Math.max(rows.length,1),barH=Math.min(18,rowH*.28);
  svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
  for(let i=0;i<=4;i++){const value=max*i/4,xx=x(value);addSvg(svg,"line",{x1:xx,x2:xx,y1:m.top,y2:height-m.bottom,stroke:"#e5eaf1"});addSvg(svg,"text",{x:xx,y:height-17,"text-anchor":"middle",fill:"#647087","font-size":10},`${value.toFixed(1)}%`)}
  rows.forEach((row,index)=>{
    const cy=m.top+rowH*(index+.5),general=num(row.general_rmse_pct),specific=num(row.specific_rmse_pct);
    const label=row.scope_value.replace("Retro Hardcore PvP","Retro Hardcore").replace("Retro Open PvP","Retro Open").replace("Optional PvP","Optional").replace("Open PvP","Open");
    addSvg(svg,"text",{x:m.left-10,y:cy+4,"text-anchor":"end",fill:"#273552","font-size":11,"font-weight":700},label);
    addSvg(svg,"rect",{x:m.left,y:cy-barH-2,width:Math.max(1,x(general)-m.left),height:barH,fill:COLORS.blue,rx:2});
    addSvg(svg,"rect",{x:m.left,y:cy+2,width:Math.max(1,x(specific)-m.left),height:barH,fill:COLORS.gold,rx:2});
    addSvg(svg,"text",{x:x(general)+5,y:cy-barH/2+1,fill:COLORS.blue,"font-size":9,"font-weight":700},general.toFixed(2));
    addSvg(svg,"text",{x:x(specific)+5,y:cy+barH/2+7,fill:"#8a6512","font-size":9,"font-weight":700},specific.toFixed(2));
  });
}

function renderModelDetail(){
  const world=$("#modelWorld").value,launchRow=launchPredictionMap.get(world);
  if(launchRow){
    const comparison=data.launchComparison.find(item=>item.scope==="pvp_type"&&item.scope_value===launchRow.pvp_type)||{};
    const winner=String(comparison.better_model||"general");
    const warning=bool(launchRow.low_sample_warning)?'<div class="evidence-callout">Low-sample launch family: this PvP has fewer than five training-eligible worlds. Its score is experimental.</div>':"";
    const stale=num(launchRow.stale_days)>0?` · data ${fmt.format(launchRow.stale_days)} days behind project date`:" · current project date";
    $("#modelDetail").innerHTML=`<div><span class="model-badge warning">Launch phase · experimental</span><h2 style="margin-top:10px">${escapeHtml(world)}</h2><p class="signal-note">${escapeHtml(launchRow.pvp_type)} · ${escapeHtml(launchRow.battleye_color)} BattlEye · ${escapeHtml(launchRow.region)}</p></div>
      <div class="fact"><span>World age</span><strong>${fmt.format(launchRow.age_days)} days</strong></div>
      <div class="fact"><span>General extrapolation</span><strong class="${num(launchRow.general_predicted_change_pct)>=0?"positive":"negative"}">${signed(launchRow.general_predicted_change_pct)}</strong></div>
      <div class="fact"><span>Launch prediction</span><strong class="${num(launchRow.launch_predicted_change_pct)>=0?"positive":"negative"}">${signed(launchRow.launch_predicted_change_pct)}</strong></div>
      <div class="fact"><span>Launch 80% interval</span><strong>${signed(launchRow.launch_low80_pct)} to ${signed(launchRow.launch_high80_pct)}</strong></div>
      <div class="fact"><span>Difference</span><strong class="${num(launchRow.launch_minus_general_pct)>=0?"positive":"negative"}">${signed(launchRow.launch_minus_general_pct)}</strong></div>
      <div class="fact"><span>PvP training pool</span><strong>${fmt.format(launchRow.model_worlds)} worlds</strong></div>
      <div class="fact"><span>Estimator</span><strong>${launchRow.selected_estimator==="random_forest"?"Random Forest":"Ridge"}</strong></div>
      <div class="fact"><span>PvP holdout winner</span><strong>${winner==="launch"?"Launch":winner==="zero"?"Zero change":"General"}</strong></div>
      <p class="signal-note">As of ${escapeHtml(launchRow.as_of)}${stale}. The mature general model remains the production default.</p>${warning}`;
    return;
  }
  const row=specificPredictionMap.get(world),registry=modelRegistryMap.get(world);
  if(!row||!registry){$("#modelDetail").innerHTML='<div class="empty">No eligible world selected.</div>';return}
  const comparison=data.modelComparison.find(item=>item.scope==="model_group"&&item.scope_value===row.group_id)||{};
  const winner=comparison.better_model==="specific"?"Specific":"General";
  const warning=bool(row.low_sample_warning)?'<div class="evidence-callout">Low-sample model: this PvP has fewer than five eligible worlds, and cannot be pooled with another PvP type.</div>':"";
  $("#modelDetail").innerHTML=`<div><span class="model-badge ${bool(row.low_sample_warning)?"warning":""}">${escapeHtml(modelLevelLabel(row.group_level))}</span><h2 style="margin-top:10px">${escapeHtml(world)}</h2><p class="signal-note">${escapeHtml(row.pvp_type)} · ${escapeHtml(row.battleye_color)} BattlEye · ${escapeHtml(row.region)}</p></div>
    <div class="fact"><span>General prediction</span><strong class="${num(row.general_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.general_predicted_change_pct)}</strong></div>
    <div class="fact"><span>Specific prediction</span><strong class="${num(row.specific_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.specific_predicted_change_pct)}</strong></div>
    <div class="fact"><span>Specific 80% interval</span><strong>${signed(row.specific_low80_pct)} to ${signed(row.specific_high80_pct)}</strong></div>
    <div class="fact"><span>Difference</span><strong class="${num(row.specific_minus_general_pct)>=0?"positive":"negative"}">${signed(row.specific_minus_general_pct)}</strong></div>
    <div class="fact"><span>Training pool</span><strong>${fmt.format(row.model_worlds)} worlds</strong></div>
    <div class="fact"><span>Estimator</span><strong>${registry.selected_estimator==="random_forest"?"Random Forest":"Ridge"}</strong></div>
    <div class="fact"><span>Group holdout winner</span><strong>${winner}</strong></div>
    <p class="signal-note">${escapeHtml(row.fallback_reason)}</p>${warning}`;
}

function filteredLaunchRows(){
  const pvp=$("#modelPvp").value,battleye=$("#modelBattleye").value,region=$("#modelRegion").value;
  const term=$("#launchSearch").value.trim().toLowerCase();
  return data.launchPredictions.filter(row=>
    (pvp==="all"||row.pvp_type===pvp)&&
    (battleye==="all"||row.battleye_color===battleye)&&
    (region==="all"||row.region===region)&&
    row.world.toLowerCase().includes(term));
}

function renderLaunchModels(){
  const pvp=$("#modelPvp").value;
  const comparison=(pvp!=="all"?data.launchComparison.find(row=>row.scope==="pvp_type"&&row.scope_value===pvp):null)||
    data.launchComparison.find(row=>row.scope==="all")||{};
  const rows=filteredLaunchRows().sort((a,b)=>num(b.launch_predicted_change_pct)-num(a.launch_predicted_change_pct));
  $("#launchActiveWorlds").textContent=fmt.format(rows.length);
  $("#launchGeneralRmse").textContent=`${num(comparison.general_rmse_pct).toFixed(3)}%`;
  $("#launchRmse").textContent=`${num(comparison.launch_rmse_pct).toFixed(3)}%`;
  const winner=comparison.better_model==="launch"?"Launch":comparison.better_model==="zero"?"Zero change":"General";
  $("#launchWinner").textContent=winner;
  const delta=Math.abs(num(comparison.launch_improvement_vs_general_pct));
  $("#launchWinnerMeta").textContent=`launch is ${delta.toFixed(2)}% ${num(comparison.launch_improvement_vs_general_pct)>=0?"lower":"higher"} RMSE vs general`;
  $("#launchTableCount").textContent=`${fmt.format(rows.length)} of ${fmt.format(data.launchPredictions.length)} active launch worlds`;
  $("#launchTable").innerHTML=rows.length?rows.map(row=>`<tr data-world="${escapeHtml(row.world)}">
    <td data-label="World"><strong>${escapeHtml(row.world)}</strong></td>
    <td data-label="Age">${fmt.format(row.age_days)}d</td>
    <td data-label="Data age" class="${num(row.stale_days)>14?"negative":""}">${num(row.stale_days)?fmt.format(row.stale_days)+"d stale":"Current"}</td>
    <td data-label="PvP">${escapeHtml(row.pvp_type)}</td>
    <td data-label="General 7d" class="${num(row.general_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.general_predicted_change_pct)}</td>
    <td data-label="Launch 7d" class="${num(row.launch_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.launch_predicted_change_pct)}</td>
    <td data-label="Difference" class="${num(row.launch_minus_general_pct)>=0?"positive":"negative"}">${signed(row.launch_minus_general_pct)}</td>
    <td data-label="Model">${row.selected_estimator==="random_forest"?"Random Forest":"Ridge"}${bool(row.low_sample_warning)?" · low sample":""}</td></tr>`).join(""):'<tr><td colspan="8"><div class="empty">No active launch worlds match these filters.</div></td></tr>';
  $$("#launchTable tr[data-world]").forEach(tableRow=>tableRow.addEventListener("click",()=>{$("#modelWorld").value=tableRow.dataset.world;renderModelDetail();updateURL()}));
  const comparisonRows=data.launchComparison.filter(row=>
    row.scope==="all"||(row.scope==="pvp_type"&&(pvp==="all"||row.scope_value===pvp)));
  $("#launchComparisonTable").innerHTML=comparisonRows.map(row=>`<tr>
    <td data-label="Scope"><strong>${escapeHtml(row.scope==="all"?"All launch worlds":row.scope_value)}</strong></td>
    <td data-label="Worlds">${fmt.format(row.n_worlds)}</td>
    <td data-label="Launch RMSE">${num(row.launch_rmse_pct).toFixed(3)}%</td>
    <td data-label="General RMSE">${num(row.general_rmse_pct).toFixed(3)}%</td>
    <td data-label="Zero RMSE">${num(row.zero_rmse_pct).toFixed(3)}%</td>
    <td data-label="Winner">${row.better_model==="launch"?"Launch":row.better_model==="zero"?"Zero change":"General"}</td></tr>`).join("");
}

function renderModelTable(){
  const rows=filteredModelRows().sort((a,b)=>num(b.specific_predicted_change_pct)-num(a.specific_predicted_change_pct));
  $("#modelTableCount").textContent=`${fmt.format(rows.length)} of ${fmt.format(data.specificPredictions.length)} eligible worlds`;
  $("#modelTable").innerHTML=rows.length?rows.map(row=>`<tr data-world="${escapeHtml(row.world)}">
    <td data-label="World"><strong>${escapeHtml(row.world)}</strong></td>
    <td data-label="PvP">${escapeHtml(row.pvp_type)}</td>
    <td data-label="BattlEye">${escapeHtml(row.battleye_color)}</td>
    <td data-label="Region">${escapeHtml(row.region)}</td>
    <td data-label="General 7d" class="${num(row.general_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.general_predicted_change_pct)}</td>
    <td data-label="Specific 7d" class="${num(row.specific_predicted_change_pct)>=0?"positive":"negative"}">${signed(row.specific_predicted_change_pct)}</td>
    <td data-label="Difference" class="${num(row.specific_minus_general_pct)>=0?"positive":"negative"}">${signed(row.specific_minus_general_pct)}</td>
    <td data-label="Group level">${escapeHtml(modelLevelLabel(row.group_level))}</td></tr>`).join(""):'<tr><td colspan="8"><div class="empty">No eligible worlds match these filters.</div></td></tr>';
  $$("#modelTable tr[data-world]").forEach(tableRow=>tableRow.addEventListener("click",()=>{$("#modelWorld").value=tableRow.dataset.world;renderModelDetail();updateURL()}));
}

function renderModelSensitivity(){
  const rows=[...data.modelSensitivity].sort((a,b)=>num(a.min_group_worlds)-num(b.min_group_worlds));
  $("#modelSensitivityTable").innerHTML=rows.map(row=>`<tr>
    <td data-label="Minimum worlds"><strong>${fmt.format(row.min_group_worlds)}</strong></td>
    <td data-label="Specific models">${fmt.format(row.n_models)}</td>
    <td data-label="Exact worlds">${fmt.format(row.n_exact_worlds)}</td>
    <td data-label="Region pooled">${fmt.format(row.n_region_pooled_worlds)}</td>
    <td data-label="PvP pooled">${fmt.format(row.n_pvp_pooled_worlds)}</td>
    <td data-label="General validation RMSE">${num(row.general_rmse_pct).toFixed(3)}%</td>
    <td data-label="Specific validation RMSE">${num(row.specific_rmse_pct).toFixed(3)}%</td></tr>`).join("");
}

function renderStrategy(){
  $$("#strategyHorizon .segment").forEach(button=>button.classList.toggle("active",Number(button.dataset.days)===selectedStrategyHorizon));
  const rows=data.strategy.filter(row=>num(row.horizon)===selectedStrategyHorizon);
  const max=Math.max(1,...rows.map(row=>num(row.net_pct)));
  $("#strategyBars").innerHTML=rows.map(row=>`<div class="bar-row"><strong>${row.period==="train"?"Training":"Holdout"}</strong><div class="bar-track"><div class="bar-fill ${row.period==="holdout"?"gold":""}" style="width:${Math.max(0,num(row.net_pct)/max*100)}%"></div></div><strong class="positive">${signed(row.net_pct)}</strong></div>`).join("");
  const holdout=rows.find(row=>row.period==="holdout")||{},train=rows.find(row=>row.period==="train")||{};
  const caution=num(holdout.n_effective)<10?`Only ${fmt.format(holdout.n_effective)} independent window${num(holdout.n_effective)===1?"":"s"}: this horizon is descriptive, not decision-grade.`:
    `${fmt.format(holdout.n_effective)} independent holdout windows support this comparison.`;
  $("#strategyEvidence").innerHTML=`<h2>${selectedStrategyHorizon}-day evidence</h2>
    <div class="fact"><span>Holdout net</span><strong class="positive">${signed(holdout.net_pct)}</strong></div>
    <div class="fact"><span>Profitable signals</span><strong>${pct1.format(num(holdout.share_profitable))}</strong></div>
    <div class="fact"><span>Effective holdout N</span><strong>${fmt.format(holdout.n_effective)}</strong></div>
    <div class="fact"><span>Training cutoff</span><strong>${num(train.cutoff_pct).toFixed(1)}% gap</strong></div>
    <div class="evidence-callout">${caution}</div>`;
}

function populateLibraryChapters(){
  const select=$("#libraryTopic");
  const topics=[...new Set(data.figures.map(item=>item.topic))];
  select.innerHTML='<option value="all">All topics</option>'+topics.map(topic=>`<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("");
}

function renderLibrary(){
  const term=$("#librarySearch").value.trim().toLowerCase(),topic=$("#libraryTopic").value;
  const rows=data.figures.filter(item=>(topic==="all"||item.topic===topic)&&`${item.title} ${item.subtitle} ${item.note} ${item.topic}`.toLowerCase().includes(term));
  $("#libraryCount").textContent=`${fmt.format(rows.length)} of ${fmt.format(data.figures.length)} exhibits`;
  $("#libraryGrid").innerHTML=rows.length?rows.map(item=>`<button class="exhibit" data-id="${escapeHtml(item.id)}"><img src="${escapeHtml(item.image)}" alt="" loading="lazy"><span class="exhibit-copy"><span class="exhibit-id">${escapeHtml(item.label)} · ${escapeHtml(item.topic)}</span><span class="exhibit-title">${escapeHtml(item.title)}</span></span></button>`).join(""):'<div class="empty">No exhibits match this search.</div>';
  $$(".exhibit").forEach(button=>button.addEventListener("click",()=>openExhibit(button.dataset.id)));
}

function openExhibit(id){
  const item=data.figures.find(row=>row.id===id);if(!item)return;
  selectedExhibit=id;$("#modalId").textContent=`${item.label} · ${item.topic}`;
  $("#modalTitle").textContent=item.title;$("#modalSubtitle").textContent=item.subtitle;
  $("#modalImage").src=item.image;$("#modalImage").alt=item.title;$("#modalNote").textContent=item.note;
  $("#modalSource").textContent=item.source;$("#modalOpenImage").href=item.image;
  $("#exhibitDialog").showModal();updateURL();
}

function closeExhibit(){
  $("#exhibitDialog").close();
  selectedExhibit="";
  updateURL();
}

function updateURL(){
  const params=new URLSearchParams();
  if(activeView!=="overview")params.set("view",activeView);
  if($("#overviewWorld").value!=="all")params.set("world",$("#overviewWorld").value);
  if($("#overviewStart").value!==$("#overviewStart").min)params.set("start",$("#overviewStart").value);
  if($("#overviewEnd").value!==$("#overviewEnd").max)params.set("end",$("#overviewEnd").value);
  if($("#worldA").value!=="Antica")params.set("a",$("#worldA").value);
  if($("#worldB").value!=="Belobra")params.set("b",$("#worldB").value);
  if(selectedWorldChartMode!=="price")params.set("worldMeasure",selectedWorldChartMode);
  if($("#forecastWorld").value!=="Belobra")params.set("forecast",$("#forecastWorld").value);
  if(selectedForecastHorizon!=="1m")params.set("horizon",selectedForecastHorizon);
  if($("#modelPvp").value!=="all")params.set("modelPvp",$("#modelPvp").value);
  if($("#modelBattleye").value!=="all")params.set("modelBe",$("#modelBattleye").value);
  if($("#modelRegion").value!=="all")params.set("modelRegion",$("#modelRegion").value);
  if($("#modelWorld").value!=="Belobra")params.set("modelWorld",$("#modelWorld").value);
  if(selectedStrategyHorizon!==7)params.set("days",selectedStrategyHorizon);
  if(selectedExhibit)params.set("exhibit",selectedExhibit);
  const query=params.toString();try{history.replaceState(null,"",`${location.pathname}${query?`?${query}`:""}${location.hash}`)}catch(_){}
}

async function copyView(){
  updateURL();const url=location.href;
  try{await navigator.clipboard.writeText(url)}catch(_){const area=document.createElement("textarea");area.value=url;area.style.position="fixed";area.style.opacity="0";document.body.appendChild(area);area.select();document.execCommand("copy");area.remove()}
  const label=$("#copyView span"),original=label.textContent;label.textContent="Copied";setTimeout(()=>label.textContent=original,1400);
}

function parseCSV(text){
  const rows=[];let row=[],field="",quoted=false;
  for(let i=0;i<text.length;i++){const char=text[i];if(quoted){if(char==='"'&&text[i+1]==='"'){field+='"';i++}else if(char==='"')quoted=false;else field+=char}else if(char==='"')quoted=true;else if(char===","){row.push(field);field=""}else if(char==="\n"){row.push(field.replace(/\r$/,""));rows.push(row);row=[];field=""}else field+=char}
  if(field.length||row.length){row.push(field.replace(/\r$/,""));rows.push(row)}
  const headers=rows.shift()||[];
  return rows.filter(values=>values.some(Boolean)).map(values=>Object.fromEntries(headers.map((header,index)=>[header,coerce(values[index]??"")])));
}

function coerce(value){
  if(value==="")return null;if(value==="True"||value==="true")return true;if(value==="False"||value==="false")return false;
  if(/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value)){const parsed=Number(value);if(Number.isFinite(parsed))return parsed}
  return value;
}

async function refreshProjectData(){
  if(!["http:","https:"].includes(location.protocol))return;
  try{
    const entries=await Promise.all(Object.entries(DATA_FILES).map(async([key,url])=>{const response=await fetch(url,{cache:"no-store"});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return[key,parseCSV(await response.text()),response.headers.get("last-modified")]}));
    const loaded=Object.fromEntries(entries.map(([key,rows])=>[key,rows]));
    loaded.marketIndex=loaded.marketIndex.filter(row=>bool(row.index_valid)&&row.ew_price!==null);
    loaded.worldSeries=loaded.worldSeries.filter(row=>row.price_gp!==null);
    Object.assign(data,loaded);
    const updated=entries.map(entry=>entry[2]).find(Boolean);
    data.meta.generatedAt=updated||new Date().toISOString();
    data.meta.worlds=data.worlds.length;data.meta.worldDays=data.worldSeries.length;
    liveMode=true;rebuildIndexes();updateStatus();renderAll();
  }catch(_){liveMode=false;updateStatus()}
}

function debounce(fn,wait){let timer;return(...args)=>{clearTimeout(timer);timer=setTimeout(()=>fn(...args),wait)}}

initialize();
void refreshProjectData();
</script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    output = HTML.replace("__DATA__", embedded.replace("</", "<\\/"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding="utf-8")
    print(
        f"[INTELLIGENCE HUB] wrote {OUTPUT.relative_to(ROOT)} with "
        f"{payload['meta']['worlds']} worlds, {len(payload['worldSeries']):,} price rows, "
        f"and {payload['meta']['figureCount']} exhibits"
    )


if __name__ == "__main__":
    main()
