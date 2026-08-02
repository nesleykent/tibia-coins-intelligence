"""Build and execute the reproducible general, specific and launch model notebook.

    python scripts/43_build_group_model_notebook.py
"""
from __future__ import annotations

import pathlib

import nbformat as nbf
from nbclient import NotebookClient


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "general_vs_specific_models.ipynb"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def main() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook["metadata"]["language_info"] = {"name": "python", "version": "3.14"}
    notebook["cells"] = [
        markdown(
            """
# General, group-specific and launch-phase Tibia Coin models

## tl;dr

The hierarchical family creates one model per sufficiently populated PvP × BattlEye ×
region group, pooling locations first and BattlEye cohorts second when samples are small.
PvP types are never mixed. On the untouched final holdout, the general model remains the
default because it has lower aggregate RMSE. The specific family is retained as an
interactive diagnostic and alternative score. A second experimental family covers regular
worlds through age 540 days with one model per PvP type; later-date, unseen-world holdout
evidence also keeps the mature general model as the default.
"""
        ),
        markdown(
            """
## Context & Methods

Both families predict the seven-day change in a world's log-price deviation from the
cross-world mean. The first 70% of dates train estimator selection, the next 15% validate
pooling sensitivity, and the final 15% are opened once for comparison. Seven dates are purged
between estimation and evaluation windows.

Launch models use deviation from the mature-world mean, include world age and observation-age
features, and are tested on later dates from launch worlds excluded from estimation.

### Key assumptions

- BattlEye green means protected since world release; yellow means protection was retrofitted.
- The preferred group minimum is five eligible worlds.
- Pooling order is location, then BattlEye; PvP is always isolated.
- Lower RMSE is better. A positive “specific improvement” means the specific family wins.
- Launch phase is fixed at 0–540 days; PvP types are never pooled and BattlEye is not split
  because all but one training-eligible launch world are green.
"""
        ),
        code(
            """
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd()
P = ROOT / "data" / "processed"
registry = pd.read_csv(P / "specific_model_registry.csv")
comparison = pd.read_csv(P / "specific_model_comparison.csv")
sensitivity = pd.read_csv(P / "specific_model_sensitivity.csv")
latest = pd.read_csv(P / "latest_specific_predictions.csv")
results = json.loads((P / "specific_model_results.json").read_text())
launch_registry = pd.read_csv(P / "launch_model_registry.csv")
launch_comparison = pd.read_csv(P / "launch_model_comparison.csv")
launch_latest = pd.read_csv(P / "latest_launch_predictions.csv")
launch_results = json.loads((P / "launch_model_results.json").read_text())
"""
        ),
        markdown("## Data"),
        code(
            """
coverage = (
    registry.groupby("group_level", observed=True)
    .agg(worlds=("world", "nunique"), models=("group_id", "nunique"))
    .rename(index={
        "pvp_battleye_region": "Exact PvP × BattlEye × region",
        "pvp_battleye": "Regions pooled",
        "pvp": "Regions + BattlEye pooled",
    })
)
coverage
"""
        ),
        code(
            """
groups = (
    registry[[
        "group_id", "pvp_type", "group_level", "model_worlds",
        "assigned_worlds", "selected_estimator", "low_sample_warning",
    ]]
    .drop_duplicates("group_id")
    .sort_values(["pvp_type", "group_level", "group_id"])
)
groups
"""
        ),
        code(
            """
launch_coverage = (
    launch_registry.groupby(["pvp_type", "cohort"], observed=True)
    .world.nunique()
    .unstack(fill_value=0)
)
launch_coverage.loc["Active scores"] = {
    "train": launch_latest.world.nunique(),
    "validation": 0,
    "holdout": 0,
}
launch_coverage
"""
        ),
        markdown("## Results"),
        code(
            """
headline = comparison.query("scope == 'all'")[[
    "n_worlds", "n_dates", "general_rmse_pct", "specific_rmse_pct",
    "specific_improvement_pct", "dm_p_specific_vs_general", "better_model",
]]
headline
"""
        ),
        code(
            """
by_pvp = comparison.query("scope == 'pvp_type'").copy()
chart = by_pvp.set_index("scope_value")[["general_rmse_pct", "specific_rmse_pct"]]
ax = chart.plot.barh(figsize=(9, 4.8), color=["#60a5fa", "#f59e0b"])
ax.set_xlabel("Untouched-holdout RMSE (%)")
ax.set_ylabel("")
ax.set_title("General and specific model error by PvP type")
ax.legend(["General", "Specific"], frameon=False)
plt.tight_layout()
plt.show()
"""
        ),
        code(
            """
sensitivity[[
    "min_group_worlds", "n_models", "n_exact_worlds",
    "n_region_pooled_worlds", "n_pvp_pooled_worlds",
    "general_rmse_pct", "specific_rmse_pct",
]]
"""
        ),
        code(
            """
launch_headline = launch_comparison[[
    "scope_value", "n_worlds", "launch_rmse_pct",
    "general_rmse_pct", "zero_rmse_pct",
    "launch_improvement_vs_general_pct", "better_model",
]]
launch_headline
"""
        ),
        code(
            """
launch_chart = (
    launch_comparison.query("scope == 'pvp_type'")
    .set_index("scope_value")[[
        "launch_rmse_pct", "general_rmse_pct", "zero_rmse_pct",
    ]]
)
ax = launch_chart.plot.barh(figsize=(9, 4.5), color=["#f59e0b", "#60a5fa", "#94a3b8"])
ax.set_xlabel("Unseen-world/later-date holdout RMSE (%)")
ax.set_ylabel("")
ax.set_title("Launch-specific, mature-general and zero-change error by PvP")
ax.legend(["Launch", "General", "Zero change"], frameon=False)
plt.tight_layout()
plt.show()
"""
        ),
        markdown(
            """
## Takeaways

- The requested hierarchy is fully represented: every eligible world receives exactly one
  model, and no training pool crosses PvP types.
- The five-world threshold is preferable to four in validation, but six is almost identical;
  the conclusion is not driven by one arbitrary cutoff.
- The general model wins the aggregate untouched holdout. The segment-specific scores should
  therefore be treated as exploratory context rather than a replacement production default.
- Retro Hardcore PvP has only three eligible worlds. It remains isolated, uses regularized
  Ridge, and carries a visible low-sample warning.
- The launch family has 21 training-eligible worlds and 18 active scores across three
  PvP-specific models. It is statistically worse than the mature general mapping overall,
  so it ships as an experimental diagnostic rather than the default.
- Retro Open launch has four training-eligible worlds and carries a low-sample warning.
"""
        ),
        code(
            """
overall = comparison.query("scope == 'all'").iloc[0]
print(
    f"Verified conclusion: {overall.better_model} wins — "
    f"general RMSE {overall.general_rmse_pct:.3f}% vs "
    f"specific {overall.specific_rmse_pct:.3f}%, "
    f"specific improvement {overall.specific_improvement_pct:+.2f}%."
)
launch_overall = launch_comparison.query("scope == 'all'").iloc[0]
print(
    f"Launch conclusion: {launch_overall.better_model} wins — "
    f"launch RMSE {launch_overall.launch_rmse_pct:.3f}% vs "
    f"general {launch_overall.general_rmse_pct:.3f}% and "
    f"zero {launch_overall.zero_rmse_pct:.3f}%."
)
"""
        ),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    nbf.write(notebook, OUTPUT)
    print(f"[NOTEBOOK] wrote and executed {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
