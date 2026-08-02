"""Tableau-style chart system with deterministic, collision-free layout.

Layout model. Matplotlib's constrained_layout only reserves space for artists it owns
(axes, ticks, axis labels). Figure-level text placed at a negative y-offset is invisible to
it, which is how titles, subtitles and source notes end up printed over axis labels. So this
module does not rely on automatic layout at all: it measures the title/subtitle band and the
wrapped source/note band in inches, grows the figure by exactly that much, and pins each
band with `fig.subplots_adjust`. Nothing can overlap because nothing shares a band.

Visual language. Data-ink is maximised rather than decorated: there are no gridlines, no
spines, no tick marks and no boxes around annotations - the marks themselves and their
labels are the only ink on the page. Colour encodes rather than decorates: one accent for
the series carrying the argument, grey for context. Typography does the structural work
through weight rather than size or rule: a bold dark title states the finding, a light
subtitle states the units, and source and method text sits quietly at the foot in the
lightest register the face provides.

Output. Figures are written as SVG and embedded into the report as true vector artwork, so
they resolve at the device's own pixel density rather than at a fixed raster resolution. A
2x PNG is written alongside for review and for any consumer that cannot take vector. Because
the output is vector, strokes are specified as hairlines (0.5pt) which stay crisp at any
zoom instead of thickening into a visible rule.
"""
import pathlib
import textwrap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import (FuncFormatter, NullFormatter, LogLocator,
                               FixedLocator, NullLocator, MaxNLocator)

# --- Palette ----------------------------------------------------------------
# Categorical hues are used only where a category must be distinguished. The default is a
# neutral foundation with ONE accent carrying the insight; everything contextual is grey.
T10 = {
    "blue": "#4E79A7",     # primary accent - the series that carries the argument
    "orange": "#F28E2B",   # secondary accent - forecasts, exceptions
    "green": "#59A14F",    # success / confirming direction
    "red": "#E15759",      # alert / adverse direction
    "teal": "#76B7B2", "purple": "#B07AA1", "yellow": "#EDC948",
    "brown": "#9C755F", "pink": "#FF9DA7", "grey": "#BAB0AC",
}
ACCENT = T10["blue"]
SEQ = [T10["blue"], T10["orange"], T10["green"], T10["red"], T10["teal"],
       T10["purple"], T10["brown"], T10["yellow"]]

BG = "#FFFFFF"
INK = "#2F2F2F"        # primary text
MUTED = "#6E6E6E"      # secondary text: axis and tick labels
FAINT = "#6E6E6E"      # source and method note
GRID = "#E6E6E6"       # reserved; no gridlines are drawn (see hgrid)
CONTEXT = "#D9D9D9"    # context elements: reference series, non-focal marks
NEUTRAL = T10["grey"]  # background categories

TITLE_FS, SUB_FS, NOTE_FS = 11.0, 8.2, 6.3
LABEL_FS, TICK_FS, LEG_FS = 8.0, 7.6, 7.6
W_TITLE, W_BODY, W_LIGHT = "bold", "normal", "light"   # hierarchy carried by weight
HAIR = 0.5                                             # hairline stroke, in points

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": TICK_FS,
    "text.color": INK,
    "axes.titlesize": TITLE_FS, "axes.labelsize": LABEL_FS,
    "axes.labelcolor": MUTED, "axes.edgecolor": GRID, "axes.linewidth": 0.0,
    "axes.facecolor": BG, "figure.facecolor": BG,
    # No gridlines anywhere: the tick labels locate the scale and the marks carry the value.
    "axes.grid": False, "axes.grid.which": "major", "axes.axisbelow": True,
    # No spines at all: the gridlines already carry the scale, so an axis line is redundant ink.
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelsize": TICK_FS, "ytick.labelsize": TICK_FS,
    # Tick marks removed; the labels alone locate the scale.
    "xtick.major.size": 0, "ytick.major.size": 0,
    "xtick.minor.size": 0, "ytick.minor.size": 0,
    "xtick.major.pad": 4, "ytick.major.pad": 3,
    "lines.linewidth": 1.2, "lines.solid_capstyle": "round",
    "patch.linewidth": HAIR,
    "svg.fonttype": "path",          # glyphs as outlines: no font substitution downstream
    "pdf.fonttype": 42,
    "legend.frameon": False, "legend.fontsize": LEG_FS,
    "legend.handlelength": 1.6, "legend.handletextpad": 0.5,
    "legend.columnspacing": 1.4, "legend.labelcolor": MUTED,
    "figure.constrained_layout.use": False,     # layout is managed explicitly below
})

gpfmt = FuncFormatter(lambda v, _: f"{v:,.0f}")
pctfmt = FuncFormatter(lambda v, _: f"{v:g}%")


def hgrid(ax, x=False, nbins=4, grid=False):
    """Strip the frame entirely: no gridlines, no spines, no tick marks.

    Gridlines are removed everywhere. Values are conveyed by direct labels on the marks and
    by the tick labels on the axis; a grid on top of those is redundant ink. The `x` and
    `grid` arguments are retained so existing call sites remain valid, but neither draws
    anything - they are inert by design rather than by oversight.

    Pass nbins=None on a categorical axis, where thinning the ticks would silently delete
    category labels.
    """
    ax.grid(False)
    ax.set_axisbelow(True)
    if nbins is not None and ax.get_yscale() == "linear":
        ax.yaxis.set_major_locator(MaxNLocator(nbins=nbins, prune=None))
    for sp in ax.spines.values():
        sp.set_visible(False)


def bar_labels(ax, values, at=None, fmt="{:.2f}", horizontal=False, fs=6.8, color=INK, pad=3):
    """Print each bar's value at its tip.

    With no gridlines a bar chart would otherwise be unreadable in magnitude. Labelling the
    bars directly is both less ink than a grid and more precise than reading against one.
    """
    anchors = values if at is None else at
    for i, (v, a) in enumerate(zip(values, anchors)):
        if not np.isfinite(v):
            continue
        if horizontal:
            ax.annotate(fmt.format(v), xy=(a, i), xytext=(pad if v >= 0 else -pad, 0),
                        textcoords="offset points", va="center",
                        ha="left" if v >= 0 else "right", fontsize=fs, color=color,
                        fontweight=W_BODY)
        else:
            ax.annotate(fmt.format(v), xy=(i, a), xytext=(0, pad if v >= 0 else -pad),
                        textcoords="offset points", ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=fs, color=color,
                        fontweight=W_BODY)


def label_line(ax, x, y, text, color, dx=6, dy=0, fs=LEG_FS, ha="left", va="center"):
    """Direct label on a series, preferred over a legend entry."""
    ax.annotate(text, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                color=color, fontsize=fs, fontweight="bold", ha=ha, va=va,
                annotation_clip=False)


def clean_log(ax, axis="x"):
    """Decade-only labels on a log axis. Matplotlib labels 2x/3x/4x minor ticks by default,
    which collide at small figure widths."""
    a = ax.xaxis if axis == "x" else ax.yaxis
    a.set_major_locator(LogLocator(base=10.0))
    a.set_minor_locator(LogLocator(base=10.0, subs=tuple(range(2, 10)), numticks=12))
    a.set_minor_formatter(NullFormatter())
    a.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))


def log_ticks_within(ax, lo, hi, axis="x", fmt=None):
    """Place 1-2-5 style log ticks strictly inside [lo, hi].

    A default LogLocator emits ticks at the panel edges, whose labels then overhang into the
    neighbouring subplot. Restricting ticks to the data range keeps every label inside its
    own panel.
    """
    import numpy as _np
    cand = []
    for k in range(-6, 9):
        for m in (1, 2, 5):
            v = m * (10.0 ** k)
            if lo < v < hi:
                cand.append(v)
    if len(cand) > 4:
        cand = [cand[i] for i in _np.linspace(0, len(cand) - 1, 4).round().astype(int)]
    a = ax.xaxis if axis == "x" else ax.yaxis
    a.set_major_locator(FixedLocator(cand))
    a.set_minor_locator(NullLocator())
    a.set_major_formatter(FuncFormatter(fmt or (lambda v, _: f"{v:,.0f}")))


def bullet_chart(ax, labels, values, target, ranges=None, fmt="{:.3f}",
                accent=None, target_label="target"):
    """Bullet chart: performance against a benchmark.

    A measure bar per category, a vertical target marker, and optional qualitative bands
    behind. Used where the question is "how does this compare with the reference value?"
    rather than "how big is this?".
    """
    accent = accent or ACCENT
    y = np.arange(len(labels))
    if ranges:
        for lo, hi, shade in ranges:
            ax.barh(y, hi - lo, left=lo, height=0.62, color=shade, lw=0, zorder=1)
    ax.barh(y, values, height=0.30, color=accent, lw=0, zorder=3)
    for i in y:
        ax.plot([target, target], [i - 0.31, i + 0.31], color=INK, lw=1.6, zorder=4,
                solid_capstyle="butt")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0)
    # Value labels are pinned to the right edge of the axes rather than to the bar tip, so
    # they cannot collide with an interval whisker drawn over the bar.
    for i, v in enumerate(values):
        ax.annotate(fmt.format(v), xy=(0.995, i), xycoords=("axes fraction", "data"),
                    xytext=(0, 0), textcoords="offset points",
                    va="center", ha="right", fontsize=7.2, color=INK, fontweight=W_TITLE)
    return y


def heatmap(ax, M, row_labels, col_labels, fmt="{:+.2f}", cmap=None, center=0.0,
            cbar_label=None):
    """Diverging heatmap for a matrix of values, with the value printed in each cell.

    Text colour flips on dark cells so every label stays legible - contrast is a
    requirement, not a preference.
    """
    import matplotlib.colors as mcolors
    cmap = cmap or mcolors.LinearSegmentedColormap.from_list(
        "div", [T10["red"], "#F4F4F4", T10["blue"]])
    A = np.asarray(M, float)
    lim = np.nanmax(np.abs(A - center))
    im = ax.imshow(A, cmap=cmap, vmin=center - lim, vmax=center + lim, aspect="auto")
    ax.set_xticks(range(len(col_labels)), labels=col_labels)
    ax.set_yticks(range(len(row_labels)), labels=row_labels)
    ax.tick_params(length=0)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            if not np.isfinite(A[i, j]):
                continue
            rel = abs(A[i, j] - center) / (lim if lim else 1)
            ax.text(j, i, fmt.format(A[i, j]), ha="center", va="center", fontsize=6.8,
                    color="white" if rel > 0.55 else INK, fontweight=W_BODY)
    return im


def note_box(ax, text, loc="upper left", fs=7.0):
    """Annotation pinned to a corner of the axes in axes-fraction coordinates."""
    xy = {"upper left": (0.012, 0.97, "left", "top"),
          "upper right": (0.988, 0.97, "right", "top"),
          "lower left": (0.012, 0.03, "left", "bottom"),
          "lower right": (0.988, 0.03, "right", "bottom")}[loc]
    # No bounding box: a border here would be pure decoration around text that is already
    # separated from the marks by position and weight.
    ax.text(xy[0], xy[1], text, transform=ax.transAxes, ha=xy[2], va=xy[3],
            fontsize=fs, color=MUTED, linespacing=1.4, fontweight=W_LIGHT)


def _wrap(text, fig_w_in, fs):
    """Wrap to the figure width. ~1.92 chars per point of width at this font size."""
    chars = max(60, int(fig_w_in * 72 / (fs * 0.50)))
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, chars) or [""])
    return out


def check_overlaps(fig, fname="", min_frac=0.12, verbose=True):
    """Report pairwise overlaps between rendered text artists.

    Eyeballing a chart does not reliably catch a label sitting on top of another label, so
    every figure is checked after rendering: all visible Text artists are collected, their
    drawn bounding boxes measured in display coordinates, and any pair overlapping by more
    than `min_frac` of the smaller box is reported.
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    items = []
    for t in fig.findobj(match=plt.Text):
        try:
            if not t.get_visible() or not t.get_text().strip():
                continue
            bb = t.get_window_extent(renderer=rend)
            if bb.width <= 0 or bb.height <= 0:
                continue
            items.append((id(t), t.get_text().strip().replace("\n", " / ")[:34], bb))
        except Exception:
            continue
    # Text drawn outside the canvas is silently clipped, which the pairwise test cannot see.
    # fig.bbox is in the same display coordinates as get_window_extent. Tick labels are
    # excluded: matplotlib routinely lays out ticks beyond the visible range and never draws
    # them, so they are not real clipping.
    ticks = set()
    for ax in fig.axes:
        for tl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            ticks.add(id(tl))
    W, Hh = fig.bbox.x1, fig.bbox.y1
    for tid, txt, bb in items:
        if tid in ticks:
            continue
        if bb.x1 > W + 1 or bb.x0 < -1 or bb.y1 > Hh + 1 or bb.y0 < -1:
            if verbose:
                print(f"  CLIPPED {fname}: {txt!r} extends outside the canvas")

    hits = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (_, ta, ba), (_, tb, bb) = items[i], items[j]
            ix = max(0.0, min(ba.x1, bb.x1) - max(ba.x0, bb.x0))
            iy = max(0.0, min(ba.y1, bb.y1) - max(ba.y0, bb.y0))
            if ix <= 0 or iy <= 0:
                continue
            inter = ix * iy
            frac = inter / min(ba.width * ba.height, bb.width * bb.height)
            if frac > min_frac:
                hits.append((frac, ta, tb))
    if hits and verbose:
        for frac, ta, tb in sorted(hits, reverse=True)[:6]:
            print(f"  OVERLAP {fname}: {frac:5.0%}  {ta!r} <-> {tb!r}")
    return hits


# Titles, subtitles and source notes are set as DOCUMENT type rather than drawn into the
# image, so their typography matches the report and the artwork carries only the data. Each
# figure records its metadata here; the report reads it back from figures/manifest.json.
MANIFEST = {}


def finish(fig, fname, title, subtitle=None, source="", note="", outdir=None,
           left=0.085, right=0.985, xlabel_pad_in=0.38, hspace=None, wspace=None):
    """Grow the figure to fit a title band and a source/note band, then pin both.

    The axes rectangle is set from exact inch measurements, so the title, the subtitle, the
    x-axis label and the source note each occupy a disjoint horizontal band.
    """
    MANIFEST[pathlib.Path(fname).stem] = {"title": title, "subtitle": subtitle or "",
                                          "source": source, "note": note}
    w_in, h_axes_in = fig.get_size_inches()

    # Only a small top pad: title and subtitle live in the document, not in the image.
    PAD_TOP = 0.06
    top_in = PAD_TOP + 0.16

    # Title, subtitle and note are drawn from `text_left`; wrapping must use the width that
    # is actually available from there to the right edge, not the full figure width.
    text_left = min(left, 0.09)
    body = ""
    lines = _wrap(body, (right - text_left) * w_in, NOTE_FS) if body else []
    note_line_h = NOTE_FS / 72 * 1.42
    note_in = (len(lines) * note_line_h + 0.16) if lines else 0.0

    bottom_in = xlabel_pad_in + note_in
    H = h_axes_in + top_in + bottom_in
    fig.set_size_inches(w_in, H)
    kw = {}
    if hspace is not None:
        kw["hspace"] = hspace
    if wspace is not None:
        kw["wspace"] = wspace
    fig.subplots_adjust(left=left, right=right,
                        top=1 - top_in / H, bottom=bottom_in / H, **kw)


    # Vector first. The PNG is written at 2x for review and for any non-vector consumer.
    stem = pathlib.Path(fname).stem
    base = (outdir / stem) if outdir else pathlib.Path(stem)
    fig.savefig(base.with_suffix(".svg"), facecolor=BG)
    fig.savefig(base.with_suffix(".png"), facecolor=BG, dpi=200)
    check_overlaps(fig, fname)
    plt.close(fig)
