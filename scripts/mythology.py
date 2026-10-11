#!/usr/bin/env python3
"""mythology.py: the goddess photo collection -> walls/mythology/<goddess>/ + art/mythology/ + catalog.

Reads the list of works (deusas-baixar's obras.tsv: goddess, name, artist, date, material, place,
city, country, Commons file, Wikidata id) and the downloaded photos (~/Pictures/Deusas), renders every
photo that is already there with raw.py (4K desktop + 4K mobile) and rewrites art/mythology/README.md.
Works whose photo is missing are skipped, so it can be run again as the collection grows.

  python3 scripts/mythology.py [--list ~/.local/share/deusas/obras.tsv] [--photos ~/Pictures/Deusas] [--force]
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raw  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# list key -> (folder in this repo, folder of the photo collection, title, what she is)
DEUSAS = {
    "Eris": ("eris", "Éris", "Eris", "discord (Discordia)"),
    "Atena": ("athena", "Atena", "Athena", "wisdom and war (Minerva)"),
    "Afrodite": ("aphrodite", "Afrodite", "Aphrodite", "love and beauty (Venus)"),
    "Artemis": ("artemis", "Ártemis", "Artemis", "the hunt and the moon (Diana)"),
    "Hera": ("hera", "Hera", "Hera", "queen of the gods (Juno)"),
    "Demeter": ("demeter", "Deméter", "Demeter", "the harvest (Ceres)"),
    "Hestia": ("hestia", "Héstia", "Hestia", "hearth and home (Vesta)"),
    "Persefone": ("persephone", "Perséfone", "Persephone", "queen of the underworld (Proserpina)"),
    "Nike": ("nike", "Nike", "Nike", "victory (Victoria)"),
    "Tique": ("tyche", "Tique", "Tyche", "fortune (Fortuna)"),
    "Higeia": ("hygieia", "Higeia", "Hygieia", "health (Salus)"),
    "Temis": ("themis", "Têmis", "Themis", "divine law and justice (Justitia)"),
    "Eos": ("eos", "Eos", "Eos", "the dawn (Aurora)"),
    "Hebe": ("hebe", "Hebe", "Hebe", "youth (Juventas)"),
    "Selene": ("selene", "Selene", "Selene", "the moon (Luna)"),
    "Hecate": ("hecate", "Hécate", "Hecate", "magic and crossroads (Trivia)"),
    "Nemesis": ("nemesis", "Nêmesis", "Nemesis", "retribution"),
}
# photos where the statue is small inside a busy scene: crop to it (fractions x0,y0,x1,y1 of the photo)
RECORTES = {
    "Discórdia (Discordia Longe)": (0.33, 0.28, 0.75, 0.93),
    "Fortuna do Palácio de Charlottenburg": (0.36, 0.22, 0.66, 0.56),
    "Diana": (0.25, 0.05, 0.75, 0.95),
    "Aurora de Rendsburg": (0.28, 0.26, 0.72, 1.0),
    "Estatueta de Hécate em madeira": (0.28, 0.04, 0.72, 0.98),
    "Fortuna ou Tutela (MAM 2735)": (0.22, 0.04, 0.78, 0.97),
    "Luna (MF 1317)": (0.28, 0.04, 0.72, 0.98),
}
UA = {"User-Agent": "ascii-walls/1.0 (https://github.com/Sapyst/ascii-walls)"}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def foto_de(pasta_fotos, deusa_pasta, n, o):
    """same file name deusas-baixar gives the photo"""
    rotulo = f"{n:02d} - {o['nome']}" + (f" ({o['cidade']})" if o["cidade"] else "")
    rotulo = re.sub(r'[\\/:*?"<>|]', "", rotulo).strip()[:150]
    return os.path.join(pasta_fotos, deusa_pasta, rotulo + ".jpg")


def creditos(arquivos):
    """photographer + license of each Commons file"""
    out = {}
    for i in range(0, len(arquivos), 50):
        q = dict(action="query", format="json", prop="imageinfo", iiprop="extmetadata|url",
                 iiextmetadatafilter="LicenseShortName|Artist", titles="|".join("File:" + a for a in arquivos[i:i + 50]))
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q), headers=UA), timeout=60).read())
        volta = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        for p in r["query"]["pages"].values():
            if "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
            limpo = lambda k: re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", m.get(k, {}).get("value", "")))).strip()
            out[volta.get(p["title"], p["title"])[5:]] = dict(licenca=limpo("LicenseShortName"),
                                                             fotografo=limpo("Artist")[:90], pagina=ii["descriptionurl"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=os.path.expanduser("~/.local/share/deusas/obras.tsv"))
    ap.add_argument("--photos", default=os.path.expanduser("~/Pictures/Deusas"))
    ap.add_argument("--force", action="store_true", help="render again even if the wall exists")
    a = ap.parse_args()
    with open(a.list, encoding="utf-8") as f:
        obras = list(csv.DictReader(f, delimiter="\t"))
    contagem, feitas, usados = {}, [], set()
    for o in obras:
        pasta, pasta_foto, titulo, _ = DEUSAS[o["deusa"]]
        contagem[o["deusa"]] = contagem.get(o["deusa"], 0) + 1
        foto = foto_de(a.photos, pasta_foto, contagem[o["deusa"]], o)
        if not os.path.exists(foto):
            continue
        nome = slug(o["nome"])
        if (o["deusa"], nome) in usados:          # same title twice (three "Hebe"): add the artist
            autor = o["autor"].split("(")[0].split(",")[0].strip()
            nome = slug(o["nome"] + " " + (autor.split()[-1] if autor and autor != "desconhecido" else o["cidade"]))
        usados.add((o["deusa"], nome))
        walls = os.path.join(RAIZ, "walls", "mythology", pasta)
        arte = os.path.join(RAIZ, "art", "mythology", pasta)
        if a.force or not os.path.exists(os.path.join(walls, f"{nome}-mobile.png")):
            os.makedirs(walls, exist_ok=True); os.makedirs(arte, exist_ok=True)
            for formato in raw.FORMATOS:
                linhas, medidas = raw.ascii_de(foto, formato, 4.5, RECORTES.get(o["nome"], (0, 0, 1, 1)))
                raw.desenhar(linhas, medidas, os.path.join(walls, f"{nome}-{formato}.png"), (1.0, 0.965, 0.91))
                with open(os.path.join(arte, f"{nome}-{formato}.txt"), "w") as f:
                    f.write("\n".join("".join(raw.caractere(v) for v in l).rstrip() for l in linhas) + "\n")
            print(f"  {pasta}/{nome}")
        feitas.append(dict(o, pasta=pasta, titulo=titulo, slug=nome))
    catalogo(feitas)
    print(f"{len(feitas)} works in walls/mythology")


def catalogo(feitas):
    cred = creditos(list(dict.fromkeys(o["arquivo"] for o in feitas)))
    e = lambda s: s.replace("|", "\\|")
    out = ["# Mythology: Greek goddesses in real statues", "",
           "Raw, ultra-detailed ASCII of real statues, reliefs and figurines of the Greek goddesses (and their",
           "Roman counterparts), each one in two 4K versions: **desktop** 3840×2160 and **mobile** 2160×3840,",
           "on pure black. The text of every wall is in `art/mythology/<goddess>/`.", "",
           "Made with `scripts/raw.py` (one photo) and `scripts/mythology.py` (the whole collection).", "",
           "**License:** each wall is a derivative of the photo listed next to it and keeps that photo's license",
           "(CC BY-SA photos give CC BY-SA walls); credit the photographer as shown when you share one.", ""]
    for chave, (pasta, _, titulo, oque) in DEUSAS.items():
        dela = [o for o in feitas if o["pasta"] == pasta]
        if not dela:
            continue
        out += [f"## {titulo}", "", f"*Goddess of {oque}.*", "",
                "| Wall | Work | Where | Photo |", "|---|---|---|---|"]
        for o in dela:
            c = cred.get(o["arquivo"], {})
            obra = f"**{e(o['nome'])}**<br>" + " · ".join(e(x) for x in (o["autor"], o["data"], o["material"]) if x)
            onde = ", ".join(e(x) for x in (o["local"], o["cidade"], o["pais"]) if x)
            if o["wikidata"]:
                onde += f"<br>[Wikidata](https://www.wikidata.org/wiki/{o['wikidata']})"
            img = f"../../walls/mythology/{pasta}/{o['slug']}"
            parede = (f"[<img src=\"{img}-mobile.png\" width=\"120\">]({img}-mobile.png)<br>"
                      f"[desktop]({img}-desktop.png) · [mobile]({img}-mobile.png)")
            foto = f"{e(c.get('fotografo', ''))}<br>{e(c.get('licenca', ''))} · [Commons]({c.get('pagina', '')})"
            out.append(f"| {parede} | {obra} | {onde} | {foto} |")
        out.append("")
    with open(os.path.join(RAIZ, "art", "mythology", "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    main()
