"""Consolidate 38 top-level sections into 8 chapters, renumbering every reference.

Chapters are contiguous blocks of the existing sections, so no content moves position - only
its label changes. Every section, subsection, table and exhibit reference is rewritten from a
single explicit map, and the result is verified against the built PDF afterwards.
"""
import pathlib, re, json

SRC = pathlib.Path(__file__).resolve().parent / "09_sections.py"

CHAPTERS = [
    (1, "Executive summary", ["1"]),
    (2, "Market overview", ["2", "3", "3A"]),
    (3, "Data and measurement", ["4", "5", "6", "7", "8", "9", "10", "11"]),
    (4, "Price dynamics", ["12", "13", "14", "15", "16", "17"]),
    (5, "Market structure, arbitrage and liquidity",
     ["18", "19", "20", "21", "22", "23", "24"]),
    (6, "Valuation, models and forecasts", ["25", "26", "26A", "27", "28"]),
    (7, "Risk, robustness and implications", ["29", "30", "31", "31A", "32"]),
    (8, "Reference", ["33", "34", "35"]),
]

CH_BLURB = {
    2: "What a Tibia Coin is, the mechanics that govern how it trades, and the theory that "
       "frames what its gold price means.",
    3: "Where every number in this report comes from, how it was cleaned, and what the data "
       "can and cannot support. The limitations recorded here govern everything that follows.",
    4: "What the price has done: its level, its trend, its statistical properties, and how it "
       "responds to the calendar and to scheduled events.",
    5: "How the 93 worlds relate to one another - where arbitrage bites, what explains the "
       "differences between worlds, and how liquidity is actually supplied.",
    6: "What the coin is worth in monetary terms, the formal econometrics behind the headline "
       "results, and an honest account of what can be forecast.",
    7: "How risky the asset is, whether the findings survive alternative specifications, what "
       "the study cannot establish, and the rating the evidence supports.",
    8: "Field definitions, the complete source inventory and the methodological detail needed "
       "to reproduce or audit the analysis.",
}

# ---- section map: old top-level id -> new "chapter.section"
SEC = {}
for ch, _title, olds in CHAPTERS:
    if ch == 1:
        SEC["1"] = "1"                      # the executive summary IS chapter 1
        continue
    for i, old in enumerate(olds, 1):
        SEC[old] = f"{ch}.{i}"

src = SRC.read_text()

# ---- exhibit and table maps, numbered sequentially within each chapter in document order
def collect(kind):
    """Order tokens by where their defining caption appears, not by first mention."""
    defs = {}
    for pat in (rf'caption=f?"{kind} ([0-9]+[A-Z]?\.[0-9]+)',
                rf'"{kind} ([0-9]+[A-Z]?\.[0-9]+) -'):
        for m in re.finditer(pat, src):
            defs.setdefault(m.group(1), m.start())
    for m in re.finditer(rf'{kind} ([0-9]+[A-Z]?\.[0-9]+)', src):
        defs.setdefault(m.group(1), m.start())
    return sorted(defs.items(), key=lambda kv: kv[1])


def build_map(kind):
    out, counter = {}, {}
    for tok, _pos in collect(kind):
        ch = SEC.get(tok.split(".")[0], tok.split(".")[0]).split(".")[0]
        counter[ch] = counter.get(ch, 0) + 1
        out[tok] = f"{ch}.{counter[ch]}"
    return out


TAB = build_map("Table")
EXH = build_map("Exhibit")

# ---- subsection map: old "19.1" -> new "5.2.1"
SUB = {}
for m in re.finditer(r'h2\(\s*f?"([0-9]+[A-Z]?)\.([0-9]+)', src):
    old_sec, idx = m.group(1), m.group(2)
    if old_sec == "1" or old_sec not in SEC:
        continue
    SUB[f"{old_sec}.{idx}"] = f"{SEC[old_sec]}.{idx}"

# ---- Rewrite in two stages via placeholders.
# Renumbering in place is unsafe: a freshly written "2.1" would be caught by a later pass
# looking for the OLD "2.1". Every target is first replaced by a unique token that cannot
# collide with anything, and tokens are resolved to final numbers only at the end.
# Token bodies must be OPAQUE. An earlier version embedded the old number in the token, and a
# later pass then rewrote the number inside the token itself. Tokens are now bare ordinals
# that no substitution rule can match.
REG = {}


def tok(kind, key):
    tid = f"\x00{len(REG)}\x00"
    REG[tid] = (kind, key)
    return tid


# Tables and exhibits (longest first so 19.10 is not matched by 19.1).
for kind, mp in (("Table", TAB), ("Exhibit", EXH)):
    for old in sorted(mp, key=lambda k: (-len(k), k)):
        src = re.sub(rf'\b{kind} {re.escape(old)}\b',
                     f'{kind} {tok(kind[0], old)}', src)

# Section references are rewritten ONLY inside an explicit "Section(s) ..." construction.
# An earlier version replaced bare numbers anywhere, which corrupted float literals in the
# code itself (fs=6.3 became a section number). Confining the rule to the word "Section"
# makes it impossible to touch anything that is not a cross-reference.
NUM = r'[0-9]+[A-Z]?(?:\.[0-9]+)?'
ALL = dict(SEC)
ALL.update(SUB)


def remap_refs(m):
    head, body = m.group(1), m.group(2)
    def one(mm):
        v = mm.group(0)
        return tok("A", v) if v in ALL else v
    return head + re.sub(NUM, one, body)


src = re.sub(rf'(Sections?\s+)((?:{NUM})(?:\s*(?:,|and|or|to|&)\s*(?:{NUM}))*)',
             remap_refs, src)

# ---- headings ---------------------------------------------------------------
HEAD_TOK = {}


def repl_h1(m):
    num, title = m.group(2), m.group(3)
    if num == "1":
        return m.group(0)
    t = tok("C", num)
    HEAD_TOK[num] = t          # remember it so chapter openers can be anchored on the heading
    return f'h2sec("{t}", "{title}")'


src = re.sub(r'h1\(\s*("?)([0-9]+[A-Z]?)\1\s*,\s*"([^"]+)"\s*\)', repl_h1, src)


def repl_h2(m):
    body = m.group(1)
    mm = re.match(rf'({NUM})(\s.*)', body, re.S)
    if not mm:
        return m.group(0)
    num, rest = mm.group(1), mm.group(2)
    if num.split(".")[0] == "1":
        return f'h2sec_plain("{body}")'          # chapter 1 keeps its own 1.x numbering
    if num not in SUB:
        return m.group(0)
    return f'h3("{tok("S", num)}{rest}")'


src = re.sub(r'h2\(\s*"([^"]+)"\s*\)', repl_h2, src)

# ---- chapter openers --------------------------------------------------------
for ch, title, olds in CHAPTERS:
    if ch == 1:
        continue
    anchor = f'h2sec("{HEAD_TOK[olds[0]]}",'
    i = src.index(anchor)
    ls = src.rfind("\n", 0, i) + 1
    src = src[:ls] + f'chapter({ch}, {title!r},\n        {CH_BLURB[ch]!r})\n' + src[ls:]

src = re.sub(r'part_divider\((?:[^()]|\([^()]*\))*\)\n\n?', '', src)

# ---- resolve placeholders ---------------------------------------------------
RESOLVE = {"T": TAB, "E": EXH, "S": SUB, "C": SEC, "A": ALL}
for tid, (kind, key) in REG.items():
    src = src.replace(tid, RESOLVE[kind][key])
leftover = sorted(set(re.findall(r"\x00([^\x00]*)\x00", src)))
if leftover:
    print("UNRESOLVED:", leftover[:25], f"({len(leftover)} total)")
    raise SystemExit(1)

SRC.write_text(src)

json.dump({"sections": SEC, "subsections": SUB, "tables": TAB, "exhibits": EXH},
          open(pathlib.Path(__file__).resolve().parents[1] /
               "data" / "processed" / "section_map.json", "w"), indent=1)
print(f"chapters: {len(CHAPTERS)} | sections remapped: {len(SEC) - 1} | "
      f"subsections: {len(SUB)} | tables: {len(TAB)} | exhibits: {len(EXH)}")
