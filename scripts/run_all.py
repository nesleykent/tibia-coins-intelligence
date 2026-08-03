"""Run the whole pipeline in the only order that is correct.

The stages share one results.json. 06_analysis rebuilds that file from scratch and the four
stages after it load, extend and rewrite it, so running them out of order does not fail loudly -
it silently drops whichever blocks were written later. That is the failure this runner exists to
prevent: the order below is the dependency order, and the check at the end refuses to declare
success unless every block the report reads is present.

    python scripts/run_all.py              # everything, collection included
    python scripts/run_all.py --no-collect # from the cached raw data
    python scripts/run_all.py --report     # figures, PDF and interactive workspaces
"""
import json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
P = ROOT / "data" / "processed"

COLLECT = ["01_collect.py", "01b_census.py"]
BUILD = ["02_ingest_prices.py", "03_build_metadata.py", "04_population.py",
         "04b_diurnal.py", "05_clean_panel.py"]
# The fundamentals study. 16 needs a local clone of the kill-stats repository and is skipped
# when the aggregated panel already exists, since the clone is 4 GB.
FUND = ["16_killstats.py", "16b_killstats_history.py", "17_features.py", "18_predict.py", "19_regimes.py",
        "20_hierarchy.py", "21_models_extra.py",
        "22_discovery.py", "23_timeseries.py", "24_deep.py",
        "25_arbitrage.py", "26_maximise.py", "27_irreducible.py", "28_supply_demand.py",
        "34_gold_emission.py", "34b_emission_history.py", "35_gold_emission_models.py",
        "29_scenarios.py", "30_model_artifact.py", "41_group_models.py",
        "42_verify_group_models.py", "44_launch_phase_models.py",
        "45_verify_launch_models.py", "43_build_group_model_notebook.py",
        "31_participants.py",
        "32_scenario_backtest.py", "33_strategy.py", "48_stability_and_seasonality.py",
        "49_long_horizon_production.py", "50_testing_ledger.py"]
# Order matters from here: 06 recreates results.json, the rest extend it.
ANALYSE = ["06_analysis.py", "07_forecast.py", "10_advanced.py", "11_finance.py",
           "14_venues.py", "47_bazaar_history.py"] + FUND
# Every stage that writes a published artifact, and every stage that checks one. The project
# publishes four surfaces, not two, and the two Gold Emission pages are as public as the PDF.
# Listing 36 only in the analysis chain meant --report rebuilt the report, the hub and the
# dashboard while the Gold Emission report kept whatever it was last given, so it could sit a
# day behind the numbers it quotes without any stage failing.
#
# 46 runs last on purpose: it compares the finished artifacts against each other, so all of
# them must already be rebuilt for its answer to mean anything.
RENDER = ["12_art.py", "13_icons.py", "08_figures.py", "09_report.py",
          "15_verify.py", "36_gold_emission_report.py", "51_render_gold_emission_report.py",
          "38_gold_emission_dashboard.py", "37_verify_gold_emission.py",
          "39_intelligence_hub.py", "40_verify_intelligence_hub.py",
          "52_coverage_manifest.py", "46_verify_artifacts.py"]

# Every top-level block the report expects to find when it renders.
REQUIRED = ["window", "desc", "index", "stationarity", "seasonality", "events", "arbitrage",
            "integration", "fees", "cross_section", "panel", "young", "merge", "micro",
            "technical", "valuation", "robustness", "forecast", "advanced", "finance",
            "venues"]
# Blocks written by the fundamentals stages, with the stage responsible for each, so a failure
# here names what to re-run instead of surfacing as a KeyError inside the renderer.
REQUIRED_FUND = {
    "strategy": "33_strategy.py",
    "panel": "18_predict.py", "granger": "18_predict.py", "model_summary": "18_predict.py",
    "fold_stability": "18_predict.py", "regimes": "19_regimes.py",
    "shap_by_family": "19_regimes.py", "hierarchy": "20_hierarchy.py",
    "window_scheme": "21_models_extra.py", "univariate_baselines": "21_models_extra.py",
    "volatility_targets": "21_models_extra.py", "discovery": "22_discovery.py",
    "classical_models": "23_timeseries.py", "latent_factors": "23_timeseries.py",
    "deep_models": "24_deep.py", "arbitrage_structure": "25_arbitrage.py",
    "max_predictability": "26_maximise.py", "irreducibility": "27_irreducible.py",
    "supply_vs_demand": "28_supply_demand.py", "scenarios": "29_scenarios.py",
    "gold_emission": "35_gold_emission_models.py",
    "group_specific_models": "41_group_models.py",
    "launch_phase_models": "44_launch_phase_models.py",
    "participants": "31_participants.py",
}


def run(stages):
    for name in stages:
        t0 = time.time()
        print(f"\n=== {name}", flush=True)
        if name == "16_killstats.py" and (P / "kill_stats_daily.csv").exists():
            print("--- 16_killstats.py skipped; aggregated panel already present")
            continue
        r = subprocess.run([PY, str(ROOT / "scripts" / name)], cwd=ROOT)
        if r.returncode:
            raise SystemExit(f"{name} failed with exit code {r.returncode}")
        print(f"--- {name} ok in {time.time() - t0:,.0f}s", flush=True)


args = set(sys.argv[1:])
if "--report" in args:
    stages = RENDER
elif "--no-collect" in args:
    stages = BUILD + ANALYSE + RENDER
else:
    stages = COLLECT + BUILD + ANALYSE + RENDER

run(stages)

res = json.load(open(P / "results.json"))
missing = [k for k in REQUIRED if k not in res]
if missing:
    raise SystemExit(f"results.json is missing {missing} - a stage ran out of order")
fund_path = P / "fundamentals_results.json"
if fund_path.exists():
    fres = json.load(open(fund_path))
    gaps = {k: v for k, v in REQUIRED_FUND.items() if k not in fres}
    if gaps:
        raise SystemExit("fundamentals_results.json is missing "
                         + "; ".join(f"{k} (run {v})" for k, v in gaps.items()))
    print(f"fundamentals blocks present: {len(REQUIRED_FUND)}")
pdf = ROOT / "reports" / "tibia_coin_market_report.pdf"
print(f"\nall {len(stages)} stages complete; {len(REQUIRED)} result blocks present"
      + (f"; {pdf.stat().st_size / 1e6:.1f} MB written to {pdf.relative_to(ROOT)}"
         if pdf.exists() else ""))
