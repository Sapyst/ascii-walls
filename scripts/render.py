#!/usr/bin/env python3
"""render.py: ASCII art -> wallpaper PNG on pure black (OLED), with each character in its own tone.
  python3 scripts/render.py statue PHOTO OUT.png --box x0,y0,x1,y1 --cols 220 [--tint RRGGBB]
  python3 scripts/render.py text  ART.txt OUT.png                 (plain .txt art, one color)
Also writes the .txt next to it in art/<category>/ when --txt is given."""
import argparse
import math
import os
import sys

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
W, H = 2560, 1440
FONTE = "JetBrains Mono"


def medir(cr, tam):
    lay = PangoCairo.create_layout(cr)
    lay.set_font_description(Pango.FontDescription(f"{FONTE} {tam}px"))
    lay.set_text("M" * 10, -1)
    w, _ = lay.get_pixel_size()
    return lay, w / 10, w / 10 * 2.05          # same cell proportion the converter assumes


def desenhar(linhas, saida, tint=(1.0, 1.0, 0.97), escala=0.86, deslocar=(0.5, 0.5)):
    """linhas: list of lists of (char, gray 0..1)."""
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    cr = cairo.Context(s)
    cr.set_source_rgb(0, 0, 0); cr.paint()
    cols = max(len(l) for l in linhas)
    # font size that fits: width and height
    lay, cw, lh = medir(cr, 100)
    tam = min(W * escala / (cols * cw / 100), H * escala / (len(linhas) * lh / 100))
    lay, cw, lh = medir(cr, tam)
    x0 = (W - cols * cw) * deslocar[0]
    y0 = (H - len(linhas) * lh) * deslocar[1]
    for r, l in enumerate(linhas):
        for c, (ch, g) in enumerate(l):
            if ch == " ":
                continue
            lay.set_text(ch, -1)
            cr.set_source_rgb(tint[0] * g, tint[1] * g, tint[2] * g)
            cr.move_to(x0 + c * cw, y0 + r * lh)
            PangoCairo.show_layout(cr, lay)
    s.write_to_png(saida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["statue", "text"])
    ap.add_argument("fonte")
    ap.add_argument("saida")
    ap.add_argument("--box", default="0,0,1,1")
    ap.add_argument("--cols", type=int, default=200)
    ap.add_argument("--tint", default="fffff7")
    ap.add_argument("--scale", type=float, default=0.86)
    ap.add_argument("--txt")
    a = ap.parse_args()
    tint = tuple(int(a.tint[i:i + 2], 16) / 255 for i in (0, 2, 4))
    if a.modo == "statue":
        from statue import art
        linhas = art(a.fonte, a.cols, tuple(float(v) for v in a.box.split(",")))
    else:
        linhas = [[(ch, 0.92) for ch in l] for l in open(a.fonte).read().rstrip("\n").split("\n")]
    desenhar(linhas, a.saida, tint, a.scale)
    if a.txt:
        os.makedirs(os.path.dirname(a.txt), exist_ok=True)
        with open(a.txt, "w") as f:
            f.write("\n".join("".join(ch for ch, _ in l).rstrip() for l in linhas) + "\n")
    print(a.saida)


if __name__ == "__main__":
    main()
