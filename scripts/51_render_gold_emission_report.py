"""Render the standalone Gold Emission report from its own artifact.

`reports/gold_emission_report.html` used to be an external "portable artifact" export produced
by a reader this repository does not contain. Nothing here could rebuild it, so every number in
it froze on the day it was exported: it still claimed 21,412 world-days after the panel reached
90,701, and the artifact verifier could only report the gap, never close it. Hand-editing it was
the one thing `AGENTS.md` forbids outright, because that is exactly how a published surface
starts disagreeing with the data behind it.

This renders the same manifest and snapshot the export consumed - `gold_emission_report_artifact.json`,
written by 36_gold_emission_report.py - into a self-contained page, so the report is generated
from canonical content like every other surface.

    python scripts/51_render_gold_emission_report.py
"""
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "reports" / "gold_emission_report_artifact.json"
OUT = ROOT / "reports" / "gold_emission_report.html"

# The canonical PDF palette, so the report agrees with every other chart in the project rather
# than inventing page-specific series colours.
PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#76B7B2", "#B07AA1", "#9C755F"]

# "Threshold" beside a percentage says nothing about which threshold, and this one is the
# coverage gate rather than the transaction-cost band the rest of the project calls a threshold.
LABELS = {"Threshold": "Coverage gate"}


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def fmt(value: object, kind: str) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if kind == "percent":
        return f"{number * 100:,.2f}%"
    if kind == "number":
        return f"{number:,.0f}" if abs(number) >= 1000 or number == int(number) else f"{number:,.2f}"
    return f"{number:,.3f}".rstrip("0").rstrip(".")


def markdown(text: str) -> str:
    """The manifest's markdown subset: headings, bold, code, lists and paragraphs."""
    out: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        if bullets:
            out.append("<ul>" + "".join(f"<li>{item}</li>" for item in bullets) + "</ul>")
            bullets.clear()

    def inline(line: str) -> str:
        line = esc(line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
        return line

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            flush()
            level = len(heading.group(1)) + 1
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if bullet:
            bullets.append(inline(bullet.group(1)))
            continue
        flush()
        out.append(f"<p>{inline(line)}</p>")
    flush()
    return "\n".join(out)


def line_chart(rows: list[dict], spec: dict) -> str:
    x_field = spec["encodings"]["x"]["field"]
    y_field = spec["encodings"]["y"]["field"]
    color_field = (spec["encodings"].get("color") or {}).get("field")
    series: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        key = str(row.get(color_field)) if color_field else "value"
        try:
            value = float(row.get(y_field))
        except (TypeError, ValueError):
            continue
        series.setdefault(key, []).append((str(row.get(x_field)), value))
    if not series:
        return "<p class='empty'>No data.</p>"

    xs = sorted({x for points in series.values() for x, _ in points})
    index = {x: i for i, x in enumerate(xs)}
    values = [v for points in series.values() for _, v in points]
    low, high = min(values), max(values)
    if high == low:
        high = low + 1
    width, height = 960, 380
    pad = {"t": 18, "r": 18, "b": 46, "l": 82}
    inner_w = width - pad["l"] - pad["r"]
    inner_h = height - pad["t"] - pad["b"]

    def px(x: str) -> float:
        return pad["l"] + (index[x] / max(1, len(xs) - 1)) * inner_w

    def py(v: float) -> float:
        return pad["t"] + (1 - (v - low) / (high - low)) * inner_h

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">']
    for tick in range(5):
        value = low + (high - low) * tick / 4
        y = py(value)
        parts.append(f'<line x1="{pad["l"]}" y1="{y:.1f}" x2="{width - pad["r"]}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad["l"] - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(value, "number")}</text>')
    for position, (name, points) in enumerate(sorted(series.items())):
        points.sort(key=lambda pair: pair[0])
        path = " ".join(
            f"{'M' if i == 0 else 'L'} {px(x):.1f} {py(v):.1f}" for i, (x, v) in enumerate(points)
        )
        colour = PALETTE[position % len(PALETTE)]
        parts.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="2.4"/>')
    for tick in (0, len(xs) // 2, len(xs) - 1):
        parts.append(
            f'<text x="{px(xs[tick]):.1f}" y="{height - 16}" class="tick" text-anchor="middle">{esc(xs[tick])}</text>'
        )
    parts.append("</svg>")
    legend = "".join(
        f'<span class="key"><i style="background:{PALETTE[i % len(PALETTE)]}"></i>{esc(name)}</span>'
        for i, name in enumerate(sorted(series))
    )
    return f'<div class="legend">{legend}</div>' + "".join(parts)


def bar_chart(rows: list[dict], spec: dict) -> str:
    x_field = spec["encodings"]["x"]["field"]
    y_field = spec["encodings"]["y"]["field"]
    color_field = (spec["encodings"].get("color") or {}).get("field")
    groups: list[str] = []
    series: dict[str, dict[str, float]] = {}
    for row in rows:
        group = str(row.get(x_field))
        key = str(row.get(color_field)) if color_field else "value"
        try:
            value = float(row.get(y_field))
        except (TypeError, ValueError):
            continue
        if group not in groups:
            groups.append(group)
        series.setdefault(key, {})[group] = value
    if not groups:
        return "<p class='empty'>No data.</p>"

    values = [v for row in series.values() for v in row.values()]
    low, high = min(values + [0.0]), max(values + [0.0])
    if high == low:
        high = low + 1
    width, height = 960, 380
    pad = {"t": 18, "r": 18, "b": 64, "l": 82}
    inner_w = width - pad["l"] - pad["r"]
    inner_h = height - pad["t"] - pad["b"]
    keys = sorted(series)
    slot = inner_w / max(1, len(groups))
    bar_w = slot / (len(keys) + 1)

    def py(v: float) -> float:
        return pad["t"] + (1 - (v - low) / (high - low)) * inner_h

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">']
    for tick in range(5):
        value = low + (high - low) * tick / 4
        y = py(value)
        parts.append(f'<line x1="{pad["l"]}" y1="{y:.1f}" x2="{width - pad["r"]}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad["l"] - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(value, "number")}</text>')
    zero = py(0.0)
    parts.append(f'<line x1="{pad["l"]}" y1="{zero:.1f}" x2="{width - pad["r"]}" y2="{zero:.1f}" class="axis"/>')
    for gi, group in enumerate(groups):
        for ki, key in enumerate(keys):
            value = series[key].get(group)
            if value is None:
                continue
            x = pad["l"] + gi * slot + (ki + 0.5) * bar_w
            y = py(value)
            parts.append(
                f'<rect x="{x:.1f}" y="{min(y, zero):.1f}" width="{bar_w * 0.9:.1f}" '
                f'height="{abs(zero - y):.1f}" fill="{PALETTE[ki % len(PALETTE)]}"/>'
            )
        parts.append(
            f'<text x="{pad["l"] + gi * slot + slot / 2:.1f}" y="{height - 34}" '
            f'class="tick" text-anchor="middle">{esc(group)}</text>'
        )
    parts.append("</svg>")
    legend = "".join(
        f'<span class="key"><i style="background:{PALETTE[i % len(PALETTE)]}"></i>{esc(key)}</span>'
        for i, key in enumerate(keys)
    )
    return f'<div class="legend">{legend}</div>' + "".join(parts)


def table_html(rows: list[dict], spec: dict) -> str:
    columns = spec["columns"]
    sort = spec.get("defaultSort") or {}
    if sort.get("field"):
        rows = sorted(
            rows,
            key=lambda row: (row.get(sort["field"]) is None, row.get(sort["field"])),
            reverse=sort.get("direction") == "desc",
        )
    head = "".join(f"<th>{esc(column['label'])}</th>" for column in columns)
    body = "".join(
        "<tr>"
        + "".join(
            f"<td class='{column.get('type', 'text')}'>{fmt(row.get(column['field']), column.get('type', 'text'))}</td>"
            if column.get("type") in {"number", "percent"}
            else f"<td>{esc(row.get(column['field']))}</td>"
            for column in columns
        )
        + "</tr>"
        for row in rows
    )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def main() -> None:
    artifact = json.loads(ARTIFACT.read_text())
    manifest = artifact["manifest"]
    datasets = artifact["snapshot"]["datasets"]
    charts = {chart["id"]: chart for chart in manifest.get("charts", [])}
    tables = {table["id"]: table for table in manifest.get("tables", [])}
    cards = {card["id"]: card for card in manifest.get("cards", [])}
    sources = {source["id"]: source for source in artifact.get("sources", [])}

    body: list[str] = []
    for block in manifest["blocks"]:
        kind = block.get("type")
        if kind == "markdown":
            body.append(f"<section>{markdown(block.get('body', ''))}</section>")
        elif kind == "metric-strip":
            tiles = []
            for card_id in block.get("cardIds", []):
                card = cards.get(card_id)
                if not card:
                    continue
                rows = datasets.get(card["dataset"]) or [{}]
                row = rows[0]
                for metric in card["metrics"]:
                    tiles.append(
                        f"<div class='tile'><span class='tile-label'>{esc(LABELS.get(metric['label'], metric['label']))}</span>"
                        f"<strong>{fmt(row.get(metric['field']), metric.get('format', 'number'))}</strong></div>"
                    )
            body.append(f"<div class='tiles'>{''.join(tiles)}</div>")
        elif kind == "chart":
            spec = charts.get(block.get("chartId"))
            if not spec:
                continue
            rows = datasets.get(spec["dataset"], [])
            drawn = line_chart(rows, spec) if spec["type"] == "line" else bar_chart(rows, spec)
            body.append(
                f"<figure><figcaption><h3>{esc(spec['title'])}</h3>"
                f"<p>{esc(spec.get('description', ''))}</p></figcaption>{drawn}</figure>"
            )
        elif kind == "table":
            spec = tables.get(block.get("tableId") or block.get("id"))
            if not spec:
                continue
            rows = datasets.get(spec["dataset"], [])
            body.append(
                f"<figure><figcaption><h3>{esc(spec['title'])}</h3>"
                f"<p>{esc(spec.get('description', ''))}</p></figcaption>{table_html(rows, spec)}</figure>"
            )

    provenance = "".join(
        f"<li><strong>{esc(source.get('label'))}</strong> — <code>{esc(source.get('path'))}</code></li>"
        for source in sources.values()
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(manifest['title'])}</title>
<style>
:root {{ color-scheme: light dark; --fg:#101828; --muted:#667085; --line:#e4e7ec; --bg:#fff; --panel:#f9fafb; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --fg:#e8eaed; --muted:#98a2b3; --line:#2a2f3a; --bg:#12141a; --panel:#181b22; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:32px 20px 72px; background:var(--bg); color:var(--fg);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1040px; margin:0 auto; }}
h1 {{ font-size:1.9rem; line-height:1.25; margin:0 0 8px; }}
h2 {{ font-size:1.3rem; margin:36px 0 8px; }}
h3 {{ font-size:1.05rem; margin:0 0 4px; }}
p {{ margin:0 0 12px; }}
code {{ background:var(--panel); padding:1px 5px; border-radius:4px; font-size:.88em; }}
.lede {{ color:var(--muted); margin-bottom:24px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; margin:20px 0; }}
.tile {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.tile-label {{ display:block; color:var(--muted); font-size:.8rem; margin-bottom:4px; }}
.tile strong {{ font-size:1.4rem; }}
figure {{ margin:28px 0; }}
figcaption p {{ color:var(--muted); font-size:.9rem; }}
.chart {{ width:100%; height:auto; }}
.grid {{ stroke:var(--line); stroke-width:1; }}
.axis {{ stroke:var(--muted); stroke-width:1.2; }}
.tick {{ fill:var(--muted); font-size:11px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:14px; margin:6px 0 10px; font-size:.85rem; color:var(--muted); }}
.key i {{ display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:6px; vertical-align:middle; }}
.table-wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }}
th {{ color:var(--muted); font-weight:600; }}
td.number, td.percent {{ text-align:right; font-variant-numeric:tabular-nums; }}
footer {{ margin-top:48px; padding-top:20px; border-top:1px solid var(--line); color:var(--muted); font-size:.88rem; }}
footer ul {{ padding-left:18px; }}
</style>
</head>
<body>
<main>
<h1>{esc(manifest['title'])}</h1>
<p class="lede">{esc(manifest.get('description', ''))}</p>
{''.join(body)}
<footer>
<h2>Sources</h2>
<ul>{provenance}</ul>
<p>Generated from <code>reports/gold_emission_report_artifact.json</code> by
<code>scripts/51_render_gold_emission_report.py</code> at {esc(manifest.get('generatedAt', ''))}.
GP means Tibia gold pieces; TC means Tibia Coins. Realization percentages are sensitivity
scenarios, not observed sales.</p>
</footer>
</main>
</body>
</html>
"""
    OUT.write_text(page)
    print(
        f"[GOLD REPORT HTML] {OUT.relative_to(ROOT)}: {len(manifest['blocks'])} blocks, "
        f"{sum(len(rows) for rows in datasets.values()):,} snapshot rows, "
        f"{OUT.stat().st_size / 1000:.0f} kB"
    )


if __name__ == "__main__":
    main()
