# The Tibia Coin Market

A quantitative study of the gold-denominated Tibia Coin market across 93 game worlds, built
from public data and rendered to a single PDF.

**Output:** `reports/tibia_coin_market_report.pdf` — 174 pages, 8 chapters, 34 exhibits,
109 tables, 5 appendices.

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
usable claim is the short one: **7 days confirmed** (+1.73% net, t = 5.3, 39 independent
windows), 30 days suggestive (6 windows), 91 days no evidence (1 window, whatever its
t-statistic says).

**A regime effect appeared and did not survive two tests.** Pooled over the history, the trade
looks like it pays four times more when cross-world dispersion is in its lowest third (+2.90% at
30 days) than in its highest (+0.75%). Two readings follow, both tested, both rejected.
Normalising each deviation by the day's dispersion is *worse* at every horizon (91-day net falls
4.04% → 0.91%). And splitting inside each period separately — so the comparison is relative calm
rather than the era's level of dispersion — shrinks the effect in training and reverses it in the
holdout (−0.17pp at 30 days): dispersion fell across the sample, so *low dispersion* and *late in
the sample* were confounded. No dispersion filter is offered. Pick the world on the raw gap. Capacity is the binding constraint: about 344M GP a month can be
deployed into the trade — the market is too thin to take size.

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

## Running it

```bash
python scripts/run_all.py               # collect, analyse, render, verify
python scripts/run_all.py --no-collect  # from cached raw data (~2 minutes)
python scripts/run_all.py --report      # figures and PDF only
```

The monetary-emission reconstruction is also available as four audit layers:

| Output | Purpose |
|---|---|
| `data/processed/creature_loot_items.csv` | Item-level probability, expected quantity, classification, NPC value, source revision and confidence |
| `data/processed/creature_gold_value.csv` | Canonical creature coverage and expected direct/potential GP per kill |
| `data/processed/gold_emission_daily.csv` | World-day direct, potential, realization-adjusted, boss-separated, cumulative and activity-normalized series |
| `reports/gold_emission_report_artifact.json` | Validated technical report manifest and bounded evidence snapshot |

Refresh the public wiki caches only when a new source snapshot is intended:

```bash
python scripts/34a_collect_loot.py
python scripts/34_gold_emission.py
python scripts/34b_collect_creatures.py
python scripts/34_gold_emission.py
python scripts/35_gold_emission_models.py
python scripts/36_gold_emission_report.py
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
pyarrow and Pillow.

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
