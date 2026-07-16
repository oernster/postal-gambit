"""Generate the full icon set for Postal Gambit from the master PNG.

Reads the repo-root master (postal-gambit.png, square RGBA) and emits every
platform asset into assets/: loose PNGs for each size, the canonical badge
PNG, a multi-frame Windows .ico and a macOS .icns.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
MASTER_PNG = PROJECT_ROOT / "postal-gambit.png"
ASSETS_DIR = PROJECT_ROOT / "assets"

PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANONICAL_PNG_SIZE = 256
ICNS_SOURCE_SIZE = 1024

PNG_NAME_TEMPLATE = "postal-gambit_icon_{size}.png"
CANONICAL_PNG_NAME = "postal-gambit_icon.png"
ICO_NAME = "postal-gambit.ico"
ICNS_NAME = "postal-gambit.icns"

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


if __name__ == "__main__":
    main()
