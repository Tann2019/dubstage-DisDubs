# -*- coding: utf-8 -*-
"""
make_icons.py - erzeugt die App-Symbole aus dem Logo.
make_icons.py - builds the app icons from the logo.

Die Welle aus docs/logo.png wird weiss auf eine abgerundete Kachel gelegt:
lila fuer DubStage, gruen fuer DubForge. Ergebnis in assets/ als .ico
(alle Groessen, die Windows fuer Explorer, Startmenue und Taskleiste
braucht) und als .png fuer Systeme ohne .ico-Unterstuetzung. Dazu die
Bilder fuer den Setup-Assistenten in installer/.

Nur noetig, wenn sich das Logo aendert:
    python installer/make_icons.py
"""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "docs", "logo.png")
OUT = os.path.join(ROOT, "assets")

BIG = 1024                                   # Arbeitsgroesse / working size
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)

THEMES = {
    "dubstage": ("#7a5cff", "#3a1bd6"),      # Markenlila / brand purple
    "dubforge": ("#4fe0a6", "#138a73"),      # Akzentgruen / accent green
}


def _rgb(hexcode):
    h = hexcode.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wave_mask():
    """Die Welle links im Logo als Graustufen-Maske."""
    im = Image.open(LOGO).convert("RGBA")
    r, g, b, a = im.split()
    # Nur die lila Welle, nicht der schwarze Schriftzug.
    blue = ImageChops.subtract(b, r)
    mask = ImageChops.multiply(a, blue.point(lambda v: 255 if v > 40 else 0))
    box = mask.getbbox()
    return mask.crop(box)


def tile(theme):
    top, bottom = (_rgb(c) for c in THEMES[theme])
    grad = Image.new("RGB", (1, BIG))
    for y in range(BIG):
        f = y / (BIG - 1.0)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * f)
                                    for i in range(3)))
    grad = grad.resize((BIG, BIG))

    shape = Image.new("L", (BIG, BIG), 0)
    m = int(BIG * 0.04)
    ImageDraw.Draw(shape).rounded_rectangle(
        (m, m, BIG - m, BIG - m), radius=int(BIG * 0.22), fill=255)

    out = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    out.paste(grad, (0, 0), shape)
    return out


def place_wave(img, mask, width_frac, thicken=0):
    w = int(BIG * width_frac)
    h = int(mask.height * w / float(mask.width))
    wave = mask.resize((w, h), Image.LANCZOS)
    if thicken:
        wave = wave.filter(ImageFilter.MaxFilter(thicken))
    white = Image.new("RGBA", wave.size, (255, 255, 255, 255))
    img = img.copy()
    img.paste(white, ((BIG - w) // 2, (BIG - h) // 2 + int(BIG * 0.01)), wave)
    return img


def build(theme, mask):
    base = tile(theme)
    normal = place_wave(base, mask, 0.70)
    # Kleine Groessen: Linie kraeftiger, sonst verschwimmt sie.
    bold = place_wave(base, mask, 0.74, thicken=31)
    frames = []
    for s in SIZES:
        src = bold if s <= 32 else normal
        frames.append(src.resize((s, s), Image.LANCZOS))
    ico = os.path.join(OUT, theme + ".ico")
    frames[-1].save(ico, format="ICO", sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    normal.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, theme + ".png"))
    return ico


def wizard_images(mask):
    """Seitenbild und Kopfsymbol fuer Setup.exe (BMP, je Bildschirmskalierung)."""
    here = os.path.dirname(os.path.abspath(__file__))
    top, bottom = (_rgb(c) for c in THEMES["dubstage"])
    for w, h in ((164, 314), (246, 471), (328, 628)):
        img = Image.new("RGB", (w, h))
        for y in range(h):
            f = y / (h - 1.0)
            col = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
            img.paste(col, (0, y, w, y + 1))
        ww = int(w * 0.62)
        wh = int(mask.height * ww / float(mask.width))
        wave = mask.resize((ww, wh), Image.LANCZOS)
        img.paste((255, 255, 255), ((w - ww) // 2, int(h * 0.36) - wh // 2,
                                    (w - ww) // 2 + ww, int(h * 0.36) - wh // 2 + wh),
                  wave)
        path = os.path.join(here, "wizard-large-%d.bmp" % w)
        img.save(path)
        print(path)
    icon = place_wave(tile("dubstage"), mask, 0.70)
    for s in (55, 83, 110):
        img = Image.new("RGB", (s, s), (255, 255, 255))
        small = icon.resize((s, s), Image.LANCZOS)
        img.paste(small, (0, 0), small)
        path = os.path.join(here, "wizard-small-%d.bmp" % s)
        img.save(path)
        print(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    mask = wave_mask()
    for theme in THEMES:
        print(build(theme, mask))
    wizard_images(mask)


if __name__ == "__main__":
    main()
