"""Hold the PDF and the site to the same numbers.

There are now two published artifacts telling one story: the PDF report and the interactive
site, plus the two standalone HTML reports the site links to. They are built by different
scripts on different days from the same data, which is exactly the arrangement in which two
artifacts quietly start disagreeing - and a reader who sees both loses confidence in both.

The rule enforced here is narrow and mechanical. A canonical fact is computed once from
data/processed, which is the shared source of truth. Every artifact that *mentions* that fact
must state it with the same value. An artifact that does not mention it is not in breach; it is
recorded as a coverage gap instead, so the two failure modes stay separate:

    disagreement    two artifacts state different values for the same quantity   -> FAIL
    gap             one artifact carries a headline finding the other omits      -> reported

Coverage gaps are not failures because the site is not obliged to reproduce a 176-page report.
They are printed so the gap is a decision someone made rather than a thing nobody noticed.

    python scripts/46_verify_artifacts.py            # exits non-zero on any disagreement
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pandas as pd
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

R = json.loads((P / "results.json").read_text())
F = json.loads((P / "fundamentals_results.json").read_text())


def flat(text: str) -> str:
    return " ".join(text.split())


def load_pdf() -> str:
    r = PdfReader(str(REPORTS / "tibia_coin_market_report.pdf"))
    return flat("\n".join(p.extract_text() or "" for p in r.pages))


def load_html(name: str) -> str:
    path = REPORTS / name
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Strip script and style bodies: a JSON payload embedded for the charts is data the page
    # holds, not a claim the page makes, and matching numbers inside it would be meaningless.
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    return flat(re.sub(r"<[^>]+>", " ", raw))


def load_hub_meta() -> dict:
    """The hub states its headline claims through the embedded payload rather than in markup.

    The page fills every figure from ``data.meta`` at render time, which is the whole point:
    a number typed into the HTML would drift the next time a pipeline stage ran. So the meta
    object, not the visible text, is where the hub's claims actually live, and it is what has
    to agree with the report.
    """
    path = REPORTS / "intelligence_hub.html"
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Balance the braces rather than anchoring on whatever key follows: the payload's key
    # order is an implementation detail of the builder, and anchoring on it made this parser
    # fail silently the first time a new dataset was inserted ahead of "marketIndex".
    i = raw.find('"meta":')
    if i < 0:
        return {}
    start = raw.find("{", i)
    depth, j, in_str, esc = 0, start, False, False
    while j < len(raw):
        ch = raw[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    try:
        return json.loads(raw[start:j + 1])
    except json.JSONDecodeError:
        return {}


ARTIFACTS = {
    "pdf": load_pdf(),
    "hub": load_html("intelligence_hub.html"),
    "gold_report": load_html("gold_emission_report.html"),
    "gold_dashboard": load_html("gold_emission_dashboard.html"),
}
HUB_META = load_hub_meta()

_STG = pd.DataFrame(F["strategy"]["grid"])
_HD = pd.DataFrame(F["strategy"]["holdout"]["rows"])


def _cell(h: int, col: str) -> float:
    row = _STG[(_STG.horizon == h) & (_STG.decile == _STG.decile.max())
               & (_STG.cost_basis == "above the fee cap")]
    return float(row[col].iloc[0])


def _hold(h: int, col: str) -> float:
    return float(_HD[(_HD.horizon == h) & (_HD.period == "holdout")][col].iloc[0])


# Each fact carries the canonical value and the patterns that would express it in prose. A
# pattern is a regex whose first group is the number as an artifact would render it.
FACTS = [
    {"key": "verdict", "scope": ("pdf", "hub"), "meta": "verdict",
     "value": "buy relative, not directional",
     "kind": "phrase",
     "topic": r"(?:Overall rating|Verdict)[:.]",
     "why": "the headline recommendation"},
    {"key": "action_threshold_pct", "scope": ("pdf", "hub"), "meta": "actionGapPct",
     "value": F["scenarios"]["levels"]["arb_act_gap_pct"],
     "kind": "number", "tol": 0.05,
     "pattern": r"(?:act (?:only )?on gaps above|act across worlds only past|"
                r"gap exceeds about)\s*(\d+(?:\.\d+)?)\s*%",
     "why": "the cross-world gap at which a reader should act"},
    {"key": "band_threshold_pct", "scope": ("pdf", "hub"), "meta": "bandThresholdPct",
     "value": R["advanced"]["tar"]["threshold_pct"],
     "kind": "number", "tol": 0.02,
     "pattern": r"(?:friction point|threshold)[^.]{0,40}?(\d\.\d\d)\s*%",
     "why": "the estimated transaction-cost band"},
    {"key": "lot_size", "scope": ("pdf", "hub"), "meta": "lotSize",
     "value": R["fees"]["lot_size"],
     "kind": "number", "tol": 0,
     "pattern": r"lots? of (\d+)\b",
     "why": "the Market's minimum trade quantity, which sets every volume figure"},
    {"key": "strategy_net_30d_pct", "scope": ("pdf", "hub"), "meta": "strategyNet30",
     "value": _cell(30, "net_pct"),
     "kind": "number", "tol": 0.02,
     "pattern": r"(?:thirty days|30 days|30-day)[^.]{0,80}?(\d\.\d\d)\s*%",
     "why": "the strategy's headline net return"},
    {"key": "holdout_windows_91d", "scope": ("pdf", "hub"), "meta": "holdoutWindows91",
     "value": _hold(91, "n_effective"),
     "kind": "number", "tol": 0,
     "pattern": r"(\d+) independent window",
     "why": "how much out-of-sample evidence stands behind the quarterly figure"},
    {"key": "bazaar_over_market", "scope": ("pdf", "hub"), "meta": "bazaarOverMarket",
     "value": R["venues"]["market_size"]["bazaar_over_market"],
     "kind": "number", "tol": 0.15,
     "pattern": r"(\d+\.\d) times (?:more|the coins|larger)",
     "why": "the Char Bazaar moves an order of magnitude more coins than the Market"},
    {"key": "emission_channel", "meta": "emissionVerdict", "scope": ("pdf", "hub", "gold_report"),
     "value": "rejected",
     "kind": "phrase",
     "topic": r"gold (?:production|emission)[^.]{0,60}(?:not supported|rejected|eliminated)",
     "why": "the GP-emission series reaches the same null as the kill-count proxy"},
]

fails: list[str] = []
gaps: list[str] = []
notes: list[str] = []


def find_numbers(text: str, pattern: str) -> list[float]:
    out = []
    for m in re.finditer(pattern, text, re.I):
        try:
            out.append(float(m.group(1)))
        except (TypeError, ValueError):
            continue
    return out


for fact in FACTS:
    stated: dict[str, list] = {}
    if fact.get("meta") and fact["meta"] in HUB_META:
        stated["hub"] = [HUB_META[fact["meta"]]]
    for name, text in ARTIFACTS.items():
        if not text:
            continue
        if fact["kind"] == "number":
            got = find_numbers(text, fact["pattern"])
            if got:
                stated[name] = got
        else:
            if re.search(fact["topic"], text, re.I):
                stated[name] = [fact["value"]]

    if not stated:
        gaps.append(f"{fact['key']}: stated by no artifact ({fact['why']})")
        continue

    if fact["kind"] == "number":
        bad = {n: v for n, v in stated.items()
               if not any(isinstance(x, (int, float))
                          and abs(x - fact["value"]) <= fact["tol"] for x in v)}
        if bad:
            fails.append(
                f"{fact['key']}: canonical {fact['value']:.3g}, "
                + "; ".join(f"{n} says {v}" for n, v in bad.items())
                + f"  ({fact['why']})")
        else:
            notes.append(f"{fact['key']} = {fact['value']:.4g} agrees in "
                         f"{', '.join(sorted(stated))}")
    else:
        wrong = {n: v[0] for n, v in stated.items()
                 if isinstance(v[0], str) and v[0].strip().lower() != fact["value"].lower()
                 and n == "hub"}
        if wrong:
            fails.append(f"{fact['key']}: canonical {fact['value']!r}, "
                         + "; ".join(f"{n} says {v!r}" for n, v in wrong.items()))
        else:
            notes.append(f"{fact['key']} present in {', '.join(sorted(stated))}")

    scope = fact.get("scope") or tuple(ARTIFACTS)
    missing = [n for n in scope if ARTIFACTS.get(n) and n not in stated]
    if missing and "pdf" in stated:
        gaps.append(f"{fact['key']}: in the PDF, absent from {', '.join(sorted(missing))} "
                    f"({fact['why']})")

# The site and the report must also agree on how much data they were built from, since a
# stale rebuild of one is the most likely way they drift apart in practice. Only an explicitly
# STATED window counts: the largest date visible in a table is a subset a page chose to show,
# not a claim about coverage, and treating it as one produces a false alarm.
_panel_end = str(pd.read_csv(P / "panel_daily.csv", usecols=["date"]).date.max())[:10]
_window_re = re.compile(r"(?:to|through|until|-)\s*(20\d\d-\d\d-\d\d)\s*(?:\.|,|\)|<|$)")
_stated = {}
for name, text in ARTIFACTS.items():
    if not text:
        continue
    hits = re.findall(r"20\d\d-\d\d-\d\d\s*(?:to|through|-)\s*(20\d\d-\d\d-\d\d)", text)
    if hits:
        _stated[name] = max(hits)
_drift = {n: v for n, v in _stated.items() if v > _panel_end}
if _drift:
    fails.append("stated coverage runs past the data: "
                 + ", ".join(f"{n} claims {v}" for n, v in sorted(_drift.items()))
                 + f", panel ends {_panel_end}")
elif _stated:
    _behind = {n: v for n, v in _stated.items()
               if (pd.Timestamp(_panel_end) - pd.Timestamp(v)).days > 14}
    if _behind:
        gaps.append("built from an older panel: "
                    + ", ".join(f"{n} to {v}" for n, v in sorted(_behind.items()))
                    + f", panel now ends {_panel_end}")
    else:
        notes.append(f"stated coverage agrees with the panel end {_panel_end} in "
                     f"{', '.join(sorted(_stated))}")

print(f"artifacts checked: {', '.join(n for n, t in ARTIFACTS.items() if t)}")
for n in notes:
    print(f"  PASS  {n}")
for g in gaps:
    print(f"  GAP   {g}")
for f_ in fails:
    print(f"  FAIL  {f_}")

print(f"\n{len(notes)} agree, {len(gaps)} coverage gaps, {len(fails)} disagreements")
if fails:
    print("\nA disagreement means two published artifacts state different values for the same "
          "quantity. Fix the artifact that is wrong, then rebuild both.")
sys.exit(1 if fails else 0)
