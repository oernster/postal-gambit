"""Generate the full icon set for Postal Gambit from the master PNGs.

Reads the repo-root icon master (postal-gambit.png, square RGBA) and emits
every platform asset into assets/: loose PNGs for each size, the canonical
badge PNG, a multi-frame Windows .ico and a macOS .icns.

It also derives the donation mark from its own master (donate.png). That mark
is not an icon: it is a wide picture drawn at a button's height, so it does
not go through the squaring path above, which would spend half its canvas on
nothing. It is cropped to the tight box of its non-transparent pixels then
scaled by height alone. The same render is written to every destination in one
loop, so the copy the application draws and the copy the site serves cannot
drift apart.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
MASTER_PNG = PROJECT_ROOT / "postal-gambit.png"
DONATE_MASTER_PNG = PROJECT_ROOT / "donate.png"
ASSETS_DIR = PROJECT_ROOT / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"

PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANONICAL_PNG_SIZE = 256
ICNS_SOURCE_SIZE = 1024

PNG_NAME_TEMPLATE = "postal-gambit_icon_{size}.png"
CANONICAL_PNG_NAME = "postal-gambit_icon.png"
ICO_NAME = "postal-gambit.ico"
ICNS_NAME = "postal-gambit.icns"
DONATE_NAME = "donate.png"

# The mark is drawn at the height of one of the application's own pill
# buttons, measured at 29px. Rendering at four times that keeps it crisp
# under display scaling without carrying the 1.7MB master into the build.
DONATE_DRAWN_HEIGHT = 29
DONATE_SCALE_FACTOR = 4
DONATE_RENDER_HEIGHT = DONATE_DRAWN_HEIGHT * DONATE_SCALE_FACTOR

# Every destination the same render is written to: the copy the application
# bundles and the copy the site serves.
DONATE_OUTPUTS = (ASSETS_DIR / DONATE_NAME, DOCS_DIR / DONATE_NAME)

RESAMPLE = Image.Resampling.LANCZOS


def _load_master() -> Image.Image:
    master = Image.open(MASTER_PNG).convert("RGBA")
    width, height = master.size
    if width != height:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        master = master.crop((left, top, left + side, top + side))
    return master


def _donate_mark() -> Image.Image:
    """The donation mark, cropped to its artwork and scaled by height.

    Scaling by height alone keeps the aspect ratio, so a wide picture stays
    wide instead of being squared into a box it does not fill.
    """
    master = Image.open(DONATE_MASTER_PNG).convert("RGBA")
    box = master.getbbox()
    if box is not None:
        master = master.crop(box)
    width, height = master.size
    scaled_width = max(1, round(width * DONATE_RENDER_HEIGHT / height))
    return master.resize((scaled_width, DONATE_RENDER_HEIGHT), RESAMPLE)


def _write_donate_mark() -> None:
    mark = _donate_mark()
    for out in DONATE_OUTPUTS:
        out.parent.mkdir(exist_ok=True)
        mark.save(out)
        print(f"wrote {out.parent.name}/{out.name} ({mark.width}x{mark.height})")


def main() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    master = _load_master()

    for size in PNG_SIZES:
        out = ASSETS_DIR / PNG_NAME_TEMPLATE.format(size=size)
        master.resize((size, size), RESAMPLE).save(out)
        print(f"wrote {out.name}")

    canonical = ASSETS_DIR / CANONICAL_PNG_NAME
    master.resize((CANONICAL_PNG_SIZE, CANONICAL_PNG_SIZE), RESAMPLE).save(canonical)
    print(f"wrote {canonical.name}")

    ico_path = ASSETS_DIR / ICO_NAME
    largest_ico = max(ICO_SIZES)
    master.resize((largest_ico, largest_ico), RESAMPLE).save(
        ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES]
    )
    print(f"wrote {ico_path.name} ({len(ICO_SIZES)} frames)")

    icns_path = ASSETS_DIR / ICNS_NAME
    master.resize((ICNS_SOURCE_SIZE, ICNS_SOURCE_SIZE), RESAMPLE).save(
        icns_path, format="ICNS"
    )
    print(f"wrote {icns_path.name}")

    _write_donate_mark()


if __name__ == "__main__":
    main()
