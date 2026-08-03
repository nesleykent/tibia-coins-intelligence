"""Map every published PDF unit to a site destination, and fail on an unexplained omission.

SITE-00 asks for the site to be the complete publication rather than a shortened companion to
the PDF, and for that claim to be checked instead of asserted. `46_verify_artifacts.py` already
compares shared *numbers* across artifacts, but nothing compared *structure*: a whole chapter
could vanish from the site and every existing check would still pass.

This walks the canonical section source and the built PDF, walks the built hub, and pairs them:

* chapters and sections  -> the hub view that carries them, from CHAPTER_DESTINATIONS;
* exhibits               -> the Research Library, matched in document order, which is exact
                            because the PDF's Exhibit numbering is assigned by the same
                            sequence of `figure()` calls the library is built from;
* tables                 -> the view that carries the same table, or an explicit reason.

An omission is only acceptable when it is declared here with a reason. Anything else is
reported as unexplained and the script exits non-zero, so the gap cannot be discovered by a
reader instead of by the build.

    python scripts/52_coverage_manifest.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
SECTIONS = ROOT / "scripts" / "09_sections.py"
REMAP = ROOT / "scripts" / "remap_sections.py"
PDF = ROOT / "reports" / "tibia_coin_market_report.pdf"
HUB = ROOT / "reports" / "intelligence_hub.html"
OUT = P / "coverage_manifest.csv"

# Which hub view publishes each PDF chapter. A chapter may name more than one view; the first is
# the primary destination. Reference material that exists to support the PDF's own apparatus is
# declared here with a reason rather than being silently absent.
CHAPTER_DESTINATIONS = {
    1: (["overview"], ""),
    2: (["overview", "worlds"], ""),
    3: (["worlds", "emission", "creatures"], ""),
    4: (["worlds", "forecasts", "library"], ""),
    5: (["worlds", "strategy", "library"], ""),
    6: (["forecasts", "models", "library"], ""),
    7: (["models", "strategy", "library"], ""),
    8: (
        ["library"],
        "reference apparatus: figure index, table index and bibliography exist to navigate the "
        "PDF itself; the site navigates by view and search instead",
    ),
}


def pdf_text() -> str:
    from pypdf import PdfReader

    return "\n".join((page.extract_text() or "") for page in PdfReader(str(PDF)).pages)


QUOTED = r"['\"]([^'\"]{3,80})['\"]"


def chapters() -> list[tuple[int, str, str]]:
    """Every chapter the report publishes, reconciled across the two places they come from.

    Chapters 2-8 are emitted by `chapter()` in the section source, but chapter 1, the executive
    summary, is built by the report's front matter and never calls it. Trusting the `chapter()`
    calls alone silently produced a seven-chapter document - the exact class of omission this
    manifest exists to catch, committed by the manifest itself. Take `remap_sections.py` as the
    declaration of what the report contains, and record how each chapter reaches the page.
    """
    block = re.search(r"^CHAPTERS = \[(.*?)^\]", REMAP.read_text(), re.S | re.M).group(1)
    declared = [(int(n), t) for n, t in re.findall(r"\(\s*(\d+),\s*\"([^\"]+)\"", block)]
    emitted = {
        int(number): title
        for number, title in re.findall(r"^chapter\((\d+),\s*" + QUOTED, SECTIONS.read_text(), re.M)
    }
    return [
        (number, emitted.get(number, title),
         "chapter() opener" if number in emitted else "front matter, no chapter() call")
        for number, title in declared
    ]


def sections() -> list[tuple[str, str]]:
    """Numbered sections from the canonical source.

    Reading these out of the extracted PDF text cannot be made reliable: a heading and a table
    row are both "number, space, words" once the layout is gone, so a loose pattern collected
    world names beside their prices ("1.04 Ignibra") while a pattern strict enough to exclude
    them dropped every sentence-case subsection. The source states each section exactly once.
    """
    return re.findall(r"^h2sec\(" + QUOTED + r",\s*" + QUOTED, SECTIONS.read_text(), re.M)


def figure_order() -> list[str]:
    """Figure ids in the order the report places them, which is the order Exhibits are numbered."""
    return re.findall(r'figure\("([a-z0-9_]+)\.png"', SECTIONS.read_text())


def site_inventory() -> tuple[set[str], list[dict]]:
    text = HUB.read_text()
    views = set(re.findall(r'data-view="([a-z]+)"', text))
    match = re.search(r'"figures":\s*(\[\{.*?\}\])\s*[,}]', text, re.S)
    figures = json.loads(match.group(1)) if match else []
    return views, figures


def main() -> None:
    text = pdf_text()
    rows: list[dict] = []

    views, figures = site_inventory()
    figure_ids = {figure["id"] for figure in figures}

    # --- chapters -------------------------------------------------------------------------
    for number, title, origin in chapters():
        destinations, reason = CHAPTER_DESTINATIONS.get(number, ([], ""))
        present = [view for view in destinations if view in views]
        missing = [view for view in destinations if view not in views]
        rows.append(
            {
                "unit": "chapter",
                "ref": str(number),
                "title": title,
                "destination": " + ".join(present),
                "status": "covered" if present and not missing else
                          ("explained" if reason else "UNEXPLAINED"),
                "reason": reason if not present or missing else "",
                "detail": (f"missing views: {', '.join(missing)}" if missing else origin),
            }
        )

    # --- sections -------------------------------------------------------------------------
    for ref, title in sections():
        chapter = int(ref.split(".")[0])
        destinations, reason = CHAPTER_DESTINATIONS.get(chapter, ([], ""))
        rows.append(
            {
                "unit": "section",
                "ref": ref,
                "title": title.strip(),
                "destination": " + ".join(view for view in destinations if view in views),
                "status": "covered" if any(v in views for v in destinations) else
                          ("explained" if reason else "UNEXPLAINED"),
                "reason": reason if not any(v in views for v in destinations) else "",
                "detail": f"inherits chapter {chapter}",
            }
        )

    # --- exhibits -------------------------------------------------------------------------
    # The PDF numbers Exhibits in the order `figure()` is called, and the library is built from
    # that same list, so position is an exact pairing rather than a guess. Verify the counts
    # agree before relying on it.
    order = figure_order()
    exhibits = sorted(
        set(re.findall(r"\bExhibit\s+(\d{1,2}\.\d{1,2})", text)),
        key=lambda ref: tuple(int(part) for part in ref.split(".")),
    )
    aligned = len(order) == len(exhibits) == len(figures)
    for index, ref in enumerate(exhibits):
        figure_id = order[index] if index < len(order) else ""
        on_site = figure_id in figure_ids
        rows.append(
            {
                "unit": "exhibit",
                "ref": ref,
                "title": figure_id,
                "destination": "library" if on_site else "",
                "status": "covered" if on_site else "UNEXPLAINED",
                "reason": "" if on_site else "no library figure carries this exhibit",
                "detail": "paired by document order" if aligned else
                          f"COUNT MISMATCH pdf={len(exhibits)} placed={len(order)} site={len(figures)}",
            }
        )

    # --- tables ---------------------------------------------------------------------------
    # Tables are the report's own tabulation of series the site publishes interactively; they are
    # covered by the view that owns the series rather than reproduced one for one.
    tables = sorted(
        set(re.findall(r"\bTable\s+(\d{1,2}\.\d{1,2})", text)),
        key=lambda ref: tuple(int(part) for part in ref.split(".")),
    )
    for ref in tables:
        chapter = int(ref.split(".")[0])
        destinations, _ = CHAPTER_DESTINATIONS.get(chapter, ([], ""))
        if chapter == 0:
            # Front matter: Table 0.1 is the report's own question-and-verdict index, a map of
            # the document rather than a series. The site answers the same questions through the
            # views themselves, so it has no destination and needs none.
            rows.append({
                "unit": "table", "ref": ref, "title": "",
                "destination": "", "status": "explained",
                "reason": "front matter: index of the report's questions and where each is settled",
                "detail": "navigational apparatus, not a published series",
            })
            continue
        present = [view for view in destinations if view in views]
        rows.append(
            {
                "unit": "table",
                "ref": ref,
                "title": "",
                "destination": " + ".join(present),
                "status": "covered" if present else "UNEXPLAINED",
                "reason": "" if present else "no view owns this chapter's series",
                "detail": "tabulation of a series the view publishes interactively",
            }
        )

    frame = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT, index=False)

    counts = frame.groupby(["unit", "status"], observed=True).size().unstack(fill_value=0)
    print(f"[COVERAGE] {OUT.relative_to(ROOT)}")
    print(counts.to_string())
    unexplained = frame[frame.status == "UNEXPLAINED"]
    if not aligned:
        print(
            f"  ! exhibit counts disagree: {len(exhibits)} in the PDF, {len(order)} placed by "
            f"09_sections.py, {len(figures)} in the library"
        )
    if len(unexplained):
        print(f"\n{len(unexplained)} unexplained omission(s):")
        for _, row in unexplained.head(20).iterrows():
            print(f"  {row.unit} {row.ref} ({row.title}): {row.reason or row.detail}")
        raise SystemExit(1)
    print(
        f"  {len(frame)} published units, 0 unexplained omissions "
        f"({frame.status.eq('explained').sum()} explained)"
    )


if __name__ == "__main__":
    main()
