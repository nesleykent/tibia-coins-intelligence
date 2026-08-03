"""Reconstruct daily GP emission from creature kill statistics.

Only two channels enter the model:

* currency dropped directly by a creature;
* loot with a guaranteed player-to-NPC sale price.

Player-market values are always zero.  TibiaWiki empirical loot statistics supply drop
frequencies and quantities.  The cached TibiaMarket item metadata supplies NPC buyer prices.
Creatures without a sufficiently sampled empirical Loot2 table remain explicitly uncovered.

    python scripts/34_gold_emission.py [path-to-tibia-kill-stats-clone]
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
SRC_ROOT = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1 else "/tmp/tibia-kill-stats"
)
SRC = SRC_ROOT / "data"
LOOT_CACHE = RAW / "tibiawiki_loot_statistics.json"
ITEM_META = RAW / "tm_item_metadata.json"
CREATURE_CACHE = RAW / "tibiawiki_creatures.json"
ALIAS_SOURCE = SRC_ROOT / "normalize-names.mjs"
MIN_RELIABLE_SAMPLES = 100
COVERAGE_THRESHOLD = 0.80
REALIZATION_RATES = (0.25, 0.50, 0.75, 1.00)
PSEUDO_PREFIXES = ("(", "[")
COINS = {"gold coin": 1.0, "platinum coin": 100.0, "crystal coin": 10_000.0}

# Player-to-NPC buyers that a character cannot reach under ordinary conditions. The main series
# uses the highest NPC offer of all, which assumes the hunter reaches the best buyer; the
# conservative series drops these so the reader can price that assumption instead of trusting it.
# Rashid trades only after the Travelling Trader Quest and moves city every day; a Hireling is
# bought from the store for Tibia Coins, so its offer is not available to an arbitrary character.
GATED_BUYERS = {
    "rashid": "Travelling Trader Quest; buyer rotates city daily",
    "hireling": "bought from the store with Tibia Coins",
}
# Premium account is treated as an ordinary condition: the worlds in this panel are hunted almost
# entirely by premium characters, so premium-only travel is not counted as an access gate.
ACCESS_BASELINE_NOTE = "premium travel treated as ordinary; quest- and store-gated buyers excluded"

# Step 5 intermediate scenario. Loot pickup and NPC selling are not observed anywhere in the
# available data (PROJECT_PLAN DATA-05), so these are declared assumptions, not measurements.
# Item weight is absent from the item metadata, so value density and the way each category is
# actually handled on a hunt stand in for carry cost. Every rate is a documented guess and the
# flat 25/50/75/100% ladder remains the primary sensitivity device.
CATEGORY_REALIZATION = {
    "valuables": 0.95,
    "creature products": 0.90,
    "amulets": 0.80,
    "rings": 0.80,
    "wands rods": 0.45,
    "distance weapons": 0.40,
    "swords": 0.35,
    "axes": 0.35,
    "clubs": 0.35,
    "fist weapons": 0.35,
    "shields": 0.35,
    "armors": 0.35,
    "legs": 0.35,
    "helmets hats": 0.35,
    "boots": 0.35,
    "quiver": 0.25,
    "containers": 0.20,
    "decoration": 0.20,
    "tools": 0.20,
    "others": 0.20,
    "potions": 0.10,
    "food": 0.05,
}
CATEGORY_REALIZATION_DEFAULT = 0.30


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def stable_id(prefix: str, value: str) -> str:
    return prefix + hashlib.sha1(norm(value).encode("utf-8")).hexdigest()[:12]


def number(value: object) -> float | None:
    if value is None:
        return None
    clean = re.sub(r"[^\d.+-]", "", str(value))
    try:
        return float(clean)
    except ValueError:
        return None


def parse_range(value: str | None) -> tuple[float, float]:
    if not value:
        return 1.0, 1.0
    parts = re.findall(r"\d+(?:\.\d+)?", value)
    if not parts:
        return 1.0, 1.0
    nums = [float(part) for part in parts]
    return (nums[0], nums[-1]) if len(nums) > 1 else (nums[0], nums[0])


def confidence(samples: int) -> str:
    if samples >= 10_000:
        return "high"
    if samples >= 1_000:
        return "medium"
    if samples >= MIN_RELIABLE_SAMPLES:
        return "low"
    return "insufficient"


def loot2_blocks(wikitext: str) -> list[str]:
    """Every Loot2/Loot2_RC template on the page, newest first, in page order."""
    blocks: list[str] = []
    for marker in re.finditer(r"\{\{Loot2(?:_RC)?(?=[\s|}])", wikitext, flags=re.I):
        start = marker.start()
        depth = 0
        index = start
        while index < len(wikitext) - 1:
            pair = wikitext[index : index + 2]
            if pair == "{{":
                depth += 1
                index += 2
                continue
            if pair == "}}":
                depth -= 1
                index += 2
                if depth == 0:
                    blocks.append(wikitext[start:index])
                    break
                continue
            index += 1
    return blocks


def block_kills(block: str) -> int:
    match = re.search(r"\|\s*kills\s*=\s*([\d,]+)", block)
    return int(match.group(1).replace(",", "")) if match else 0


def select_loot2_block(wikitext: str) -> tuple[str | None, str]:
    """Pick the loot sample to model, and say why it was picked.

    TibiaWiki lists the newest client version first, so the first block is the most current
    picture of the loot table.  It is also frequently a handful of kills recorded right after a
    content update, and taking it unconditionally threw away thousands of kills recorded under
    the previous version: 67 creatures, among them Abyssador (2 kills preferred over 117) and
    Energuardian of Tales (46 preferred over 8,558), were demoted to `insufficient_sample` that
    way.  Prefer the newest block that clears the reliability threshold, and fall back to the
    largest sample on the page when no block clears it.
    """
    blocks = loot2_blocks(wikitext)
    if not blocks:
        return None, "no Loot2 template on the page"
    for position, block in enumerate(blocks):
        if block_kills(block) >= MIN_RELIABLE_SAMPLES:
            if position == 0:
                return block, "newest loot table on the page"
            return block, (
                f"newest table clearing {MIN_RELIABLE_SAMPLES} kills; "
                f"{position} newer but smaller table(s) declined"
            )
    best = max(range(len(blocks)), key=lambda i: block_kills(blocks[i]))
    return blocks[best], "largest sample on the page; no table clears the reliability threshold"


@dataclass
class Price:
    max_gp: float
    conservative_gp: float
    buyers: str
    conservative_buyers: str
    access_note: str
    category: str
    source: str


def offer_gate(offer: dict) -> str:
    """Why this offer is not available to an arbitrary character, or "" when it is."""
    name = norm(offer.get("name"))
    if name in GATED_BUYERS:
        return f"{offer.get('name')}: {GATED_BUYERS[name]}"
    flag = str(offer.get("currency_quest_flag_display_name") or "").strip()
    if flag:
        return f"{offer.get('name')}: metadata quest flag {flag}"
    return ""


def item_prices() -> dict[str, Price]:
    payload = json.loads(ITEM_META.read_text())
    items = payload if isinstance(payload, list) else payload.get("items", [])
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for item in items:
        keys = {norm(item.get("name")), norm(item.get("wiki_name"))}
        for key in keys - {""}:
            grouped[key].append(item)

    def describe(offers: list[dict]) -> str:
        return "; ".join(
            sorted(
                {
                    f"{offer.get('name', 'unknown')} @ {offer.get('location', 'unknown')}"
                    for offer in offers
                }
            )
        )

    prices: dict[str, Price] = {}
    for key, candidates in grouped.items():
        offers: list[tuple[float, dict]] = []
        category = ""
        for item in candidates:
            category = category or str(item.get("category") or "")
            for offer in item.get("npc_buy") or []:
                gp = number(offer.get("price"))
                # A non-zero currency object means the NPC pays in something other than gold,
                # which is not gold creation.  Every npc_buy offer in the cache pays in gold
                # (currency_object_type_id 0); the guard keeps that true if the cache changes.
                currency = number(offer.get("currency_object_type_id")) or 0
                if gp is not None and gp > 0 and currency == 0:
                    offers.append((gp, offer))
        if not offers:
            continue
        maximum = max(gp for gp, _ in offers)
        best = [offer for gp, offer in offers if gp == maximum]
        open_offers = [(gp, offer) for gp, offer in offers if not offer_gate(offer)]
        conservative = max((gp for gp, _ in open_offers), default=0.0)
        conservative_best = [offer for gp, offer in open_offers if gp == conservative]

        gates = sorted({gate for _, offer in offers if (gate := offer_gate(offer))})
        if conservative >= maximum:
            note = f"best offer reachable without a quest or store purchase; {ACCESS_BASELINE_NOTE}"
        elif conservative > 0:
            note = (
                f"best offer needs access ({'; '.join(gates)}); "
                f"best open offer pays {conservative:,.0f} GP; {ACCESS_BASELINE_NOTE}"
            )
        else:
            note = (
                f"every NPC buyer needs access ({'; '.join(gates)}); "
                f"conservative value is zero; {ACCESS_BASELINE_NOTE}"
            )

        prices[key] = Price(
            max_gp=maximum,
            conservative_gp=conservative,
            buyers=describe(best),
            conservative_buyers=describe(conservative_best),
            access_note=note,
            category=category,
            source="data/raw/tm_item_metadata.json (TibiaMarket item metadata, npc_buy offers)",
        )
    return prices


LOOT_FIELD = re.compile(r"([A-Za-z_]+)\s*:\s*([^,]*)")


def parse_loot_line(body: str) -> dict | None:
    """Parse one `Name, times:N, amount:A, total:T` row of a Loot2 template.

    Read the fields by name rather than by position.  The previous positional pattern anchored
    `times:([\\d,]+)` with a greedy character class that included the comma, so it consumed the
    separator before the optional `amount:` and `total:` groups could match.  Because both groups
    were optional the match still succeeded, silently, on every row: all 17,681 items in
    `creature_loot_items.csv` carried quantity 1.  Gold Coin stacks average 66 coins and Platinum
    Coin stacks average 10, so direct-coin emission was understated by roughly an order of
    magnitude.  Reading by name also handles the three rows that put `amount:` before `times:`.
    """
    first = LOOT_FIELD.search(body)
    if not first:
        return None
    name = body[: first.start()].rstrip().rstrip(",").strip()
    if not name:
        return None
    fields = {key.casefold(): value.strip() for key, value in LOOT_FIELD.findall(body)}
    times = number(fields.get("times"))
    if times is None or times <= 0:
        return None
    total = number(fields.get("total")) if fields.get("total") else None
    return {
        "item_name": name,
        "times": int(times),
        "amount": fields.get("amount") or None,
        "total": int(total) if total is not None else None,
    }


def parse_loot_cache() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict], dict]:
    cache = json.loads(LOOT_CACHE.read_text())
    prices = item_prices()
    item_rows: list[dict] = []
    creature_rows: list[dict] = []
    models: dict[str, dict] = {}

    for page in cache["pages"].values():
        block, block_reason = select_loot2_block(page.get("wikitext", ""))
        title = page["title"].split(":", 1)[-1]
        if not block:
            continue
        fields: dict[str, str] = {}
        raw_items: list[dict] = []
        for raw_line in block.splitlines()[1:]:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            body = line[1:].strip()
            if "=" in body and "," not in body:
                key, value = body.split("=", 1)
                fields[norm(key)] = value.strip()
                continue
            parsed = parse_loot_line(body)
            if parsed:
                raw_items.append(parsed)

        samples = int(number(fields.get("kills")) or 0)
        creature_name = fields.get("name") or title
        if samples <= 0:
            continue
        conf = confidence(samples)
        reliable = samples >= MIN_RELIABLE_SAMPLES
        direct_gp = npc_gp = 0.0
        conservative_npc_gp = category_npc_gp = 0.0
        considered = discarded = complete = 0
        inconsistent_totals = 0

        for raw_item in raw_items:
            item_name = raw_item["item_name"]
            if norm(item_name) in {"empty", "!empty"}:
                continue
            considered += 1
            times = raw_item["times"]
            qmin, qmax = parse_range(raw_item["amount"])
            drop_frequency = times / samples
            probability = min(1.0, drop_frequency)
            total = raw_item["total"]
            if total is not None and total >= times:
                # `total` is the summed quantity over the whole sample, so total / kills is the
                # exact empirical expectation per kill.  Prefer it over the range midpoint.
                expected_quantity = total / samples
                distribution = "empirical total / kills"
                complete += 1
            else:
                if total is not None:
                    # total < times cannot happen if every drop yields at least one unit; the
                    # wiki row is internally inconsistent, so fall back and record it.
                    inconsistent_totals += 1
                expected_quantity = drop_frequency * (qmin + qmax) / 2
                distribution = (
                    "range midpoint fallback; source total inconsistent with times"
                    if total is not None
                    else "range midpoint fallback"
                    if raw_item["amount"]
                    else "unit quantity assumed; source states neither amount nor total"
                )
                if raw_item["amount"]:
                    complete += 1
            conditional_quantity = (
                expected_quantity / probability if probability > 0 else 0.0
            )

            coin_value = COINS.get(norm(item_name), 0.0)
            price = prices.get(norm(item_name))
            npc_value = price.max_gp if price and not coin_value else 0.0
            npc_conservative = price.conservative_gp if price and not coin_value else 0.0
            item_category = price.category if price else ""
            category = (
                "direct_coin"
                if coin_value
                else "npc_sellable"
                if npc_value
                else "player_only_or_no_npc_buyer"
            )
            realization = (
                1.0
                if category == "direct_coin"
                else CATEGORY_REALIZATION.get(
                    norm(item_category), CATEGORY_REALIZATION_DEFAULT
                )
            )
            if category == "direct_coin":
                expected_direct = expected_quantity * coin_value
                expected_npc = expected_conservative = expected_category = 0.0
            elif category == "npc_sellable":
                expected_direct = 0.0
                expected_npc = expected_quantity * npc_value
                expected_conservative = expected_quantity * npc_conservative
                expected_category = expected_npc * realization
            else:
                expected_direct = expected_npc = 0.0
                expected_conservative = expected_category = 0.0
                discarded += 1
            direct_gp += expected_direct
            npc_gp += expected_npc
            conservative_npc_gp += expected_conservative
            category_npc_gp += expected_category

            item_rows.append(
                {
                    "creature_id": stable_id("cr_", creature_name),
                    "creature_name": creature_name,
                    "item_id": stable_id("it_", item_name),
                    "item_name": item_name,
                    "drop_probability": probability,
                    "drop_frequency_per_kill": drop_frequency,
                    "drop_probability_method": (
                        "times / kills"
                        if drop_frequency <= 1
                        else "at-least-one probability capped at 1; repeated stacks observed"
                    ),
                    "quantity_min": qmin,
                    "quantity_max": qmax,
                    "expected_quantity_conditional": conditional_quantity,
                    "expected_quantity_per_kill": expected_quantity,
                    "quantity_distribution_method": distribution,
                    "monetary_category": category,
                    "item_category": item_category,
                    "nominal_coin_value_gp": coin_value,
                    "npc_sell_value_max_gp": npc_value,
                    "npc_sell_value_conservative_gp": npc_conservative,
                    "category_realization_rate": realization,
                    "expected_direct_coin_gp_per_kill": expected_direct,
                    "expected_npc_sale_gp_per_kill": expected_npc,
                    "expected_npc_sale_gp_per_kill_conservative": expected_conservative,
                    "expected_npc_sale_gp_per_kill_category_realized": expected_category,
                    "npc_best_buyers": price.buyers if price else "",
                    "npc_conservative_buyers": price.conservative_buyers if price else "",
                    "npc_access_requirement": price.access_note if price else "",
                    "npc_price_source": price.source if price else "",
                    "loot_samples": samples,
                    "loot_version": fields.get("version", ""),
                    "loot_confidence": conf,
                    "loot_source_url": page["source_url"],
                    "loot_source_revision_id": page.get("revision_id"),
                    "loot_source_revision_utc": page.get("revision_timestamp_utc"),
                    "loot_collection_utc": cache.get("collection_completed_utc"),
                }
            )

        completeness = complete / considered if considered else 1.0
        status = "complete" if reliable and completeness == 1 else (
            "partial" if reliable else "insufficient_sample"
        )
        row = {
            "creature_id": stable_id("cr_", creature_name),
            "creature_name": creature_name,
            "wiki_title": title,
            "loot_model_status": status,
            "loot_samples": samples,
            "loot_confidence": conf,
            "loot_version": fields.get("version", ""),
            "loot_block_selection": block_reason,
            "loot_item_count": considered,
            "valued_item_count": considered - discarded,
            "discarded_item_count": discarded,
            "loot_fields_complete_pct": completeness,
            "inconsistent_total_rows": inconsistent_totals,
            "expected_direct_coin_gp_per_kill": direct_gp if reliable else np.nan,
            "expected_npc_sale_gp_per_kill": npc_gp if reliable else np.nan,
            "expected_total_potential_gp_per_kill": direct_gp + npc_gp if reliable else np.nan,
            # Conservative = direct coins plus NPC sales at buyers reachable without a quest or a
            # store purchase.  It used to be direct coins alone, which made the "conservative NPC
            # price" scenario indistinguishable from the direct-coin series.
            "expected_total_conservative_gp_per_kill": (
                direct_gp + conservative_npc_gp if reliable else np.nan
            ),
            "expected_npc_sale_gp_per_kill_conservative": (
                conservative_npc_gp if reliable else np.nan
            ),
            "expected_total_category_realized_gp_per_kill": (
                direct_gp + category_npc_gp if reliable else np.nan
            ),
            "loot_source_url": page["source_url"],
            "loot_source_revision_id": page.get("revision_id"),
            "loot_source_revision_utc": page.get("revision_timestamp_utc"),
            "loot_collection_utc": cache.get("collection_completed_utc"),
        }
        creature_rows.append(row)
        key = norm(creature_name)
        if key not in models or samples > models[key]["loot_samples"]:
            models[key] = row

    items = pd.DataFrame(item_rows)
    creatures = pd.DataFrame(creature_rows)
    return items, creatures, models, cache


def aliases() -> dict[str, str]:
    result: dict[str, str] = {}
    if not ALIAS_SOURCE.exists():
        return result
    text = ALIAS_SOURCE.read_text(encoding="utf-8")
    for raw_name, pretty_name in re.findall(
        r"\[\s*'((?:\\'|[^'])*)'\s*,\s*'((?:\\'|[^'])*)'\s*\]", text
    ):
        result[norm(raw_name.replace("\\'", "'"))] = pretty_name.replace("\\'", "'")
    return result


def plural_aliases(models: dict) -> dict[str, str]:
    """Map plural race names back to the singular keys the loot catalogue is built on.

    The archive of historical kill statistics writes races in the plural - werehyaenas, glooth
    blobs, medusae - while the live source writes them singular, and the catalogue follows the
    live source. Left alone this matches 1% of historical kills against 95% of recent ones,
    which is not a coverage gap but a broken join wearing one.

    The direction matters. Rather than stripping suffixes off whatever the archive says, which
    invents singulars for creatures that do not exist, this generates the plurals of names the
    catalogue already contains and maps those back. Every key produced is therefore a creature
    with a loot model behind it, and a name that resolves to nothing keeps resolving to nothing.
    """
    def forms(name: str) -> set[str]:
        # Tibia names pluralise on their head noun, which is the last word except when the name
        # is a phrase - "adept of the cult" becomes "adepts of the cult", not "adept of the cults".
        head, sep, tail = name.partition(" of ")
        if sep:
            return {f"{p} of {tail}" for p in forms(head)}
        prefix, _, last = name.rpartition(" ")
        pre = f"{prefix} " if prefix else ""
        out = {pre + last + "s"}
        if last.endswith("man"):
            out.add(pre + last[:-3] + "men")
        if last.endswith("mouse"):
            out.add(pre + last[:-5] + "mice")
        if last.endswith(("s", "x", "z", "ch", "sh")):
            out.add(pre + last + "es")
        if last.endswith("a"):                       # medusa -> medusae
            out.add(pre + last + "e")
        if last.endswith("ops"):                     # cyclops -> cyclopes
            out.add(pre + last[:-3] + "opes")
        if last.endswith("y") and len(last) > 1 and last[-2] not in "aeiou":
            out.add(pre + last[:-1] + "ies")
        if last.endswith("fe"):
            out.add(pre + last[:-2] + "ves")
        elif last.endswith("f"):
            out.add(pre + last[:-1] + "ves")
        return out

    extra: dict[str, str] = {}
    for key in models:
        for form in forms(key):
            if form not in models:
                extra.setdefault(form, key)
    return extra


def creature_classifications() -> dict[str, dict]:
    if not CREATURE_CACHE.exists():
        return {}
    cache = json.loads(CREATURE_CACHE.read_text())
    result: dict[str, dict] = {}
    for page in cache.get("pages", {}).values():
        if page.get("missing"):
            continue
        title = str(page.get("title") or "")
        categories = {norm(value) for value in page.get("categories", [])}
        wikitext = page.get("wikitext", "")
        boss_field = re.search(r"^\|\s*isboss\s*=\s*([^|\n]+)", wikitext, flags=re.I | re.M)
        loot_field = re.search(r"^\|\s*loot\s*=\s*([^|\n]+)", wikitext, flags=re.I | re.M)
        loot_value = norm(loot_field.group(1)) if loot_field else ""
        no_loot = bool(
            loot_value
            and (
                loot_value in {"none", "nothing", "--", "no loot"}
                or "has no loot" in loot_value
                or "cannot be looted" in loot_value
            )
        )
        lower_title = norm(title)
        result[lower_title] = {
            "is_boss": (
                "bosses" in categories
                or bool(boss_field and norm(boss_field.group(1)) in {"yes", "true"})
            ),
            "is_event_creature": bool(
                {"event creatures", "event related articles"} & categories
            ),
            # TibiaWiki exposes "Summonable Creatures" (can be summoned) but not a
            # reliable category for kill-stat entries that are themselves summoned.
            "is_summon": "summoned creatures" in categories,
            "is_training": bool(re.search(r"\b(training|dummy)\b", lower_title)),
            "explicit_no_loot": no_loot,
            "classification_source_url": page.get("source_url", ""),
            "classification_revision_id": page.get("revision_id"),
            "classification_revision_utc": page.get("revision_timestamp_utc"),
        }
    return result


MODELS: dict[str, dict] = {}
ALIASES: dict[str, str] = {}
BOSSES: set[str] = set()
CLASSIFICATIONS: dict[str, dict] = {}
PLURALS: dict[str, str] = {}


def scan_world(world_dir: pathlib.Path) -> tuple[list[dict], dict[str, dict]]:
    daily_rows: list[dict] = []
    creature_totals: dict[str, dict] = {}
    for path in sorted(world_dir.glob("20*.json")):
        try:
            stats = json.loads(path.read_text())["killstatistics"]
        except Exception:
            continue
        date = pd.Timestamp(path.stem) - pd.Timedelta(days=1)
        sums = collections.defaultdict(float)
        sums.update(
            {
                "total_kills": 0,
                "nonboss_kills": 0,
                "boss_kills": 0,
                "modeled_kills_all": 0,
                "modeled_kills_nonboss": 0,
                "low_confidence_modeled_kills": 0,
                "low_confidence_potential_gp": 0,
                "assumed_quantity_potential_gp": 0,
                "known_zero_emission_kills": 0,
                "event_creature_kills": 0,
                "summon_kills": 0,
                "training_kills": 0,
                "direct_coin_gp": 0,
                "npc_potential_gp_max": 0,
                "npc_potential_gp_conservative": 0,
                "npc_potential_gp_category_realized": 0,
                "boss_direct_coin_gp": 0,
                "boss_npc_potential_gp_max": 0,
                "boss_npc_potential_gp_conservative": 0,
            }
        )
        top_emission_name = ""
        top_emission_gp = 0.0
        top_kill_name = ""
        top_kills = 0
        for entry in stats.get("entries", []):
            raw_name = str(entry.get("race") or "").strip()
            kills = int(entry.get("last_day_killed") or 0)
            if kills <= 0 or raw_name.startswith(PSEUDO_PREFIXES):
                continue
            canonical = ALIASES.get(norm(raw_name), raw_name)
            key = norm(canonical)
            # The archive writes races in the plural; the catalogue is keyed singular.
            key = PLURALS.get(key, key)
            model = MODELS.get(key)
            classification = CLASSIFICATIONS.get(key, {})
            is_boss = key in BOSSES or classification.get("is_boss", False)
            known_zero = any(
                classification.get(flag, False)
                for flag in ("explicit_no_loot", "is_summon", "is_training")
            )
            sums["total_kills"] += kills
            sums["boss_kills" if is_boss else "nonboss_kills"] += kills
            if classification.get("is_event_creature", False):
                sums["event_creature_kills"] += kills
            if classification.get("is_summon", False):
                sums["summon_kills"] += kills
            if classification.get("is_training", False):
                sums["training_kills"] += kills
            if kills > top_kills and not is_boss:
                top_kill_name, top_kills = canonical, kills
            record = creature_totals.setdefault(
                key,
                {
                    "canonical_name": canonical,
                    "raw_names": set(),
                    "total_kills": 0,
                    "first_date": date,
                    "last_date": date,
                    "worlds": set(),
                    "is_boss": is_boss,
                    "is_event_creature": classification.get("is_event_creature", False),
                    "is_summon": classification.get("is_summon", False),
                    "is_training": classification.get("is_training", False),
                    "explicit_no_loot": classification.get("explicit_no_loot", False),
                    "classification_source_url": classification.get(
                        "classification_source_url", ""
                    ),
                    "classification_revision_id": classification.get(
                        "classification_revision_id"
                    ),
                    "classification_revision_utc": classification.get(
                        "classification_revision_utc"
                    ),
                },
            )
            record["raw_names"].add(raw_name)
            record["total_kills"] += kills
            record["first_date"] = min(record["first_date"], date)
            record["last_date"] = max(record["last_date"], date)
            record["worlds"].add(stats.get("world", world_dir.name.title()))
            for flag in (
                "is_boss",
                "is_event_creature",
                "is_summon",
                "is_training",
                "explicit_no_loot",
            ):
                record[flag] = record[flag] or bool(classification.get(flag, False))

            if known_zero:
                sums["known_zero_emission_kills"] += kills
                sums["modeled_kills_all"] += kills
                if not is_boss:
                    sums["modeled_kills_nonboss"] += kills
                continue
            # `partial` means some rows of an otherwise well-sampled table state no quantity, so
            # those rows fall back to one unit. The creature still has a usable expected value and
            # its loot_fields_complete_pct travels with it; excluding it would drop coverage
            # without making the estimate more honest.
            if not model or model["loot_model_status"] not in {"complete", "partial"}:
                continue
            direct = model["expected_direct_coin_gp_per_kill"] * kills
            npc = model["expected_npc_sale_gp_per_kill"] * kills
            npc_conservative = model["expected_npc_sale_gp_per_kill_conservative"] * kills
            npc_category = (
                model["expected_total_category_realized_gp_per_kill"]
                - model["expected_direct_coin_gp_per_kill"]
            ) * kills
            sums["modeled_kills_all"] += kills
            if model["loot_confidence"] == "low":
                sums["low_confidence_modeled_kills"] += kills
            if is_boss:
                sums["boss_direct_coin_gp"] += direct
                sums["boss_npc_potential_gp_max"] += npc
                sums["boss_npc_potential_gp_conservative"] += npc_conservative
            else:
                sums["modeled_kills_nonboss"] += kills
                sums["direct_coin_gp"] += direct
                sums["npc_potential_gp_max"] += npc
                sums["npc_potential_gp_conservative"] += npc_conservative
                sums["npc_potential_gp_category_realized"] += npc_category
                contribution = direct + npc
                # Step 7 asks for the share of estimated VALUE resting on weak data, which is a
                # different question from the share of deaths: a rare creature with a thin loot
                # sample can carry far more GP than its kill count suggests.
                if model["loot_confidence"] == "low":
                    sums["low_confidence_potential_gp"] += contribution
                if model["loot_fields_complete_pct"] < 1:
                    sums["assumed_quantity_potential_gp"] += contribution
                if contribution > top_emission_gp:
                    top_emission_name, top_emission_gp = canonical, contribution

        if sums["total_kills"] > 0:
            daily_rows.append(
                {
                    "world": stats.get("world", world_dir.name.title()),
                    "date": date,
                    "top_kill_creature_name": top_kill_name,
                    "top_kill_creature_kills": top_kills,
                    "top_emission_creature_name": top_emission_name,
                    "top_emission_creature_gp": top_emission_gp,
                    **sums,
                }
            )
    return daily_rows, creature_totals


def merge_creature_totals(parts: list[dict[str, dict]]) -> pd.DataFrame:
    combined: dict[str, dict] = {}
    for part in parts:
        for key, row in part.items():
            target = combined.setdefault(
                key,
                {
                    "canonical_name": row["canonical_name"],
                    "raw_names": set(),
                    "total_kills": 0,
                    "first_date": row["first_date"],
                    "last_date": row["last_date"],
                    "worlds": set(),
                    "is_boss": row["is_boss"],
                    "is_event_creature": row["is_event_creature"],
                    "is_summon": row["is_summon"],
                    "is_training": row["is_training"],
                    "explicit_no_loot": row["explicit_no_loot"],
                    "classification_source_url": row["classification_source_url"],
                    "classification_revision_id": row["classification_revision_id"],
                    "classification_revision_utc": row["classification_revision_utc"],
                },
            )
            target["raw_names"].update(row["raw_names"])
            target["total_kills"] += row["total_kills"]
            target["first_date"] = min(target["first_date"], row["first_date"])
            target["last_date"] = max(target["last_date"], row["last_date"])
            target["worlds"].update(row["worlds"])
            for flag in (
                "is_boss",
                "is_event_creature",
                "is_summon",
                "is_training",
                "explicit_no_loot",
            ):
                target[flag] = target[flag] or row[flag]
    rows = []
    for key, row in combined.items():
        rows.append(
            {
                "creature_id": stable_id("cr_", row["canonical_name"]),
                "canonical_name": row["canonical_name"],
                "normalized_name": key,
                "raw_names": " | ".join(sorted(row["raw_names"])),
                "raw_name_count": len(row["raw_names"]),
                "total_kills": row["total_kills"],
                "first_date": row["first_date"],
                "last_date": row["last_date"],
                "world_count": len(row["worlds"]),
                "is_boss": row["is_boss"],
                "is_event_creature": row["is_event_creature"],
                "is_summon": row["is_summon"],
                "is_training": row["is_training"],
                "explicit_no_loot": row["explicit_no_loot"],
                "classification_source_url": row["classification_source_url"],
                "classification_revision_id": row["classification_revision_id"],
                "classification_revision_utc": row["classification_revision_utc"],
            }
        )
    return pd.DataFrame(rows).sort_values("total_kills", ascending=False)


# Exactly what scan_world emits, and therefore the only columns build_daily may be handed.
# build_daily merges population, world metadata and events itself, so passing it a table that
# already carries those columns collides on the join and produces suffixed duplicates it then
# cannot find. Stating the contract here lets any stage re-derive the published table without
# having to re-scan an archive to discover which columns were raw.
RAW_DAILY_COLUMNS = [
    "world",
    "date",
    "top_kill_creature_name",
    "top_kill_creature_kills",
    "top_emission_creature_name",
    "top_emission_creature_gp",
    "total_kills",
    "nonboss_kills",
    "boss_kills",
    "modeled_kills_all",
    "modeled_kills_nonboss",
    "low_confidence_modeled_kills",
    "low_confidence_potential_gp",
    "assumed_quantity_potential_gp",
    "known_zero_emission_kills",
    "event_creature_kills",
    "summon_kills",
    "training_kills",
    "direct_coin_gp",
    "npc_potential_gp_max",
    "npc_potential_gp_conservative",
    "npc_potential_gp_category_realized",
    "boss_direct_coin_gp",
    "boss_npc_potential_gp_max",
    "boss_npc_potential_gp_conservative",
]


def build_daily(daily: pd.DataFrame) -> pd.DataFrame:
    daily["coverage_deaths_pct_all"] = (
        daily.modeled_kills_all / daily.total_kills.replace(0, np.nan)
    )
    daily["coverage_deaths_pct_nonboss"] = (
        daily.modeled_kills_nonboss / daily.nonboss_kills.replace(0, np.nan)
    )
    daily["low_confidence_deaths_pct"] = (
        daily.low_confidence_modeled_kills / daily.modeled_kills_all.replace(0, np.nan)
    )
    potential_denominator = (
        daily.direct_coin_gp + daily.npc_potential_gp_max
    ).replace(0, np.nan)
    # Share of estimated VALUE, not of deaths. A thinly sampled creature can carry far more GP
    # than its kill count implies, so the death share understates how much of the number rests
    # on weak loot data.
    daily["low_confidence_value_pct"] = (
        daily.low_confidence_potential_gp / potential_denominator
    )
    daily["assumed_quantity_value_pct"] = (
        daily.assumed_quantity_potential_gp / potential_denominator
    )
    daily["potential_total_gp_max"] = (
        daily.direct_coin_gp + daily.npc_potential_gp_max
    )
    # Potential emission priced at NPC buyers a character reaches without a quest or a store
    # purchase.  This used to be direct coins alone, which answered no question the max-price
    # series had not already answered.
    daily["potential_total_gp_conservative"] = (
        daily.direct_coin_gp + daily.npc_potential_gp_conservative
    )
    # Step 5's intermediate scenario: per-item-category realisation rates instead of one flat
    # rate.  The rates are declared assumptions, not observations - see CATEGORY_REALIZATION.
    daily["realized_estimate_gp_category"] = (
        daily.direct_coin_gp + daily.npc_potential_gp_category_realized
    )
    daily["boss_potential_total_gp_max"] = (
        daily.boss_direct_coin_gp + daily.boss_npc_potential_gp_max
    )
    daily["potential_total_gp_max_with_bosses"] = (
        daily.potential_total_gp_max + daily.boss_potential_total_gp_max
    )
    daily["top_emission_creature_share"] = (
        daily.top_emission_creature_gp / daily.potential_total_gp_max.replace(0, np.nan)
    )
    daily["top_kill_creature_share"] = (
        daily.top_kill_creature_kills / daily.nonboss_kills.replace(0, np.nan)
    )
    for rate in REALIZATION_RATES:
        suffix = int(rate * 100)
        daily[f"realized_estimate_gp_{suffix}"] = (
            daily.direct_coin_gp + rate * daily.npc_potential_gp_max
        )
    daily["low_quality_flag"] = daily.coverage_deaths_pct_nonboss < COVERAGE_THRESHOLD
    reporting = daily.groupby("date", observed=True).world.transform("nunique")
    daily["worlds_reporting_date"] = reporting
    # A date is partial when the worlds that existed then did not report, not when the panel had
    # fewer worlds than it has today. Comparing against every world ever seen flagged the whole
    # pre-2025 archive - 44 worlds existed in 2022 against 93 in 2026 - and the quality filter
    # then dropped 68% of the panel, so extending the series to 3.5 years changed no model at all.
    # A world counts as expected on a date when that date lies inside its own observed span.
    span = daily.groupby("world", observed=True).date.agg(["min", "max"])
    dates = np.sort(daily.date.unique())
    starts = np.sort(span["min"].to_numpy())
    ends = np.sort(span["max"].to_numpy())
    expected = pd.Series(
        np.searchsorted(starts, dates, side="right")
        - np.searchsorted(ends, dates, side="left"),
        index=dates,
    )
    daily["worlds_expected_date"] = daily.date.map(expected)
    daily["partial_date_flag"] = reporting < np.ceil(daily.worlds_expected_date * 0.80)
    daily["low_quality_flag"] = daily.low_quality_flag | daily.partial_date_flag

    population = pd.read_csv(P / "population_daily.csv", parse_dates=["date"])
    worlds = pd.read_csv(P / "world_summary.csv")[
        ["world", "active_chars", "converged", "region", "pvp_type"]
    ]
    events = pd.read_csv(P / "event_calendar.csv", parse_dates=["date"])
    daily = (
        daily.merge(population, on=["world", "date"], how="left")
        .merge(worlds, on="world", how="left")
        .merge(events, on="date", how="left")
        .sort_values(["world", "date"])
        .reset_index(drop=True)
    )
    denominator_online = daily.players_online_avg.replace(0, np.nan)
    denominator_chars = daily.active_chars.replace(0, np.nan)
    for column in [
        "direct_coin_gp",
        "potential_total_gp_max",
        "realized_estimate_gp_50",
    ]:
        daily[f"{column}_per_avg_online"] = daily[column] / denominator_online
        daily[f"{column}_per_active_character"] = daily[column] / denominator_chars
        daily[f"{column}_per_1000_kills"] = (
            daily[column] / daily.nonboss_kills.replace(0, np.nan) * 1000
        )
        daily[f"cumulative_{column}"] = daily.groupby("world", observed=True)[
            column
        ].cumsum()
    return daily


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"kill-statistics archive not found at {SRC}")
    for required in (LOOT_CACHE, ITEM_META, CREATURE_CACHE):
        if not required.exists():
            raise SystemExit(f"required source cache missing: {required.relative_to(ROOT)}")

    items, loot_creatures, models, cache = parse_loot_cache()
    global MODELS, ALIASES, BOSSES, CLASSIFICATIONS, PLURALS
    MODELS = models
    ALIASES = aliases()
    PLURALS = plural_aliases(models)
    CLASSIFICATIONS = creature_classifications()
    boss_names = json.loads((RAW / "boss_names.json").read_text())
    BOSSES = {norm(ALIASES.get(norm(name), name)) for name in boss_names}
    BOSSES.update(
        key for key, value in CLASSIFICATIONS.items() if value.get("is_boss", False)
    )

    worlds = sorted(path for path in SRC.iterdir() if path.is_dir() and not path.name.startswith("_"))
    print(
        f"{len(models):,} parsed loot models, {len(ALIASES):,} explicit aliases, "
        f"{len(CLASSIFICATIONS):,} source classifications, "
        f"{len(worlds):,} kill-statistic worlds"
    )
    # Thread workers avoid platform semaphore requirements while still overlapping the archive's
    # many small file reads. JSON parsing is small relative to filesystem latency here.
    with ThreadPoolExecutor(max_workers=12) as executor:
        scanned = list(executor.map(scan_world, worlds))
    daily = pd.DataFrame(row for part, _ in scanned for row in part)
    daily = daily[daily.total_kills > 0].copy()
    canonical = merge_creature_totals([part for _, part in scanned])

    model_columns = [
        "creature_name",
        "wiki_title",
        "loot_model_status",
        "loot_samples",
        "loot_confidence",
        "loot_version",
        "loot_block_selection",
        "loot_item_count",
        "valued_item_count",
        "discarded_item_count",
        "loot_fields_complete_pct",
        "inconsistent_total_rows",
        "expected_direct_coin_gp_per_kill",
        "expected_npc_sale_gp_per_kill",
        "expected_npc_sale_gp_per_kill_conservative",
        "expected_total_potential_gp_per_kill",
        "expected_total_conservative_gp_per_kill",
        "expected_total_category_realized_gp_per_kill",
        "loot_source_url",
        "loot_source_revision_id",
        "loot_source_revision_utc",
        "loot_collection_utc",
    ]
    model_frame = loot_creatures[model_columns].copy()
    model_frame["normalized_name"] = model_frame.creature_name.map(norm)
    model_frame = model_frame.sort_values("loot_samples", ascending=False).drop_duplicates(
        "normalized_name"
    )
    coverage = canonical.merge(model_frame.drop(columns=["creature_name"]), on="normalized_name", how="left")
    coverage["loot_model_status"] = coverage.loot_model_status.fillna("absent")
    known_zero = coverage[
        ["explicit_no_loot", "is_summon", "is_training"]
    ].fillna(False).any(axis=1)
    modeled_status = coverage.loot_model_status.isin(["complete", "partial"])
    coverage["coverage_category"] = np.select(
        [
            coverage.is_boss,
            known_zero,
            modeled_status,
            coverage.loot_model_status.eq("insufficient_sample"),
        ],
        ["boss_separate", "known_zero_emission", "modeled", "insufficient_sample"],
        default="missing_loot_table",
    )
    coverage["included_in_main_series"] = coverage.coverage_category.eq("modeled")
    coverage["exclusion_reason"] = np.select(
        [
            coverage.is_boss,
            known_zero,
            coverage.loot_model_status.eq("insufficient_sample"),
            coverage.loot_model_status.eq("absent"),
        ],
        [
            "TibiaWiki/Bosstiary boss; emitted value retained only in boss series",
            "source-classified no-loot, summon, or training creature; counted as known zero",
            f"empirical loot sample below {MIN_RELIABLE_SAMPLES} kills",
            "no current empirical Loot2 table matched; no value imputed",
        ],
        default="",
    )

    daily = build_daily(daily)
    total_deaths = coverage.total_kills.sum()
    covered_deaths = coverage.loc[modeled_status | known_zero, "total_kills"].sum()
    nonboss = coverage[~coverage.is_boss]
    nonboss_known_zero = nonboss[
        ["explicit_no_loot", "is_summon", "is_training"]
    ].fillna(False).any(axis=1)
    nonboss_coverage = (
        nonboss.loc[
            nonboss.loot_model_status.isin(["complete", "partial"]) | nonboss_known_zero,
            "total_kills",
        ].sum()
        / nonboss.total_kills.sum()
    )
    quality = {
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "kill_source": "github.com/tibiamaps/tibia-kill-stats local archive",
        "loot_source": cache["source"],
        "loot_collection_utc": cache.get("collection_completed_utc"),
        "npc_price_source": "data/raw/tm_item_metadata.json (player-to-NPC offers)",
        "world_days": int(len(daily)),
        "worlds": int(daily.world.nunique()),
        "date_start": str(daily.date.min().date()),
        "date_end": str(daily.date.max().date()),
        "canonical_creatures": int(len(coverage)),
        "loot_statistics_pages": int(cache["category_member_count"]),
        "matched_complete_creatures": int(coverage.loot_model_status.eq("complete").sum()),
        "matched_partial_creatures": int(coverage.loot_model_status.eq("partial").sum()),
        "modeled_creatures": int(modeled_status.sum()),
        "insufficient_sample_creatures": int(
            coverage.loot_model_status.eq("insufficient_sample").sum()
        ),
        "absent_creatures": int(coverage.loot_model_status.eq("absent").sum()),
        "total_deaths": int(total_deaths),
        "covered_deaths": int(covered_deaths),
        "covered_deaths_pct_all": float(covered_deaths / total_deaths),
        "covered_deaths_pct_nonboss": float(nonboss_coverage),
        "low_quality_world_days": int(daily.low_quality_flag.sum()),
        "low_quality_world_days_pct": float(daily.low_quality_flag.mean()),
        "partial_date_world_days": int(daily.partial_date_flag.sum()),
        "minimum_reliable_loot_samples": MIN_RELIABLE_SAMPLES,
        "daily_coverage_threshold": COVERAGE_THRESHOLD,
        "realization_rates": list(REALIZATION_RATES),
        "quantity_rule": (
            "expected quantity per kill is the empirical total / kills reported by the loot "
            "table; the amount range midpoint is used only when the source omits a total"
        ),
        "quantity_rows_empirical": int(
            items.quantity_distribution_method.eq("empirical total / kills").sum()
        ),
        "quantity_rows_midpoint": int(
            items.quantity_distribution_method.str.startswith("range midpoint").sum()
        ),
        "quantity_rows_unit_assumed": int(
            items.quantity_distribution_method.str.startswith("unit quantity").sum()
        ),
        "inconsistent_total_rows": int(
            items.quantity_distribution_method.str.contains("inconsistent").sum()
        ),
        "loot_block_fallbacks": int(
            loot_creatures.loot_block_selection.str.contains("declined").sum()
        ),
        "conservative_npc_rule": (
            "conservative NPC value is the highest player-to-NPC offer from a buyer reachable "
            "without a quest or a store purchase; Rashid (Travelling Trader Quest) and Hirelings "
            "(bought with Tibia Coins) are excluded, premium travel is treated as ordinary"
        ),
        "category_realization_rule": (
            "assumed, not observed: per-item-category pickup-and-sale rates standing in for "
            "carry cost and convenience, because loot pickup is unobserved (DATA-05) and item "
            "weight is absent from the item metadata; the flat 25/50/75/100% ladder remains the "
            "primary sensitivity device"
        ),
        "category_realization_rates": CATEGORY_REALIZATION,
        "category_realization_default": CATEGORY_REALIZATION_DEFAULT,
        "npc_currency_rule": (
            "only offers paid in gold (currency_object_type_id 0) create GP; offers paid in "
            "another currency object are excluded"
        ),
        "event_rule": (
            "event flags are retained; per-kill values are not multiplied because the cache "
            "does not encode event-specific loot mechanics"
        ),
        "boss_rule": (
            "TibiaWiki boss classification supplemented by the official Bosstiary list; "
            "bosses are excluded from the main series and retained separately"
        ),
        "summon_training_rule": (
            "no special creature is assigned a zero value without source evidence; unmatched "
            "summons/training creatures remain explicitly uncovered"
        ),
        # The summon count is 0 because the source cannot identify one, not because the archive
        # was searched and found none. TibiaWiki carries "Summonable Creatures" (a creature a
        # player may summon) and "Creatures that Use Summon"; neither says that a kill-statistics
        # entry was itself a summoned creature. Reporting a measured zero here would overstate
        # what the classification can do.
        "summon_identification": (
            "not identifiable from the source: TibiaWiki has no category marking a kill-statistics "
            "entry as a summoned creature, so summon double-counting can be neither confirmed nor "
            "excluded"
        ),
        "training_identification": (
            "training creatures are matched by title only; Tibia's training targets are objects "
            "rather than kill-statistics races, so no match is expected"
        ),
    }

    # The published quality artifacts disagreed with each other and with the series they describe:
    # the JSON reported 69,010 low-quality world-days out of 21,412 while the CSV reported 1 and
    # the daily table contained none. Assert the invariants here so a stale or miscounted figure
    # fails the build instead of being rendered on the dashboard and the hub.
    if not 0 <= quality["low_quality_world_days"] <= quality["world_days"]:
        raise SystemExit(
            f"low_quality_world_days={quality['low_quality_world_days']} outside "
            f"0..{quality['world_days']}"
        )
    if quality["low_quality_world_days"] != int(daily.low_quality_flag.sum()):
        raise SystemExit("quality low-quality count disagrees with the daily table")
    if not 0 <= quality["covered_deaths_pct_nonboss"] <= 1:
        raise SystemExit("non-boss coverage outside 0..1")
    # The parse regression that valued every stack as one unit was silent. Refuse to ship a build
    # in which the empirical quantity is missing from most of the loot table.
    empirical_share = items.quantity_distribution_method.eq("empirical total / kills").mean()
    if empirical_share < 0.90:
        raise SystemExit(
            f"only {empirical_share:.1%} of loot rows carry an empirical total; "
            "the quantity parser is not reading the source"
        )

    P.mkdir(parents=True, exist_ok=True)
    items.to_csv(P / "creature_loot_items.csv", index=False)
    coverage.to_csv(P / "creature_gold_value.csv", index=False)
    # Gzipped because the panel reached 3.5 years and the plain CSV hit 82.6 MB, past GitHub's
    # 50 MB warning and heading for the 100 MB hard limit at roughly 23 MB a year. Every row and
    # column is kept; only the encoding changes. pandas reads .csv.gz by extension, and the
    # dashboard decompresses in the browser, which also cuts what that page downloads by 2.4x.
    daily.to_csv(P / "gold_emission_daily.csv.gz", index=False, compression="gzip")
    pd.DataFrame(
        [
            {"metric": key, "value": json.dumps(value) if isinstance(value, (list, dict)) else value}
            for key, value in quality.items()
        ]
    ).to_csv(P / "gold_emission_quality.csv", index=False)
    (P / "gold_emission_quality.json").write_text(json.dumps(quality, indent=1))

    print(
        f"[GOLD EMISSION] {len(coverage):,} creatures, {len(daily):,} world-days, "
        f"{nonboss_coverage:.1%} non-boss death coverage"
    )
    print(
        f"  complete={quality['matched_complete_creatures']:,}; "
        f"insufficient={quality['insufficient_sample_creatures']:,}; "
        f"absent={quality['absent_creatures']:,}; "
        f"low-quality days={quality['low_quality_world_days_pct']:.1%}"
    )


if __name__ == "__main__":
    main()
