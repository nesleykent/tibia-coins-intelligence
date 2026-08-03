#!/usr/bin/env python3
"""Build the standalone gold-emission dashboard and creature GP reference pages.

Both workspaces live in ``scripts/emission_view.py`` so that these pages and the
matching intelligence-hub views cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path

import emission_view


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "gold_emission_dashboard.html"
RANKING_OUTPUT = ROOT / "reports" / "creature_gp_per_kill.html"


SHELL = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Gold Emission from Tibia Kill Statistics</title>
  <style>
    :root {
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #12203a;
      background: #ffffff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-width: 320px; background: #fff; }
    html { scroll-behavior: smooth; }
    a { color: #1d4ed8; }
    .em-page { width: min(1480px, 100%); margin: 0 auto; padding: 28px 24px 56px; }
    .em-page h1 { margin: 0 0 6px; font-size: clamp(28px, 3vw, 42px); line-height: 1.08; letter-spacing: -.035em; }
    .em-page-intro { margin: 0 0 18px; max-width: 78ch; color: #667085; font-size: 14px; line-height: 1.55; }
    .em-page-links { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 20px; }
    .em-page-links a {
      display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px;
      border: 1px solid #aeb9cb; border-radius: 7px; font-size: 13px; font-weight: 700;
      text-decoration: none; color: #174ea6;
    }
    .em-page-links a:hover { background: #f7f9fc; }
    @media (max-width: 680px) { .em-page { padding: 20px 14px 40px; } }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
    }
    @media print { .em-page { width: 100%; padding: 0; } }
__STYLE__
  </style>
</head>
<body>
  <main class="em-page">
    <h1>Gold Emission from Tibia Kill Statistics</h1>
    <p class="em-page-intro">
      Reconstructed gold production by world and date: the GP creatures drop directly, plus the most
      NPCs would pay for the loot they drop. GP means Tibia gold pieces; TC means Tibia Coins.
    </p>
    <nav class="em-page-links" aria-label="Related pages">
      <a href="creature_gp_per_kill.html">Which creatures pay the most per kill →</a>
      <a href="intelligence_hub.html?view=emission">Open inside Tibia Coins Intelligence →</a>
    </nav>
__MARKUP__
  </main>

  <script>
  "use strict";
  const EMISSION_DATA = __DATA__;
  </script>
  <script>
__SCRIPT__
  </script>
  <script>
  "use strict";
  (function () {
    let pushed = false;
    const write = (params, mode) => {
      const search = new URLSearchParams(params).toString();
      const url = `${location.pathname}${search ? `?${search}` : ""}${location.hash}`;
      try {
        if (mode === "push") { history.pushState(null, "", url); pushed = true; }
        else if (mode === "pop" && pushed) { pushed = false; history.back(); }
        else { history.replaceState(null, "", url); }
      } catch (_) { /* file:// URLs reject history writes */ }
    };
    window.EmissionView.mount({
      root: document.getElementById("emissionApp"),
      data: EMISSION_DATA,
      params: new URLSearchParams(location.search),
      onStateChange: write
    });
    window.addEventListener("popstate", () => {
      window.EmissionView.applyParams(new URLSearchParams(location.search));
    });
  })();
  </script>
</body>
</html>
"""


RANKING_SHELL = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Which creatures pay the most GP per kill</title>
  <style>
    :root {
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #12203a;
      background: #ffffff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-width: 320px; background: #fff; }
    a { color: #1d4ed8; }
    .em-page { width: min(1240px, 100%); margin: 0 auto; padding: 28px 24px 56px; }
    .em-page h1 { margin: 0 0 6px; font-size: clamp(28px, 3vw, 42px); line-height: 1.08; letter-spacing: -.035em; }
    .em-page-intro { margin: 0 0 18px; max-width: 78ch; color: #667085; font-size: 14px; line-height: 1.55; }
    .em-page-links { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 20px; }
    .em-page-links a {
      display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px;
      border: 1px solid #aeb9cb; border-radius: 7px; font-size: 13px; font-weight: 700;
      text-decoration: none; color: #174ea6;
    }
    .em-page-links a:hover { background: #f7f9fc; }
    @media (max-width: 680px) { .em-page { padding: 20px 14px 40px; } }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition: none !important; }
    }
__STYLE__
  </style>
</head>
<body>
  <main class="em-page">
    <h1>Which creatures pay the most GP per kill</h1>
    <p class="em-page-intro">
      Average GP one kill is worth: the gold the creature drops directly, plus the most NPCs would
      pay for the rest of its loot. Use it to compare hunting targets. It does not say how much gold
      a world produced, because that also depends on how many players hunt each creature.
    </p>
    <nav class="em-page-links" aria-label="Related pages">
      <a href="gold_emission_dashboard.html">← Gold emission by world and date</a>
      <a href="intelligence_hub.html?view=creatures">Open inside Tibia Coins Intelligence →</a>
    </nav>
__MARKUP__
  </main>

  <script>
  "use strict";
  const CREATURE_DATA = __DATA__;
  </script>
  <script>
__SCRIPT__
  </script>
  <script>
  "use strict";
  window.EmissionView.mountRanking({
    root: document.getElementById("creatureRanking"),
    data: CREATURE_DATA
  });
  </script>
</body>
</html>
"""


def main() -> None:
    payload = emission_view.build_payload()
    output = (
        SHELL.replace("__STYLE__", emission_view.STYLE)
        .replace("__MARKUP__", emission_view.MARKUP)
        .replace("__SCRIPT__", emission_view.SCRIPT)
        .replace("__DATA__", emission_view.embed(payload))
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding="utf-8")

    ranking_payload = emission_view.build_ranking_payload()
    ranking_output = (
        RANKING_SHELL.replace("__STYLE__", emission_view.STYLE)
        .replace("__MARKUP__", emission_view.RANKING_MARKUP)
        .replace("__SCRIPT__", emission_view.SCRIPT)
        .replace("__DATA__", emission_view.embed(ranking_payload))
    )
    RANKING_OUTPUT.write_text(ranking_output, encoding="utf-8")
    print(
        f"[GOLD DASHBOARD] wrote {OUTPUT.relative_to(ROOT)} "
        f"with {payload['meta']['worldDays']:,} world-days and "
        f"{RANKING_OUTPUT.relative_to(ROOT)} with "
        f"{ranking_payload['meta']['creatures']:,} creatures"
    )


if __name__ == "__main__":
    main()
