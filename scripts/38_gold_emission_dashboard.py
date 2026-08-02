#!/usr/bin/env python3
"""Build a self-contained interactive gold-emission dashboard."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "gold_emission_daily.csv"
PRICE_SOURCE = ROOT / "data" / "processed" / "panel_daily.csv"
CREATURE_VALUE_SOURCE = ROOT / "data" / "processed" / "creature_gold_value.csv"
OUTPUT = ROOT / "reports" / "gold_emission_dashboard.html"

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


def build_payload() -> dict[str, object]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(FIELDS) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing dashboard fields: {', '.join(missing)}")
        rows = [_compact_row(row) for row in reader]

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

    creature_fields = (
        "canonical_name", "raw_names", "loot_model_status", "is_boss",
        "included_in_main_series", "expected_direct_coin_gp_per_kill",
        "expected_npc_sale_gp_per_kill", "exclusion_reason",
    )
    with CREATURE_VALUE_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(creature_fields) - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing creature-value fields: {', '.join(missing)}")
        creature_values = [[row[field] for field in creature_fields] for row in reader]

    worlds = sorted({str(row[0]) for row in rows})
    dates = sorted({str(row[1]) for row in rows})
    return {
        "schema": list(FIELDS),
        "rows": rows,
        "priceSchema": ["world", "date", "price_gp"],
        "priceRows": price_rows,
        "creatureValueSchema": list(creature_fields),
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


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Gold Emission from Tibia Kill Statistics</title>
  <style>
    :root {
      --bg: #ffffff;
      --surface: #ffffff;
      --ink: #12203a;
      --muted: #667085;
      --line: #d8dee8;
      --line-soft: #edf0f4;
      --direct: #2467c9;
      --potential: #bc643f;
      --realized: #d39418;
      --good: #24875d;
      --warning: #b77905;
      --danger: #c43d3d;
      --focus: #1d4ed8;
      --radius: 8px;
      --shadow: 0 8px 28px rgb(18 32 58 / 8%);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-width: 320px; background: var(--bg); }
    button, input, select { font: inherit; }
    button, select, input[type="date"] { min-height: 44px; }
    button:focus-visible, select:focus-visible, input:focus-visible, summary:focus-visible {
      outline: 3px solid rgb(29 78 216 / 22%);
      outline-offset: 2px;
    }
    .app { width: min(1480px, 100%); margin: 0 auto; padding: 28px 24px 56px; }
    .topbar {
      display: flex; align-items: end; justify-content: space-between; gap: 24px;
      padding-bottom: 18px; border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: clamp(28px, 3vw, 42px); line-height: 1.08; letter-spacing: -.035em; }
    .data-status { max-width: 460px; color: var(--muted); font-size: 13px; text-align: right; line-height: 1.45; }
    .filters {
      display: grid; grid-template-columns: minmax(170px, 1fr) minmax(250px, 1.35fr) minmax(180px, .85fr) minmax(260px, 1.35fr) auto;
      gap: 16px; align-items: end; padding: 20px 0;
    }
    .field { display: grid; gap: 7px; min-width: 0; }
    .field > label, .series-summary { font-size: 13px; font-weight: 700; letter-spacing: .01em; }
    select, input[type="date"] {
      width: 100%; color: var(--ink); background: var(--surface); border: 1px solid #cbd3df;
      border-radius: 7px; padding: 0 12px;
    }
    .date-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .series-control {
      min-height: 44px; border: 1px solid #cbd3df; border-radius: 7px; padding: 6px 10px;
      display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px;
    }
    .check { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; white-space: nowrap; }
    .check input { width: 17px; height: 17px; accent-color: var(--focus); }
    .actions { display: grid; gap: 8px; }
    .button {
      border: 1px solid var(--ink); background: var(--surface); color: var(--ink); border-radius: 7px;
      padding: 0 16px; font-weight: 700; cursor: pointer; white-space: nowrap;
    }
    .button:hover { background: #f7f9fc; }
    .button.secondary { border-color: #7aa2df; color: #174ea6; }
    .button.text { border-color: transparent; color: var(--focus); min-height: 36px; }
    .metrics {
      display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--line);
      border-radius: var(--radius); overflow: hidden; margin-bottom: 16px;
    }
    .metric { padding: 17px 20px; min-width: 0; text-align: center; }
    .metric + .metric { border-left: 1px solid var(--line); }
    .metric-label { font-size: 13px; font-weight: 700; }
    .metric-value {
      display: block; margin-top: 8px; color: var(--realized); font-weight: 750;
      font-size: clamp(22px, 2.3vw, 34px); line-height: 1; font-variant-numeric: tabular-nums;
      overflow-wrap: anywhere;
    }
    .metric-meta { display: block; margin-top: 7px; color: var(--muted); font-size: 12px; }
    .main-grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, .9fr); gap: 16px; }
    .panel { border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
    .panel-inner { padding: 16px; }
    .panel h2 { margin: 0; font-size: 17px; letter-spacing: -.01em; }
    .panel-heading { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; margin-bottom: 12px; }
    .panel-note { color: var(--muted); font-size: 12px; }
    .legend { display: flex; flex-wrap: wrap; gap: 8px 20px; margin: 8px 0 0; color: #344054; font-size: 12px; }
    .legend-item { display: inline-flex; align-items: center; gap: 7px; }
    .legend-line { width: 24px; border-top: 3px solid; }
    .legend-line.potential { border-top-style: dashed; }
    .legend-line.realized { border-top-style: dotted; }
    .chart-wrap { position: relative; width: 100%; min-height: 360px; }
    #lineChart { display: block; width: 100%; height: 360px; overflow: visible; }
    .chart-tooltip {
      position: absolute; z-index: 4; min-width: 220px; max-width: 280px; pointer-events: none;
      background: rgb(255 255 255 / 97%); border: 1px solid #bac4d2; border-radius: 7px;
      box-shadow: var(--shadow); padding: 11px 12px; font-size: 12px; line-height: 1.45;
      opacity: 0; transform: translateY(4px); transition: opacity .12s ease, transform .12s ease;
    }
    .chart-tooltip.visible { opacity: 1; transform: translateY(0); }
    .tooltip-date { font-weight: 800; margin-bottom: 6px; }
    .tooltip-row { display: grid; grid-template-columns: 10px 1fr auto; gap: 7px; align-items: center; }
    .tooltip-row + .tooltip-row { margin-top: 4px; }
    .tooltip-dot { width: 8px; height: 8px; border-radius: 50%; }
    .tooltip-value { font-variant-numeric: tabular-nums; font-weight: 700; }
    .visually-hidden {
      position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important;
      margin: -1px !important; overflow: hidden !important; clip: rect(0,0,0,0) !important;
      white-space: nowrap !important; border: 0 !important;
    }
    .composition { display: grid; align-content: start; min-height: 100%; }
    .composition-total { margin-top: 24px; font-size: 12px; color: var(--muted); }
    .composition-total strong { display: block; margin-top: 4px; color: var(--ink); font-size: 25px; font-variant-numeric: tabular-nums; }
    .stack { height: 34px; display: flex; overflow: hidden; border-radius: 5px; margin: 20px 0 12px; background: var(--line-soft); }
    .stack > div { min-width: 0; transition: width .2s ease; }
    .stack-direct { background: var(--direct); }
    .stack-realized { background: var(--realized); }
    .stack-unrealized { background: var(--potential); }
    .composition-list { display: grid; gap: 14px; margin-top: 18px; }
    .composition-row { display: grid; grid-template-columns: 12px 1fr auto; gap: 9px; align-items: start; font-size: 13px; }
    .swatch { width: 11px; height: 11px; margin-top: 2px; border-radius: 2px; }
    .composition-row strong { font-variant-numeric: tabular-nums; text-align: right; }
    .composition-row small { display: block; color: var(--muted); margin-top: 3px; }
    .world-breakdown { margin-top: 16px; overflow: hidden; }
    .world-detail-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--border); }
    .world-detail { background: #fff; padding: 18px 20px; min-height: 94px; }
    .world-detail span { display: block; color: var(--muted); font-size: 12px; line-height: 1.35; }
    .world-detail strong { display: block; margin-top: 7px; color: var(--ink); font-size: 18px; line-height: 1.25; font-variant-numeric: tabular-nums; }
    .quality { margin-top: 16px; }
    .quality-header { display: flex; justify-content: space-between; gap: 12px; padding: 14px 16px 8px; }
    .quality-strip { display: flex; gap: 3px; overflow-x: auto; padding: 8px 16px 15px; }
    .quality-day {
      flex: 1 0 5px; height: 22px; min-width: 5px; border: 0; border-radius: 2px; padding: 0;
      cursor: pointer;
    }
    .quality-day.complete { background: var(--good); }
    .quality-day.partial { background: var(--warning); }
    .quality-day.low { background: var(--danger); }
    .quality-key { display: flex; flex-wrap: wrap; gap: 8px 15px; color: var(--muted); font-size: 12px; }
    .quality-key span { display: inline-flex; align-items: center; gap: 6px; }
    .key-dot { width: 8px; height: 8px; border-radius: 2px; }
    .table-panel { margin-top: 16px; }
    .table-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 15px 16px 10px; }
    .table-wrap { overflow: auto; border-top: 1px solid var(--line-soft); }
    table { width: 100%; border-collapse: collapse; min-width: 960px; font-size: 12px; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line-soft); text-align: right; white-space: nowrap; }
    th { position: sticky; top: 0; z-index: 1; background: #f8fafc; color: #344054; font-weight: 800; }
    th:first-child, td:first-child, th:nth-child(3), td:nth-child(3), th:last-child, td:last-child { text-align: left; }
    td { font-variant-numeric: tabular-nums; }
    .quality-label { display: inline-flex; align-items: center; gap: 7px; }
    .quality-label::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
    .quality-label.complete { color: var(--good); }
    .quality-label.partial { color: var(--warning); }
    .quality-label.low { color: var(--danger); }
    .table-footer { display: flex; justify-content: center; padding: 10px; }
    .date-drill {
      border: 0; background: transparent; color: var(--focus); font-weight: 800;
      padding: 5px 2px; min-height: 32px; cursor: pointer; text-decoration: underline;
      text-decoration-thickness: 1px; text-underline-offset: 3px;
    }
    .creature-detail { margin-top: 16px; overflow: hidden; }
    .creature-detail[hidden] { display: none; }
    .creature-detail .table-head { align-items: start; }
    .creature-detail table { min-width: 1120px; }
    .detail-message { padding: 24px 16px; color: var(--muted); line-height: 1.5; }
    .detail-summary { color: var(--muted); font-size: 12px; margin-top: 5px; }
    .empty { padding: 72px 20px; text-align: center; color: var(--muted); }
    .error {
      margin: 0 0 16px; border-left: 4px solid var(--danger); background: #fff6f6;
      color: #8f2525; padding: 12px 14px; display: none;
    }
    .error.visible { display: block; }
    .footnote { margin: 18px 2px 0; color: var(--muted); font-size: 12px; line-height: 1.5; }
    @media (max-width: 1080px) {
      .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .actions { grid-column: 1 / -1; display: flex; }
      .main-grid { grid-template-columns: 1fr; }
      .composition { min-height: auto; }
    }
    @media (max-width: 680px) {
      .app { padding: 20px 14px 40px; }
      .topbar { display: block; }
      .data-status { text-align: left; margin-top: 10px; }
      .filters { grid-template-columns: 1fr 1fr; gap: 14px 10px; }
      .field.series-field { grid-column: 1 / -1; }
      .series-control { display: grid; grid-template-columns: 1fr 1fr; }
      .actions { display: grid; grid-column: 1 / -1; }
      .metrics { grid-template-columns: 1fr 1fr; border: 0; gap: 10px; overflow: visible; }
      .metric { border: 1px solid var(--line); border-radius: var(--radius); text-align: left; padding: 14px; }
      .metric + .metric { border-left: 1px solid var(--line); }
      .metric-value { font-size: clamp(21px, 7vw, 30px); }
      .chart-wrap, #lineChart { min-height: 330px; height: 330px; }
      .legend { gap: 7px 13px; }
      .quality-header { display: block; }
      .world-detail-grid { grid-template-columns: 1fr 1fr; }
      .quality-key { margin-top: 8px; }
      .quality-day { flex-basis: 9px; min-width: 9px; }
      .table-head { align-items: start; }
    }
    @media (max-width: 430px) {
      .date-pair { grid-template-columns: 1fr; }
      .series-control { grid-template-columns: 1fr; }
      .metric { min-height: 122px; }
      .chart-tooltip { min-width: 190px; max-width: 230px; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
    }
    @media print {
      .filters, .actions, .table-footer, .visually-hidden { display: none !important; }
      .app { width: 100%; padding: 0; }
      .panel, .metrics { break-inside: avoid; }
      .table-wrap { overflow: visible; }
    }
  </style>
</head>
<body>
  <main class="app">
    <header class="topbar">
      <h1>Gold Emission from Tibia Kill Statistics</h1>
      <div id="dataStatus" class="data-status" aria-live="polite"></div>
    </header>

    <section class="filters" aria-label="Dashboard filters">
      <div class="field">
        <label for="worldSelect">World</label>
        <select id="worldSelect"></select>
      </div>
      <div class="field">
        <label for="dateStart">Date range</label>
        <div class="date-pair">
          <input id="dateStart" type="date" aria-label="Start date">
          <input id="dateEnd" type="date" aria-label="End date">
        </div>
      </div>
      <div class="field">
        <label for="scenarioSelect">Realization scenario</label>
        <select id="scenarioSelect">
          <option value="0.25">25% realization</option>
          <option value="0.5" selected>50% realization</option>
          <option value="0.75">75% realization</option>
          <option value="1">100% realization</option>
        </select>
      </div>
      <div class="field series-field">
        <div class="series-summary">Series</div>
        <div class="series-control" role="group" aria-label="Visible chart series">
          <label class="check"><input type="checkbox" data-series="direct" checked> Direct GP drops</label>
          <label class="check"><input type="checkbox" data-series="potential" checked> Potential GP maximum</label>
          <label class="check"><input type="checkbox" data-series="realized" checked> Realized GP estimate</label>
          <label class="check"><input id="tcPriceToggle" type="checkbox"> TC price (GP/TC)</label>
        </div>
      </div>
      <div class="actions">
        <button id="loadButton" class="button" type="button">Load updated CSV</button>
        <button id="resetButton" class="button secondary" type="button">Reset filters</button>
        <input id="fileInput" type="file" accept=".csv,text/csv" hidden>
      </div>
    </section>

    <div id="errorBox" class="error" role="alert"></div>

    <section class="metrics" aria-label="Summary metrics">
      <div class="metric">
        <span class="metric-label">Total estimated</span>
        <strong id="totalMetric" class="metric-value">—</strong>
        <span id="totalMeta" class="metric-meta">—</span>
      </div>
      <div class="metric">
        <span class="metric-label">Daily average</span>
        <strong id="averageMetric" class="metric-value">—</strong>
        <span class="metric-meta">GP per day</span>
      </div>
      <div class="metric">
        <span class="metric-label">Peak day</span>
        <strong id="peakMetric" class="metric-value">—</strong>
        <span id="peakMeta" class="metric-meta">—</span>
      </div>
      <div class="metric">
        <span class="metric-label">Coverage</span>
        <strong id="coverageMetric" class="metric-value">—</strong>
        <span id="coverageMeta" class="metric-meta">—</span>
      </div>
    </section>

    <section id="worldBreakdown" class="panel world-breakdown" hidden></section>

    <section class="main-grid">
      <article class="panel">
        <div class="panel-inner">
          <div class="panel-heading">
            <h2>Emission over time</h2>
            <span class="panel-note">Emission uses the left axis · TC price uses the right axis</span>
          </div>
          <div id="chartLegend" class="legend" aria-hidden="true"></div>
          <div class="chart-wrap">
            <svg id="lineChart" role="img" aria-labelledby="chartTitle chartDescription">
              <title id="chartTitle">Gold emission over time</title>
              <desc id="chartDescription">Daily gold emission and, when selected, Tibia Coin price in GP per TC for the selected world and dates.</desc>
            </svg>
            <div id="chartTooltip" class="chart-tooltip"></div>
            <label class="visually-hidden" for="chartInspector">Inspect chart by date</label>
            <input id="chartInspector" class="visually-hidden" type="range" min="0" max="0" value="0">
          </div>
        </div>
      </article>

      <article class="panel composition">
        <div class="panel-inner">
          <div class="panel-heading">
            <h2>Emission composition</h2>
          </div>
          <div class="composition-total">
            Potential GP maximum in selected period
            <strong id="potentialTotal">—</strong>
          </div>
          <div id="compositionStack" class="stack" aria-label="Composition of maximum potential emission">
            <div class="stack-direct"></div>
            <div class="stack-realized"></div>
            <div class="stack-unrealized"></div>
          </div>
          <div id="compositionList" class="composition-list"></div>
          <p class="panel-note">
            Direct GP drops are always realized. The selected scenario applies only to NPC-sellable loot.
            GP means gold pieces; Tibia Coins are labeled TC and are not part of these emission totals.
          </p>
        </div>
      </article>
    </section>

    <section class="panel quality" aria-labelledby="qualityTitle">
      <div class="quality-header">
        <h2 id="qualityTitle">Coverage by date</h2>
        <div class="quality-key" aria-label="Coverage quality legend">
          <span><i class="key-dot" style="background:var(--good)"></i> Complete</span>
          <span><i class="key-dot" style="background:var(--warning)"></i> Partial</span>
          <span><i class="key-dot" style="background:var(--danger)"></i> Low quality</span>
        </div>
      </div>
      <div id="qualityStrip" class="quality-strip"></div>
    </section>

    <section class="panel table-panel" aria-labelledby="tableTitle">
      <div class="table-head">
        <div>
          <h2 id="tableTitle">Daily detail</h2>
          <span id="tableCount" class="panel-note"></span>
        </div>
        <button id="tableToggle" class="button text" type="button">View all</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Coverage</th>
              <th scope="col">Quality</th>
              <th scope="col">Daily kills</th>
              <th scope="col">Direct GP drops</th>
              <th scope="col">Potential GP maximum</th>
              <th id="realizedHeader" scope="col">Realized GP estimate</th>
              <th scope="col">Top emitter</th>
            </tr>
          </thead>
          <tbody id="detailBody"></tbody>
        </table>
      </div>
      <div class="table-footer">
        <button id="tableToggleBottom" class="button text" type="button">View all</button>
      </div>
    </section>

    <section id="creatureDetail" class="panel creature-detail" aria-labelledby="creatureDetailTitle" hidden>
      <div class="table-head">
        <div>
          <h2 id="creatureDetailTitle">Creature detail</h2>
          <p id="creatureDetailSummary" class="detail-summary"></p>
        </div>
        <button id="closeCreatureDetail" class="button text" type="button">Close</button>
      </div>
      <div id="creatureDetailContent" aria-live="polite"></div>
    </section>

    <p class="footnote">
      Source: reconstructed creature loot values joined to Tibia world kill statistics. Player-market values are zero.
      “Potential GP maximum” assumes all modeled NPC-sellable loot is collected and sold; realized scenarios apply only to that NPC component.
      GP means Tibia gold pieces. TC means Tibia Coins; no TC are counted as generated gold.
      Boss emissions remain excluded from the primary series.
    </p>
  </main>

  <script>
  "use strict";
  const EMBEDDED = __DATA__;
  const SCHEMA = EMBEDDED.schema;
  const COLORS = { direct: "#2467c9", potential: "#bc643f", realized: "#d39418", tcPrice: "#7c3aed" };
  const SERIES = {
    direct: { label: "Direct GP drops", color: COLORS.direct, dash: "" },
    potential: { label: "Potential GP maximum", color: COLORS.potential, dash: "8 6" },
    realized: { label: "Realized GP estimate", color: COLORS.realized, dash: "3 5" }
  };
  const REQUIRED_CSV = [
    "world", "date", "top_emission_creature_name", "top_emission_creature_gp",
    "total_kills", "nonboss_kills", "modeled_kills_nonboss", "direct_coin_gp",
    "npc_potential_gp_max", "potential_total_gp_max", "low_quality_flag",
    "partial_date_flag", "ev_any"
  ];
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });
  const NS = "http://www.w3.org/2000/svg";

  let rawRows = decodeRows(EMBEDDED.schema, EMBEDDED.rows);
  const rawPriceRows = decodeRows(EMBEDDED.priceSchema, EMBEDDED.priceRows);
  const creatureValueRows = decodeRows(EMBEDDED.creatureValueSchema, EMBEDDED.creatureValues);
  let priceByWorldDate = new Map();
  let priceByDateMedian = new Map();
  let creatureValueMap = new Map();
  let sourceMeta = EMBEDDED.meta;
  let filtered = [];
  let showAllRows = false;

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

  function toDate(value) {
    return new Date(`${value}T00:00:00Z`);
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

  function qualityOf(row) {
    if (row.partial) return "partial";
    if (row.low || row.coverage < 0.8) return "low";
    return "complete";
  }

  function initialize() {
    rebuildPriceIndexes();
    rebuildCreatureValueIndex();
    populateWorlds();
    const params = new URLSearchParams(location.search);
    const dates = rawRows.map(row => row.date).sort();
    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];
    $("#dateStart").min = $("#dateEnd").min = minDate;
    $("#dateStart").max = $("#dateEnd").max = maxDate;
    $("#dateStart").value = validDate(params.get("start"), minDate, maxDate) || minDate;
    $("#dateEnd").value = validDate(params.get("end"), minDate, maxDate) || maxDate;
    const requestedWorld = params.get("world");
    if (requestedWorld && [...$("#worldSelect").options].some(option => option.value === requestedWorld)) {
      $("#worldSelect").value = requestedWorld;
    }
    const requestedScenario = params.get("scenario");
    if ([...$("#scenarioSelect").options].some(option => option.value === requestedScenario)) {
      $("#scenarioSelect").value = requestedScenario;
    }
    const requestedSeries = params.get("series");
    if (requestedSeries) {
      const selected = new Set(requestedSeries.split(","));
      $$("[data-series]").forEach(input => { input.checked = selected.has(input.dataset.series); });
      if (!$$("[data-series]:checked").length) $("[data-series='realized']").checked = true;
    }
    $("#tcPriceToggle").checked = params.get("tcPrice") === "1";
    bindEvents();
    updateStatus();
    render();
  }

  function populateWorlds(preserve = "all") {
    const worlds = [...new Set(rawRows.map(row => row.world))].sort((a, b) => a.localeCompare(b));
    $("#worldSelect").innerHTML = `<option value="all">All worlds</option>` +
      worlds.map(world => `<option value="${escapeHtml(world)}">${escapeHtml(world)}</option>`).join("");
    $("#worldSelect").value = worlds.includes(preserve) ? preserve : "all";
  }

  function validDate(value, min, max) {
    return value && value >= min && value <= max ? value : "";
  }

  function clampDate(value, min, max) {
    if (!value || value < min) return min;
    if (value > max) return max;
    return value;
  }

  function bindEvents() {
    ["#worldSelect", "#dateStart", "#dateEnd"].forEach(selector => {
      $(selector).addEventListener("change", () => { closeCreatureDetail(); render(); });
    });
    $("#scenarioSelect").addEventListener("change", () => {
      closeCreatureDetail();
      render();
    });
    $$("[data-series]").forEach(input => input.addEventListener("change", () => {
      if (!$$("[data-series]:checked").length) input.checked = true;
      render();
    }));
    $("#tcPriceToggle").addEventListener("change", render);
    $("#resetButton").addEventListener("click", resetFilters);
    $("#loadButton").addEventListener("click", () => $("#fileInput").click());
    $("#fileInput").addEventListener("change", loadCSV);
    $("#tableToggle").addEventListener("click", toggleTable);
    $("#tableToggleBottom").addEventListener("click", toggleTable);
    $("#closeCreatureDetail").addEventListener("click", closeCreatureDetail);
    $("#chartInspector").addEventListener("input", event => showTooltipAt(Number(event.target.value), true));
    window.addEventListener("resize", debounce(() => renderChart(filtered), 100));
  }

  function resetFilters() {
    $("#worldSelect").value = "all";
    $("#dateStart").value = $("#dateStart").min;
    $("#dateEnd").value = $("#dateEnd").max;
    $("#scenarioSelect").value = "0.5";
    $$("[data-series]").forEach(input => { input.checked = true; });
    $("#tcPriceToggle").checked = false;
    showAllRows = false;
    render();
  }

  function selectedSeries() {
    return $$("[data-series]:checked").map(input => input.dataset.series);
  }

  function rebuildPriceIndexes() {
    priceByWorldDate = new Map();
    const valuesByDate = new Map();
    for (const row of rawPriceRows) {
      const value = numeric(row.price_gp);
      if (!value) continue;
      priceByWorldDate.set(`${row.world}|${row.date}`, value);
      if (!valuesByDate.has(row.date)) valuesByDate.set(row.date, []);
      valuesByDate.get(row.date).push(value);
    }
    priceByDateMedian = new Map([...valuesByDate].map(([date, values]) => {
      values.sort((a, b) => a - b);
      const middle = Math.floor(values.length / 2);
      const median = values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
      return [date, median];
    }));
  }

  function normalizedCreatureName(value) {
    return String(value || "").trim().toLocaleLowerCase("en-US").replace(/\s+/g, " ");
  }

  function rebuildCreatureValueIndex() {
    creatureValueMap = new Map();
    for (const row of creatureValueRows) {
      const names = [row.canonical_name, ...String(row.raw_names || "").split(" | ")];
      for (const name of names) creatureValueMap.set(normalizedCreatureName(name), row);
    }
  }

  function aggregateRows() {
    const world = $("#worldSelect").value;
    const start = $("#dateStart").value;
    const end = $("#dateEnd").value;
    const selected = rawRows.filter(row =>
      (world === "all" || row.world === world) && row.date >= start && row.date <= end
    );
    const byDate = new Map();
    for (const row of selected) {
      const current = byDate.get(row.date) || {
        date: row.date, kills: 0, nonboss: 0, modeled: 0, direct: 0, npc: 0,
        potential: 0, low: false, partial: false, event: false,
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
      if (numeric(row.top_emission_creature_gp) > current.topGp) {
        current.topGp = numeric(row.top_emission_creature_gp);
        current.topName = row.top_emission_creature_name || "—";
        current.topWorld = row.world;
      }
      byDate.set(row.date, current);
    }
    const scenario = numeric($("#scenarioSelect").value);
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date)).map(row => ({
      ...row,
      potential: row.direct + row.npc,
      realized: row.direct + scenario * row.npc,
      coverage: row.nonboss > 0 ? row.modeled / row.nonboss : 0,
      tcPrice: world === "all"
        ? numeric(priceByDateMedian.get(row.date))
        : numeric(priceByWorldDate.get(`${world}|${row.date}`))
    }));
  }

  function render() {
    clearError();
    if ($("#dateStart").value > $("#dateEnd").value) {
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
    updateURL();
    updateMetrics(filtered);
    renderLegend();
    renderChart(filtered);
    renderComposition(filtered);
    renderWorldBreakdown(filtered);
    renderQuality(filtered);
    renderTable(filtered);
  }

  function updateMetrics(rows) {
    if (!rows.length) {
      ["#totalMetric", "#averageMetric", "#peakMetric", "#coverageMetric"].forEach(id => $(id).textContent = "—");
      $("#totalMeta").textContent = "No observations";
      $("#peakMeta").textContent = "—";
      $("#coverageMeta").textContent = "0 days";
      return;
    }
    const total = sum(rows, "realized");
    const peak = rows.reduce((best, row) => row.realized > best.realized ? row : best, rows[0]);
    const nonboss = sum(rows, "nonboss");
    const modeled = sum(rows, "modeled");
    $("#totalMetric").textContent = metricCompact(total);
    $("#totalMetric").title = `${number.format(total)} GP`;
    $("#totalMeta").textContent = `${number.format(total)} GP · ${scenarioLabel()}`;
    $("#averageMetric").textContent = metricCompact(total / rows.length);
    $("#averageMetric").title = `${number.format(total / rows.length)} GP per day`;
    $("#peakMetric").textContent = metricCompact(peak.realized);
    $("#peakMetric").title = `${number.format(peak.realized)} GP`;
    $("#peakMeta").textContent = isoDate(peak.date);
    $("#coverageMetric").textContent = percent.format(nonboss ? modeled / nonboss : 0);
    $("#coverageMeta").textContent = `${rows.length} observed days`;
  }

  function renderLegend() {
    const emissionLegend = selectedSeries().map(key =>
      `<span class="legend-item"><i class="legend-line ${key}" style="border-color:${SERIES[key].color}"></i>${SERIES[key].label}${key === "realized" ? ` (${scenarioPercent()})` : ""}</span>`
    ).join("");
    const priceLegend = $("#tcPriceToggle").checked
      ? `<span class="legend-item"><i class="legend-line" style="border-color:${COLORS.tcPrice}"></i>TC price (GP/TC) · right axis</span>`
      : "";
    $("#chartLegend").innerHTML = emissionLegend + priceLegend;
  }

  function renderChart(rows) {
    const svg = $("#lineChart");
    svg.innerHTML = `<title id="chartTitle">Gold emission over time</title>
      <desc id="chartDescription">Daily gold emission and, when selected, Tibia Coin price in GP per TC for the selected world and dates.</desc>`;
    $("#chartTooltip").classList.remove("visible");
    if (!rows.length) {
      svg.setAttribute("viewBox", "0 0 800 360");
      addSVG(svg, "text", { x: 400, y: 180, "text-anchor": "middle", fill: "#667085", "font-size": 14 }, "No observations for this selection");
      return;
    }
    const keys = selectedSeries();
    const showTcPrice = $("#tcPriceToggle").checked;
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
    const tickIndexes = uniqueIndexes(tickCount, rows.length);
    for (const index of tickIndexes) {
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
        d: pricePath, fill: "none", stroke: COLORS.tcPrice, "stroke-width": 2.8,
        "stroke-linecap": "round", "stroke-linejoin": "round",
        "vector-effect": "non-scaling-stroke"
      });
    }

    const crosshair = addSVG(svg, "line", {
      id: "crosshair", x1: margin.left, x2: margin.left, y1: margin.top, y2: margin.top + innerHeight,
      stroke: "#344054", "stroke-width": 1, opacity: 0
    });
    const dots = {};
    for (const key of keys) {
      dots[key] = addSVG(svg, "circle", {
        id: `dot-${key}`, cx: margin.left, cy: margin.top, r: 4.5,
        fill: SERIES[key].color, stroke: "#fff", "stroke-width": 2, opacity: 0
      });
    }
    if (showTcPrice && tcPrices.length) {
      dots.tcPrice = addSVG(svg, "circle", {
        id: "dot-tc-price", cx: margin.left, cy: margin.top, r: 4.5,
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
      showTooltipAt(index, false, { x, y, yPrice, margin, width, height, crosshair, dots, rows, keys, showTcPrice });
    });
    capture.addEventListener("pointerdown", event => capture.setPointerCapture?.(event.pointerId));
    capture.addEventListener("pointerleave", hideTooltip);
    capture.addEventListener("blur", hideTooltip);
    capture.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let index = Number($("#chartInspector").value || 0);
      if (event.key === "ArrowLeft") index--;
      if (event.key === "ArrowRight") index++;
      if (event.key === "Home") index = 0;
      if (event.key === "End") index = rows.length - 1;
      index = Math.max(0, Math.min(rows.length - 1, index));
      $("#chartInspector").value = index;
      showTooltipAt(index, true);
    });
    svg._chart = { x, y, yPrice, margin, width, height, crosshair, dots, rows, keys, showTcPrice };
    $("#chartInspector").max = rows.length - 1;
    $("#chartInspector").value = 0;
  }

  function showTooltipAt(index, fromKeyboard = false, chartState = null) {
    const state = chartState || $("#lineChart")._chart;
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
    $("#chartInspector").value = index;
    const tooltip = $("#chartTooltip");
    tooltip.innerHTML = `<div class="tooltip-date">${isoDate(row.date)}</div>` +
      keys.map(key => `<div class="tooltip-row"><i class="tooltip-dot" style="background:${SERIES[key].color}"></i><span>${SERIES[key].label}${key === "realized" ? ` (${scenarioPercent()})` : ""}</span><span class="tooltip-value">${number.format(row[key])} GP</span></div>`).join("") +
      (showTcPrice ? `<div class="tooltip-row"><i class="tooltip-dot" style="background:${COLORS.tcPrice}"></i><span>TC price</span><span class="tooltip-value">${row.tcPrice ? `${number.format(row.tcPrice)} GP/TC` : "No price data"}</span></div>` : "") +
      `<div class="tooltip-row" style="margin-top:7px"><i></i><span>Coverage</span><span class="tooltip-value">${percent.format(row.coverage)}</span></div>`;
    const chartWidth = $(".chart-wrap").clientWidth;
    const scaledX = xx / width * chartWidth;
    tooltip.style.left = `${Math.min(Math.max(6, scaledX + 12), chartWidth - 290)}px`;
    tooltip.style.top = `${Math.max(8, margin.top + 8)}px`;
    tooltip.classList.add("visible");
    if (fromKeyboard) {
      $("#chartInspector").setAttribute("aria-valuetext", `${isoDate(row.date)}: realized ${number.format(row.realized)} GP${showTcPrice && row.tcPrice ? `; TC price ${number.format(row.tcPrice)} GP per TC` : ""}`);
    }
  }

  function hideTooltip() {
    const state = $("#lineChart")._chart;
    if (state) {
      state.crosshair.setAttribute("opacity", 0);
      Object.values(state.dots).forEach(dot => dot.setAttribute("opacity", 0));
    }
    $("#chartTooltip").classList.remove("visible");
  }

  function renderComposition(rows) {
    const direct = sum(rows, "direct");
    const npc = sum(rows, "npc");
    const rate = numeric($("#scenarioSelect").value);
    const realizedNpc = npc * rate;
    const unrealizedNpc = npc - realizedNpc;
    const potential = direct + npc;
    $("#potentialTotal").textContent = `${number.format(potential)} GP`;
    const segments = [
      { key: "direct", label: "Direct GP drops", value: direct, color: COLORS.direct },
      { key: "realized", label: `Realized NPC loot (${scenarioPercent()})`, value: realizedNpc, color: COLORS.realized },
      { key: "unrealized", label: "Unrealized NPC potential", value: unrealizedNpc, color: COLORS.potential }
    ];
    const stackParts = $("#compositionStack").children;
    segments.forEach((segment, index) => {
      stackParts[index].style.width = `${potential ? segment.value / potential * 100 : 0}%`;
      stackParts[index].title = `${segment.label}: ${number.format(segment.value)} GP`;
    });
    $("#compositionList").innerHTML = segments.map(segment =>
      `<div class="composition-row">
        <i class="swatch" style="background:${segment.color}"></i>
        <span>${segment.label}<small>${potential ? percent.format(segment.value / potential) : "0%"}</small></span>
        <strong>${number.format(segment.value)} GP</strong>
      </div>`
    ).join("");
    $("#compositionStack").setAttribute("aria-label", segments.map(segment =>
      `${segment.label} ${potential ? percent.format(segment.value / potential) : "0%"}`
    ).join(", "));
  }

  function renderWorldBreakdown(rows) {
    const host = $("#worldBreakdown");
    const world = $("#worldSelect").value;
    if (world === "all" || !rows.length) {
      host.hidden = true;
      host.innerHTML = "";
      return;
    }
    const kills = sum(rows, "kills");
    const direct = sum(rows, "direct");
    const npc = sum(rows, "npc");
    const realizedNpc = npc * numeric($("#scenarioSelect").value);
    const nonboss = sum(rows, "nonboss");
    const modeled = sum(rows, "modeled");
    const flagged = rows.filter(row => qualityOf(row) !== "complete").length;
    const top = rows.reduce((best, row) => row.topGp > best.topGp ? row : best, rows[0]);
    host.innerHTML = `<div class="panel-inner">
      <div class="panel-heading"><div><h2>What generated GP in ${escapeHtml(world)}</h2><p class="panel-note">Details for the selected dates. The NPC-loot estimate changes with the chosen realization scenario.</p></div></div>
      <div class="world-detail-grid">
        <div class="world-detail"><span>Creature deaths recorded</span><strong>${number.format(kills)}</strong></div>
        <div class="world-detail"><span>GP dropped directly by creatures</span><strong>${number.format(direct)} GP</strong></div>
        <div class="world-detail"><span>Estimated GP from selling loot to NPCs</span><strong>${number.format(realizedNpc)} GP</strong></div>
        <div class="world-detail"><span>Largest creature source on one day</span><strong>${escapeHtml(top.topName || "—")}</strong><span>${isoDate(top.date)} · ${number.format(top.topGp)} GP</span></div>
        <div class="world-detail"><span>Deaths covered by the GP model</span><strong>${percent.format(nonboss ? modeled / nonboss : 0)}</strong></div>
        <div class="world-detail"><span>Days needing extra caution</span><strong>${number.format(flagged)} of ${number.format(rows.length)}</strong></div>
      </div>
    </div>`;
    host.hidden = false;
  }

  function renderQuality(rows) {
    const strip = $("#qualityStrip");
    strip.innerHTML = rows.map((row, index) => {
      const quality = qualityOf(row);
      const label = `${isoDate(row.date)}: ${quality}, ${percent.format(row.coverage)} coverage`;
      return `<button class="quality-day ${quality}" data-index="${index}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"></button>`;
    }).join("");
    strip.querySelectorAll(".quality-day").forEach(button => {
      button.addEventListener("click", () => {
        const index = Number(button.dataset.index);
        showTooltipAt(index, true);
        $(".chart-wrap").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
      });
    });
  }

  function renderTable(rows) {
    const ordered = [...rows].reverse();
    const visible = showAllRows ? ordered : ordered.slice(0, 30);
    $("#realizedHeader").textContent = `Realized GP estimate (${scenarioPercent()})`;
    $("#detailBody").innerHTML = visible.map(row => {
      const quality = qualityOf(row);
      const qualityLabel = quality === "low" ? "Low quality" : quality[0].toUpperCase() + quality.slice(1);
      const topEmitter = $("#worldSelect").value === "all" ? `${row.topName} · ${row.topWorld}` : row.topName;
      return `<tr>
        <td><button class="date-drill" type="button" data-detail-date="${isoDate(row.date)}" aria-label="Open creature details for ${isoDate(row.date)}">${isoDate(row.date)}</button></td>
        <td>${percent.format(row.coverage)}</td>
        <td><span class="quality-label ${quality}">${qualityLabel}</span></td>
        <td>${number.format(row.kills)}</td>
        <td>${number.format(row.direct)}</td>
        <td>${number.format(row.potential)}</td>
        <td>${number.format(row.realized)}</td>
        <td>${escapeHtml(topEmitter || "—")}</td>
      </tr>`;
    }).join("");
    $$("[data-detail-date]").forEach(button => button.addEventListener("click", () => {
      openCreatureDetail(button.dataset.detailDate);
    }));
    $("#tableCount").textContent = `${number.format(rows.length)} observed days`;
    const toggleLabel = showAllRows ? "Show latest 30" : `View all ${number.format(rows.length)}`;
    $("#tableToggle").textContent = $("#tableToggleBottom").textContent = toggleLabel;
    $("#tableToggle").hidden = $("#tableToggleBottom").hidden = rows.length <= 30;
  }

  function toggleTable() {
    showAllRows = !showAllRows;
    renderTable(filtered);
  }

  function closeCreatureDetail() {
    const host = $("#creatureDetail");
    host.hidden = true;
    $("#creatureDetailContent").innerHTML = "";
  }

  async function openCreatureDetail(date) {
    const world = $("#worldSelect").value;
    const host = $("#creatureDetail");
    host.hidden = false;
    $("#creatureDetailTitle").textContent = `Creature detail · ${date}`;
    if (world === "all") {
      $("#creatureDetailSummary").textContent = "Choose one world first; the daily row currently combines all worlds.";
      $("#creatureDetailContent").innerHTML = `<div class="detail-message">Select a specific server in the World filter, then click the date again to see every creature killed there.</div>`;
      host.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      return;
    }
    $("#creatureDetailSummary").textContent = `${world} · ${date} · loading source kill statistics…`;
    $("#creatureDetailContent").innerHTML = `<div class="detail-message">Loading every creature killed on this day…</div>`;
    host.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    const sourceUrl = `https://raw.githubusercontent.com/tibiamaps/tibia-kill-stats/main/data/${encodeURIComponent(world.toLocaleLowerCase("en-US"))}/${date}.json`;
    try {
      const response = await fetch(sourceUrl, { cache: "force-cache" });
      if (!response.ok) throw new Error(`source returned HTTP ${response.status}`);
      const payload = await response.json();
      const stats = payload.killstatistics || payload;
      const entries = Array.isArray(stats.entries) ? stats.entries : [];
      const scenario = numeric($("#scenarioSelect").value);
      const details = entries.map(entry => {
        const name = String(entry.race || "").trim();
        const kills = numeric(entry.last_day_killed);
        if (!name || kills <= 0) return null;
        const model = creatureValueMap.get(normalizedCreatureName(name));
        const directPerKill = model ? numeric(model.expected_direct_coin_gp_per_kill) : 0;
        const npcPerKill = model ? numeric(model.expected_npc_sale_gp_per_kill) : 0;
        const modeled = Boolean(model) && (model.loot_model_status === "complete" || directPerKill > 0 || npcPerKill > 0);
        return {
          name, kills, modeled,
          direct: directPerKill * kills,
          npc: npcPerKill * kills,
          realized: (directPerKill + scenario * npcPerKill) * kills,
          included: model ? bool(model.included_in_main_series) : false,
          boss: model ? bool(model.is_boss) : false,
          status: model?.exclusion_reason || model?.loot_model_status || "No GP model"
        };
      }).filter(Boolean).sort((a, b) => b.realized - a.realized || b.kills - a.kills || a.name.localeCompare(b.name));
      renderCreatureDetail(world, date, details, sourceUrl);
    } catch (error) {
      $("#creatureDetailSummary").textContent = `${world} · ${date}`;
      $("#creatureDetailContent").innerHTML = `<div class="detail-message">The detailed public kill-statistics file could not be loaded. Check your connection or <a href="${sourceUrl}" target="_blank" rel="noopener">open the source file</a>. ${escapeHtml(error.message)}</div>`;
    }
  }

  function renderCreatureDetail(world, date, rows, sourceUrl) {
    const modeledRows = rows.filter(row => row.modeled);
    const totalKills = rows.reduce((total, row) => total + row.kills, 0);
    const realized = modeledRows.reduce((total, row) => total + row.realized, 0);
    $("#creatureDetailSummary").textContent =
      `${world} · ${date} · ${number.format(rows.length)} creature types · ${number.format(totalKills)} deaths · ${number.format(realized)} modeled GP at ${scenarioPercent()} realization`;
    if (!rows.length) {
      $("#creatureDetailContent").innerHTML = `<div class="detail-message">No creature deaths were recorded for this world and date.</div>`;
      return;
    }
    $("#creatureDetailContent").innerHTML = `<div class="table-wrap"><table>
      <thead><tr>
        <th scope="col">Creature</th>
        <th scope="col">Deaths</th>
        <th scope="col">Direct GP drops</th>
        <th scope="col">NPC loot maximum</th>
        <th scope="col">Realized GP estimate (${scenarioPercent()})</th>
        <th scope="col">Model coverage</th>
      </tr></thead>
      <tbody>${rows.map(row => `<tr>
        <td>${escapeHtml(row.name)}${row.boss ? " · Boss" : ""}</td>
        <td>${number.format(row.kills)}</td>
        <td>${row.modeled ? number.format(row.direct) : "—"}</td>
        <td>${row.modeled ? number.format(row.npc) : "—"}</td>
        <td>${row.modeled ? number.format(row.realized) : "—"}</td>
        <td>${row.modeled ? (row.included ? "Included in main series" : `Modeled · outside main series`) : `Not modeled${row.status ? ` · ${escapeHtml(row.status)}` : ""}`}</td>
      </tr>`).join("")}</tbody>
    </table></div>
    <div class="detail-message">GP values use the same creature loot model as the daily total. Bosses and other excluded categories remain visible here but are marked outside the main series. <a href="${sourceUrl}" target="_blank" rel="noopener">Open source kill statistics</a>.</div>`;
  }

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
      world: $("#worldSelect").value,
      start: $("#dateStart").value,
      end: $("#dateEnd").value,
      min: $("#dateStart").min,
      max: $("#dateEnd").max
    };
    rawRows = rows;
    sourceMeta = meta;
    populateWorlds(preserveFilters ? previous.world : "all");
    $("#dateStart").min = $("#dateEnd").min = sourceMeta.minDate;
    $("#dateStart").max = $("#dateEnd").max = sourceMeta.maxDate;
    if (preserveFilters) {
      $("#dateStart").value = previous.start === previous.min
        ? sourceMeta.minDate
        : clampDate(previous.start, sourceMeta.minDate, sourceMeta.maxDate);
      $("#dateEnd").value = previous.end === previous.max
        ? sourceMeta.maxDate
        : clampDate(previous.end, sourceMeta.minDate, sourceMeta.maxDate);
      if ($("#dateStart").value > $("#dateEnd").value) {
        $("#dateStart").value = sourceMeta.minDate;
        $("#dateEnd").value = sourceMeta.maxDate;
      }
    } else {
      $("#dateStart").value = sourceMeta.minDate;
      $("#dateEnd").value = sourceMeta.maxDate;
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
    const generated = new Date(sourceMeta.generatedAt);
    const stamp = isoTimestamp(generated);
    const sourceLabel = sourceMeta.mode === "project"
      ? `project CSV refreshed ${stamp}`
      : sourceMeta.mode === "manual"
        ? `loaded CSV updated ${stamp}`
        : sourceMeta.mode === "fallback"
          ? `embedded fallback · project CSV unavailable · snapshot updated ${stamp}`
          : `embedded snapshot updated ${stamp}`;
    $("#dataStatus").textContent =
      `${number.format(sourceMeta.worldDays)} world-days · ${number.format(sourceMeta.worlds)} worlds · ` +
      `${sourceMeta.minDate} to ${sourceMeta.maxDate} · ${sourceLabel}`;
  }

  function updateURL() {
    const params = new URLSearchParams();
    if ($("#worldSelect").value !== "all") params.set("world", $("#worldSelect").value);
    if ($("#dateStart").value !== $("#dateStart").min) params.set("start", $("#dateStart").value);
    if ($("#dateEnd").value !== $("#dateEnd").max) params.set("end", $("#dateEnd").value);
    if ($("#scenarioSelect").value !== "0.5") params.set("scenario", $("#scenarioSelect").value);
    if ($("#tcPriceToggle").checked) params.set("tcPrice", "1");
    const series = selectedSeries();
    if (series.length !== 3) params.set("series", series.join(","));
    const query = params.toString();
    try { history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`); } catch (_) {}
  }

  function scenarioPercent() {
    return `${Math.round(numeric($("#scenarioSelect").value) * 100)}%`;
  }

  function scenarioLabel() {
    return `${scenarioPercent()} realization`;
  }

  function metricCompact(value) {
    const magnitude = Math.abs(value);
    if (magnitude >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
    if (magnitude >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (magnitude >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    return number.format(value);
  }

  function sum(rows, key) {
    return rows.reduce((total, row) => total + numeric(row[key]), 0);
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

  function addSVG(parent, tag, attributes, text = "") {
    const element = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text) element.textContent = text;
    parent.appendChild(element);
    return element;
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

  function showError(message) {
    $("#errorBox").textContent = message;
    $("#errorBox").classList.add("visible");
  }

  function clearError() {
    $("#errorBox").classList.remove("visible");
    $("#errorBox").textContent = "";
  }

  initialize();
  void refreshProjectCSV();
  </script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    output = HTML.replace("__DATA__", embedded)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding="utf-8")
    print(
        f"[GOLD DASHBOARD] wrote {OUTPUT.relative_to(ROOT)} "
        f"with {payload['meta']['worldDays']:,} world-days"
    )


if __name__ == "__main__":
    main()
