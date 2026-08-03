"""Shared Gold Emission workspace: payload, styles, markup and behaviour.

Both publication surfaces mount the same component from here:

- ``scripts/38_gold_emission_dashboard.py`` writes the standalone page;
- ``scripts/39_intelligence_hub.py`` mounts it natively inside the hub view.

Keeping one implementation is what stops the two artifacts from drifting. The
markup carries no page title, so each host supplies its own heading, and every
id and class is prefixed so the component can live inside another application
without colliding with it.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "gold_emission_daily.csv"
PRICE_SOURCE = ROOT / "data" / "processed" / "panel_daily.csv"
CREATURE_VALUE_SOURCE = ROOT / "data" / "processed" / "creature_gold_value.csv"

FIELDS = (
    "world",
    "date",
    "top_emission_creature_name",
    "top_emission_creature_gp",
    "total_kills",
    "nonboss_kills",
    "modeled_kills_nonboss",
    "direct_coin_gp",
    "npc_potential_gp_max",
    "potential_total_gp_max",
    "low_quality_flag",
    "partial_date_flag",
    "ev_any",
)

NUMERIC_FIELDS = {
    "top_emission_creature_gp",
    "total_kills",
    "nonboss_kills",
    "modeled_kills_nonboss",
    "direct_coin_gp",
    "npc_potential_gp_max",
    "potential_total_gp_max",
}

BOOLEAN_FIELDS = {"low_quality_flag", "partial_date_flag", "ev_any"}

CREATURE_FIELDS = (
    "canonical_name",
    "raw_names",
    "loot_model_status",
    "loot_confidence",
    "loot_samples",
    "is_boss",
    "included_in_main_series",
    "expected_direct_coin_gp_per_kill",
    "expected_npc_sale_gp_per_kill",
    "exclusion_reason",
)


def _compact_row(row: dict[str, str]) -> list[object]:
    values: list[object] = []
    for field in FIELDS:
        value = row[field]
        if field in NUMERIC_FIELDS:
            values.append(round(float(value or 0), 3))
        elif field in BOOLEAN_FIELDS:
            values.append(value.strip().lower() in {"1", "true", "yes"})
        else:
            values.append(value)
    return values


def build_payload(*, include_prices: bool = True) -> dict[str, object]:
    """Read the emission datasets the component needs.

    ``include_prices`` is off for the hub, which already embeds the same daily
    prices for its other views and hands them to the component at mount time.
    """
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(FIELDS) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing dashboard fields: {', '.join(missing)}")
        rows = [_compact_row(row) for row in reader]

    price_rows: list[list[object]] = []
    if include_prices:
        with PRICE_SOURCE.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"world", "date", "price_gp"}
            missing = sorted(required - set(reader.fieldnames or ()))
            if missing:
                raise ValueError(f"Missing TC price fields: {', '.join(missing)}")
            price_rows = [
                [row["world"], row["date"], round(float(row["price_gp"]), 3)]
                for row in reader
                if row.get("world") and row.get("date") and row.get("price_gp")
            ]

    with CREATURE_VALUE_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(CREATURE_FIELDS) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing creature-value fields: {', '.join(missing)}")
        creature_values = [[row[field] for field in CREATURE_FIELDS] for row in reader]

    worlds = sorted({str(row[0]) for row in rows})
    dates = sorted({str(row[1]) for row in rows})
    payload: dict[str, object] = {
        "schema": list(FIELDS),
        "rows": rows,
        "creatureValueSchema": list(CREATURE_FIELDS),
        "creatureValues": creature_values,
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": str(SOURCE.relative_to(ROOT)),
            "worlds": len(worlds),
            "worldDays": len(rows),
            "minDate": dates[0],
            "maxDate": dates[-1],
        },
    }
    if include_prices:
        payload["priceSchema"] = ["world", "date", "price_gp"]
        payload["priceRows"] = price_rows
    return payload


def build_ranking_payload() -> dict[str, object]:
    """Creature loot values only, for the standalone creature ranking page."""
    with CREATURE_VALUE_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(CREATURE_FIELDS) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing creature-value fields: {', '.join(missing)}")
        creature_values = [[row[field] for field in CREATURE_FIELDS] for row in reader]
    return {
        "creatureValueSchema": list(CREATURE_FIELDS),
        "creatureValues": creature_values,
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": str(CREATURE_VALUE_SOURCE.relative_to(ROOT)),
            "creatures": len(creature_values),
        },
    }


def embed(payload: dict[str, object]) -> str:
    """Serialise a payload for safe inclusion inside a script element."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


STYLE = r"""
    .em-root {
      --em-ink:#12203a; --em-muted:#667085; --em-line:#d8dee8; --em-line-soft:#edf0f4;
      --em-direct:#4E79A7; --em-potential:#F28E2B; --em-tc:#59A14F;
      --em-good:#24875d; --em-warning:#b77905; --em-danger:#c43d3d; --em-focus:#1d4ed8;
      --em-radius:8px; --em-shadow:0 8px 28px rgb(18 32 58 / 8%);
      color:var(--em-ink); font-size:14px; line-height:1.5;
    }
    .em-root *{box-sizing:border-box}
    .em-root button,.em-root input,.em-root select{font:inherit;color:inherit}
    .em-root button,.em-root select,.em-root input[type="date"]{min-height:44px}
    .em-root button:focus-visible,.em-root select:focus-visible,.em-root input:focus-visible{
      outline:3px solid rgb(29 78 216 / 22%);outline-offset:2px}
    .em-status{color:var(--em-muted);font-size:12px;line-height:1.45;padding:0 0 14px;
      border-bottom:1px solid var(--em-line)}
    .em-filters{display:grid;grid-template-columns:minmax(170px,1fr) minmax(250px,1.35fr) minmax(260px,1.35fr) auto;
      gap:16px;align-items:end;padding:18px 0}
    .em-field{display:grid;gap:7px;min-width:0}
    .em-field>label,.em-series-summary{font-size:13px;font-weight:700;letter-spacing:.01em}
    .em-root select,.em-root input[type="date"],.em-root input[type="search"]{
      width:100%;background:#fff;border:1px solid #cbd3df;border-radius:7px;padding:0 12px;font-size:13px}
    .em-date-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .em-series-control{min-height:44px;border:1px solid #cbd3df;border-radius:7px;padding:6px 10px;
      display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px}
    .em-check{display:inline-flex;align-items:center;gap:7px;font-size:13px;white-space:nowrap}
    .em-check input{width:17px;height:17px;min-height:0;accent-color:var(--em-focus)}
    .em-actions{display:grid;gap:8px}
    .em-button{border:1px solid var(--em-ink);background:#fff;color:var(--em-ink);border-radius:7px;
      padding:0 16px;font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap}
    .em-button:hover{background:#f7f9fc}
    .em-button.em-secondary{border-color:#7aa2df;color:#174ea6}
    .em-button.em-text{border-color:transparent;color:var(--em-focus);min-height:36px;padding:0 8px}
    .em-metrics{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--em-line);
      border-radius:var(--em-radius);overflow:hidden;margin-bottom:16px}
    .em-metric{padding:17px 20px;min-width:0;text-align:center}
    .em-metric+.em-metric{border-left:1px solid var(--em-line)}
    .em-metric-label{font-size:13px;font-weight:700}
    .em-metric-value{display:block;margin-top:8px;color:var(--em-potential);font-weight:750;
      font-size:clamp(22px,2.3vw,34px);line-height:1;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
    .em-metric-meta{display:block;margin-top:7px;color:var(--em-muted);font-size:12px}
    .em-main-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,.9fr);gap:16px}
    .em-panel{border:1px solid var(--em-line);border-radius:var(--em-radius);background:#fff;min-width:0}
    .em-panel-inner{padding:16px}
    .em-root h3.em-panel-title{margin:0;font-size:17px;letter-spacing:-.01em;font-weight:750}
    .em-panel-heading{display:flex;justify-content:space-between;gap:12px;align-items:baseline;margin-bottom:12px}
    .em-note{color:var(--em-muted);font-size:12px;margin:0}
    .em-legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin:8px 0 0;color:#344054;font-size:12px}
    .em-legend-item{display:inline-flex;align-items:center;gap:7px}
    .em-legend-line{width:24px;border-top:3px solid}
    .em-legend-line.potential{border-top-style:dashed}
    .em-chart-wrap{position:relative;width:100%;min-height:360px}
    .em-root #emChart{display:block;width:100%;height:360px;overflow:visible}
    .em-tooltip{position:absolute;z-index:4;min-width:220px;max-width:280px;pointer-events:none;
      background:rgb(255 255 255 / 97%);border:1px solid #bac4d2;border-radius:7px;
      box-shadow:var(--em-shadow);padding:11px 12px;font-size:12px;line-height:1.45;
      opacity:0;transform:translateY(4px);transition:opacity .12s ease,transform .12s ease}
    .em-tooltip.visible{opacity:1;transform:translateY(0)}
    .em-tooltip-date{font-weight:800;margin-bottom:6px}
    .em-tooltip-row{display:grid;grid-template-columns:10px 1fr auto;gap:7px;align-items:center}
    .em-tooltip-row+.em-tooltip-row{margin-top:4px}
    .em-tooltip-dot{width:8px;height:8px;border-radius:50%}
    .em-tooltip-value{font-variant-numeric:tabular-nums;font-weight:700}
    .em-hidden{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;
      margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;
      white-space:nowrap!important;border:0!important}
    .em-composition{display:grid;align-content:start;min-height:100%}
    .em-composition-total{margin-top:24px;font-size:12px;color:var(--em-muted)}
    .em-composition-total strong{display:block;margin-top:4px;color:var(--em-ink);font-size:25px;
      font-variant-numeric:tabular-nums}
    .em-stack{height:34px;display:flex;overflow:hidden;border-radius:5px;margin:20px 0 12px;background:var(--em-line-soft)}
    .em-stack>div{min-width:0;transition:width .2s ease}
    .em-stack-direct{background:var(--em-direct)}
    .em-stack-npc{background:var(--em-potential)}
    .em-composition-list{display:grid;gap:14px;margin-top:18px}
    .em-composition-row{display:grid;grid-template-columns:12px 1fr auto;gap:9px;align-items:start;font-size:13px}
    .em-swatch{width:11px;height:11px;margin-top:2px;border-radius:2px}
    .em-composition-row strong{font-variant-numeric:tabular-nums;text-align:right}
    .em-composition-row small{display:block;color:var(--em-muted);margin-top:3px}
    .em-world-breakdown{margin-top:16px;overflow:hidden}
    .em-world-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--em-line)}
    .em-world-cell{background:#fff;padding:18px 20px;min-height:94px}
    .em-world-cell span{display:block;color:var(--em-muted);font-size:12px;line-height:1.35}
    .em-world-cell strong{display:block;margin-top:7px;color:var(--em-ink);font-size:18px;line-height:1.25;
      font-variant-numeric:tabular-nums}
    .em-quality{margin-top:16px}
    .em-quality-header{display:flex;justify-content:space-between;gap:12px;padding:14px 16px 8px}
    .em-quality-strip{display:flex;gap:3px;overflow-x:auto;padding:8px 16px 15px}
    .em-quality-day{flex:1 0 5px;height:22px;min-width:5px;border:0;border-radius:2px;padding:0;cursor:pointer}
    .em-quality-day.complete{background:var(--em-good)}
    .em-quality-day.partial{background:var(--em-warning)}
    .em-quality-day.low{background:var(--em-danger)}
    .em-quality-key{display:flex;flex-wrap:wrap;gap:8px 15px;color:var(--em-muted);font-size:12px}
    .em-quality-key span{display:inline-flex;align-items:center;gap:6px}
    .em-key-dot{width:8px;height:8px;border-radius:2px}
    .em-table-panel{margin-top:16px}
    .em-table-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:15px 16px 10px}
    .em-table-wrap{overflow:auto;border-top:1px solid var(--em-line-soft)}
    .em-root table{width:100%;border-collapse:collapse;min-width:960px;font-size:12px}
    .em-root th,.em-root td{padding:10px 12px;border-bottom:1px solid var(--em-line-soft);
      text-align:right;white-space:nowrap}
    .em-root th{position:sticky;top:0;z-index:1;background:#f8fafc;color:#344054;font-weight:800}
    .em-root td{font-variant-numeric:tabular-nums}
    .em-root tbody tr{cursor:default}
    .em-root tbody tr:hover{background:#f8faff}
    /* A text column is declared on the header and the cell together, so a left-aligned
       value can never sit under a right-aligned label. */
    .em-root th.em-text-cell,.em-root td.em-text-cell{text-align:left}
    .em-root td.em-text-cell{white-space:normal}
    .em-quality-label{display:inline-flex;align-items:center;gap:7px}
    .em-quality-label::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
    .em-quality-label.complete{color:var(--em-good)}
    .em-quality-label.partial{color:var(--em-warning)}
    .em-quality-label.low{color:var(--em-danger)}
    .em-table-footer{display:flex;justify-content:center;padding:10px}
    .em-date-drill{border:0;background:transparent;color:var(--em-focus);font-weight:800;padding:5px 2px;
      min-height:32px;cursor:pointer;text-decoration:underline;text-decoration-thickness:1px;
      text-underline-offset:3px}
    .em-day-detail{margin-top:16px;overflow:hidden}
    .em-day-detail[hidden]{display:none}
    .em-root.em-detail-mode .em-filters,
    .em-root.em-detail-mode .em-metrics,
    .em-root.em-detail-mode .em-world-breakdown,
    .em-root.em-detail-mode .em-main-grid,
    .em-root.em-detail-mode .em-quality,
    .em-root.em-detail-mode .em-table-panel,
    .em-root.em-detail-mode .em-ranking,
    .em-root.em-detail-mode .em-footnote{display:none!important}
    .em-root.em-detail-mode .em-day-detail{margin-top:20px}
    .em-day-detail .em-table-head{align-items:start}
    .em-day-detail table{min-width:1120px}
    .em-detail-message{padding:24px 16px;color:var(--em-muted);line-height:1.5}
    .em-detail-summary{color:var(--em-muted);font-size:12px;margin:5px 0 0}
    .em-progress{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;
      border-top:1px solid var(--em-line-soft);color:var(--em-muted);font-size:12px}
    .em-progress-track{flex:1 1 220px;height:8px;border-radius:99px;background:var(--em-line-soft);overflow:hidden}
    .em-progress-track i{display:block;height:100%;background:var(--em-direct);transition:width .2s ease}
    .em-partial{margin:0;padding:12px 16px;background:#fff8e7;color:#765910;font-size:12px;line-height:1.5;
      border-top:1px solid var(--em-line-soft)}
    .em-ranking{margin-top:16px}
    .em-ranking-tools{display:grid;grid-template-columns:auto minmax(180px,1fr) minmax(170px,220px);
      gap:10px;align-items:center;padding:0 16px 12px}
    .em-segmented{display:inline-flex;border:1px solid #b9c3d2;border-radius:7px;overflow:hidden}
    .em-segment{min-height:40px;border:0;border-right:1px solid #b9c3d2;background:#fff;padding:0 14px;
      cursor:pointer;font-size:12px;font-weight:700}
    .em-segment:last-child{border-right:0}
    .em-segment.active{background:var(--em-focus);color:#fff}
    .em-tag{display:inline-flex;align-items:center;min-height:20px;border-radius:999px;background:#eef2f9;
      color:#3b4760;padding:0 8px;font-size:10px;font-weight:800;margin-left:6px}
    .em-sort-button{width:100%;min-height:32px;border:0;background:transparent;color:inherit;padding:0;
      font:inherit;font-weight:inherit;text-align:inherit;cursor:pointer}
    .em-sort-button::after{content:" \2195";color:#8792a6;font-size:10px}
    .em-root th[aria-sort="ascending"] .em-sort-button::after{content:" \2191";color:var(--em-focus)}
    .em-root th[aria-sort="descending"] .em-sort-button::after{content:" \2193";color:var(--em-focus)}
    .em-error{margin:0 0 16px;border-left:4px solid var(--em-danger);background:#fff6f6;color:#8f2525;
      padding:12px 14px;display:none}
    .em-error.visible{display:block}
    .em-footnote{margin:18px 2px 0;color:var(--em-muted);font-size:12px;line-height:1.5}
    @media (max-width:1080px){
      .em-filters{grid-template-columns:repeat(2,minmax(0,1fr))}
      .em-actions{grid-column:1/-1;display:flex}
      .em-main-grid{grid-template-columns:1fr}
      .em-composition{min-height:auto}
      .em-ranking-tools{grid-template-columns:1fr 1fr}
    }
    @media (max-width:680px){
      .em-filters{grid-template-columns:1fr 1fr;gap:14px 10px}
      .em-field.em-series-field{grid-column:1/-1}
      .em-series-control{display:grid;grid-template-columns:1fr 1fr}
      .em-actions{display:grid;grid-column:1/-1}
      .em-metrics{grid-template-columns:1fr 1fr;border:0;gap:10px;overflow:visible}
      .em-metric{border:1px solid var(--em-line);border-radius:var(--em-radius);text-align:left;padding:14px}
      .em-metric+.em-metric{border-left:1px solid var(--em-line)}
      .em-metric-value{font-size:clamp(21px,7vw,30px)}
      .em-chart-wrap,.em-root #emChart{min-height:330px;height:330px}
      .em-legend{gap:7px 13px}
      .em-quality-header{display:block}
      .em-world-grid{grid-template-columns:1fr 1fr}
      .em-quality-key{margin-top:8px}
      .em-quality-day{flex-basis:9px;min-width:9px}
      .em-table-head{align-items:start}
      .em-ranking-tools{grid-template-columns:1fr}
      .em-segmented{width:100%}
      .em-segment{flex:1}
    }
    @media (max-width:430px){
      /* Stacked date inputs make the second column taller than the first, so the row
         becomes one column instead of leaving the World label floating beside it. */
      .em-filters{grid-template-columns:1fr}
      .em-date-pair{grid-template-columns:1fr}
      .em-series-control{grid-template-columns:1fr}
      .em-metric{min-height:122px}
      .em-tooltip{min-width:190px;max-width:230px}
    }
    @media print{
      .em-filters,.em-actions,.em-table-footer,.em-hidden,.em-ranking-tools{display:none!important}
      .em-panel,.em-metrics{break-inside:avoid}
      .em-table-wrap{overflow:visible}
    }
"""


MARKUP = r"""
<div class="em-root" id="emissionApp">
  <div id="emStatus" class="em-status" aria-live="polite"></div>

  <section class="em-filters" aria-label="Gold emission filters">
    <div class="em-field">
      <label for="emWorldSelect">World</label>
      <select id="emWorldSelect"></select>
    </div>
    <div class="em-field">
      <label for="emDateStart">Date range</label>
      <div class="em-date-pair">
        <input id="emDateStart" type="date" aria-label="Start date">
        <input id="emDateEnd" type="date" aria-label="End date">
      </div>
    </div>
    <div class="em-field em-series-field">
      <div class="em-series-summary">Series</div>
      <div class="em-series-control" role="group" aria-label="Visible chart series">
        <label class="em-check"><input type="checkbox" data-em-series="direct" checked> Direct GP</label>
        <label class="em-check"><input type="checkbox" data-em-series="potential" checked> Potential GP</label>
        <label class="em-check"><input id="emTcPriceToggle" type="checkbox"> TC price (GP/TC)</label>
      </div>
    </div>
    <div class="em-actions">
      <button id="emLoadButton" class="em-button" type="button">Load updated CSV</button>
      <button id="emResetButton" class="em-button em-secondary" type="button">Reset filters</button>
      <input id="emFileInput" type="file" accept=".csv,text/csv" hidden>
    </div>
  </section>

  <div id="emError" class="em-error" role="alert"></div>

  <section class="em-metrics" aria-label="Summary metrics">
    <div class="em-metric">
      <span class="em-metric-label">Total potential GP</span>
      <strong id="emTotalMetric" class="em-metric-value">—</strong>
      <span id="emTotalMeta" class="em-metric-meta">—</span>
    </div>
    <div class="em-metric">
      <span class="em-metric-label">Average potential GP</span>
      <strong id="emAverageMetric" class="em-metric-value">—</strong>
      <span class="em-metric-meta">GP per day</span>
    </div>
    <div class="em-metric">
      <span class="em-metric-label">Highest potential GP day</span>
      <strong id="emPeakMetric" class="em-metric-value">—</strong>
      <span id="emPeakMeta" class="em-metric-meta">—</span>
    </div>
    <div class="em-metric">
      <span class="em-metric-label">Coverage</span>
      <strong id="emCoverageMetric" class="em-metric-value">—</strong>
      <span id="emCoverageMeta" class="em-metric-meta">—</span>
    </div>
  </section>

  <section id="emWorldBreakdown" class="em-panel em-world-breakdown" hidden></section>

  <section class="em-main-grid">
    <article class="em-panel">
      <div class="em-panel-inner">
        <div class="em-panel-heading">
          <h3 class="em-panel-title">Emission over time</h3>
          <span class="em-note">Emission uses the left axis · TC price uses the right axis</span>
        </div>
        <div id="emChartLegend" class="em-legend" aria-hidden="true"></div>
        <div class="em-chart-wrap">
          <svg id="emChart" role="img" aria-labelledby="emChartTitle emChartDescription">
            <title id="emChartTitle">Gold emission over time</title>
            <desc id="emChartDescription">Daily gold emission and, when selected, Tibia Coin price in GP per TC for the selected world and dates.</desc>
          </svg>
          <div id="emChartTooltip" class="em-tooltip"></div>
          <label class="em-hidden" for="emChartInspector">Inspect chart by date</label>
          <input id="emChartInspector" class="em-hidden" type="range" min="0" max="0" value="0">
        </div>
      </div>
    </article>

    <article class="em-panel em-composition">
      <div class="em-panel-inner">
        <div class="em-panel-heading">
          <h3 class="em-panel-title">Emission composition</h3>
        </div>
        <div class="em-composition-total">
          Potential GP in selected period
          <strong id="emPotentialTotal">—</strong>
        </div>
        <div id="emCompositionStack" class="em-stack" aria-label="Composition of maximum potential emission">
          <div class="em-stack-direct"></div>
          <div class="em-stack-npc"></div>
        </div>
        <div id="emCompositionList" class="em-composition-list"></div>
        <p class="em-note" style="margin-top:14px">
          Potential GP is direct GP plus the NPC value of all modeled loot. It is a modeled maximum,
          not proof that every dropped item was collected and sold.
        </p>
      </div>
    </article>
  </section>

  <section class="em-panel em-quality" aria-labelledby="emQualityTitle">
    <div class="em-quality-header">
      <h3 class="em-panel-title" id="emQualityTitle">Coverage by date</h3>
      <div class="em-quality-key" aria-label="Coverage quality legend">
        <span><i class="em-key-dot" style="background:var(--em-good)"></i> Complete</span>
        <span><i class="em-key-dot" style="background:var(--em-warning)"></i> Partial</span>
        <span><i class="em-key-dot" style="background:var(--em-danger)"></i> Low quality</span>
      </div>
    </div>
    <div id="emQualityStrip" class="em-quality-strip"></div>
  </section>

  <section class="em-panel em-table-panel" aria-labelledby="emTableTitle">
    <div class="em-table-head">
      <div>
        <h3 class="em-panel-title" id="emTableTitle">Daily detail</h3>
        <span id="emTableCount" class="em-note"></span>
      </div>
      <button id="emTableToggle" class="em-button em-text" type="button">View all</button>
    </div>
    <p class="em-note" style="padding:0 16px 10px">Click a date to see every creature killed that day. With <strong>All worlds</strong> selected the day view adds every world together.</p>
    <div class="em-table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col" class="em-text-cell" data-em-sort-key="date">Date</th>
            <th scope="col" data-em-sort-key="coverage">Coverage</th>
            <th scope="col" class="em-text-cell" data-em-sort-key="quality">Quality</th>
            <th scope="col" data-em-sort-key="kills">Daily kills</th>
            <th scope="col" data-em-sort-key="direct">Direct GP</th>
            <th scope="col" data-em-sort-key="potential">Potential GP</th>
            <th scope="col" class="em-text-cell" data-em-sort-key="top">Top emitter</th>
          </tr>
        </thead>
        <tbody id="emDetailBody"></tbody>
      </table>
    </div>
    <div class="em-table-footer">
      <button id="emTableToggleBottom" class="em-button em-text" type="button">View all</button>
    </div>
  </section>

  <section id="emDayDetail" class="em-panel em-day-detail" aria-labelledby="emDayDetailTitle" hidden>
    <div class="em-table-head">
      <div>
        <h3 class="em-panel-title" id="emDayDetailTitle">Creature detail</h3>
        <p id="emDayDetailSummary" class="em-detail-summary"></p>
      </div>
      <button id="emCloseDayDetail" class="em-button em-text" type="button">← Back to Gold Emission</button>
    </div>
    <div id="emDayDetailContent" aria-live="polite"></div>
  </section>

  <p class="em-footnote">
    Source: reconstructed creature loot values joined to Tibia world kill statistics. Player-market values are zero.
    “Potential GP maximum” assumes all modeled NPC-sellable loot is collected and sold.
    GP means Tibia gold pieces. TC means Tibia Coins; no TC are counted as generated gold.
    Boss emissions remain excluded from the primary series.
  </p>
</div>
"""


# The creature ranking is its own surface: a hub view and a standalone page, never a
# panel appended under the daily emission tables.
RANKING_MARKUP = r"""
<div class="em-root" id="creatureRanking">
  <section class="em-panel em-ranking" aria-labelledby="emRankingTitle">
    <div class="em-table-head">
      <div>
        <h3 class="em-panel-title" id="emRankingTitle">Ranking</h3>
        <p class="em-detail-summary" id="emRankingSummary"></p>
      </div>
      <button id="emRankingToggle" class="em-button em-text" type="button">View all</button>
    </div>
    <div class="em-ranking-tools">
      <div id="emRankMeasure" class="em-segmented" role="group" aria-label="Rank creatures by">
        <button class="em-segment" type="button" data-em-measure="direct">Direct GP</button>
        <button class="em-segment active" type="button" data-em-measure="potential">Potential GP</button>
      </div>
      <input id="emRankSearch" type="search" placeholder="Search a creature…" aria-label="Search creatures">
      <select id="emRankScope" aria-label="Creature group">
        <option value="nonboss">Regular creatures</option>
        <option value="all">Regular creatures and bosses</option>
        <option value="boss">Bosses only</option>
      </select>
    </div>
    <div class="em-table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Rank</th>
            <th scope="col" class="em-text-cell" data-em-sort-key="name">Creature</th>
            <th scope="col" data-em-sort-key="direct">Direct GP per kill</th>
            <th scope="col" data-em-sort-key="npc">NPC loot GP per kill</th>
            <th scope="col" data-em-sort-key="potential">Potential GP per kill</th>
            <th scope="col" data-em-sort-key="samples">Loot samples</th>
            <th scope="col" class="em-text-cell" data-em-sort-key="confidence">Model confidence</th>
          </tr>
        </thead>
        <tbody id="emRankingBody"></tbody>
      </table>
    </div>
    <div class="em-table-footer">
      <button id="emRankingToggleBottom" class="em-button em-text" type="button">View all</button>
    </div>
  </section>

  <p class="em-footnote">
    Direct GP per kill is the gold the creature drops itself. NPC loot GP per kill is the most NPCs
    would pay for everything else it drops, so Potential GP per kill is an upper bound that assumes
    you collect and sell all of it. Values are averages from TibiaWiki loot statistics; a creature
    with few loot samples is a rougher estimate. Player-market prices are never counted.
    GP means Tibia gold pieces. TC means Tibia Coins.
  </p>
</div>
"""


SCRIPT = r"""
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const COLORS = { direct: "#4E79A7", potential: "#F28E2B", tcPrice: "#59A14F" };
  const SERIES = {
    direct: { label: "Direct GP", color: COLORS.direct, dash: "" },
    potential: { label: "Potential GP", color: COLORS.potential, dash: "8 6" }
  };
  const REQUIRED_CSV = [
    "world", "date", "top_emission_creature_name", "top_emission_creature_gp",
    "total_kills", "nonboss_kills", "modeled_kills_nonboss", "direct_coin_gp",
    "npc_potential_gp_max", "potential_total_gp_max", "low_quality_flag",
    "partial_date_flag", "ev_any"
  ];
  const KILL_STATS_BASE = "https://raw.githubusercontent.com/tibiamaps/tibia-kill-stats/main/data/";
  const WORLD_CONCURRENCY = 6;
  const RANKING_PREVIEW = 40;
  const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const decimal = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });

  let host = { prefix: "", onStateChange: () => {}, prices: null };
  let root = null;
  let rankRoot = null;
  let rawRows = [];
  let embeddedPriceRows = [];
  let creatureValueRows = [];
  let creatureRanking = [];
  let priceByWorldDate = new Map();
  let priceByDateMedian = new Map();
  let creatureValueMap = new Map();
  let sourceMeta = {};
  let filtered = [];
  let showAllRows = false;
  let showAllCreatures = false;
  let rankMeasure = "potential";
  let detail = null;
  let detailRun = 0;
  let detailAbort = null;
  let ready = false;

  const $ = (selector) => root.querySelector(selector);
  const $$ = (selector) => [...root.querySelectorAll(selector)];
  const $r = (selector) => rankRoot.querySelector(selector);
  const $$r = (selector) => [...rankRoot.querySelectorAll(selector)];

  function decodeRows(schema, rows) {
    return rows.map(values => Object.fromEntries(schema.map((name, index) => [name, values[index]])));
  }

  function numeric(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function bool(value) {
    return value === true || value === 1 || String(value).toLowerCase() === "true";
  }

  function isoDate(value) {
    if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) return value.slice(0, 10);
    const parsed = new Date(value);
    return Number.isNaN(parsed.valueOf()) ? String(value ?? "") : parsed.toISOString().slice(0, 10);
  }

  function isoTimestamp(value) {
    const parsed = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(parsed.valueOf())) return String(value ?? "");
    const stamp = parsed.toISOString();
    return `${stamp.slice(0, 10)} ${stamp.slice(11, 16)} UTC`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  function debounce(callback, wait) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => callback(...args), wait);
    };
  }

  function sum(rows, key) {
    return rows.reduce((total, row) => total + numeric(row[key]), 0);
  }

  function qualityOf(row) {
    if (row.partial) return "partial";
    if (row.low || row.coverage < 0.8) return "low";
    return "complete";
  }

  function normalizedCreatureName(value) {
    return String(value || "").trim().toLocaleLowerCase("en-US").replace(/\s+/g, " ");
  }

  /* ---------------------------------------------------------------- mounting */

  function mount(options) {
    root = options.root;
    host = { prefix: "", onStateChange: () => {}, prices: null, ...options };
    rawRows = decodeRows(options.data.schema, options.data.rows);
    creatureValueRows = decodeRows(
      options.data.creatureValueSchema, options.data.creatureValues
    );
    embeddedPriceRows = options.data.priceRows
      ? decodeRows(options.data.priceSchema, options.data.priceRows)
      : [];
    sourceMeta = { ...options.data.meta };
    rebuildCreatureIndexes();
    refreshPrices();
    populateWorlds();

    const params = options.params || new URLSearchParams();
    const dates = rawRows.map(row => row.date).sort();
    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];
    $("#emDateStart").min = $("#emDateEnd").min = minDate;
    $("#emDateStart").max = $("#emDateEnd").max = maxDate;
    $("#emDateStart").value = validDate(read(params, "start"), minDate, maxDate) || minDate;
    $("#emDateEnd").value = validDate(read(params, "end"), minDate, maxDate) || maxDate;
    const requestedWorld = read(params, "world");
    if (requestedWorld && hasWorld(requestedWorld)) $("#emWorldSelect").value = requestedWorld;
    const requestedSeries = read(params, "series");
    if (requestedSeries) {
      const selected = new Set(requestedSeries.split(","));
      $$("[data-em-series]").forEach(input => { input.checked = selected.has(input.dataset.emSeries); });
      if (!$$("[data-em-series]:checked").length) $("[data-em-series='potential']").checked = true;
    }
    $("#emTcPriceToggle").checked = read(params, "tcPrice") === "1";

    bindEvents();
    updateStatus();
    render();
    ready = true;
    if (options.rankingRoot) mountRanking({ root: options.rankingRoot });

    const detailWorld = read(params, "detailWorld");
    const detailDate = read(params, "detailDate");
    if (detailWorld && detailDate && (detailWorld === "all" || hasWorld(detailWorld))) {
      $("#emWorldSelect").value = detailWorld;
      render();
      openDayDetail(detailDate, "replace");
    }
    void refreshProjectCSV();
  }

  function activate() {
    if (!ready) return;
    renderChart(filtered);
  }

  function hasWorld(world) {
    return [...$("#emWorldSelect").options].some(option => option.value === world);
  }

  function paramName(name) {
    return host.prefix ? host.prefix + name[0].toUpperCase() + name.slice(1) : name;
  }

  function read(params, name) {
    return params.get(paramName(name));
  }

  function params() {
    if (!ready) return {};
    const map = {};
    const series = selectedSeries();
    if ($("#emWorldSelect").value !== "all") map[paramName("world")] = $("#emWorldSelect").value;
    if ($("#emDateStart").value !== $("#emDateStart").min) map[paramName("start")] = $("#emDateStart").value;
    if ($("#emDateEnd").value !== $("#emDateEnd").max) map[paramName("end")] = $("#emDateEnd").value;
    if (series.length !== 2) map[paramName("series")] = series.join(",");
    if ($("#emTcPriceToggle").checked) map[paramName("tcPrice")] = "1";
    if (detail) {
      map[paramName("detailWorld")] = detail.world;
      map[paramName("detailDate")] = detail.date;
    }
    return map;
  }

  function publish(mode = "replace") {
    if (!ready) return;
    host.onStateChange(params(), mode);
  }

  function applyParams(incoming) {
    if (!ready) return;
    const world = read(incoming, "world") || "all";
    if (hasWorld(world)) $("#emWorldSelect").value = world;
    const start = validDate(read(incoming, "start"), $("#emDateStart").min, $("#emDateStart").max);
    const end = validDate(read(incoming, "end"), $("#emDateEnd").min, $("#emDateEnd").max);
    $("#emDateStart").value = start || $("#emDateStart").min;
    $("#emDateEnd").value = end || $("#emDateEnd").max;
    const series = read(incoming, "series");
    const selected = new Set((series || "direct,potential").split(","));
    $$("[data-em-series]").forEach(input => { input.checked = selected.has(input.dataset.emSeries); });
    if (!$$("[data-em-series]:checked").length) $("[data-em-series='potential']").checked = true;
    $("#emTcPriceToggle").checked = read(incoming, "tcPrice") === "1";
    render();
    const detailDate = read(incoming, "detailDate");
    if (detailDate) openDayDetail(detailDate, "none");
    else exitDayDetail();
  }

  /* ------------------------------------------------------------------ inputs */

  function populateWorlds(preserve = "all") {
    const worlds = [...new Set(rawRows.map(row => row.world))].sort((a, b) => a.localeCompare(b));
    $("#emWorldSelect").innerHTML = `<option value="all">All worlds</option>` +
      worlds.map(world => `<option value="${escapeHtml(world)}">${escapeHtml(world)}</option>`).join("");
    $("#emWorldSelect").value = worlds.includes(preserve) ? preserve : "all";
  }

  function validDate(value, min, max) {
    return value && value >= min && value <= max ? value : "";
  }

  function clampDate(value, min, max) {
    if (!value || value < min) return min;
    if (value > max) return max;
    return value;
  }

  function selectedSeries() {
    return $$("[data-em-series]:checked").map(input => input.dataset.emSeries);
  }

  function bindEvents() {
    ["#emWorldSelect", "#emDateStart", "#emDateEnd"].forEach(selector => {
      $(selector).addEventListener("change", () => { exitDayDetail(); render(); publish(); });
    });
    $$("[data-em-series]").forEach(input => input.addEventListener("change", () => {
      if (!$$("[data-em-series]:checked").length) input.checked = true;
      render();
      publish();
    }));
    $("#emTcPriceToggle").addEventListener("change", () => { render(); publish(); });
    $("#emResetButton").addEventListener("click", resetFilters);
    $("#emLoadButton").addEventListener("click", () => $("#emFileInput").click());
    $("#emFileInput").addEventListener("change", loadCSV);
    $("#emTableToggle").addEventListener("click", toggleTable);
    $("#emTableToggleBottom").addEventListener("click", toggleTable);
    $("#emCloseDayDetail").addEventListener("click", closeDayDetail);
    $("#emChartInspector").addEventListener("input", event => showTooltipAt(Number(event.target.value), true));
    window.addEventListener("resize", debounce(() => renderChart(filtered), 100));
  }

  function resetFilters() {
    $("#emWorldSelect").value = "all";
    $("#emDateStart").value = $("#emDateStart").min;
    $("#emDateEnd").value = $("#emDateEnd").max;
    $$("[data-em-series]").forEach(input => { input.checked = true; });
    $("#emTcPriceToggle").checked = false;
    showAllRows = false;
    exitDayDetail();
    render();
    publish();
  }

  /* ------------------------------------------------------------------ indexes */

  function refreshPrices() {
    const rows = typeof host.prices === "function" ? host.prices() : embeddedPriceRows;
    priceByWorldDate = new Map();
    const valuesByDate = new Map();
    for (const row of rows || []) {
      const value = numeric(row.price_gp);
      if (!value || !row.world || !row.date) continue;
      const date = isoDate(row.date);
      priceByWorldDate.set(`${row.world}|${date}`, value);
      if (!valuesByDate.has(date)) valuesByDate.set(date, []);
      valuesByDate.get(date).push(value);
    }
    priceByDateMedian = new Map([...valuesByDate].map(([date, values]) => {
      values.sort((a, b) => a - b);
      const middle = Math.floor(values.length / 2);
      const median = values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
      return [date, median];
    }));
    if (ready) render();
  }

  function rebuildCreatureIndexes() {
    creatureValueMap = new Map();
    for (const row of creatureValueRows) {
      const names = [row.canonical_name, ...String(row.raw_names || "").split(" | ")];
      for (const name of names) creatureValueMap.set(normalizedCreatureName(name), row);
    }
    creatureRanking = creatureValueRows.map(row => {
      const direct = numeric(row.expected_direct_coin_gp_per_kill);
      const npc = numeric(row.expected_npc_sale_gp_per_kill);
      return {
        name: row.canonical_name,
        direct,
        npc,
        potential: direct + npc,
        boss: bool(row.is_boss),
        included: bool(row.included_in_main_series),
        status: row.loot_model_status,
        confidence: row.loot_confidence || "",
        samples: numeric(row.loot_samples)
      };
    }).filter(row => row.name && row.potential > 0);
  }

  function worldsReporting(date) {
    return [...new Set(rawRows.filter(row => row.date === date).map(row => row.world))]
      .sort((a, b) => a.localeCompare(b));
  }

  function aggregateRows() {
    const world = $("#emWorldSelect").value;
    const start = $("#emDateStart").value;
    const end = $("#emDateEnd").value;
    const selected = rawRows.filter(row =>
      (world === "all" || row.world === world) && row.date >= start && row.date <= end
    );
    const byDate = new Map();
    for (const row of selected) {
      const current = byDate.get(row.date) || {
        date: row.date, kills: 0, nonboss: 0, modeled: 0, direct: 0, npc: 0,
        potential: 0, low: false, partial: false, event: false, worlds: 0,
        topName: "", topWorld: "", topGp: -1
      };
      current.kills += numeric(row.total_kills);
      current.nonboss += numeric(row.nonboss_kills);
      current.modeled += numeric(row.modeled_kills_nonboss);
      current.direct += numeric(row.direct_coin_gp);
      current.npc += numeric(row.npc_potential_gp_max);
      current.potential += numeric(row.potential_total_gp_max);
      current.low ||= bool(row.low_quality_flag);
      current.partial ||= bool(row.partial_date_flag);
      current.event ||= bool(row.ev_any);
      current.worlds += 1;
      if (numeric(row.top_emission_creature_gp) > current.topGp) {
        current.topGp = numeric(row.top_emission_creature_gp);
        current.topName = row.top_emission_creature_name || "—";
        current.topWorld = row.world;
      }
      byDate.set(row.date, current);
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date)).map(row => ({
      ...row,
      potential: row.direct + row.npc,
      coverage: row.nonboss > 0 ? row.modeled / row.nonboss : 0,
      tcPrice: world === "all"
        ? numeric(priceByDateMedian.get(row.date))
        : numeric(priceByWorldDate.get(`${world}|${row.date}`))
    }));
  }

  /* ------------------------------------------------------------------ render */

  function render() {
    clearError();
    if ($("#emDateStart").value > $("#emDateEnd").value) {
      showError("Start date must be on or before end date.");
      filtered = [];
      updateMetrics(filtered);
      renderLegend();
      renderChart(filtered);
      renderComposition(filtered);
      renderWorldBreakdown(filtered);
      renderQuality(filtered);
      renderTable(filtered);
      return;
    }
    filtered = aggregateRows();
    updateMetrics(filtered);
    renderLegend();
    renderChart(filtered);
    renderComposition(filtered);
    renderWorldBreakdown(filtered);
    renderQuality(filtered);
    renderTable(filtered);
  }

  function metricCompact(value) {
    const magnitude = Math.abs(value);
    if (magnitude >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
    if (magnitude >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (magnitude >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    return number.format(value);
  }

  function updateMetrics(rows) {
    if (!rows.length) {
      ["#emTotalMetric", "#emAverageMetric", "#emPeakMetric", "#emCoverageMetric"]
        .forEach(id => { $(id).textContent = "—"; });
      $("#emTotalMeta").textContent = "No observations";
      $("#emPeakMeta").textContent = "—";
      $("#emCoverageMeta").textContent = "0 days";
      return;
    }
    const total = sum(rows, "potential");
    const peak = rows.reduce((best, row) => row.potential > best.potential ? row : best, rows[0]);
    const nonboss = sum(rows, "nonboss");
    const modeled = sum(rows, "modeled");
    $("#emTotalMetric").textContent = metricCompact(total);
    $("#emTotalMetric").title = `${number.format(total)} GP`;
    $("#emTotalMeta").textContent = `${number.format(total)} potential GP`;
    $("#emAverageMetric").textContent = metricCompact(total / rows.length);
    $("#emAverageMetric").title = `${number.format(total / rows.length)} GP per day`;
    $("#emPeakMetric").textContent = metricCompact(peak.potential);
    $("#emPeakMetric").title = `${number.format(peak.potential)} potential GP`;
    $("#emPeakMeta").textContent = isoDate(peak.date);
    $("#emCoverageMetric").textContent = percent.format(nonboss ? modeled / nonboss : 0);
    $("#emCoverageMeta").textContent = `${rows.length} observed days`;
  }

  function renderLegend() {
    const emissionLegend = selectedSeries().map(key =>
      `<span class="em-legend-item"><i class="em-legend-line ${key}" style="border-color:${SERIES[key].color}"></i>${SERIES[key].label}</span>`
    ).join("");
    const priceLegend = $("#emTcPriceToggle").checked
      ? `<span class="em-legend-item"><i class="em-legend-line" style="border-color:${COLORS.tcPrice}"></i>TC price (GP/TC) · right axis</span>`
      : "";
    $("#emChartLegend").innerHTML = emissionLegend + priceLegend;
  }

  function addSVG(parent, tag, attributes, text = "") {
    const element = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text) element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function niceMax(value) {
    const exponent = Math.floor(Math.log10(value));
    const unit = 10 ** exponent;
    const normalized = value / unit;
    const nice = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return nice * unit;
  }

  function uniqueIndexes(count, length) {
    if (length <= 1) return [0];
    return [...new Set(Array.from({ length: count }, (_, index) => Math.round(index * (length - 1) / (count - 1))))];
  }

  function renderChart(rows) {
    const svg = $("#emChart");
    svg.innerHTML = `<title id="emChartTitle">Gold emission over time</title>
      <desc id="emChartDescription">Daily gold emission and, when selected, Tibia Coin price in GP per TC for the selected world and dates.</desc>`;
    $("#emChartTooltip").classList.remove("visible");
    if (!rows.length) {
      svg.setAttribute("viewBox", "0 0 800 360");
      addSVG(svg, "text", { x: 400, y: 180, "text-anchor": "middle", fill: "#667085", "font-size": 14 }, "No observations for this selection");
      return;
    }
    const keys = selectedSeries();
    const showTcPrice = $("#emTcPriceToggle").checked;
    const tcPrices = rows.map(row => row.tcPrice).filter(value => value > 0);
    const width = Math.max(320, svg.clientWidth || 800);
    const height = 360;
    const margin = { top: 22, right: showTcPrice ? (width < 720 ? 58 : 76) : 14, bottom: 46, left: width < 720 ? 54 : 76 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const yMaxRaw = Math.max(...rows.flatMap(row => keys.map(key => row[key])), 1);
    const yMax = niceMax(yMaxRaw);
    const x = index => margin.left + (rows.length === 1 ? innerWidth / 2 : index / (rows.length - 1) * innerWidth);
    const y = value => margin.top + innerHeight - value / yMax * innerHeight;
    const priceMinRaw = tcPrices.length ? Math.min(...tcPrices) : 0;
    const priceMaxRaw = tcPrices.length ? Math.max(...tcPrices) : 1;
    const pricePad = Math.max((priceMaxRaw - priceMinRaw) * 0.1, priceMaxRaw * 0.01, 1);
    const priceMin = Math.max(0, priceMinRaw - pricePad);
    const priceMax = priceMaxRaw + pricePad;
    const yPrice = value => margin.top + innerHeight - (value - priceMin) / (priceMax - priceMin || 1) * innerHeight;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    for (let i = 0; i <= 4; i++) {
      const value = yMax * i / 4;
      const yy = y(value);
      addSVG(svg, "line", { x1: margin.left, x2: width - margin.right, y1: yy, y2: yy, stroke: "#e2e7ee", "stroke-dasharray": i ? "4 4" : "" });
      addSVG(svg, "text", { x: margin.left - 10, y: yy + 4, "text-anchor": "end", fill: "#667085", "font-size": 11 }, compact.format(value));
      if (showTcPrice && tcPrices.length) {
        const priceValue = priceMin + (priceMax - priceMin) * i / 4;
        addSVG(svg, "text", {
          x: width - margin.right + 9, y: yPrice(priceValue) + 4,
          fill: COLORS.tcPrice, "font-size": 11
        }, compact.format(priceValue));
      }
    }

    const tickCount = Math.min(width < 720 ? 3 : 6, rows.length);
    for (const index of uniqueIndexes(tickCount, rows.length)) {
      addSVG(svg, "text", { x: x(index), y: height - 14, "text-anchor": "middle", fill: "#667085", "font-size": 11 }, isoDate(rows[index].date));
    }

    for (const key of keys) {
      const path = rows.map((row, index) => `${index ? "L" : "M"} ${x(index).toFixed(2)} ${y(row[key]).toFixed(2)}`).join(" ");
      addSVG(svg, "path", {
        d: path, fill: "none", stroke: SERIES[key].color, "stroke-width": 2.5,
        "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": SERIES[key].dash,
        "vector-effect": "non-scaling-stroke"
      });
    }
    if (showTcPrice && tcPrices.length) {
      let started = false;
      const pricePath = rows.map((row, index) => {
        if (!row.tcPrice) { started = false; return ""; }
        const command = started ? "L" : "M";
        started = true;
        return `${command} ${x(index).toFixed(2)} ${yPrice(row.tcPrice).toFixed(2)}`;
      }).filter(Boolean).join(" ");
      addSVG(svg, "path", {
        d: pricePath, fill: "none", stroke: COLORS.tcPrice, "stroke-width": 3.2,
        "stroke-linecap": "round", "stroke-linejoin": "round",
        "vector-effect": "non-scaling-stroke"
      });
    }

    const crosshair = addSVG(svg, "line", {
      x1: margin.left, x2: margin.left, y1: margin.top, y2: margin.top + innerHeight,
      stroke: "#344054", "stroke-width": 1, opacity: 0
    });
    const dots = {};
    for (const key of keys) {
      dots[key] = addSVG(svg, "circle", {
        cx: margin.left, cy: margin.top, r: 4.5,
        fill: SERIES[key].color, stroke: "#fff", "stroke-width": 2, opacity: 0
      });
    }
    if (showTcPrice && tcPrices.length) {
      dots.tcPrice = addSVG(svg, "circle", {
        cx: margin.left, cy: margin.top, r: 4.5,
        fill: COLORS.tcPrice, stroke: "#fff", "stroke-width": 2, opacity: 0
      });
    }
    const capture = addSVG(svg, "rect", {
      x: margin.left, y: margin.top, width: innerWidth, height: innerHeight,
      fill: "transparent", tabindex: "0", role: "application",
      "aria-label": "Interactive time chart. Emission uses the left axis and TC price uses the right axis. Move pointer or use the chart date slider to inspect values."
    });
    capture.addEventListener("pointermove", event => {
      const bounds = svg.getBoundingClientRect();
      const pointerX = (event.clientX - bounds.left) / bounds.width * width;
      const index = Math.max(0, Math.min(rows.length - 1, Math.round((pointerX - margin.left) / innerWidth * (rows.length - 1))));
      showTooltipAt(index, false);
    });
    capture.addEventListener("pointerdown", event => capture.setPointerCapture?.(event.pointerId));
    capture.addEventListener("pointerleave", hideTooltip);
    capture.addEventListener("blur", hideTooltip);
    capture.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let index = Number($("#emChartInspector").value || 0);
      if (event.key === "ArrowLeft") index--;
      if (event.key === "ArrowRight") index++;
      if (event.key === "Home") index = 0;
      if (event.key === "End") index = rows.length - 1;
      index = Math.max(0, Math.min(rows.length - 1, index));
      $("#emChartInspector").value = index;
      showTooltipAt(index, true);
    });
    svg._chart = { x, y, yPrice, margin, width, height, crosshair, dots, rows, keys, showTcPrice };
    $("#emChartInspector").max = rows.length - 1;
    $("#emChartInspector").value = 0;
  }

  function showTooltipAt(index, fromKeyboard = false) {
    const state = $("#emChart")._chart;
    if (!state || !state.rows[index]) return;
    const { x, y, yPrice, margin, width, crosshair, dots, rows, keys, showTcPrice } = state;
    const row = rows[index];
    const xx = x(index);
    crosshair.setAttribute("x1", xx);
    crosshair.setAttribute("x2", xx);
    crosshair.setAttribute("opacity", 1);
    for (const key of keys) {
      dots[key].setAttribute("cx", xx);
      dots[key].setAttribute("cy", y(row[key]));
      dots[key].setAttribute("opacity", 1);
    }
    if (showTcPrice && dots.tcPrice) {
      dots.tcPrice.setAttribute("cx", xx);
      dots.tcPrice.setAttribute("cy", row.tcPrice ? yPrice(row.tcPrice) : margin.top);
      dots.tcPrice.setAttribute("opacity", row.tcPrice ? 1 : 0);
    }
    $("#emChartInspector").value = index;
    const tooltip = $("#emChartTooltip");
    tooltip.innerHTML = `<div class="em-tooltip-date">${isoDate(row.date)}</div>` +
      keys.map(key => `<div class="em-tooltip-row"><i class="em-tooltip-dot" style="background:${SERIES[key].color}"></i><span>${SERIES[key].label}</span><span class="em-tooltip-value">${number.format(row[key])} GP</span></div>`).join("") +
      (showTcPrice ? `<div class="em-tooltip-row"><i class="em-tooltip-dot" style="background:${COLORS.tcPrice}"></i><span>TC price</span><span class="em-tooltip-value">${row.tcPrice ? `${number.format(row.tcPrice)} GP/TC` : "No price data"}</span></div>` : "") +
      `<div class="em-tooltip-row" style="margin-top:7px"><i></i><span>Coverage</span><span class="em-tooltip-value">${percent.format(row.coverage)}</span></div>`;
    const chartWidth = root.querySelector(".em-chart-wrap").clientWidth;
    const scaledX = xx / width * chartWidth;
    tooltip.style.left = `${Math.min(Math.max(6, scaledX + 12), Math.max(6, chartWidth - 290))}px`;
    tooltip.style.top = `${Math.max(8, margin.top + 8)}px`;
    tooltip.classList.add("visible");
    if (fromKeyboard) {
      $("#emChartInspector").setAttribute("aria-valuetext", `${isoDate(row.date)}: potential ${number.format(row.potential)} GP${showTcPrice && row.tcPrice ? `; TC price ${number.format(row.tcPrice)} GP per TC` : ""}`);
    }
  }

  function hideTooltip() {
    const state = $("#emChart")._chart;
    if (state) {
      state.crosshair.setAttribute("opacity", 0);
      Object.values(state.dots).forEach(dot => dot.setAttribute("opacity", 0));
    }
    $("#emChartTooltip").classList.remove("visible");
  }

  function renderComposition(rows) {
    const direct = sum(rows, "direct");
    const npc = sum(rows, "npc");
    const potential = direct + npc;
    $("#emPotentialTotal").textContent = `${number.format(potential)} GP`;
    const segments = [
      { key: "direct", label: "Direct GP", value: direct, color: COLORS.direct },
      { key: "npc", label: "NPC-sellable loot potential", value: npc, color: COLORS.potential }
    ];
    const stackParts = $("#emCompositionStack").children;
    segments.forEach((segment, index) => {
      stackParts[index].style.width = `${potential ? segment.value / potential * 100 : 0}%`;
      stackParts[index].title = `${segment.label}: ${number.format(segment.value)} GP`;
    });
    $("#emCompositionList").innerHTML = segments.map(segment =>
      `<div class="em-composition-row">
        <i class="em-swatch" style="background:${segment.color}"></i>
        <span>${segment.label}<small>${potential ? percent.format(segment.value / potential) : "0%"}</small></span>
        <strong>${number.format(segment.value)} GP</strong>
      </div>`
    ).join("");
    $("#emCompositionStack").setAttribute("aria-label", segments.map(segment =>
      `${segment.label} ${potential ? percent.format(segment.value / potential) : "0%"}`
    ).join(", "));
  }

  function renderWorldBreakdown(rows) {
    const host_ = $("#emWorldBreakdown");
    const world = $("#emWorldSelect").value;
    if (world === "all" || !rows.length) {
      host_.hidden = true;
      host_.innerHTML = "";
      return;
    }
    const kills = sum(rows, "kills");
    const direct = sum(rows, "direct");
    const npc = sum(rows, "npc");
    const nonboss = sum(rows, "nonboss");
    const modeled = sum(rows, "modeled");
    const flagged = rows.filter(row => qualityOf(row) !== "complete").length;
    const top = rows.reduce((best, row) => row.topGp > best.topGp ? row : best, rows[0]);
    host_.innerHTML = `<div class="em-panel-inner">
      <div class="em-panel-heading"><div><h3 class="em-panel-title">What generated potential GP in ${escapeHtml(world)}</h3><p class="em-note">Direct GP plus the maximum NPC value of modeled loot for the selected dates.</p></div></div>
      <div class="em-world-grid">
        <div class="em-world-cell"><span>Creature deaths recorded</span><strong>${number.format(kills)}</strong></div>
        <div class="em-world-cell"><span>GP dropped directly by creatures</span><strong>${number.format(direct)} GP</strong></div>
        <div class="em-world-cell"><span>Potential GP from selling all modeled loot to NPCs</span><strong>${number.format(npc)} GP</strong></div>
        <div class="em-world-cell"><span>Largest creature source on one day</span><strong>${escapeHtml(top.topName || "—")}</strong><span>${isoDate(top.date)} · ${number.format(top.topGp)} GP</span></div>
        <div class="em-world-cell"><span>Deaths covered by the GP model</span><strong>${percent.format(nonboss ? modeled / nonboss : 0)}</strong></div>
        <div class="em-world-cell"><span>Days needing extra caution</span><strong>${number.format(flagged)} of ${number.format(rows.length)}</strong></div>
      </div>
    </div>`;
    host_.hidden = false;
  }

  function renderQuality(rows) {
    const strip = $("#emQualityStrip");
    strip.innerHTML = rows.map((row, index) => {
      const quality = qualityOf(row);
      const label = `${isoDate(row.date)}: ${quality}, ${percent.format(row.coverage)} coverage`;
      return `<button class="em-quality-day ${quality}" data-em-index="${index}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"></button>`;
    }).join("");
    strip.querySelectorAll(".em-quality-day").forEach(button => {
      button.addEventListener("click", () => {
        showTooltipAt(Number(button.dataset.emIndex), true);
        root.querySelector(".em-chart-wrap").scrollIntoView({
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
          block: "center"
        });
      });
    });
  }

  function renderTable(rows) {
    const ordered = sortRows("daily", rows);
    const visible = showAllRows ? ordered : ordered.slice(0, 30);
    const allWorlds = $("#emWorldSelect").value === "all";
    $("#emDetailBody").innerHTML = visible.map(row => {
      const quality = qualityOf(row);
      const qualityLabel = quality === "low" ? "Low quality" : quality[0].toUpperCase() + quality.slice(1);
      const topEmitter = allWorlds ? `${row.topName} · ${row.topWorld}` : row.topName;
      return `<tr>
        <td class="em-text-cell"><button class="em-date-drill" type="button" data-em-date="${isoDate(row.date)}" aria-label="Open creature details for ${isoDate(row.date)}">${isoDate(row.date)}</button></td>
        <td>${percent.format(row.coverage)}</td>
        <td class="em-text-cell"><span class="em-quality-label ${quality}">${qualityLabel}</span></td>
        <td>${number.format(row.kills)}</td>
        <td>${number.format(row.direct)}</td>
        <td>${number.format(row.potential)}</td>
        <td class="em-text-cell">${escapeHtml(topEmitter || "—")}</td>
      </tr>`;
    }).join("");
    $$("[data-em-date]").forEach(button => button.addEventListener("click", () => {
      openDayDetail(button.dataset.emDate, "push");
    }));
    const table = $("#emDetailBody").closest("table");
    bindSortHeaders(table, "daily", () => renderTable(filtered));
    markSortHeaders(table, "daily");
    $("#emTableCount").textContent = `${number.format(rows.length)} observed days`;
    const toggleLabel = showAllRows ? "Show first 30" : `View all ${number.format(rows.length)}`;
    $("#emTableToggle").textContent = $("#emTableToggleBottom").textContent = toggleLabel;
    $("#emTableToggle").hidden = $("#emTableToggleBottom").hidden = rows.length <= 30;
  }

  function toggleTable() {
    showAllRows = !showAllRows;
    renderTable(filtered);
  }

  /* --------------------------------------------------------- creature ranking */

  function mountRanking(options) {
    rankRoot = options.root;
    if (options.data) {
      creatureValueRows = decodeRows(
        options.data.creatureValueSchema, options.data.creatureValues
      );
      rebuildCreatureIndexes();
    }
    $$r("[data-em-measure]").forEach(button => button.addEventListener("click", () => {
      rankMeasure = button.dataset.emMeasure;
      // The measure buttons and the column headers drive the same ordering, so they stay
      // in agreement instead of each claiming a different sort.
      sortState.ranking = { key: rankMeasure, direction: "descending" };
      $$r("[data-em-measure]").forEach(other => other.classList.toggle("active", other === button));
      renderRanking();
    }));
    $r("#emRankSearch").addEventListener("input", debounce(renderRanking, 140));
    $r("#emRankScope").addEventListener("change", renderRanking);
    $r("#emRankingToggle").addEventListener("click", toggleRanking);
    $r("#emRankingToggleBottom").addEventListener("click", toggleRanking);
    renderRanking();
  }

  function toggleRanking() {
    showAllCreatures = !showAllCreatures;
    renderRanking();
  }

  function rankingRows() {
    const scope = $r("#emRankScope").value;
    const query = normalizedCreatureName($r("#emRankSearch").value);
    const matching = creatureRanking
      .filter(row => scope === "all" || (scope === "boss" ? row.boss : !row.boss))
      .filter(row => !query || normalizedCreatureName(row.name).includes(query));
    return sortRows("ranking", matching);
  }

  function renderRanking() {
    if (!rankRoot) return;
    const rows = rankingRows();
    const visible = showAllCreatures ? rows : rows.slice(0, RANKING_PREVIEW);
    const sortKey = sortState.ranking && sortState.ranking.key;
    const measureLabel = { direct: "direct GP", npc: "NPC loot GP", potential: "potential GP" }[sortKey];
    $r("#emRankingSummary").textContent = !rows.length
      ? "No modeled creature matches this search."
      : measureLabel && sortState.ranking.direction === "descending"
        ? `${number.format(rows.length)} modeled creatures ranked by ${measureLabel} per kill · best: ${rows[0].name} with ${decimal.format(rows[0][sortKey])} GP per kill`
        : `${number.format(rows.length)} modeled creatures · sorted by ${escapeHtml(sortColumnLabel("ranking"))}`;
    $r("#emRankingBody").innerHTML = visible.map((row, index) => `<tr>
      <td>${number.format(index + 1)}</td>
      <td class="em-text-cell">${escapeHtml(row.name)}${row.boss ? `<span class="em-tag">Boss</span>` : ""}${row.included ? "" : `<span class="em-tag">Outside main series</span>`}</td>
      <td>${decimal.format(row.direct)}</td>
      <td>${decimal.format(row.npc)}</td>
      <td>${decimal.format(row.potential)}</td>
      <td>${row.samples ? number.format(row.samples) : "—"}</td>
      <td class="em-text-cell">${escapeHtml(row.confidence || row.status || "—")}</td>
    </tr>`).join("") || `<tr><td colspan="7" class="em-text-cell">No creature matches this search.</td></tr>`;
    const table = $r("#emRankingBody").closest("table");
    bindSortHeaders(table, "ranking", renderRanking);
    markSortHeaders(table, "ranking");
    const toggleLabel = showAllCreatures
      ? `Show top ${RANKING_PREVIEW}`
      : `View all ${number.format(rows.length)}`;
    $r("#emRankingToggle").textContent = $r("#emRankingToggleBottom").textContent = toggleLabel;
    $r("#emRankingToggle").hidden = $r("#emRankingToggleBottom").hidden = rows.length <= RANKING_PREVIEW;
  }

  /* ------------------------------------------------------------ day drilldown */

  // A kill-statistics file records what died during the previous day, so the file for an
  // emission date is stamped one day later. scripts/34_gold_emission.py applies the same
  // shift when it builds the daily series.
  function killStatsFileDate(date) {
    const stamp = new Date(`${date}T00:00:00Z`);
    stamp.setUTCDate(stamp.getUTCDate() + 1);
    return stamp.toISOString().slice(0, 10);
  }

  function killStatsUrl(world, date) {
    return `${KILL_STATS_BASE}${encodeURIComponent(world.toLocaleLowerCase("en-US"))}/${killStatsFileDate(date)}.json`;
  }

  function exitDayDetail() {
    if (detailAbort) detailAbort.abort();
    detailRun += 1;
    detail = null;
    root.classList.remove("em-detail-mode");
    $("#emDayDetail").hidden = true;
    $("#emDayDetailContent").innerHTML = "";
  }

  function closeDayDetail() {
    exitDayDetail();
    publish("pop");
  }

  function openDayDetail(date, mode = "push") {
    const world = $("#emWorldSelect").value;
    const worlds = world === "all" ? worldsReporting(date) : [world];
    if (detailAbort) detailAbort.abort();
    detailRun += 1;
    detail = {
      run: detailRun, date, world, worlds,
      totals: new Map(), failed: [], completed: 0, loading: worlds.length > 0, stopped: false
    };
    root.classList.remove("em-detail-mode");
    root.classList.add("em-detail-mode");
    $("#emDayDetail").hidden = false;
    $("#emDayDetailTitle").textContent = `Creatures killed on ${date}`;
    if (mode !== "none") publish(mode);
    scrollToTop();
    renderDayDetail();
    if (worlds.length) void loadDayDetail(detail);
  }

  function scrollToTop() {
    if (typeof host.onOpenDetail === "function") host.onOpenDetail();
    else window.scrollTo({ top: 0, behavior: "auto" });
  }

  async function loadDayDetail(state) {
    const controller = new AbortController();
    detailAbort = controller;
    const queue = [...state.worlds];
    let lastPaint = 0;
    const paint = force => {
      if (detail !== state) return;
      const now = Date.now();
      if (!force && now - lastPaint < 400) return;
      lastPaint = now;
      renderDayDetail();
    };
    async function worker() {
      while (queue.length) {
        if (detail !== state || state.stopped) return;
        const world = queue.shift();
        try {
          const response = await fetch(killStatsUrl(world, state.date), {
            cache: "force-cache", signal: controller.signal
          });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const payload = await response.json();
          accumulate(state.totals, payload.killstatistics || payload);
        } catch (error) {
          if (error.name === "AbortError") return;
          state.failed.push(world);
        }
        state.completed += 1;
        paint(false);
      }
    }
    await Promise.all(
      Array.from({ length: Math.min(WORLD_CONCURRENCY, queue.length) }, worker)
    );
    if (detail !== state || state.stopped) return;
    state.loading = false;
    renderDayDetail();
  }

  function stopDayDetail() {
    if (!detail || !detail.loading) return;
    detail.stopped = true;
    detail.loading = false;
    if (detailAbort) detailAbort.abort();
    renderDayDetail();
  }

  function accumulate(totals, stats) {
    const entries = Array.isArray(stats.entries) ? stats.entries : [];
    for (const entry of entries) {
      const name = String(entry.race || "").trim();
      const kills = numeric(entry.last_day_killed);
      // "(" and "[" mark aggregate pseudo-entries the daily series also skips.
      if (!name || kills <= 0 || name.startsWith("(") || name.startsWith("[")) continue;
      const key = normalizedCreatureName(name);
      const current = totals.get(key) || { name, kills: 0, worlds: 0 };
      current.kills += kills;
      current.worlds += 1;
      totals.set(key, current);
    }
  }

  function detailRows(state) {
    return [...state.totals.values()].map(entry => {
      const model = creatureValueMap.get(normalizedCreatureName(entry.name));
      // Only a complete loot model contributes GP to the daily series, so the drill-down
      // applies the same rule instead of inventing a value for a partial model.
      const modeled = Boolean(model) && model.loot_model_status === "complete";
      const directPerKill = modeled ? numeric(model.expected_direct_coin_gp_per_kill) : 0;
      const npcPerKill = modeled ? numeric(model.expected_npc_sale_gp_per_kill) : 0;
      return {
        name: entry.name,
        kills: entry.kills,
        worlds: entry.worlds,
        modeled,
        direct: directPerKill * entry.kills,
        npc: npcPerKill * entry.kills,
        potential: (directPerKill + npcPerKill) * entry.kills,
        included: model ? bool(model.included_in_main_series) : false,
        boss: model ? bool(model.is_boss) : false,
        status: model?.exclusion_reason || model?.loot_model_status || "No GP model"
      };
    }).sort((a, b) => b.potential - a.potential || b.kills - a.kills || a.name.localeCompare(b.name));
  }

  function renderDayDetail() {
    if (!detail) return;
    const state = detail;
    const allWorlds = state.world === "all";
    const rows = detailRows(state);
    const totalKills = rows.reduce((total, row) => total + row.kills, 0);
    // The daily series excludes bosses, so the day total is reported the same way and the
    // boss contribution is named separately instead of silently inflating the number.
    const potential = rows
      .filter(row => row.modeled && !row.boss)
      .reduce((total, row) => total + row.potential, 0);
    const bossPotential = rows
      .filter(row => row.modeled && row.boss)
      .reduce((total, row) => total + row.potential, 0);
    const scope = allWorlds
      ? `All worlds (${number.format(state.worlds.length)})`
      : state.world;
    const loaded = state.completed - state.failed.length;
    const summaryParts = [scope, state.date];
    if (allWorlds) summaryParts.push(`${number.format(Math.max(loaded, 0))} worlds added together`);
    summaryParts.push(`${number.format(rows.length)} creature types`);
    summaryParts.push(`${number.format(totalKills)} deaths`);
    summaryParts.push(`${number.format(potential)} potential GP`);
    if (bossPotential > 0) {
      summaryParts.push(`bosses add ${number.format(bossPotential)} GP outside the main series`);
    }
    $("#emDayDetailSummary").textContent = state.loading
      ? `${scope} · ${state.date} · reading the public kill statistics…`
      : summaryParts.join(" · ");

    const progress = state.loading
      ? `<div class="em-progress">
          <div class="em-progress-track"><i style="width:${state.worlds.length ? Math.round(state.completed / state.worlds.length * 100) : 0}%"></i></div>
          <span>Read ${number.format(state.completed)} of ${number.format(state.worlds.length)} world files${allWorlds ? " · about 0.25 MB each" : ""}</span>
          <button id="emStopDetail" class="em-button em-text" type="button">Stop and show what loaded</button>
        </div>`
      : "";

    const problems = [];
    if (state.stopped) problems.push("Loading was stopped, so these totals cover only the worlds already read.");
    if (state.failed.length) {
      problems.push(`${number.format(state.failed.length)} world file(s) could not be read (${escapeHtml(state.failed.slice(0, 6).join(", "))}${state.failed.length > 6 ? "…" : ""}), so their creatures are missing from these totals.`);
    }
    const warning = problems.length ? `<p class="em-partial">${problems.join(" ")}</p>` : "";

    if (!rows.length) {
      const message = state.loading
        ? "Loading every creature killed on this day…"
        : state.failed.length === state.worlds.length && state.worlds.length
          ? `The public kill-statistics files could not be loaded. Check your connection or <a href="${killStatsUrl(state.worlds[0] || "antica", state.date)}" target="_blank" rel="noopener">open a source file</a>.`
          : "No creature deaths were recorded for this selection.";
      $("#emDayDetailContent").innerHTML = `${progress}${warning}<div class="em-detail-message">${message}</div>`;
      bindStopButton();
      return;
    }

    $("#emDayDetailContent").innerHTML = `${progress}${warning}<div class="em-table-wrap"><table>
      <thead><tr>
        <th scope="col" class="em-text-cell" data-em-sort-key="name">Creature</th>
        <th scope="col" data-em-sort-key="kills">Deaths</th>
        ${allWorlds ? `<th scope="col" data-em-sort-key="worlds">Worlds</th>` : ""}
        <th scope="col" data-em-sort-key="direct">Direct GP</th>
        <th scope="col" data-em-sort-key="npc">NPC loot maximum</th>
        <th scope="col" data-em-sort-key="potential">Potential GP</th>
        <th scope="col" class="em-text-cell" data-em-sort-key="model">Model coverage</th>
      </tr></thead>
      <tbody>${sortRows("detail", rows).map(row => `<tr>
        <td class="em-text-cell">${escapeHtml(row.name)}${row.boss ? `<span class="em-tag">Boss</span>` : ""}</td>
        <td>${number.format(row.kills)}</td>
        ${allWorlds ? `<td>${number.format(row.worlds)}</td>` : ""}
        <td>${row.modeled ? number.format(row.direct) : "—"}</td>
        <td>${row.modeled ? number.format(row.npc) : "—"}</td>
        <td>${row.modeled ? number.format(row.potential) : "—"}</td>
        <td class="em-text-cell">${escapeHtml(modelCoverageLabel(row))}</td>
      </tr>`).join("")}</tbody>
    </table></div>
    <div class="em-detail-message">GP values use the same creature loot model as the daily total. Bosses and other excluded categories remain visible here but are marked outside the main series.
    ${allWorlds
      ? `Deaths come from one public kill-statistics file per world for ${state.date}.`
      : `<a href="${killStatsUrl(state.world, state.date)}" target="_blank" rel="noopener">Open source kill statistics</a>.`}</div>`;
    bindStopButton();
    const table = $("#emDayDetailContent").querySelector("table");
    bindSortHeaders(table, "detail", renderDayDetail);
    markSortHeaders(table, "detail");
  }

  function bindStopButton() {
    const button = $("#emStopDetail");
    if (button) button.addEventListener("click", stopDayDetail);
  }

  /* ------------------------------------------------------------------ sorting */

  // Sorting works on the underlying rows, not on the rows that happen to be visible,
  // so "View all" and a re-render never contradict the arrow in the header.
  const COLUMNS = {
    daily: {
      date: { type: "date", value: row => row.date },
      coverage: { type: "number", value: row => row.coverage },
      quality: { type: "text", value: row => qualityOf(row) },
      kills: { type: "number", value: row => row.kills },
      direct: { type: "number", value: row => row.direct },
      potential: { type: "number", value: row => row.potential },
      top: { type: "text", value: row => row.topName || "" }
    },
    ranking: {
      name: { type: "text", value: row => row.name },
      direct: { type: "number", value: row => row.direct },
      npc: { type: "number", value: row => row.npc },
      potential: { type: "number", value: row => row.potential },
      samples: { type: "number", value: row => row.samples },
      confidence: { type: "text", value: row => row.confidence || row.status || "" }
    },
    detail: {
      name: { type: "text", value: row => row.name },
      kills: { type: "number", value: row => row.kills },
      worlds: { type: "number", value: row => row.worlds },
      direct: { type: "number", value: row => row.direct },
      npc: { type: "number", value: row => row.npc },
      potential: { type: "number", value: row => row.potential },
      model: { type: "text", value: row => modelCoverageLabel(row) }
    }
  };

  const sortState = {
    daily: { key: "date", direction: "descending" },
    ranking: { key: "potential", direction: "descending" },
    detail: { key: "potential", direction: "descending" }
  };

  function sortRows(tableKey, rows) {
    const state = sortState[tableKey];
    const column = state && COLUMNS[tableKey][state.key];
    if (!column) return rows;
    const sign = state.direction === "ascending" ? 1 : -1;
    return [...rows].sort((left, right) => {
      const a = column.value(left);
      const b = column.value(right);
      const compared = column.type === "number"
        ? numeric(a) - numeric(b)
        : String(a).localeCompare(String(b), "en", { numeric: true, sensitivity: "base" });
      return compared ? compared * sign : 0;
    });
  }

  function markSortHeaders(table, tableKey) {
    if (!table) return;
    const state = sortState[tableKey];
    [...table.querySelectorAll("thead th")].forEach(th => {
      const key = th.dataset.emSortKey;
      if (!key) {
        th.setAttribute("aria-sort", "none");
        return;
      }
      th.setAttribute(
        "aria-sort",
        state && state.key === key ? state.direction : "none"
      );
    });
  }

  function bindSortHeaders(table, tableKey, rerender) {
    if (!table) return;
    [...table.querySelectorAll("thead th")].forEach(th => {
      const key = th.dataset.emSortKey;
      if (!key || th.dataset.emSortReady === "true") {
        if (!key) return;
        return;
      }
      th.dataset.emSortReady = "true";
      const label = th.textContent.trim();
      th.innerHTML = `<button class="em-sort-button" type="button" aria-label="Sort by ${escapeHtml(label)}">${escapeHtml(label)}</button>`;
      th.querySelector("button").addEventListener("click", () => {
        const state = sortState[tableKey];
        const numericColumn = COLUMNS[tableKey][key].type !== "text";
        sortState[tableKey] = state && state.key === key
          ? { key, direction: state.direction === "ascending" ? "descending" : "ascending" }
          // Numbers and dates are most useful largest-first; names read best A to Z.
          : { key, direction: numericColumn ? "descending" : "ascending" };
        rerender();
      });
    });
    markSortHeaders(table, tableKey);
  }

  function sortColumnLabel(tableKey) {
    const state = sortState[tableKey];
    if (!state) return "";
    const labels = {
      name: "creature name", direct: "direct GP per kill", npc: "NPC loot GP per kill",
      potential: "potential GP per kill", samples: "loot samples", confidence: "model confidence"
    };
    const direction = state.direction === "ascending" ? "lowest first" : "highest first";
    return `${labels[state.key] || state.key} · ${direction}`;
  }

  function modelCoverageLabel(row) {
    if (!row.modeled) return `Not modeled${row.status ? ` · ${row.status}` : ""}`;
    return row.included ? "Included in main series" : "Modeled · outside main series";
  }

  /* --------------------------------------------------------------- CSV inputs */

  async function loadCSV(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const rows = normalizeCSV(text);
      applyDataset(rows, datasetMeta(rows, file.name, new Date().toISOString(), "manual"));
    } catch (error) {
      showError(`Could not load CSV. ${error.message}`);
    } finally {
      event.target.value = "";
    }
  }

  function normalizeCSV(text) {
    const parsed = parseCSV(text);
    const missing = REQUIRED_CSV.filter(field => !parsed.headers.includes(field));
    if (missing.length) throw new Error(`Missing required columns: ${missing.join(", ")}`);
    const rows = parsed.rows.map(row => ({
      ...row,
      top_emission_creature_gp: numeric(row.top_emission_creature_gp),
      total_kills: numeric(row.total_kills),
      nonboss_kills: numeric(row.nonboss_kills),
      modeled_kills_nonboss: numeric(row.modeled_kills_nonboss),
      direct_coin_gp: numeric(row.direct_coin_gp),
      npc_potential_gp_max: numeric(row.npc_potential_gp_max),
      potential_total_gp_max: numeric(row.potential_total_gp_max),
      low_quality_flag: bool(row.low_quality_flag),
      partial_date_flag: bool(row.partial_date_flag),
      ev_any: bool(row.ev_any)
    }));
    if (!rows.length) throw new Error("The CSV contains no data rows.");
    if (rows.some(row => !row.world || !/^\d{4}-\d{2}-\d{2}$/.test(row.date))) {
      throw new Error("The CSV contains an invalid world or date.");
    }
    return rows;
  }

  function datasetMeta(rows, source, generatedAt, mode) {
    const dates = rows.map(row => row.date).sort();
    return {
      generatedAt, source, mode,
      worlds: new Set(rows.map(row => row.world)).size,
      worldDays: rows.length,
      minDate: dates[0],
      maxDate: dates[dates.length - 1]
    };
  }

  function applyDataset(rows, meta, preserveFilters = false) {
    const previous = {
      world: $("#emWorldSelect").value,
      start: $("#emDateStart").value,
      end: $("#emDateEnd").value,
      min: $("#emDateStart").min,
      max: $("#emDateEnd").max
    };
    rawRows = rows;
    sourceMeta = meta;
    populateWorlds(preserveFilters ? previous.world : "all");
    $("#emDateStart").min = $("#emDateEnd").min = sourceMeta.minDate;
    $("#emDateStart").max = $("#emDateEnd").max = sourceMeta.maxDate;
    if (preserveFilters) {
      $("#emDateStart").value = previous.start === previous.min
        ? sourceMeta.minDate
        : clampDate(previous.start, sourceMeta.minDate, sourceMeta.maxDate);
      $("#emDateEnd").value = previous.end === previous.max
        ? sourceMeta.maxDate
        : clampDate(previous.end, sourceMeta.minDate, sourceMeta.maxDate);
      if ($("#emDateStart").value > $("#emDateEnd").value) {
        $("#emDateStart").value = sourceMeta.minDate;
        $("#emDateEnd").value = sourceMeta.maxDate;
      }
    } else {
      $("#emDateStart").value = sourceMeta.minDate;
      $("#emDateEnd").value = sourceMeta.maxDate;
    }
    showAllRows = false;
    updateStatus();
    render();
  }

  async function refreshProjectCSV() {
    if (!["http:", "https:"].includes(location.protocol)) return;
    try {
      const response = await fetch("../data/processed/gold_emission_daily.csv", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const rows = normalizeCSV(await response.text());
      const updatedAt = response.headers.get("last-modified") || new Date().toISOString();
      applyDataset(
        rows,
        datasetMeta(rows, "data/processed/gold_emission_daily.csv", updatedAt, "project"),
        true
      );
    } catch (_) {
      sourceMeta = { ...sourceMeta, mode: "fallback" };
      updateStatus();
    }
  }

  function parseCSV(text) {
    const rows = [];
    let row = [], field = "", quoted = false;
    for (let index = 0; index < text.length; index++) {
      const char = text[index];
      if (quoted) {
        if (char === '"' && text[index + 1] === '"') { field += '"'; index++; }
        else if (char === '"') quoted = false;
        else field += char;
      } else if (char === '"') quoted = true;
      else if (char === ",") { row.push(field); field = ""; }
      else if (char === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
      else field += char;
    }
    if (field.length || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
    const headers = rows.shift() || [];
    return {
      headers,
      rows: rows.filter(values => values.some(Boolean)).map(values =>
        Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
      )
    };
  }

  function updateStatus() {
    const stamp = isoTimestamp(new Date(sourceMeta.generatedAt));
    const sourceLabel = sourceMeta.mode === "project"
      ? `project CSV refreshed ${stamp}`
      : sourceMeta.mode === "manual"
        ? `loaded CSV updated ${stamp}`
        : sourceMeta.mode === "fallback"
          ? `embedded fallback · project CSV unavailable · snapshot updated ${stamp}`
          : `embedded snapshot updated ${stamp}`;
    $("#emStatus").textContent =
      `${number.format(sourceMeta.worldDays)} world-days · ${number.format(sourceMeta.worlds)} worlds · ` +
      `${sourceMeta.minDate} to ${sourceMeta.maxDate} · ${sourceLabel}`;
  }

  function showError(message) {
    $("#emError").textContent = message;
    $("#emError").classList.add("visible");
  }

  function clearError() {
    $("#emError").classList.remove("visible");
    $("#emError").textContent = "";
  }

  window.EmissionView = { mount, mountRanking, activate, params, applyParams, refreshPrices };
})();
"""
