# The Tibia Coin Market

A quantitative study of the gold-denominated Tibia Coin market across 93 game worlds, built
from public data and rendered to a single PDF.

**Living product and research plan:** [`PROJECT_PLAN.md`](PROJECT_PLAN.md) — verified current
state, ordered site backlog, analytical gaps, missing data, and definitions of done shared by
all agents.

**Publication requirement:** the site must publish the complete analysis contained in the PDF,
not only its executive summary or selected dashboards. Shared claims come from canonical
content and are checked for coverage and numerical agreement across artifacts.

**Interactive workspace:** `reports/intelligence_hub.html` — seven connected areas for market
overview, worlds, forecasts, general-versus-specific models, strategy, gold emission and all
34 research exhibits.

**Technical report:** `reports/tibia_coin_market_report.pdf` — 181 pages, 8 chapters,
34 exhibits, 111 tables, 5 appendices.

**Window:** 2023-01-11 to 2026-07-30 — 40,658 cleaned world-days across 93 worlds.

**Headline:** the gold price of a Tibia Coin is an exchange rate, not an asset price. Coin
supply is perfectly elastic at a money price CipSoft fixes, neither leg pays a yield, and a 2%
fee holds a 1.79% band open — a friction point recovered from prices alone, with no fee figure
supplied to the estimator. Seven established facts have exactly one joint explanation, and that
mechanism predicts every null in the study. Verdict **buy relative, not directional**,
confidence **78/100**.

**What is and is not forecastable.** The price *level* is not, and that survives fifteen model
classes, 140 engineered features and a gold-production series: nothing beats a random walk at
any horizon. A world's price *relative to the others* is forecastable at an out-of-sample R² of
0.06 to 0.11, and whether the coming week is volatile at an AUC of 0.74.

**The relative edge does clear its cost, conditionally.** Averaged over every signal past the
band and held a week, the convergence trade nets −0.019% — which is the correct answer to the
wrong question. Conditioned on the strongest decile and held longer, it nets **+1.68% at 30
days** and **+4.20% at 91**, winning on 71% and 88% of occasions, surviving a Newey-West
correction for overlapping windows, a one-day delay between signal and execution, and a
by-world and by-year concentration check. The spread version needs a short leg Tibia does not
offer; the long-only version — buy on a world trading below the cross-world mean — is worth
+0.44% a month (t = 2.1) and is not established at a quarter, where 2.3 years of history hold
only 8 independent windows. A true holdout — cutoff fitted on the training period alone,
final 50% of world-days never looked at — keeps the edge positive at every horizon, but the
usable claim is the short one: **7 days confirmed** (+1.73% net, t = 4.6, 33 independent
windows), 30 days suggestive (7 windows), 91 days no evidence (1 window, whatever its
t-statistic says). Inference is run on a per-date series, not on the pooled panel: several
worlds qualifying on one day are views of one day, since every deviation is measured against
the same cross-world mean. The sample is counted in calendar span rather than in rows.

**A regime effect appeared and did not survive two tests.** Pooled over the history, the trade
looks like it pays four times more when cross-world dispersion is in its lowest third (+2.90% at
30 days) than in its highest (+0.75%). Two readings follow, both tested, both rejected.
Normalising each deviation by the day's dispersion is *worse* at every horizon (91-day net falls
4.04% → 0.91%). And splitting inside each period separately — so the comparison is relative calm
rather than the era's level of dispersion — shrinks the effect in training and reverses it in the
holdout (−0.17pp at 30 days): dispersion fell across the sample, so *low dispersion* and *late in
the sample* were confounded. No dispersion filter is offered. Pick the world on the raw gap. Capacity is the binding constraint: about 344M GP a month can be
deployed into the trade — the market is too thin to take size.

**Two artifacts, one source of content.** The claims the report and the site both make are
defined once in `scripts/narrative.py`, with their numbers read from `data/processed`. The PDF
renders each as a labelled paragraph (§7.6.4); the site renders it as a card with fact tiles
and, where the claim names one, an interactive view of the data behind it — the full
strategy grid by decile and horizon, or the in-sample-against-holdout table. Adding a finding
there makes it appear in both; there is nothing to port across. `scripts/46_verify_artifacts.py`
runs last in the pipeline as a backstop: it computes each headline fact once and fails the
build if any artifact that states it disagrees, reporting facts an artifact simply omits as
coverage gaps rather than failures.

**The Char Bazaar, six years of it.** NabBot publishes a year page from 2020 onward: six annual
TC totals and 65 monthly auction counts. The venue is not growing — auctions created fell 38%
from 2021 to 2025 while the mean price per completed auction rose from 2,249 to 3,347 TC, so
coins exchanged sit flat between 488M and 607M a year. Fewer character sales at higher prices.

**A units error, found late and corrected throughout.** `day_sold` / `day_bought` count
25-coin lots, not coins: the values run 1, 2, 3 with only 3.7% multiples of 25, which a coin
count cannot be, since the Market accepts no other quantity. Every traded-volume figure is
converted at the lot. The order book is the opposite case — minimum 25, every amount a whole
lot, quoted against a per-coin price — so those are already coins and are left alone. Two
verifier checks now re-derive both classifications from the data on every build.

**The gold-supply story does not survive a monetary reconstruction.** 21,412 world-days of kill
statistics were joined to revision-audited TibiaWiki loot tables and guaranteed player-to-NPC
prices. Reliable models cover 96.2% of non-boss deaths and separate direct coins, maximum
potential NPC sales, and 25%/50%/75%/100% realization scenarios. On identical fixed-effects
samples, all 1-, 7-, and 30-day headline coefficients overlap zero. Monetary weighting does not
improve holdout forecasts: the best result is raw kill counts at one day, only 0.17% better than
a random walk; the monetary variants are worse. Behavioural variables remain far more useful.

**The model ships.** `models/deviation_model.pkl` predicts the seven-day change in a world's
relative position with a conformal interval, and refuses to emit a level forecast:

```bash
python scripts/30_model_artifact.py --predict   # writes latest_predictions.csv
```

**A segment-specific family ships beside it.** `models/specific_models.pkl.gz` contains 11
models grouped first by PvP type, then BattlEye cohort and region. Groups below five worlds
pool locations first and BattlEye cohorts second; PvP types are never mixed. The final untouched
holdout keeps the general model as the default (1.867% RMSE versus 1.885% specific), while the
specific scores remain available for diagnosis and comparison:

```bash
python scripts/41_group_models.py
python scripts/42_verify_group_models.py
```

**Launch phase is modelled separately.** Regular worlds from creation through age 540 days
receive one experimental model per PvP type. The family has 21 training-eligible worlds and
18 current scores; Retro Open carries a low-sample warning. A later-date holdout made entirely
of unseen launch worlds keeps the mature general model as the default (10.653% RMSE versus
11.753% launch and 11.051% zero change):

```bash
python scripts/44_launch_phase_models.py
python scripts/45_verify_launch_models.py
```

## Running it

```bash
python scripts/run_all.py               # collect, analyse, render, verify
python scripts/run_all.py --no-collect  # from cached raw data (~2 minutes)
python scripts/run_all.py --report      # figures, PDF and interactive workspaces
```

Serve the repository root and open the workspace:

```bash
python3 -m http.server 4173
# then open http://127.0.0.1:4173/
```

The workspace automatically refreshes its price, world, forecast, general/specific model,
strategy and prediction datasets while served over HTTP. It keeps a complete embedded snapshot
for direct-file and offline use, stores the active view and filters in the URL, embeds the
gold-emission explorer, and turns every report exhibit into a searchable detail view.

The monetary-emission reconstruction is also available as four audit layers:

| Output | Purpose |
|---|---|
| `data/processed/creature_loot_items.csv` | Item-level probability, expected quantity, classification, NPC value, source revision and confidence |
| `data/processed/creature_gold_value.csv` | Canonical creature coverage and expected direct/potential GP per kill |
| `data/processed/gold_emission_daily.csv` | World-day direct, potential, realization-adjusted, boss-separated, cumulative and activity-normalized series |
| `reports/gold_emission_report_artifact.json` | Validated technical report manifest and bounded evidence snapshot |
| `reports/gold_emission_dashboard.html` | Self-contained interactive dashboard with world, time, realization and series filters |

Open `reports/gold_emission_dashboard.html` directly in a browser for its embedded offline
snapshot. When the project is served over HTTP, the dashboard automatically refreshes from
`data/processed/gold_emission_daily.csv`, preserves shareable URL filters, and falls back to
the embedded data if that file is unavailable. A newer CSV can also be selected through the
**Load updated CSV** control.

```bash
python3 -m http.server 4173
# then open http://127.0.0.1:4173/reports/gold_emission_dashboard.html
```

Regenerate the embedded snapshot after the monetary pipeline changes:

```bash
python scripts/38_gold_emission_dashboard.py
```

Refresh the public wiki caches only when a new source snapshot is intended:

```bash
python scripts/34a_collect_loot.py
python scripts/34_gold_emission.py
python scripts/34b_collect_creatures.py
python scripts/34_gold_emission.py
python scripts/35_gold_emission_models.py
python scripts/36_gold_emission_report.py
python scripts/38_gold_emission_dashboard.py
python scripts/37_verify_gold_emission.py
```

The two-pass creature sequence is deliberate: the first pass creates the canonical kill-stat
name universe; the classification collector then resolves boss, event and explicit no-loot
evidence before the final monetary pass.

Stage order is not incidental. The five modelling stages share one `results.json`;
`06_analysis.py` rebuilds that file from scratch and the four after it load, extend and rewrite
it. Running them out of sequence does not fail — it silently drops whichever blocks were
written later. `run_all.py` exists to enforce the order and refuses to report success unless
all 21 result blocks are present.

`scripts/15_verify.py` runs last. It reads the text back out of the finished PDF and checks it
against the data: that every cross-reference resolves, that table and exhibit numbering is
contiguous, that every contents entry points at the right page, that all 93 worlds and all 408
forecast cells are printed, that the currency convention holds, and that the figures agree with
the body text. It exits non-zero on failure, so a broken build cannot pass quietly.

Python 3.14 with pandas, numpy, statsmodels, scipy, arch, matplotlib, reportlab, svglib, pypdf,
pyarrow, Pillow, nbformat, nbclient and ipykernel.

## Sources, and the terms they were used under

| Source | Used for | Note |
|---|---|---|
| `tibia-warzones-schedule` archive | The price panel, 41,584 raw snapshots | A deduplicated third-party mirror of the TibiaMarket.top MarketValues model — **not** an official CipSoft feed |
| TibiaMarket.top | Order books, event calendar, item metadata | `item_id 22118`; the `/events` endpoint carries no world dimension |
| TibiaWiki / Fandom | Empirical loot frequencies, quantities and creature classification | Each cached page records revision ID, source timestamp and collection timestamp |
| TibiaData v4 | World attributes, news archive | Current snapshot only, no history |
| GuildStats.eu | Creation dates, merge register, activity history, census | `robots.txt: Allow: /` |
| TibiaVIP | Character roster per world | Supplied as a saved page. **The population endpoints are disallowed by `robots.txt` and were not collected.** |
| tibia.com | Tibia Token mechanics | Service agreement |
| BNB Smart Chain | Token supply, liquidity pools, quoted price | Read directly from contract `0x111B95C2…45E446`; cached and block-stamped |
| NabBot | Char Bazaar annual turnover | Third-party aggregate, treated as a lower bound |

Network reads are cached under `data/raw/` with the block height or date they were taken at, so
a rebuild reproduces the same figures and does not depend on the network.

## What the report will not tell you

The driver of the common gold price level is unidentified. Gross monster-loot emission can now
be estimated, but the initial gold stock, actual NPC-sale realization, and measurable sink
history remain unavailable. The leading explanation — gold accumulating faster than it is
destroyed — therefore remains plausible but untested as a net-stock mechanism. The report says
so rather than issuing a directional call on the strength of it.

Every claim in the document is labelled as documented mechanic, observed data, statistical
relationship, economic interpretation, hypothesis, forecast, analyst judgement or limitation,
so a reader can see which kind of thing they are being told at every point.

## Attribution

Tibia is a registered trademark of CipSoft GmbH; all game content and artwork are copyright
CipSoft GmbH and appear here under the terms distributed with the official fankit. This is an
independent study, is not published for payment, and is not endorsed by or affiliated with
CipSoft. The analysis, the opinions and any errors are the author's alone.
