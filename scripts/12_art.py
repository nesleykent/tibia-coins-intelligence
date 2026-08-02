"""Prepare Tibia artwork for editorial use.

The source art is highly saturated game illustration. Dropping it into the report as-is would
break the restrained palette, so each image is converted to a duotone that maps luminance onto
the report's own navy-to-pale-blue ramp. The result reads as texture and atmosphere while
staying inside the colour system.

Assets are CipSoft's, used here under the terms distributed with the official fankit: this
report is about the game, is not sold or licensed, and the marks appear only to indicate
origin. Attribution is printed in the report's credits.
"""
import pathlib
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "assets"
OUT = ROOT / "figures" / "art"
OUT.mkdir(parents=True, exist_ok=True)

DARK = (5, 28, 44)        # #051C2C, the cover navy
LIGHT = (173, 205, 230)   # pale blue highlight


def duotone(src, dest, w=1800, dark=DARK, light=LIGHT, gamma=1.0, vignette=False):
    im = Image.open(src).convert("RGB")
    im = im.resize((w, round(w * im.height / im.width)), Image.LANCZOS)
    lum = np.asarray(ImageEnhance.Contrast(im.convert("L")).enhance(1.15), float) / 255.0
    lum = np.clip(lum, 0, 1) ** gamma
    ramp = (np.array(dark)[None, None, :] * (1 - lum[..., None])
            + np.array(light)[None, None, :] * lum[..., None])
    out = Image.fromarray(ramp.astype("uint8"))
    if vignette:
        h, wd = out.height, out.width
        yy, xx = np.mgrid[0:h, 0:wd]
        d = np.sqrt(((xx - wd / 2) / (wd / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        mask = np.clip(1.15 - 0.55 * d, 0, 1)[..., None]
        base = np.asarray(out, float) * mask + np.array(dark)[None, None, :] * (1 - mask)
        out = Image.fromarray(base.astype("uint8"))
    out.save(dest, quality=92)
    return dest


# Cover: a full-page navy field with the artwork set into the upper two-thirds and faded to
# navy at both edges. The fade is composited into the pixels here rather than drawn as an
# overlay at render time - PDF fill alpha does not apply to placed images, so a scrim drawn
# on top would simply hide the picture.
def cover_plate(src, dest, pw=1654, ph=2339):
    art = Image.open(src).convert("RGB")
    lum = np.asarray(ImageEnhance.Contrast(art.convert("L")).enhance(1.10), float) / 255.0
    lum = np.clip(lum * 1.22, 0, 1) ** 1.05
    ramp = (np.array(DARK)[None, None, :] * (1 - lum[..., None])
            + np.array(LIGHT)[None, None, :] * lum[..., None])
    art = Image.fromarray(ramp.astype("uint8"))

    band_h = int(ph * 0.60)
    scale = max(pw / art.width, band_h / art.height)
    art = art.resize((int(art.width * scale), int(art.height * scale)), Image.LANCZOS)
    left = (art.width - pw) // 2
    art = art.crop((left, 0, left + pw, band_h))

    a = np.asarray(art, float)
    yy = np.linspace(0, 1, band_h)[:, None, None]
    # opaque through the middle, falling away to navy at the top (behind the title) and at the
    # bottom (where the data ribbon takes over)
    fade = np.clip(np.minimum(yy / 0.58, (1 - yy) / 0.28), 0, 1) ** 1.35 * 0.58
    a = a * fade + np.array(DARK)[None, None, :] * (1 - fade)

    plate = Image.new("RGB", (pw, ph), DARK)
    plate.paste(Image.fromarray(a.astype("uint8")), (0, 0))
    plate.save(dest, quality=93)


cover_plate(ART / "Tibia/Artworks/Tibia_KeyArtwork_EGS.jpg", OUT / "cover_bg.jpg")

# Chapter openers: one band each, chosen to suit the chapter's subject.
CH = {
    2: "TibiaFankit/Illustrations/Artworks/LandingPage1.jpg",
    3: "TibiaFankit/Illustrations/Artworks/01_TrailerArtwork.jpg",
    4: "TibiaFankit/Illustrations/Artworks/ClientArtworkSummer2023.jpg",
    5: "TibiaFankit/Illustrations/Artworks/WebsiteArtworkSummer2024.jpg",
    6: "TibiaFankit/Illustrations/Artworks/ClientArtworkWinter2023.jpg",
    7: "TibiaFankit/Illustrations/Artworks/WebsiteArtworkWinter2024.jpg",
    8: "TibiaFankit/Illustrations/Artworks/WebsiteArtworkSummer2019.jpg",
}
made = []
for ch, rel in CH.items():
    src = ART / rel
    if not src.exists():
        print("missing:", rel)
        continue
    im = Image.open(src)
    # Crop a wide editorial band from the middle of the image before toning.
    band_h = int(im.height * 0.46)
    top = int(im.height * 0.30)
    im.crop((0, top, im.width, top + band_h)).save(OUT / f"_tmp{ch}.jpg", quality=95)
    duotone(OUT / f"_tmp{ch}.jpg", OUT / f"ch{ch}.jpg", w=1500, gamma=1.30)
    (OUT / f"_tmp{ch}.jpg").unlink()
    made.append(ch)

# Marks for the key-statistic pages. A hero page is one number on an empty field, which reads as
# austere rather than considered; a small figure in the lower corner gives the page a subject
# without competing with the number. Silhouette matters more than subject at this size, so each
# is knocked back to a pale tint of the report's blue and cropped to its own content.
MARKS = {
    "index": "GoldSphinx.png",          # the market's own appreciation
    "cost": "Jousters.png",             # two sides, and what passing between them costs
    "variance": "CrystalWolf.png",      # worlds travelling separately
    "cointegration": "ForestMother.png",  # many parts, one trend
    "band": "Scorpion.png",             # the friction that keeps the band open
}
ISO = ART / "TibiaFankit/Illustrations/Isolated"
made_marks = []
for key, fn in MARKS.items():
    src = ISO / fn
    if not src.exists():
        print("missing mark:", fn)
        continue
    im = Image.open(src).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())          # trim the transparent margin
    im.thumbnail((900, 900), Image.LANCZOS)
    a = np.asarray(im, float)
    lum = np.asarray(im.convert("L"), float) / 255.0
    # A single pale tint, darkest where the illustration is darkest, so the mark reads as one
    # shape rather than as a picture. Alpha is scaled down so it sits under the type.
    tint = np.dstack([
        np.full(lum.shape, 0x9F + 0x30 * lum),
        np.full(lum.shape, 0xB6 + 0x28 * lum),
        np.full(lum.shape, 0xCC + 0x20 * lum),
        a[..., 3] * 0.42])
    Image.fromarray(np.clip(tint, 0, 255).astype("uint8"), "RGBA").save(OUT / f"mark_{key}.png")
    made_marks.append(key)

# Logo, used only to indicate origin, on a light ground.
logo = ART / "Tibia/Logos/Tibia_Logo.png"
if logo.exists():
    lg = Image.open(logo).convert("RGBA")
    lg.thumbnail((640, 640), Image.LANCZOS)
    a = np.asarray(lg, float)
    # Recolour the mark to the pale blue of the palette, keeping its alpha, so it reads on the
    # navy field without importing the logo's own colours into the report.
    keep = a[..., 3:4] / 255.0
    tint = np.dstack([np.full(a.shape[:2], LIGHT[0], float),
                      np.full(a.shape[:2], LIGHT[1], float),
                      np.full(a.shape[:2], LIGHT[2], float),
                      keep[..., 0] * 255.0])
    Image.fromarray(tint.astype("uint8"), "RGBA").save(OUT / "tibia_logo_navy.png")

print(f"cover background + {len(made)} chapter bands + {len(made_marks)} hero marks + logo written to {OUT}")
