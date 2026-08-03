"""How many hypotheses does this study test, and which of them are corrected?

The report applies Benjamini-Hochberg in five places and a Sidak adjustment in one, each inside
its own family, and never says how many tests the study runs in total or which families go
uncorrected. That is the gap: a reader cannot judge whether a surviving result survived a
serious correction or a lenient one without knowing what it was corrected against.

This stage counts. It reads the result files rather than the prose, so the ledger cannot drift
from what the pipeline actually did, and it separates three categories that are usually blurred:

    corrected     a family where a correction is applied and the survivor count is reported
    reported      a family reported without correction, deliberately, with the reason
    descriptive   an estimate quoted with a standard error but never used as a discovery

The distinction matters because correcting everything against everything is as wrong as
correcting nothing. A coefficient the report states as a magnitude, with no claim that it is
distinguishable from zero, is not a hypothesis test and should not enter a family.

    python scripts/50_testing_ledger.py
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

R = json.loads((P / "results.json").read_text())
F = json.loads((P / "fundamentals_results.json").read_text())


def count(path, default=0):
    """Read a nested key path out of the result files, tolerating an absent stage."""
    for src in (F, R):
        cur = src
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok:
            return cur
    return default


rows = []


def add(family, n, status, correction, survivors, why):
    rows.append({"family": family, "n_tests": int(n), "status": status,
                 "correction": correction,
                 "survivors": None if survivors is None else int(survivors), "why": why})


# ---- families where a correction is applied ------------------------------------------
g = count(["granger"], {})
if g:
    add("Leading indicators, Granger",
        g.get("n_hypotheses", g.get("n_tested", 0)),
        "corrected", "Sidak over the lag grid, then Benjamini-Hochberg across series",
        g.get("n_survive_bh_5pct", 0),
        "the smallest p across six lags is not a p-value, so two searches are paid for")

ms = count(["model_summary"], [])
if isinstance(ms, list) and ms:
    md = pd.DataFrame(ms)
    add("Model comparison against a random walk",
        len(md), "corrected", "Benjamini-Hochberg at 5% across every model-horizon cell",
        int(md.get("beats_rw", pd.Series(dtype=bool)).sum()) if "beats_rw" in md else None,
        "one family: every model tried on every horizon and target")

lh = count(["long_horizon_production"], {})
if lh:
    add("Production, long horizon and cumulative",
        lh.get("n_specifications", 0), "corrected",
        "Benjamini-Hochberg, then a per-date re-test of every survivor",
        lh.get("n_survive_bh", 0),
        "four families of specification searched jointly over horizons and windows")
    if "monetary_long" in lh:
        # The monetary series is eight months long while the horizons run to a year, so the
        # calendar supplies no independent windows and the cells are not estimable. Recording
        # them as a corrected family with zero survivors would read as a rejection; the
        # honest label is that the family was attempted and could not be tested.
        n_est = lh.get("monetary_n_estimable", 0)
        add("Production, monetary series",
            len(lh["monetary_long"]),
            "corrected" if n_est else "not estimable",
            "per-date Newey-West with a minimum independent-window count and a sign check"
            if n_est else "none possible",
            lh.get("monetary_n_survive_honest") if n_est else None,
            "the same search on GP emission rather than on kill counts" if n_est else
            f"{lh.get('monetary_span_years', 0):.2f} years of emission cannot support "
            f"horizons to a year; untested rather than rejected")

disc = count(["discovery"], {})
if isinstance(disc, dict) and disc:
    n_int = disc.get("n_interactions_tested") or disc.get("n_tested") or 0
    if n_int:
        add("Interaction search", n_int, "corrected",
            "confirmation required on an independent split",
            disc.get("n_replicated", 0),
            "a search over pairs finds pairs; replication is the correction that matters")

st = count(["strategy"], {})
if st:
    add("Strategy grid", st.get("n_cells", 0), "corrected",
        "per-date Newey-West and a calendar-span window count",
        st.get("n_cells_significant"),
        "strength by holding period and signal decile, tested as one grid")

# ---- families reported without a correction, deliberately -----------------------------
sd = count(["supply_vs_demand", "supply_elasticity"], [])
if isinstance(sd, list) and sd:
    add("Gold-supply elasticity", len(sd), "reported", "none",
        None, "reported as magnitudes; the conclusion rests on the size and sign, not on "
              "any cell clearing a threshold")

seas = count(["stability_seasonality"], {})
if seas:
    n_seas = len(seas.get("month_effects", [])) + (1 if "day_of_week" in seas else 0) \
        + (1 if "events" in seas else 0)
    add("Seasonality", n_seas, "corrected",
        "joint chi-squared rather than per-coefficient tests",
        n_seas, "eleven month dummies asked as one question, which is what a joint test is for")
    add("Regime splits", len(seas.get("regime_splits", [])), "reported", "none",
        None, "descriptive contrasts between subsamples, not a search for a significant one")

irr = count(["irreducibility", "bds"], [])
if isinstance(irr, list) and irr:
    add("Entropy and BDS against surrogates", len(irr), "reported",
        "surrogate distribution rather than an analytic p-value",
        None, "the null is generated, so the comparison is to a simulated distribution")

ledger = pd.DataFrame(rows)
ledger.to_csv(P / "testing_ledger.csv", index=False)

total = int(ledger.n_tests.sum())
corrected = int(ledger.loc[ledger.status == "corrected", "n_tests"].sum())
print(f"[LEDGER] {total:,} hypothesis tests across {len(ledger)} families")
print(f"[LEDGER] {corrected:,} ({corrected / max(1, total):.0%}) sit inside a family that "
      f"carries a correction")
print()
print(ledger[["family", "n_tests", "status", "survivors"]].to_string(index=False))

LED = {
    # A family with no survivor count carries None, not NaN. Round-tripping through a DataFrame
    # turns that None into a float NaN, and the site's payload is serialised with allow_nan
    # off - so the whole page fails to build over a value that is meant to be absent.
    "families": [{k: (None if pd.isna(v) else v) for k, v in row.items()}
                 for row in ledger.to_dict("records")],
    "n_families": int(len(ledger)),
    "n_tests_total": total,
    "n_tests_corrected": corrected,
    "share_corrected": corrected / max(1, total),
    "n_survivors_total": int(ledger.survivors.fillna(0).sum()),
    "principle": ("a family is a set of tests asked as one question; correcting across "
                  "families that answer different questions would be as wrong as not "
                  "correcting within one"),
}
out = json.loads((P / "fundamentals_results.json").read_text())
out["testing_ledger"] = LED
(P / "fundamentals_results.json").write_text(json.dumps(out, indent=1, default=str))
print("\n[LEDGER] written: testing_ledger")
