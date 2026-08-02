"""Cache TibiaWiki creature-page classifications for creatures seen in kill statistics.

This source is used only for evidence-backed special-creature flags (boss, event, summon,
training, and no-loot). It does not supply player-market prices.

    python scripts/34b_collect_creatures.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import time
import urllib.parse
import urllib.request

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "creature_gold_value.csv"
OUT = ROOT / "data" / "raw" / "tibiawiki_creatures.json"
API = "https://tibia.fandom.com/api.php"
USER_AGENT = "TibiaCoinMarketResearch/1.0 (public-data research; revision-audited cache)"


def api_get(params: dict[str, object], retries: int = 5) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def save(cache: dict) -> None:
    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    temporary.replace(OUT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    if not INPUT.exists():
        raise SystemExit("run scripts/34_gold_emission.py once to build the canonical name list")

    creatures = pd.read_csv(INPUT)
    titles = sorted(
        set(creatures.wiki_title.dropna().astype(str))
        | set(creatures.canonical_name.dropna().astype(str))
    )
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    pages = existing.get("pages", {})
    if not args.refresh:
        titles = [title for title in titles if title.casefold() not in pages]

    cache = {
        "source": "TibiaWiki / Fandom creature pages",
        "api_url": API,
        "collection_started_utc": existing.get(
            "collection_started_utc", dt.datetime.now(dt.UTC).isoformat()
        ),
        "collection_completed_utc": None,
        "pages": pages,
    }
    print(f"{len(titles):,} creature titles need collection")
    for start in range(0, len(titles), args.batch_size):
        batch = titles[start : start + args.batch_size]
        continuation: dict[str, str] = {}
        batch_pages: dict[str, dict] = {}
        while True:
            params: dict[str, object] = {
                "action": "query",
                "format": "json",
                "prop": "revisions|categories",
                "titles": "|".join(batch),
                "redirects": 1,
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
                "cllimit": "max",
                **continuation,
            }
            payload = api_get(params)
            for page_id, page in payload["query"]["pages"].items():
                record = batch_pages.setdefault(
                    page_id,
                    {
                        "pageid": int(page_id),
                        "title": page.get("title"),
                        "missing": "missing" in page,
                        "categories": [],
                    },
                )
                record["categories"].extend(
                    category["title"].split(":", 1)[-1]
                    for category in page.get("categories", [])
                )
                revisions = page.get("revisions") or []
                if revisions and "wikitext" not in record:
                    revision = revisions[0]
                    slot = revision.get("slots", {}).get("main", {})
                    record.update(
                        {
                            "revision_id": revision.get("revid"),
                            "revision_timestamp_utc": revision.get("timestamp"),
                            "source_url": "https://tibia.fandom.com/wiki/"
                            + urllib.parse.quote(
                                page.get("title", "").replace(" ", "_"), safe=":_()'"
                            ),
                            "wikitext": slot.get("*", slot.get("content", "")),
                        }
                    )
            continuation = payload.get("continue", {})
            if not continuation:
                break
        for record in batch_pages.values():
            record["categories"] = sorted(set(record["categories"]))
            pages[str(record.get("title", "")).casefold()] = record
        cache["pages"] = pages
        save(cache)
        print(f"  collected {min(start + args.batch_size, len(titles)):,}/{len(titles):,}")
        time.sleep(0.15)

    cache["collection_completed_utc"] = dt.datetime.now(dt.UTC).isoformat()
    cache["pages"] = dict(sorted(pages.items()))
    save(cache)
    print(f"[CREATURE CACHE] {len(pages):,} pages -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
