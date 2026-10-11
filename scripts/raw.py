#!/usr/bin/env python3
"""raw.py: a photo -> raw, ultra-detailed ASCII wallpapers in 4K, on pure black (OLED).
The whole photo becomes text (no cut-out): every cell gets a character from a 70-step ramp
and its own gray level, after an adaptive local contrast pass, so the marble keeps its relief.

  python3 scripts/raw.py PHOTO NAME --dir walls/mythology/athena [--txt-dir art/mythology/athena]
          [--box x0,y0,x1,y1] [--tint fff6e8] [--cell 4.5]

Writes NAME-desktop.png (3840x2160) and NAME-mobile.png (2160x3840), plus the two .txt sources.
The photo is fitted inside the frame (nothing is cropped) and centered.
Needs python-gobject (GdkPixbuf, Pango), python-cairo, JetBrains Mono, and vips for the final
palette PNG (optional: without vips the PNG is kept as full RGB)."""
import argparse
import math
import os
import shutil
import subprocess

import cairo
import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GdkPixbuf, Pango, PangoCairo  # noqa: E402

FONTE = "JetBrains Mono Bold"
# Paul Bourke's 70-level ramp, light to dense
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
FORMATOS = {"desktop": (3840, 2160), "mobile": (2160, 3840)}
TONS = 48                                   # gray levels actually drawn (keeps the PNG small)
MARGEM = 0.04                               # black border around the art, as a fraction of the frame


def celula(tam):
    """pixel width and line height of one monospace cell at font size tam"""
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
    lay = PangoCairo.create_layout(cairo.Context(s))
    lay.set_font_description(Pango.FontDescription(f"{FONTE} {tam}px"))
    lay.set_text("M" * 20, -1)
    w, _ = lay.get_pixel_size()
    return w / 20, w / 20 * 2.0


def abrir(foto, box=(0, 0, 1, 1)):
    """photo, cropped to box (fractions x0,y0,x1,y1)"""
    p = GdkPixbuf.Pixbuf.new_from_file(foto).apply_embedded_orientation()
    if tuple(box) != (0, 0, 1, 1):
        w, h = p.get_width(), p.get_height()
        x0, y0 = int(box[0] * w), int(box[1] * h)
        p = p.new_subpixbuf(x0, y0, int(box[2] * w) - x0, int(box[3] * h) - y0)
    return p


def grade(p, cols, rows):
    """photo scaled to the character grid -> (luminance list, rgb list), row major"""
    p = p.scale_simple(cols, rows, GdkPixbuf.InterpType.HYPER)
    n, st, d = p.get_n_channels(), p.get_rowstride(), p.get_pixels()
    rgb = [(d[y * st + x * n] / 255, d[y * st + x * n + 1] / 255, d[y * st + x * n + 2] / 255)
           for y in range(rows) for x in range(cols)]
    return [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in rgb], rgb


def fundo(rgb, w, h, tol=0.11):
    """plain backdrop (studio wall, sky, museum gradient): cells connected to the border whose color
    stays close to their neighbours' and to the border's typical color -> True. Busy backgrounds
    (gardens, streets) do not pass the test and stay in the picture, raw."""
    borda = [rgb[i] for i in list(range(w)) + list(range((h - 1) * w, h * w)) +
             [y * w for y in range(h)] + [y * w + w - 1 for y in range(h)]]
    ref = [sorted(c[k] for c in borda)[len(borda) // 2] for k in range(3)]
    perto = lambda c, o, t: abs(c[0] - o[0]) + abs(c[1] - o[1]) + abs(c[2] - o[2]) < t
    vis = bytearray(w * h)
    pilha = [i for i in range(w * h) if (i < w or i >= (h - 1) * w or i % w in (0, w - 1)) and perto(rgb[i], ref, 3 * tol)]
    for i in pilha:
        vis[i] = 1
    while pilha:
        i = pilha.pop()
        x, y = i % w, i // w
        for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
            if ok and not vis[j] and perto(rgb[j], rgb[i], tol) and perto(rgb[j], ref, 5 * tol):
                vis[j] = 1; pilha.append(j)
    # only trust it when it really is a backdrop (a busy photo floods almost nothing)
    return vis if sum(vis) > 0.08 * w * h else bytearray(w * h)


def borrar(a, w, h, r):
    """box blur, two passes"""
    t = [0.0] * (w * h)
    for y in range(h):
        acc = 0.0; row = y * w
        for x in range(-r, w):
            if x + r < w: acc += a[row + x + r]
            if x - r - 1 >= 0: acc -= a[row + x - r - 1]
            if x >= 0: t[row + x] = acc / (2 * r + 1)
    o = [0.0] * (w * h)
    for x in range(w):
        acc = 0.0
        for y in range(-r, h):
            if y + r < h: acc += t[(y + r) * w + x]
            if y - r - 1 >= 0: acc -= t[(y - r - 1) * w + x]
            if y >= 0: o[y * w + x] = acc / (2 * r + 1)
    return o


def tons(lum, w, h):
    """global stretch + adaptive local contrast (CLAHE-like) + a little sharpening"""
    ordem = sorted(lum[::7])
    lo, hi = ordem[int(len(ordem) * 0.01)], ordem[int(len(ordem) * 0.995)]
    lum = [min(1.0, max(0.0, (v - lo) / max(1e-3, hi - lo))) for v in lum]
    r = max(3, min(w, h) // 10)
    media = borrar(lum, w, h, r)
    quad = borrar([v * v for v in lum], w, h, r)
    fino = borrar(lum, w, h, 1)
    out = []
    for i, v in enumerate(lum):
        dp = math.sqrt(max(1e-5, quad[i] - media[i] * media[i]))
        local = 0.5 + 0.5 * math.tanh(1.2 * (v - media[i]) / (dp + 0.07))
        out.append(min(1.0, max(0.0, 0.6 * v + 0.4 * local + 0.7 * (v - fino[i]))))
    return out


def ascii_de(foto, formato, cell, box=(0, 0, 1, 1)):
    W, H = FORMATOS[formato]
    cw, lh = celula(cell / 0.6)              # JetBrains Mono advance is 0.6 em
    img = abrir(foto, box)
    pw, ph = img.get_width(), img.get_height()
    # fit the photo inside the frame, in cell units (cells are lh/cw times taller than wide)
    max_c, max_r = int(W * (1 - 2 * MARGEM) / cw), int(H * (1 - 2 * MARGEM) / lh)
    cols = max_c
    rows = round(cols * (ph / pw) * (cw / lh))
    if rows > max_r:
        rows = max_r
        cols = round(rows * (pw / ph) * (lh / cw))
    lum, rgb = grade(img, cols, rows)
    bg = fundo(rgb, cols, rows)
    v = tons(lum, cols, rows)
    # backdrop -> blank, with a soft one-cell fade so the outline is not cut with scissors
    perto_bg = borrar([float(b) for b in bg], cols, rows, 1)
    v = [0.0 if bg[i] else v[i] * (1 - 0.6 * perto_bg[i]) for i in range(len(v))]
    # stray specks: a faint cell with almost nothing around it is noise, not detail
    viz = borrar(v, cols, rows, 2)
    v = [0.0 if x < 0.16 and viz[i] < 0.12 else x for i, x in enumerate(v)]
    linhas = [[v[r * cols + c] for c in range(cols)] for r in range(rows)]
    return linhas, (W, H, cw, lh, cell / 0.6)


def caractere(v):
    return RAMP[min(len(RAMP) - 1, int(v * (len(RAMP) - 1) + 0.5))]


def desenhar(linhas, medidas, saida, tint):
    W, H, cw, lh, tam = medidas
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    cr = cairo.Context(s)
    cr.set_source_rgb(0, 0, 0); cr.paint()
    fo = cairo.FontOptions(); fo.set_antialias(cairo.ANTIALIAS_GRAY); fo.set_hint_style(cairo.HINT_STYLE_NONE)
    lay = PangoCairo.create_layout(cr)
    PangoCairo.context_set_font_options(lay.get_context(), fo)
    lay.set_font_description(Pango.FontDescription(f"{FONTE} {tam}px"))
    rows, cols = len(linhas), len(linhas[0])
    x0, y0 = (W - cols * cw) / 2, (H - rows * lh) / 2
    for r, l in enumerate(linhas):
        c = 0
        while c < cols:            # runs of cells with the same tone are drawn in one go
            t = round(l[c] * (TONS - 1))
            fim = c
            while fim + 1 < cols and round(l[fim + 1] * (TONS - 1)) == t:
                fim += 1
            texto = "".join(caractere(x) for x in l[c:fim + 1])
            if texto.strip():
                g = 0.10 + 0.90 * (t / (TONS - 1)) ** 0.85
                cr.set_source_rgb(tint[0] * g, tint[1] * g, tint[2] * g)
                lay.set_text(texto, -1)
                cr.move_to(x0 + c * cw, y0 + r * lh)
                PangoCairo.show_layout(cr, lay)
            c = fim + 1
    tmp = saida + ".rgb.png"
    s.write_to_png(tmp)
    if shutil.which("vips"):       # same picture, 8-bit palette: a fraction of the size
        subprocess.run(["vips", "pngsave", tmp, saida, "--palette", "--bitdepth", "8", "--Q", "100",
                        "--effort", "10", "--compression", "9"], check=True, stderr=subprocess.DEVNULL)
        os.remove(tmp)
    else:
        os.replace(tmp, saida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("foto")
    ap.add_argument("nome")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--txt-dir")
    ap.add_argument("--tint", default="fff6e8")
    ap.add_argument("--box", default="0,0,1,1", help="crop x0,y0,x1,y1 (fractions of the photo)")
    ap.add_argument("--cell", type=float, default=4.5, help="cell width in px at 4K (smaller = more detail)")
    a = ap.parse_args()
    tint = tuple(int(a.tint[i:i + 2], 16) / 255 for i in (0, 2, 4))
    os.makedirs(a.dir, exist_ok=True)
    for formato in FORMATOS:
        linhas, medidas = ascii_de(a.foto, formato, a.cell, tuple(float(x) for x in a.box.split(",")))
        png = os.path.join(a.dir, f"{a.nome}-{formato}.png")
        desenhar(linhas, medidas, png, tint)
        if a.txt_dir:
            os.makedirs(a.txt_dir, exist_ok=True)
            with open(os.path.join(a.txt_dir, f"{a.nome}-{formato}.txt"), "w") as f:
                f.write("\n".join("".join(caractere(v) for v in l).rstrip() for l in linhas) + "\n")
        print(png, f"{len(linhas[0])}x{len(linhas)} chars")


if __name__ == "__main__":
    main()
