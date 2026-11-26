"""Buyer-facing measurement card picture for a listing.

Uses the drawing from the item's photo card, with the measured numbers filled
in, in the Nelsons Nostalgia navy and teal frame.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ART = Path(__file__).with_name("card_art")
NAVY = (19, 38, 58)
TEAL = (43, 181, 176)
SIZE = 1600

_FONTS = ["/usr/share/fonts/opentype/inter/Inter-{w}.otf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans{d}.ttf"]


def _font(px: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for pat in _FONTS:
        path = pat.format(w="Bold" if bold else "Regular", d="-Bold" if bold else "")
        if Path(path).exists():
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def make(card: dict, values: dict[str, str], out: Path) -> Path:
    rows = [(k, card["measurements"][k], v) for k, v in sorted(values.items())
            if v and k in card["measurements"]]
    im = Image.new("RGB", (SIZE, SIZE), "white")
    d = ImageDraw.Draw(im)
    # frame: navy border, thin teal inner line (brand)
    d.rectangle([20, 20, SIZE - 21, SIZE - 21], outline=NAVY, width=16)
    d.rectangle([52, 52, SIZE - 53, SIZE - 53], outline=TEAL, width=4)

    logo = Image.open(ART / "_logo.png").convert("RGBA")
    logo.thumbnail((260, 260))
    im.paste(logo, (90, 90), logo)
    d.text((380, 120), "Measurements", font=_font(84, True), fill=NAVY)
    d.text((384, 225), card["name"], font=_font(44), fill=TEAL)

    # drawing
    top, bottom_rows = 380, 140 + 95 * len(rows)
    box_w, box_h = SIZE - 240, SIZE - top - bottom_rows - 60
    art = Image.open(ART / f"{card['id']}.png").convert("RGB")
    scale = min(box_w / art.width, box_h / art.height)
    art = art.resize((int(art.width * scale), int(art.height * scale)), Image.LANCZOS)
    im.paste(art, ((SIZE - art.width) // 2, top + (box_h - art.height) // 2))

    # filled-in legend
    y = SIZE - bottom_rows
    for letter, label, value in rows:
        d.ellipse([140, y, 210, y + 70], fill=NAVY)
        d.text((175, y + 35), letter, font=_font(44, True), fill="white", anchor="mm")
        d.text((240, y + 35), label, font=_font(46), fill=NAVY, anchor="lm")
        d.text((SIZE - 140, y + 35), value, font=_font(56, True), fill=TEAL, anchor="rm")
        y += 95
    d.text((SIZE // 2, SIZE - 105), "Approximate, measured by hand.", font=_font(36),
           fill=NAVY, anchor="mm")
    im.save(out, quality=92)
    return out
