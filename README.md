<div align="center">

```
   ▄▀█ █▀ █▀▀ █ █   █ █ █ ▄▀█ █   █   █▀
   █▀█ ▄█ █▄▄ █ █   ▀▄▀▄▀ █▀█ █▄▄ █▄▄ ▄█
```

**ASCII & text-mode wallpapers** · made on Arch Aero OS

</div>

## Layout

| Folder | What goes there |
|---|---|
| `walls/<category>/` | Final wallpapers (PNG/JPG, ideally 2560×1440 or larger) |
| `art/<category>/` | The ASCII source of each wallpaper (`.txt`), same name as the image |
| `palettes/` | Color palettes used to render the art |
| `scripts/` | Tools that turn `art/*.txt` into `walls/*.png` |
| `preview/` | Small previews for this README |

Categories: `abstract` · `nature` · `space` · `city` · `characters` · `minimal` · `retro`

## Gallery

| | |
|---|---|
| ![](walls/characters/venus-de-milo-bust.png) | ![](walls/characters/venus-de-milo-figure.png) |
| ![](walls/retro/venus-gold.png) | ![](walls/minimal/know-thyself.png) |

## Make your own

```bash
# a statue photo -> 2560x1440 OLED wallpaper, each character in its own marble tone
python3 scripts/render.py statue photo.jpg walls/characters/name.png --box 0.18,0,0.82,0.5 --cols 210 --txt art/characters/name.txt
# plain text art -> wallpaper
python3 scripts/render.py text art/minimal/name.txt walls/minimal/name.png
```
Needs python-gobject, python-cairo and a mono font (JetBrains Mono).

## Use

Browse it straight from **Settings → Theme → Wallpaper** on Arch Aero OS (add this repository as a collection),
or grab any file from `walls/`.

## Sources

The Venus de Milo pieces are generated from a public-domain photo of the statue in the Louvre
([Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Venus_de_Milo_Louvre_Ma399_n4.jpg)).

## License

Original art in this repository: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
