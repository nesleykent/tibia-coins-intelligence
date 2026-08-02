"""Render the full quantitative report to PDF.

Table safety: ReportLab does not wrap plain string cells. Every cell is measured against its
column width with stringWidth() and converted to a Paragraph when it would overflow, so no
table can print text over its own gridlines.
"""
import json, pathlib, re, warnings
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image, PageBreak, KeepTogether,
                                NextPageTemplate, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, FIG, OUT = ROOT / "data" / "processed", ROOT / "figures", ROOT / "reports"
OUT.mkdir(exist_ok=True)

R = json.load(open(P / "results.json"))
panel = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv", parse_dates=["first", "last", "created"])
idxdf = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
band = pd.read_csv(P / "arbitrage_band.csv")
ts = pd.read_csv(P / "stationarity.csv")
bd = pd.read_csv(P / "order_books.csv")
fcs = pd.read_csv(P / "forecasts_sa.csv")
fcj = json.load(open(P / "forecasts_sa.json"))
mreg = pd.read_csv(P / "world_merge_register.csv", parse_dates=["merge_date"])
bts = pd.read_csv(P / "forecast_backtest_summary.csv")
btsa = pd.read_csv(P / "forecast_backtest_summary_sa.csv")
prof = pd.read_csv(P / "snapshot_bias_summary.csv")
cal = pd.read_csv(P / "event_calendar.csv", parse_dates=["date"])
sm = pd.read_csv(P / "population_summary.csv")
raw_n = len(pd.read_parquet(P / "snapshots_raw.parquet"))
SRC_N = panel.price_source.value_counts().to_dict()

W = R["window"]
PW, PH = A4
# Editorial measure. Wider margins and a shorter line make the page scannable;
# density is reduced by giving the text less width, not by removing content.
ML, MR = 24 * mm, 22 * mm
MT, MB = 24 * mm, 20 * mm
AVAIL = PW - ML - MR

# Display type is a serif, body type a sans - the convention these reports follow.
SERIF, SERIF_B = "Times-Roman", "Times-Bold"
try:
    _g = pathlib.Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("Georgia", _g / "Georgia.ttf"))
    pdfmetrics.registerFont(TTFont("Georgia-Bold", _g / "Georgia Bold.ttf"))
    SERIF, SERIF_B = "Georgia", "Georgia-Bold"
except Exception:
    pass

NAVY = colors.HexColor("#051C2C")
ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontSize=20, leading=24, spaceAfter=4),
    "sub": ParagraphStyle("sb", parent=ss["Normal"], fontSize=10.5, leading=14,
                          alignment=TA_CENTER, textColor=colors.HexColor("#444444")),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=SERIF_B, fontSize=23,
                         leading=27, spaceBefore=0, spaceAfter=13,
                         textColor=colors.HexColor("#2F2F2F")),
    "kicker": ParagraphStyle("kick", parent=ss["Normal"], fontSize=7.8, leading=11,
                             fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=6,
                             textColor=colors.HexColor("#4E79A7")),
    "h2sec": ParagraphStyle("h2s", parent=ss["Heading2"], fontName=SERIF_B, fontSize=16.5,
                            leading=20, spaceBefore=6, spaceAfter=9,
                            textColor=colors.HexColor("#2F2F2F")),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, leading=15,
                         spaceBefore=17, spaceAfter=6,
                         textColor=colors.HexColor("#1f4e79")),
    "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=9.5, leading=12, spaceBefore=6,
                         spaceAfter=2, textColor=colors.HexColor("#333333")),
    "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.4, leading=15.2,
                           alignment=TA_LEFT, spaceAfter=9.5,
                           textColor=colors.HexColor("#2F2F2F")),
    "bullet": ParagraphStyle("bu", parent=ss["BodyText"], fontSize=9.4, leading=14.6,
                             leftIndent=13, bulletIndent=2, spaceAfter=7,
                             alignment=TA_LEFT, textColor=colors.HexColor("#2F2F2F")),
    "cap": ParagraphStyle("c", parent=ss["Normal"], fontSize=7.3, leading=10.2,
                          textColor=colors.HexColor("#6E6E6E"), spaceAfter=10, spaceBefore=4),
    "ex_lbl": ParagraphStyle("exl", parent=ss["Normal"], fontSize=7.6, leading=10,
                             textColor=colors.HexColor("#6E6E6E"), spaceAfter=4,
                             spaceBefore=22),
    "ex_ttl": ParagraphStyle("ext", parent=ss["Normal"], fontSize=12.5, leading=16,
                             fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#2F2F2F"), spaceAfter=5),
    "ex_sig": ParagraphStyle("exs", parent=ss["Normal"], fontSize=6.6, leading=9,
                             fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#6E6E6E"), spaceBefore=5,
                             spaceAfter=24),
    "cell": ParagraphStyle("ce", parent=ss["Normal"], fontSize=7.2, leading=8.8),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontSize=7.2, leading=8.8,
                            fontName="Helvetica-Bold"),
    "note": ParagraphStyle("n", parent=ss["BodyText"], fontSize=8.2, leading=11,
                           leftIndent=8, textColor=colors.HexColor("#333333"),
                           borderPadding=3, spaceAfter=6, alignment=TA_JUSTIFY),
    # Bottom-line callout: the section's answer, stated before its evidence.
    "bl": ParagraphStyle("bl", parent=ss["BodyText"], fontSize=9.2, leading=12.8,
                         textColor=colors.HexColor("#1f4e79"), alignment=TA_JUSTIFY,
                         leftIndent=6, rightIndent=4, spaceBefore=1, spaceAfter=1),
    "hero_v": ParagraphStyle("hv", parent=ss["Normal"], fontName=SERIF_B, fontSize=72,
                             leading=88, spaceAfter=6,
                             textColor=colors.HexColor("#1f4e79")),
    "hero_l": ParagraphStyle("hl", parent=ss["Normal"], fontSize=13.5, leading=19,
                             rightIndent=40, spaceAfter=3,
                             textColor=colors.HexColor("#2F2F2F")),
    "hero_s": ParagraphStyle("hs", parent=ss["Normal"], fontSize=9.6, leading=15.5,
                             rightIndent=52, textColor=colors.HexColor("#6E6E6E")),
    "takeaway": ParagraphStyle("tk", parent=ss["Normal"], fontSize=9.6, leading=13.5,
                               textColor=colors.HexColor("#1f4e79"), spaceBefore=6,
                               spaceAfter=5),
    "kpi_v": ParagraphStyle("kv", parent=ss["Normal"], fontSize=13.5, leading=15,
                            fontName="Helvetica-Bold", alignment=TA_CENTER,
                            textColor=colors.HexColor("#1f4e79")),
    "kpi_l": ParagraphStyle("kl", parent=ss["Normal"], fontSize=6.8, leading=8.4,
                            alignment=TA_CENTER, textColor=colors.HexColor("#555555")),
    "cover_t": ParagraphStyle("ct", parent=ss["Normal"], fontSize=30, leading=34,
                              fontName="Helvetica-Bold", textColor=colors.HexColor("#2F2F2F")),
    "cover_s": ParagraphStyle("cs", parent=ss["Normal"], fontSize=12.5, leading=17,
                              textColor=colors.HexColor("#4E79A7")),
    "cover_m": ParagraphStyle("cm", parent=ss["Normal"], fontSize=8.6, leading=13,
                              textColor=colors.HexColor("#6E6E6E")),
    "part": ParagraphStyle("part", parent=ss["Normal"], fontName=SERIF_B, fontSize=26,
                           leading=31, textColor=colors.HexColor("#2F2F2F")),
    "part_n": ParagraphStyle("pn", parent=ss["Normal"], fontSize=9.5, leading=13,
                             fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#4E79A7")),
    "part_b": ParagraphStyle("pb", parent=ss["Normal"], fontSize=10, leading=14.5,
                             textColor=colors.HexColor("#6E6E6E"), alignment=TA_JUSTIFY),
    "h1_noindex": ParagraphStyle("h1x", parent=ss["Heading1"], fontName=SERIF_B,
                                 fontSize=15.5, leading=19, spaceBefore=12, spaceAfter=7,
                                 textColor=colors.HexColor("#2F2F2F")),
    "toc1": ParagraphStyle("toc1", parent=ss["Normal"], fontSize=8.6, leading=17,
                           fontName="Helvetica-Bold", spaceBefore=9,
                           textColor=colors.HexColor("#4E79A7")),
    "bl_plain": ParagraphStyle("blp", parent=ss["BodyText"], fontSize=10.5, leading=15.5,
                               textColor=colors.HexColor("#4E79A7"), spaceAfter=4),
    "cmp_hd": ParagraphStyle("ch", parent=ss["Normal"], fontSize=6.9, leading=9.5,
                             fontName="Helvetica-Bold", textColor=colors.white),
    "cmp_l": ParagraphStyle("cl", parent=ss["Normal"], fontSize=8.6, leading=12.4,
                            textColor=colors.HexColor("#8A1F1F")),
    "cmp_r": ParagraphStyle("cr", parent=ss["Normal"], fontSize=8.6, leading=12.4,
                            textColor=colors.HexColor("#2F2F2F")),
    "cmp_n": ParagraphStyle("cn", parent=ss["Normal"], fontSize=9.2, leading=12.4,
                            textColor=colors.HexColor("#1f4e79")),
    "toc2": ParagraphStyle("toc2", parent=ss["Normal"], fontSize=9, leading=14.6,
                           leftIndent=10, textColor=colors.HexColor("#2F2F2F")),
    # Icon-led recommendation cards
    "card_who": ParagraphStyle("cw", parent=ss["Normal"], fontSize=7.4, leading=10,
                               fontName="Helvetica-Bold", spaceAfter=2,
                               textColor=colors.HexColor("#4E79A7")),
    "card_act": ParagraphStyle("ca", parent=ss["Normal"], fontSize=9.6, leading=13.4,
                               textColor=colors.HexColor("#2F2F2F")),
    "card_ev": ParagraphStyle("cev", parent=ss["Normal"], fontSize=7.4, leading=10.4,
                              spaceBefore=3, textColor=colors.HexColor("#6E6E6E")),
    # Verdict page, set on the navy field
    "v_kick": ParagraphStyle("vk", parent=ss["Normal"], fontSize=8, leading=11,
                             fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#7FA8C9")),
    "v_word": ParagraphStyle("vw", parent=ss["Normal"], fontName=SERIF_B, fontSize=66,
                             leading=72, textColor=colors.HexColor("#FFFFFF")),
    "v_lead": ParagraphStyle("vl", parent=ss["Normal"], fontSize=12.5, leading=18,
                             textColor=colors.HexColor("#ADCDE6")),
    "v_num": ParagraphStyle("vn", parent=ss["Normal"], fontName=SERIF_B, fontSize=21,
                            leading=24, textColor=colors.HexColor("#FFFFFF")),
    "v_hd": ParagraphStyle("vh", parent=ss["Normal"], fontSize=7.6, leading=10.5,
                           fontName="Helvetica-Bold", spaceAfter=5,
                           textColor=colors.HexColor("#7FA8C9")),
    "v_item": ParagraphStyle("vi", parent=ss["Normal"], fontSize=8.6, leading=12.6,
                             spaceAfter=6, textColor=colors.HexColor("#DCE8F2")),
    "v_foot": ParagraphStyle("vf", parent=ss["Normal"], fontSize=8, leading=12,
                             textColor=colors.HexColor("#7FA8C9")),
}

CLAIM = {
    "mech": "Documented mechanic", "obs": "Observed data", "stat": "Statistical relationship",
    "econ": "Economic interpretation", "hyp": "Hypothesis", "fc": "Forecast",
    "judg": "Analyst judgement", "lim": "Limitation",
}
TAGCOL = {"mech": "#2f6f2f", "obs": "#1f4e79", "stat": "#6a3d9a", "econ": "#a05000",
          "hyp": "#8a6d00", "fc": "#8a1f1f", "judg": "#555555", "lim": "#8a1f1f"}

story = []


def tag(k):
    return (f'<font color="{TAGCOL[k]}" size="7.4"><b>[{CLAIM[k]}]</b></font> ')


def para(txt, st="body"):
    story.append(Paragraph(txt, S[st]))


class SetChapterBand(Spacer):
    """Zero-height flowable that tells the page template which artwork band to lay down."""

    def __init__(self, path):
        super().__init__(0, 0)
        self.path = path

    def draw(self):
        pass

    def wrap(self, aw, ah):
        self.canv._doctemplate._ch_band = self.path
        return (0, 0)


def fresh_page(template=None):
    """Begin the next flowable on a new page, without leaving an empty one behind.

    Sections end with their own PageBreak, and page-level constructs - chapter openers, key
    statistics, the verdict, the appendices - each opened another. Two breaks in a row emit a
    blank page, so when the story already ends with one the template switch is inserted ahead
    of it rather than a second break being appended.
    """
    if story and isinstance(story[-1], PageBreak):
        if template:
            story.insert(len(story) - 1, NextPageTemplate(template))
        return
    if template:
        story.append(NextPageTemplate(template))
    story.append(PageBreak())


def chapter(num, title, blurb):
    """Full-page chapter opener: number, large serif title, and what the chapter establishes."""
    fresh_page("plain")
    story.append(Spacer(1, 58 * mm))
    story.append(Paragraph(f"Chapter {num}", S["part_n"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(title, S["part"]))
    story.append(Spacer(1, 14))
    t = Table([[""]], colWidths=[40 * mm], rowHeights=[2.4])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4E79A7"))]))
    story.append(t)
    story.append(Spacer(1, 15))
    story.append(Paragraph(blurb, S["part_b"]))
    mark = FIG / f"mark_ch{num}.svg"
    if mark.exists():
        art = vector(mark, AVAIL * 0.62)
        if art is not None:
            story.append(Spacer(1, 22))
            story.append(art)
    story.append(SetChapterBand(FIG / "art" / f"ch{num}.jpg"))
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())


def h2sec(num, kicker, insight=None):
    """Section opener: a small navigational kicker, then the finding as the headline.

    The kicker keeps the contents and the running header scannable; the headline states the
    conclusion so the page can be understood before it is read.
    """
    story.append(CondPageBreak(240))
    if insight is None:
        story.append(Paragraph(f"{num} {kicker}", S["h2sec"]))
        return
    story.append(Paragraph(f"{num}  {kicker.upper()}", S["kicker"]))
    story.append(Paragraph(insight, S["h2sec"]))


def h2sec_plain(t):
    story.append(Paragraph(t, S["h2sec"]))


def h3(t):
    story.append(Paragraph(t, S["h2"]))


def h1(n, t):
    # A section title never sits at the foot of a page: if less than a third of the page
    # remains, the section opens on a fresh one with room to breathe.
    story.append(CondPageBreak(230))
    story.append(Paragraph(f"{n}. {t}", S["h1"]))


def h2(t):
    story.append(Paragraph(t, S["h2"]))


def h1_plain(t):
    """An unnumbered chapter-level heading that still reaches the contents page."""
    story.append(CondPageBreak(230))
    story.append(Paragraph(t, S["h1"]))


def part_divider(num, title, blurb):
    """Full-page section divider: part number, title, and what the part establishes."""
    fresh_page("plain")
    story.append(Spacer(1, 62 * mm))
    story.append(Paragraph(num, S["part_n"]))
    story.append(Spacer(1, 3))
    story.append(Paragraph(title, S["part"]))
    story.append(Spacer(1, 13))
    t = Table([[""]], colWidths=[38 * mm], rowHeights=[2.2])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4E79A7"))]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(blurb, S["part_b"]))
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())


class HeroMark(Spacer):
    """Zero-height flowable naming the artwork for the key-statistic page it opens."""

    def __init__(self, key):
        Spacer.__init__(self, 1, 0)
        self.key = key

    def draw(self):
        self.canv._doctemplate._hero_mark = self.key


def hero(value, label, support=None, mark=None):
    """A key-statistic page. One number, its meaning, and the evidence behind it - nothing
    else on the page, so the figure lands before anything competes with it. An optional mark
    sits low in the outer corner, knocked well back, to give the page a subject."""
    fresh_page()
    if mark:
        story.append(HeroMark(mark))
    story.append(Spacer(1, 46 * mm))
    story.append(Paragraph(value, S["hero_v"]))
    story.append(Paragraph(label, S["hero_l"]))
    if support:
        story.append(Spacer(1, 7))
        story.append(Paragraph(support, S["hero_s"]))
    story.append(PageBreak())


ICO = FIG / "icons"


def icon_cards(items, caption=None):
    """Recommendations as marked cards rather than table rows.

    As a four-column table this asked the reader to scan across three columns of supporting
    detail before reaching the recommendation. Leading each row with a mark lets a reader find
    their own row without reading the others, and setting the action as the line of type puts
    the recommendation where the eye lands first. No content is dropped: the evidence and the
    falsifying condition follow in the small line beneath.
    """
    rows, styles = [], [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 7), ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]
    iw = 13 * mm
    for i, (icon, who, action, evidence, changes) in enumerate(items):
        art = vector(ICO / f"{icon}.svg", 9.5 * mm)
        body = [Paragraph(who.upper(), S["card_who"]), Paragraph(action, S["card_act"]),
                Paragraph(f"<b>Evidence</b> {evidence} &nbsp;&nbsp;|&nbsp;&nbsp; "
                          f"<b>Reverses if</b> {changes}", S["card_ev"])]
        rows.append([art if art is not None else "", body])
        # Alternate rows carry a faint tint so the cards separate without a rule between them.
        if i % 2:
            styles.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4F7FA")))
    t = Table(rows, colWidths=[iw, AVAIL - iw])
    t.setStyle(TableStyle(styles))
    story.append(t)
    if caption:
        story.append(Paragraph(caption, S["cap"]))


def verdict_page(word, lead, score, supporting, against, foot):
    """The conclusion as a designed page: the rating, the score, and the two-sided balance.

    The verdict is the one thing every reader is looking for, and in running text it arrived as
    another paragraph among paragraphs. Setting it on the navy field gives it the weight of a
    chapter opener, and putting the two lists side by side shows the balance rather than
    asserting it - the reader can see that neither column dominates.
    """
    fresh_page("verdict")
    story.append(Spacer(1, 50 * mm))
    story.append(Paragraph("THE VERDICT", S["v_kick"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(word, S["v_word"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(lead, S["v_lead"]))
    story.append(Spacer(1, 16))

    # Confidence as a filled rule: the number and the proportion it represents, together.
    bar = Table([[""] * 2], colWidths=[AVAIL * score / 100, AVAIL * (100 - score) / 100],
                rowHeights=[3.2])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#4E79A7")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#183A50")),
    ]))
    story.append(Paragraph(f"{score} <font size=11>/ 100</font>&nbsp;&nbsp;"
                           f"<font size=8 color='#7FA8C9'>CONFIDENCE</font>", S["v_num"]))
    story.append(Spacer(1, 5))
    story.append(bar)
    story.append(Spacer(1, 18))

    col = (AVAIL - 10 * mm) / 2
    left = [Paragraph("WHAT SUPPORTS A FIRMER VIEW", S["v_hd"])] + \
           [Paragraph("&mdash;&nbsp; " + x, S["v_item"]) for x in supporting]
    right = [Paragraph("WHAT ARGUES AGAINST IT", S["v_hd"])] + \
            [Paragraph("&mdash;&nbsp; " + x, S["v_item"]) for x in against]
    two = Table([[left, "", right]], colWidths=[col, 10 * mm, col])
    two.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(two)
    story.append(Spacer(1, 14))
    story.append(Paragraph(foot, S["v_foot"]))
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())


_COUNT_WORD = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven"}


def comparison_page(title, standfirst, rows, foot=None):
    """A page that sets the obvious measure against the right one.

    Several findings in this study are of the same shape - a number everyone reaches for turns
    out to measure something else - and they are scattered across four chapters. Collecting
    them on one page lets a reader see the pattern rather than four unrelated corrections.
    """
    fresh_page()
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("HOW TO READ THIS MARKET", S["kicker"]))
    story.append(Paragraph(title.replace("{n}", _COUNT_WORD.get(len(rows), str(len(rows)))),
                           S["h1"]))
    story.append(Paragraph(standfirst, S["bl_plain"]))
    story.append(Spacer(1, 9))
    hdr = [Paragraph("THE OBVIOUS MEASURE", S["cmp_hd"]),
           Paragraph("WHAT IT ACTUALLY SHOWS", S["cmp_hd"]),
           Paragraph("SIZE OF THE ERROR", S["cmp_hd"])]
    data = [hdr]
    for wrong, right, size, where in rows:
        data.append([Paragraph(wrong, S["cmp_l"]),
                     Paragraph(right, S["cmp_r"]),
                     Paragraph(f"<b>{size}</b><br/><font size=6.6 color='#6E6E6E'>{where}</font>",
                               S["cmp_n"])])
    w1 = (AVAIL - 32 * mm) * 0.42
    t = Table(data, colWidths=[w1, AVAIL - 32 * mm - w1, 32 * mm])
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#051C2C"))]
    for i in range(1, len(data)):
        if i % 2:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4F7FA")))
    t.setStyle(TableStyle(st))
    story.append(t)
    if foot:
        story.append(Spacer(1, 8))
        story.append(Paragraph(foot, S["cap"]))
    story.append(PageBreak())


def takeaway(txt):
    """One-line conclusion placed above a table, so the reader knows what it shows."""
    story.append(Paragraph("<b>" + txt + "</b>", S["takeaway"]))


def bottomline(txt):
    """State the section's conclusion before presenting its evidence (Minto's pyramid)."""
    t = Table([[Paragraph("<b>Bottom line.</b> " + txt, S["bl"])]], colWidths=[AVAIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f8")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 7))


def kpi_row(items):
    """A compact row of headline figures, each with a one-line label."""
    cells = [[Paragraph(v, S["kpi_v"])] + [Paragraph(l, S["kpi_l"])] for v, l in items]
    data = [[Paragraph(v, S["kpi_v"]) for v, _ in items],
            [Paragraph(l, S["kpi_l"]) for _, l in items]]
    w = AVAIL / len(items)
    t = Table(data, colWidths=[w] * len(items))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1), ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FA")),
    ]))
    story.append(t)
    story.append(Spacer(1, 9))


def bullets(items, st="bullet"):
    for it in items:
        story.append(Paragraph(it, S[st], bulletText="•"))
    story.append(Spacer(1, 3))


def gp(v, d=0):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:,.{d}f}"


def pc(v, d=2, sign=False):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    return f"{v:+.{d}f}%" if sign else f"{v:.{d}f}%"


def pval(p):
    if p is None or (isinstance(p, float) and not np.isfinite(p)):
        return "n/a"
    return "&lt;0.001" if p < 0.001 else f"{p:.3f}"


def mktable(rows, widths, align=None, header=True, fs=7.2, hdr_bg="#1f4e79",
            zebra=True, halign="LEFT"):
    """Build a Table, converting any cell that would overflow its column into a Paragraph."""
    font, bfont = "Helvetica", "Helvetica-Bold"
    data = []
    for i, row in enumerate(rows):
        out = []
        for j, cell in enumerate(row):
            txt = "" if cell is None else str(cell)
            isH = header and i == 0
            fn = bfont if isH else font
            pad = 7
            # A plain string cell is drawn verbatim, so any cell carrying inline markup or an
            # HTML entity must become a Paragraph or the tags print literally.
            has_markup = ("<" in txt and ">" in txt) or "&" in txt
            plain = re.sub(r"<[^>]+>", "", txt)
            plain = re.sub(r"&[a-zA-Z]+;", "x", plain)
            if has_markup or stringWidth(plain, fn, fs) > widths[j] - pad:
                stl = ParagraphStyle(
                    f"c{i}_{j}", parent=S["cellb" if isH else "cell"], fontSize=fs,
                    leading=fs * 1.22,
                    textColor=colors.white if isH else colors.black,
                    alignment=TA_CENTER if (align and align[j] == "C") else 0)
                out.append(Paragraph(txt, stl))
            else:
                out.append(txt)
        data.append(out)

    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign=halign)
    cmds = [
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("LEADING", (0, 0), (-1, -1), fs * 1.22),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(hdr_bg)),
                 ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                 ("FONTNAME", (0, 0), (-1, 0), bfont)]
    if zebra:
        for i in range(1 + (1 if header else 0), len(data), 2):
            cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f2f5f8")))
    if align:
        for j, a in enumerate(align):
            if a in ("R", "C"):
                cmds.append(("ALIGN", (j, 0), (j, -1), "RIGHT" if a == "R" else "CENTER"))
    t.setStyle(TableStyle(cmds))
    return t


def table(rows, widths, caption=None, **kw):
    t = mktable(rows, widths, **kw)
    story.append(t)
    if caption:
        story.append(Paragraph(caption, S["cap"]))
    else:
        story.append(Spacer(1, 6))


def vector(path, width):
    """Load an SVG as a scaled ReportLab Drawing - true vector, not a raster placement.

    The report is a PDF, so embedding figures as artwork rather than as pixels means they
    resolve at the reader's own device density instead of at a baked-in resolution.
    """
    d = svg2rlg(str(path))
    if d is None:
        return None
    sc = width / d.width
    d.scale(sc, sc)
    d.width, d.height = width, d.height * sc
    d.hAlign = "LEFT"
    return d


EXHIBIT_N = [0]
MF = json.load(open(FIG / "manifest.json")) if (FIG / "manifest.json").exists() else {}


def figure(name, caption="", width=None):
    """Place an exhibit: numbered label, insight-led title and units subtitle in document
    type, the artwork, then source and method notes and a signature rule.

    Title and subtitle come from the figure's own manifest entry rather than being drawn into
    the image, so their typography matches the surrounding text exactly.
    """
    stem = pathlib.Path(name).stem
    meta = MF.get(stem, {})
    # Exhibits are numbered by section (Exhibit 19.1, not Exhibit 7), so every cross-reference
    # in the running text resolves without a lookup table.
    m = re.match(r"\s*(?:Figure|Exhibit)\s+([0-9A-Za-z]+\.[0-9]+)", caption or "")
    if m:
        num = m.group(1)
    else:
        EXHIBIT_N[0] += 1
        num = str(EXHIBIT_N[0])
    head = [Paragraph(f"Exhibit {num}", S["ex_lbl"])]
    if meta.get("title"):
        head.append(Paragraph(meta["title"], S["ex_ttl"]))
    if meta.get("subtitle"):
        head.append(Paragraph(meta["subtitle"], S["cap"]))
    art = _artwork(stem, width)
    if art is None:
        return
    # The manifest note supersedes the legacy caption text, which said the same thing twice.
    tail = []
    foot = " ".join(x for x in [meta.get("source", ""), meta.get("note", "")] if x)
    if foot:
        tail.append(Paragraph(foot, S["cap"]))
    tail.append(Paragraph("Tibia Coin Market Report", S["ex_sig"]))
    story.append(KeepTogether(head + [art] + tail))


def _artwork(stem, width=None):
    svg, png = FIG / f"{stem}.svg", FIG / f"{stem}.png"
    w = width or AVAIL
    maxh = PH - MT - MB - 40
    art = None
    if svg.exists():
        art = vector(svg, w)
        if art is not None and art.height > maxh:
            art = vector(svg, w * maxh / art.height)
    if art is None and png.exists():                 # raster fallback
        from PIL import Image as PILImage
        iw, ih = PILImage.open(png).size
        h = w * ih / iw
        if h > maxh:
            h, w = maxh, maxh * iw / ih
        art = Image(str(png), width=w, height=h)
    return art


# ============================================================== page furniture
from reportlab.lib.pagesizes import landscape
LW, LH = landscape(A4)


def _foot(canv, right_edge):
    canv.saveState()
    canv.setFont("Helvetica", 7)
    canv.setFillColor(colors.HexColor("#777777"))
    canv.drawString(ML, 9 * mm, "Tibia Coin Market - Multi-World Quantitative Report")
    canv.drawRightString(right_edge, 9 * mm, f"Page {canv.getPageNumber()}")
    canv.setStrokeColor(colors.HexColor("#cccccc"))
    canv.setLineWidth(0.4)
    canv.line(ML, 12 * mm, right_edge, 12 * mm)
    canv.restoreState()


def _head(canv, doc, right_edge):
    """Running header: the section the reader is currently in."""
    label = getattr(doc, "cur_section", "") or ""
    if not label:
        return
    canv.saveState()
    canv.setFont("Helvetica", 7)
    canv.setFillColor(colors.HexColor("#8A8A8A"))
    canv.drawString(ML, PH - MT + 5 * mm, label[:88])
    canv.setStrokeColor(colors.HexColor("#E6E6E6"))
    canv.setLineWidth(0.4)
    canv.line(ML, PH - MT + 3.6 * mm, right_edge, PH - MT + 3.6 * mm)
    canv.restoreState()


def _page(canv, doc):
    canv.setPageSize(A4)
    _foot(canv, PW - MR)


def _page_end(canv, doc):
    # Drawn at page end, not page begin: the flowable that names the mark has to have been
    # laid out before the canvas can know which page it belongs to.
    _head(canv, doc, PW - MR)
    mark = getattr(doc, "_hero_mark", None)
    if mark:
        art = FIG / "art" / f"mark_{mark}.png"
        if art.exists():
            from PIL import Image as _PIL
            iw, ih = _PIL.open(art).size
            w = 64 * mm
            canv.drawImage(str(art), PW - MR - w, MB + 10 * mm, width=w, height=w * ih / iw,
                           preserveAspectRatio=True, mask="auto")
        doc._hero_mark = None


def _page_wide(canv, doc):
    canv.setPageSize(landscape(A4))
    _foot(canv, LW - ML)


def _page_plain(canv, doc):
    """Chapter openers: no furniture, and a full-bleed artwork band at the foot."""
    canv.setPageSize(A4)
    band = getattr(doc, "_ch_band", None)
    if band and band.exists():
        from PIL import Image as _PIL
        iw, ih = _PIL.open(band).size
        h = PW * ih / iw
        canv.drawImage(str(band), 0, 0, width=PW, height=h,
                       preserveAspectRatio=False, mask=None)
    doc._ch_band = None


def _page_verdict(canv, doc):
    """The conclusion page: navy field, no furniture, so the rating carries the page."""
    canv.setPageSize(A4)
    canv.setFillColor(NAVY)
    canv.rect(0, 0, PW, PH, stroke=0, fill=1)


def _page_cover(canv, doc):
    """Full-bleed cover, drawn on the canvas so the artwork reaches the page edge."""
    canv.setPageSize(A4)
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, PW, PH, stroke=0, fill=1)
    # Artwork as atmosphere, duotoned into the navy ramp and faded out toward the title so it
    # never competes with the type. The data ribbon composites on top of it.
    bg = FIG / "art" / "cover_bg.jpg"
    if bg.exists():
        canv.drawImage(str(bg), 0, 0, width=PW, height=PH,
                       preserveAspectRatio=False, mask=None)
    art = FIG / "cover_art.svg"
    if art.exists():
        d = svg2rlg(str(art))
        if d is not None:
            sc = PW / d.width
            d.scale(sc, sc)
            renderPDF.draw(d, canv, 0, PH - d.height * sc)
    canv.setFillColor(colors.white)
    canv.setFont(SERIF_B, 34)
    canv.drawString(20 * mm, PH - 62 * mm, "The Tibia")
    canv.drawString(20 * mm, PH - 76 * mm, "Coin Market")
    canv.setFont("Helvetica", 12)
    canv.setFillColor(colors.HexColor("#BBD3E8"))
    canv.drawString(20 * mm, PH - 89 * mm,
                    "Price formation, arbitrage and efficiency")
    canv.drawString(20 * mm, PH - 95.5 * mm, "across 93 game worlds")
    canv.setFont("Helvetica", 8.5)
    canv.setFillColor(colors.HexColor("#8FAFC9"))
    canv.drawString(20 * mm, PH - 107 * mm, "July 2026")
    # Scope block, bottom left - the equivalent of the authors block on these covers
    canv.setFont("Helvetica-Bold", 8)
    canv.setFillColor(colors.white)
    canv.drawString(20 * mm, 30 * mm, "Coverage")
    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#BBD3E8"))
    for i, line in enumerate(["93 worlds", "40,658 world-day observations",
                              "11 Jan 2023 - 30 Jul 2026", "4 independent data sources"]):
        canv.drawString(20 * mm, 30 * mm - (i + 1) * 4.6 * mm, line)
    # Origin mark only, per the terms the artwork is distributed under.
    lg = FIG / "art" / "tibia_logo_navy.png"
    if lg.exists():
        w = 32 * mm
        canv.drawImage(str(lg), PW - 22 * mm - w, 24 * mm, width=w, height=w * 252 / 640,
                       mask="auto")
    canv.restoreState()


class ReportDoc(BaseDocTemplate):
    """Doc template that records headings for the table of contents and the running header."""

    cur_section = ""

    def handle_documentBegin(self):
        # multiBuild runs the story twice; without this the header on the second pass opens
        # showing whatever section the first pass ended on.
        self.cur_section = ""
        super().handle_documentBegin()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        name = flowable.style.name
        # Parts index at level 0 and sections at level 1, so the contents page carries the
        # document's structure rather than one flat list.
        if name == "h1":
            # Only the front matter and the executive summary carry this style, and both are
            # chapter-level items - indexing them at level 1 set them below their own sections.
            txt = flowable.getPlainText()
            self.cur_section = txt
            self.notify("TOCEntry", (0, txt.upper(), self.page))
        elif name == "kick":
            self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))

        elif name == "part":
            txt = flowable.getPlainText()
            self.cur_section = f"{self._pending_ch} {txt}" if getattr(self, "_pending_ch", "") else txt
            # Carry the chapter number into the contents. Sections index as "5.2 ARBITRAGE",
            # so a bare "MARKET STRUCTURE" above them gave the reader nothing to match on.
            ch = re.sub(r"\D", "", getattr(self, "_pending_ch", ""))
            self.notify("TOCEntry",
                        (0, f"{ch}. {txt.upper()}" if ch else txt.upper(), self.page))
        elif name == "pn":
            self._pending_ch = flowable.getPlainText() + "  ·"


doc = ReportDoc(str(OUT / "tibia_coin_market_report.pdf"), pagesize=A4,
                      leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                      title="Tibia Coin Market: Multi-World Quantitative Report",
                      author="Quantitative analysis", subject="gold-denominated Tibia Coin market")
frame = Frame(ML, MB, AVAIL, PH - MT - MB, id="n", leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)
AW = LW - ML - ML                       # usable width on a landscape page
frameL = Frame(ML, MB, AW, LH - MT - MB, id="l", leftPadding=0, rightPadding=0,
               topPadding=0, bottomPadding=0)
frameC = Frame(ML, MB, AVAIL, PH - MT - MB, id="c", leftPadding=0, rightPadding=0,
               topPadding=0, bottomPadding=0)
# "plain" is listed first because ReportLab always begins on templates[0]; the cover and the
# part dividers carry no header, footer or page number.
doc.addPageTemplates([PageTemplate(id="cover", frames=[frameC], onPage=_page_cover,
                                   pagesize=A4),
                      PageTemplate(id="plain", frames=[frameC], onPage=_page_plain,
                                   pagesize=A4),
                      PageTemplate(id="normal", frames=[frame], onPage=_page,
                                   onPageEnd=_page_end, pagesize=A4),
                      PageTemplate(id="wide", frames=[frameL], onPage=_page_wide,
                                   pagesize=landscape(A4)),
                      PageTemplate(id="verdict", frames=[frameC], onPage=_page_verdict,
                                   pagesize=A4)])

exec(open(pathlib.Path(__file__).parent / "09_sections.py").read())

# multiBuild: the table of contents needs a second pass to resolve page numbers.
doc.multiBuild(story)
print("PDF written:", OUT / "tibia_coin_market_report.pdf")
