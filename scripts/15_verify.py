"""Verify the built PDF against the data and against itself.

Every check here exists because the corresponding defect actually reached a build: blank pages
from doubled page breaks, a cross-reference to a renumbered section, an exhibit numbered by
analogy with the tables around it, a figure disagreeing with the body text about a live figure,
a trading recommendation left below the threshold it was meant to clear.

Reading the text back out of the finished PDF is the point. Checking the source would verify
what the code meant to emit; this verifies what a reader will actually see.

    python scripts/15_verify.py            # exits non-zero if any check fails
"""
import json, pathlib, re, sys
import pandas as pd
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
PDF = ROOT / "reports" / "tibia_coin_market_report.pdf"

FOOTER = re.compile(r"Tibia Coin Market - Multi-World Quantitative Report|Page \d+")
NUM = r"\d+(?:\.\d+){0,2}"

reader = PdfReader(str(PDF))
pages = [p.extract_text() or "" for p in reader.pages]
flat = [" ".join(t.split()) for t in pages]
txt = "\n".join(pages)
doc = " ".join(flat)

fails, notes = [], []


def check(name, ok, detail=""):
    (notes if ok else fails).append(f"{'PASS' if ok else 'FAIL'}  {name}"
                                    + (f"  ({detail})" if detail else ""))


# ---- structure -------------------------------------------------------------
blank = [i + 1 for i, t in enumerate(flat) if len(FOOTER.sub("", t).strip()) < 30]
check("no blank pages", not blank, f"pages {blank}" if blank else f"{len(pages)} pages")

# A heading must never be the last thing on a page with its section overleaf.
stranded = [i + 1 for i, t in enumerate(pages) if (ls := [x.strip() for x in t.split("\n")
            if x.strip() and not FOOTER.match(x.strip())])
            and re.match(rf"^{NUM}\s+\S", ls[-1]) and len(ls[-1]) < 70
            and not ls[-1].endswith(".") and i > 4
            # The verdict page is a designed full-page layout whose last line is the
            # confidence score, not a stranded heading.
            and "THE VERDICT" not in t]
check("no headings stranded at a page foot", not stranded, f"pages {stranded}")

# An exhibit label must not be orphaned from its artwork.
split = [i + 1 for i, t in enumerate(pages) if (ls := [x.strip() for x in t.split("\n")
         if x.strip() and not FOOTER.match(x.strip())])
         and any(re.fullmatch(r"Exhibit \d+\.\d+", x) for x in ls[-2:])]
check("no exhibit split from its artwork", not split, f"pages {split}")

# ---- cross-references ------------------------------------------------------
heads = set(re.findall(rf"\n\s*({NUM})\s+[A-Z]", txt)) | set(re.findall(r"Chapter (\d+)", txt))
tables = set(re.findall(r"Table ([0-9A-Z]+\.\d+) -", txt))
exhibits = set(re.findall(r"Exhibit (\d+\.\d+)\b", txt))

refs = set()
for m in re.finditer(rf"Sections?\s+((?:{NUM})(?:\s*(?:,|and|or|to|&)\s*(?:{NUM}))*)", txt):
    refs |= set(re.findall(NUM, m.group(1)))
dangling = sorted(x for x in refs
                  if x not in heads and not any(h.startswith(x + ".") for h in heads))
check("every section reference resolves", not dangling, f"missing {dangling}")
check("every table reference resolves",
      not (m := sorted(set(re.findall(r"Table (\d+\.\d+)", txt)) - tables)), f"missing {m}")
check("every exhibit reference resolves",
      not (m := sorted(set(re.findall(r"Exhibit (\d+\.\d+)", txt)) - exhibits)), f"missing {m}")

for kind, found in (("table", tables), ("exhibit", exhibits)):
    gaps = []
    for ch in sorted({t.split(".")[0] for t in found}):
        n = sorted(int(t.split(".")[1]) for t in found if t.split(".")[0] == ch)
        if n != list(range(1, len(n) + 1)):
            gaps.append((ch, n))
    check(f"{kind} numbering is contiguous", not gaps, f"{gaps}" if gaps
          else f"{len(found)} {kind}s")

# Subsections, which are numbered by hand and drifted into duplicates once already.
subs = re.findall(r"\n(\d+\.\d+)\.(\d+) [A-Z]", txt)
bysec = {}
for sec, n in subs:
    bysec.setdefault(sec, []).append(int(n))
sub_bad = []
for sec, ns in bysec.items():
    if len(ns) != len(set(ns)):
        sub_bad.append((sec, "duplicate"))
    elif sorted(ns) != list(range(1, len(ns) + 1)):
        sub_bad.append((sec, sorted(ns)))
check("subsection numbering is contiguous and unique", not sub_bad,
      f"{sub_bad[:3]}" if sub_bad else f"{len(bysec)} sections checked")

# Units. Coins trade only in lots of 25, and day_sold/day_bought count lots, not coins: the
# values run 1, 2, 3 with ~4% multiples of 25, which a coin count cannot be. Reporting them
# raw understated coin volume by 25x and made the depth-to-flow ratio meaningless. The book's
# own amounts are the opposite case - minimum 25, every value a whole lot - so they are
# already coins and must not be scaled again. Both directions are checked from the data.
import pandas as _pd
_pan = _pd.read_csv(ROOT / "data" / "processed" / "panel_daily.csv")
_lo = _pd.read_csv(ROOT / "data" / "processed" / "live_offers.csv")
_unit_bad = []
for _c in ("day_sold", "day_bought", "month_sold", "month_bought"):
    if _c in _pan:
        _v = _pan[_c].dropna()
        _v = _v[_v > 0]
        if len(_v) and (_v % 25 == 0).mean() > 0.5:
            _unit_bad.append((_c, "reads like coins; the pipeline scales it by 25 as lots"))
_amt = _lo.amount.dropna()
if len(_amt) and not (_amt % 25 == 0).all():
    _unit_bad.append(("live_offers.amount", "not every offer is a whole 25-coin lot"))
# The converted column must be exactly 25x the raw one, with no double scaling anywhere.
if "day_sold_tc" in _pan:
    _r = (_pan.day_sold_tc / _pan.day_sold).dropna()
    if len(_r) and not ((_r - 25).abs() < 1e-9).all():
        _unit_bad.append(("day_sold_tc", f"not exactly 25x day_sold (min {_r.min():.3f})"))
check("volume fields carry the units the report claims", not _unit_bad,
      f"{_unit_bad}" if _unit_bad else
      f"lots {(_pan.day_sold.dropna() % 25 == 0).mean():.1%} multiples of 25, "
      f"offers {(_amt % 25 == 0).mean():.0%}, day_sold_tc = 25x")

# No surviving sentence may report the lot count as if it were a coin quantity.
_tc_claim = re.findall(r"\b103 TC\b|\bTC quantity executed", txt)
check("transaction counts are never reported as coins", not _tc_claim, f"{_tc_claim[:3]}")

# The report must not name two different gaps as "the binding limitation". This drifted once:
# the gold-supply gap was binding until Section 6.6.14 obtained the series and rejected the
# channel, after which the venue gap took over and three older passages still disagreed.
# The headline verdict is stated in several places and they drifted apart once. The check
# compares each statement against the canonical value in narrative.py rather than blacklisting
# a word: an earlier version made the colon optional, which matched table headers like
# "Verdict against the global model", and only ever policed the literal string "neutral" - a
# drift to "Hold" would have passed silently.
_canon = None
try:
    import narrative as _nar_v
    _canon = _nar_v.facts()["verdict"].strip().lower()
except Exception:
    pass
# A real statement of the verdict is a label followed by a colon and a short phrase that ends
# at a sentence boundary. Table headers have no colon and are excluded by construction.
_verdicts = [v.strip().lower().rstrip(".")
             for v in re.findall(r"(?:Overall rating|Verdict):\s*([A-Za-z][^.\n]{0,60}?)\s*"
                                 r"(?:\.|Confidence)", doc)]
if _canon is None:
    check("every statement of the verdict agrees", False, "narrative.py unavailable")
elif not _verdicts:
    check("every statement of the verdict agrees", False,
          "the report states no verdict at all")
else:
    _off = sorted({v for v in _verdicts if v != _canon})
    check("every statement of the verdict agrees", not _off,
          f"canonical {_canon!r}, found {_off}" if _off
          else f"{len(_verdicts)} statements, all {_canon!r}")

_bind = re.findall(r"[^.]{0,90}binding (?:limitation|one)[^.]{0,90}\.", doc)
_stale = [b for b in _bind if "gold" in b.lower() and "at the time" not in b.lower()]
check("only one gap is described as binding", not _stale,
      f"{[b.strip()[:70] for b in _stale]}" if _stale else f"{len(_bind)} mentions, consistent")

# The action threshold. The executive summary told the reader to act on cross-world gaps above
# 6% while every decision table said 4%, so a reader following the summary skipped a region the
# report's own evidence calls tradable. Every statement of the rule must name the same number.
_act = set(re.findall(r"(?:act (?:only )?on gaps above|act across worlds only past|"
                      r"gap exceeds about|Above \+?)(\d+(?:\.\d+)?)%", doc))
_fres = json.load(open(ROOT / "data" / "processed" / "fundamentals_results.json"))
_act_expect = f"{_fres['scenarios']['levels']['arb_act_gap_pct']:.0f}"
_act_bad = sorted(a for a in _act if a.rstrip("0").rstrip(".") not in
                  (_act_expect, f"{float(_act_expect):.1f}".rstrip("0").rstrip(".")))
check("the cross-world action threshold is one number everywhere", not _act_bad,
      f"expected {_act_expect}%, also found {_act_bad}" if _act_bad
      else f"{_act_expect}% in {len(_act)} statement(s)")

# Fold counts asserted in prose must match the computed table. "beat the random walk in every
# one of its six folds" stood beside a table cell reading 5 of 6 for the same model.
_ms = _pd.read_csv(ROOT / "data" / "processed" / "model_summary.csv")
# Fold counts are reported from three separate model tables - the main comparison, the extra
# model classes and the neural sequence models, which run a different number of folds - so a
# prose claim is valid if it appears in any of them.
_real = set()
for _f in ("model_summary.csv", "extra_models_summary.csv", "deep_summary.csv"):
    _t = _pd.read_csv(ROOT / "data" / "processed" / _f)
    if "folds_better" in _t.columns:
        _real |= {(int(a), int(b)) for a, b in
                  zip(_t.folds_better.dropna(), _t.folds.dropna())}
_claimed = {(int(a), int(b)) for a, b in re.findall(r"(\d+) of (\d+) folds", doc)}
_fold_bad = sorted(_claimed - _real)
check("fold counts in prose match the model table", not _fold_bad,
      f"not in model_summary: {_fold_bad}" if _fold_bad else f"{len(_claimed)} claim(s) checked")

# A figure caption that names one model must quote that model's own numbers. The skill exhibit
# described the 7-day forest and printed the 1-day ElasticNet's R-squared, because it took
# whichever row sorted first.
_mf = json.load(open(ROOT / "figures" / "manifest.json"))
_skill = _mf.get("fig27_fundamentals_skill", {}).get("note", "")
_r2_claimed = re.findall(r"out-of-sample R.{0,3} of (\d\.\d+)", _skill)
_rf7 = _ms.query("target == 'rel' and horizon == 7 and model == 'RandomForest'")
_r2_bad = (_r2_claimed and len(_rf7)
           and abs(float(_r2_claimed[0]) - float(_rf7.iloc[0].r2_oos)) > 0.0006)
check("the skill exhibit quotes the model it names", not _r2_bad,
      f"caption {_r2_claimed}, row {float(_rf7.iloc[0].r2_oos):.3f}" if _r2_bad
      else f"R2 {_r2_claimed[0] if _r2_claimed else 'n/a'} matches the 7d forest")

# Shared claims are stated twice by design - the summary asserts, the body derives - but the
# two must be the summary and full forms of one definition, not two hand-written sentences
# that happen to agree today. A claim's full text appearing twice means one placement is a
# copy that will drift.
import sys as _sys
_sys.path.insert(0, str(ROOT / "scripts"))
try:
    import narrative as _nar
    # Compare the tail, not the head: a claim's summary and full forms deliberately open the
    # same way, so matching on the opening flags the intended pair as a duplicate.
    _dupe = [c.key for c in _nar.claims()
             if len(c.text) > 80 and doc.count(c.text[-70:]) > 1]
    check("no shared claim is stated twice verbatim", not _dupe,
          f"{_dupe}" if _dupe else f"{len(_nar.claims())} claims checked")
    # And every claim must actually reach the page, or the shared spine is decorative.
    _missing = [c.key for c in _nar.claims() if c.text[-70:] not in doc]
    check("every shared claim reaches the report", not _missing, f"{_missing}")
except Exception as _e:                                    # narrative is optional at build time
    check("shared-claim checks ran", False, f"narrative.py unusable: {_e}")

labels = re.findall(r"Exhibit (\d+\.\d+)\n", txt)
check("no exhibit number used twice", len(labels) == len(set(labels)))

# Table numbers must run 1..n within each chapter *in the order they appear*. Renumbering by
# hand after an insertion is exactly where this drifts, and a caption that reads 7.21 after
# 7.24 is invisible to every other check here.
tbl_seq, tbl_bad = {}, []
for ch, num in re.findall(r"Table ([0-9A-Z]+)\.(\d+) -", txt):
    tbl_seq.setdefault(ch, []).append(int(num))
for ch, ns in tbl_seq.items():
    if ns != list(range(1, len(ns) + 1)):
        tbl_bad.append((ch, ns))
check("table numbers are sequential in document order", not tbl_bad,
      f"{tbl_bad[:2]}" if tbl_bad else f"{len(tbl_seq)} chapters, {sum(map(len, tbl_seq.values()))} tables")

# ---- contents --------------------------------------------------------------
lines = [x for pg in range(1, 5) for x in pages[pg].split("\n")]
toc = [(lines[i + 1].strip(), int(m.group(1))) for i, l in enumerate(lines)
       for m in [re.match(r"^[\s.]*?(\d{1,3})\s*$", l)]
       if m and i + 1 < len(lines) and lines[i + 1].strip()]
bad_toc = [t for t, n in toc if not 1 <= n <= len(pages)
           or re.sub(r"^\d+\.\s+", "", " ".join(t.split()).lower()) not in flat[n - 1].lower()]
check("every contents entry points at the right page", not bad_toc,
      f"{bad_toc[:4]}" if bad_toc else f"{len(toc)} entries")

# ---- conventions -----------------------------------------------------------
check("currency is written GP throughout",
      not re.search(r"(?<![A-Za-z_])gp(?![A-Za-z_])", txt) and not re.search(r"\bGC\b", txt),
      f"{len(re.findall(r'(?<![A-Za-z])GP(?![A-Za-z])', txt))} GP tokens")
CLAIMS = ["Observed data", "Statistical relationship", "Economic interpretation", "Hypothesis",
          "Analyst judgement", "Limitation", "Documented mechanic", "Forecast"]
check("claims carry evidence labels", (n := sum(doc.count(c) for c in CLAIMS)) > 200, f"{n} labels")
check("no meta-commentary about the report's own revisions",
      not re.search(r"\b(in the previous version|as corrected|earlier draft|this was wrong)\b",
                    doc, re.I))

# ---- coverage against the data --------------------------------------------
res = json.load(open(P / "results.json"))
worlds = pd.read_csv(P / "world_summary.csv").world
check("all 93 worlds appear", (miss := [w for w in worlds if w not in doc]) == [],
      f"missing {miss[:5]}" if miss else f"{len(worlds)} worlds")

fc = pd.read_csv(P / "forecasts_sa.csv")
cells = [(x.world, h, q) for _, x in fc.iterrows() for h in ("2w", "1m", "3m", "6m")
         for q in ("p50", "p10", "p90") if f"{x[h + '_' + q]:,.0f}" not in doc]
check("every forecast cell is printed", not cells,
      f"{len(cells)} missing" if cells else f"{len(fc) * 12} cells")

scripts = {p.name for p in (ROOT / "scripts").glob("*.py")}
check("every pipeline script is documented",
      (miss := sorted(s for s in scripts if s not in doc)) == [],
      f"missing {miss}" if miss else f"{len(scripts)} scripts")

# ---- internal consistency --------------------------------------------------
vn = res["venues"]
supply = f"{vn['token']['total_supply']:,.0f}"
stated = set(re.findall(r"supply stood at ([\d,]+) TIB", doc)) | \
         set(re.findall(r"([\d,]+) TIB existed at block", doc))
check("body text and exhibit agree on the token supply",
      stated == {supply}, f"results.json says {supply}, document says {stated or 'nothing'}")
check("pooled tokens are reported as a share of supply, not as supply",
      vn["dex"]["tib_in_pools"] < vn["token"]["total_supply"]
      and f"{vn['dex']['tib_in_pools']:,.0f} TIB" in doc,
      f"{vn['dex']['tib_in_pools'] / vn['token']['total_supply']:.0%} of supply")

fe = res["fees"]
check("the fee-cap advice names a placeable lot",
      fe["cap_binds_at_lot_tc"] % fe["lot_size"] == 0
      and fe["cap_binds_at_lot_tc"] >= fe["cap_binds_above_tc"]
      and f"{fe['cap_binds_at_lot_tc']:,.0f} TC" in doc,
      f"{fe['cap_binds_at_lot_tc']:,.0f} TC")

# ---- methods carry a citation ----------------------------------------------
# Fifteen of seventeen methods added during the study were used in the body and never cited.
# A named estimator without a reference is the kind of gap a reader notices and an author does
# not, so the mapping is checked rather than trusted.
METHOD_CITE = {
    "Boruta": "Kursa", "conformal": "Lei", "BDS": "Brock",
    "permutation entropy": "Bandt", "sample entropy": "Richman",
    "surrogate": "Schreiber", "Markov-switching": "Hamilton",
    "random forest": "Breiman", "XGBoost": "Chen", "SHAP": "Lundberg",
    "LSTM": "Hochreiter", "transformer": "Vaswani", "block bootstrap": "Kunsch",
    "Benjamini-Hochberg": "Benjamini", "change point": "Killick", "Prophet": "Taylor",
    "Diebold-Mariano": "Diebold", "GARCH": "Bollerslev",
}
refs_start = txt.find("Appendix C. References")
refs_seg = txt[refs_start:] if refs_start > 0 else ""
uncited = [m for m, author in METHOD_CITE.items()
           if re.search(re.escape(m), doc, re.I) and author not in refs_seg]
check("every named method is cited in the references", not uncited,
      f"uncited: {uncited}" if uncited else f"{len(METHOD_CITE)} methods checked")

# The reference list is alphabetical by surname, and a block pasted in the wrong place breaks it.
sur = [n.split(",")[0].strip() for n in
       re.findall(r"([A-Z][A-Za-z'-]+(?:, [A-Z]\.)+[^(]*)\((?:19|20)\d\d\)", refs_seg)]
check("references are in alphabetical order", sur == sorted(sur, key=str.lower),
      f"{len(sur)} references")

# ---- statistical integrity -------------------------------------------------
# Claims of significance must agree with the p-values printed alongside them.
mismatch = []
for sent in re.split(r"(?<=[.]) ", doc):
    if not re.search(r"\bsignifican", sent, re.I):
        continue
    ps = [float(x) for x in re.findall(r"p\s*(?:=|is|of)?\s*([0-9]*\.[0-9]+)", sent)]
    hedged = re.search(r"\b(not|no|nor|never|fails? to|cannot|insignificant)\b.{0,40}"
                       r"significan|significan\w*\s+(?:only\s+)?at\b", sent, re.I)
    if ps and not hedged and max(ps) > 0.05:
        mismatch.append(f"p={max(ps)}: {sent[:80]}")
check("significance claims agree with their p-values", not mismatch, "; ".join(mismatch[:2]))

# "N of M" is a count out of a total and cannot exceed it.
overflow = [m.group(0) for m in re.finditer(r"([\d,]+)\s+of\s+([\d,]+)\b", doc)
            if int(m.group(1).replace(",", "")) > int(m.group(2).replace(",", ""))]
check("no count exceeds its denominator", not overflow, "; ".join(overflow[:3]))

n_worlds = res["window"]["n_worlds"]
# Exclude the page footer: flattening the PDF puts "Page 133" next to a line that happens to
# begin with "worlds", which reads as a 133-world subsample that does not exist.
cited = {int(x.replace(",", "")) for x in re.findall(r"(?<!Page )(\d[\d,]*) worlds", doc)
         if x.replace(",", "").isdigit()}
# The kill-statistics archive reaches back to 2022 and so covers worlds that have since been
# merged away - more worlds than are live today. The bound is that universe, not the price
# panel, and it is read from the data rather than assumed.
try:
    _ks_worlds = int(pd.read_csv(P / "kill_stats_daily.csv", usecols=["world"]).world.nunique())
except Exception:
    _ks_worlds = 0
_universe = max(n_worlds, _ks_worlds)
check("no subsample is larger than any observed universe",
      not (over := sorted(c for c in cited if c > _universe)), f"{over}" if over else
      f"max {max(cited)} against {n_worlds} priced and {_ks_worlds} in the kill archive")

tar = res["advanced"]["tar"]
check("the threshold estimate lies inside its confidence set",
      tar["threshold_ci_pct"][0] <= tar["threshold_pct"] <= tar["threshold_ci_pct"][1],
      f"{tar['threshold_pct']:.2f}% in [{tar['threshold_ci_pct'][0]:.2f}, "
      f"{tar['threshold_ci_pct'][1]:.2f}]")

fcs = pd.read_csv(P / "forecasts_sa.csv")
unordered = [(r.world, h) for _, r in fcs.iterrows() for h in ("2w", "1m", "3m", "6m")
             if not r[f"{h}_p10"] <= r[f"{h}_p50"] <= r[f"{h}_p90"]]
check("forecast quantiles are ordered", not unordered, f"{unordered[:3]}")

# ---- the README describes this build, so it is checked against it ----------
readme = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
if readme:
    quoted = {"pages": len(pages), "exhibits": len(exhibits), "tables": len(tables)}
    wrong = [f"{k}: says {m.group(1)}, is {v}" for k, v in quoted.items()
             if (m := re.search(rf"([\d,]+) {k}", readme))
             and int(m.group(1).replace(",", "")) != v]
    check("README matches the built report", not wrong, "; ".join(wrong) or "pages, exhibits, tables")

print("\n".join(notes))
if fails:
    print("\n" + "\n".join(fails))
    sys.exit(f"\n{len(fails)} of {len(fails) + len(notes)} checks failed")
print(f"\nall {len(notes)} checks passed on {len(pages)} pages")
