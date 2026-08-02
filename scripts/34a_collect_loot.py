"""Cache TibiaWiki loot-statistics pages with revision-level provenance.

The collector deliberately stores source text instead of parsed estimates.  That makes later
changes to parsing or confidence rules reproducible without querying the wiki again.

Source: https://tibia.fandom.com/wiki/Category:Loot_Statistics

    python scripts/34a_collect_loot.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import time
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "tibiawiki_loot_statistics.json"
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


def enumerate_pages() -> list[dict]:
    pages: list[dict] = []
    continuation: str | None = None
    while True:
        params: dict[str, object] = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": "Category:Loot Statistics",
            "cmnamespace": 112,
            "cmlimit": "max",
        }
        if continuation:
            params["cmcontinue"] = continuation
        payload = api_get(params)
        pages.extend(payload["query"]["categorymembers"])
        continuation = payload.get("continue", {}).get("cmcontinue")
        if not continuation:
            break
    return sorted(pages, key=lambda row: row["title"].casefold())


def save_cache(cache: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    temporary.replace(OUT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="refetch pages already cached")
    parser.add_argument("--batch-size", type=int, default=40)
    args = parser.parse_args()

    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    cached_pages = existing.get("pages", {})
    members = enumerate_pages()
    page_ids = [str(row["pageid"]) for row in members]
    if not args.refresh:
        page_ids = [page_id for page_id in page_ids if page_id not in cached_pages]

    cache = {
        "source": "TibiaWiki / Fandom, Category:Loot Statistics",
        "source_url": "https://tibia.fandom.com/wiki/Category:Loot_Statistics",
        "api_url": API,
        "collection_started_utc": existing.get(
            "collection_started_utc", dt.datetime.now(dt.UTC).isoformat()
        ),
        "collection_completed_utc": None,
        "category_member_count": len(members),
        "pages": cached_pages,
    }
    print(f"{len(members):,} pages listed; {len(page_ids):,} need collection")

    for start in range(0, len(page_ids), args.batch_size):
        batch = page_ids[start : start + args.batch_size]
        payload = api_get(
            {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "pageids": "|".join(batch),
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
            }
        )
        for page_id, page in payload["query"]["pages"].items():
            revision = page.get("revisions", [{}])[0]
            slot = revision.get("slots", {}).get("main", {})
            cached_pages[page_id] = {
                "pageid": int(page_id),
                "title": page.get("title"),
                "revision_id": revision.get("revid"),
                "revision_parent_id": revision.get("parentid"),
                "revision_timestamp_utc": revision.get("timestamp"),
                "source_url": "https://tibia.fandom.com/wiki/"
                + urllib.parse.quote(page.get("title", "").replace(" ", "_"), safe=":_()'"),
                "wikitext": slot.get("*", slot.get("content", "")),
            }
        cache["pages"] = cached_pages
        save_cache(cache)
        done = min(start + args.batch_size, len(page_ids))
        print(f"  collected {done:,}/{len(page_ids):,} missing pages")
        time.sleep(0.15)

    cache["collection_completed_utc"] = dt.datetime.now(dt.UTC).isoformat()
    cache["pages"] = dict(
        sorted(cached_pages.items(), key=lambda item: item[1]["title"].casefold())
    )
    save_cache(cache)
    print(f"[LOOT CACHE] {len(cached_pages):,} revision-audited pages -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
