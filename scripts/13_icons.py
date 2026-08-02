"""Draw the executive-summary pictograms.

The recommendation cards in Chapter 1 address five different readers, and a reader looking for
their own row should be able to find it without reading the others. A mark per row does that
work faster than a label does.

These are drawn rather than sourced: the game artwork is illustrative and would fight the
restrained palette at this size, whereas a geometric mark in the report's own navy sits inside
the type. Each is a 48x48 line drawing at a single stroke weight, so the five read as one set.
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "figures" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#051C2C"
SW = 2.0

HEAD = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">'
        f'<g fill="none" stroke="{NAVY}" stroke-width="{SW}" '
        f'stroke-linecap="round" stroke-linejoin="round">')
TAIL = "</g></svg>"

ICONS = {
    # Cross-world trader: two worlds, and value moving both ways between them.
    "trader": """
      <circle cx="9.5" cy="24" r="6"/>
      <circle cx="38.5" cy="24" r="6"/>
      <path d="M17 18.5 L31 18.5"/>
      <path d="M27.5 15 L31 18.5 L27.5 22"/>
      <path d="M31 29.5 L17 29.5"/>
      <path d="M20.5 26 L17 29.5 L20.5 33"/>
    """,
    # Coin holder: one holding, and a level line that goes nowhere - no directional view.
    "holder": """
      <circle cx="24" cy="17" r="8.5"/>
      <circle cx="24" cy="17" r="3.5"/>
      <path d="M8 35 L40 35"/>
      <path d="M13 39.5 L13 35 M24 39.5 L24 35 M35 39.5 L35 35"/>
    """,
    # Multi-world holder: several holdings tied to one common trend at the centre.
    "multi": """
      <circle cx="24" cy="24" r="5"/>
      <circle cx="24" cy="8" r="3.5"/>
      <circle cx="38" cy="32" r="3.5"/>
      <circle cx="10" cy="32" r="3.5"/>
      <path d="M24 19 L24 11.5"/>
      <path d="M28.4 26.6 L34.6 30.2"/>
      <path d="M19.6 26.6 L13.4 30.2"/>
    """,
    # New-world participant: a price starting low and converging on the established band.
    "newworld": """
      <path d="M8 40 L8 8"/>
      <path d="M8 40 L42 40"/>
      <path d="M12 36 C20 34, 24 22, 40 19"/>
      <path d="M12 19 L40 19" stroke-dasharray="3 3"/>
      <circle cx="40" cy="19" r="2.6" fill="#051C2C"/>
    """,
    # Analyst: a measure taken of the data, not of its appearance.
    "analyst": """
      <path d="M7 39 L7 28 M14 39 L14 21 M21 39 L21 32"/>
      <circle cx="31" cy="20" r="9"/>
      <path d="M37.5 26.5 L42 31"/>
    """,
}

for name, body in ICONS.items():
    (OUT / f"{name}.svg").write_text(HEAD + body.strip() + TAIL)

print(f"{len(ICONS)} icons written to {OUT}")
