#!/usr/bin/env python
"""Generate pyscenedetect.ico from pyscenedetect.svg.

Requires Inkscape (for SVG rasterization) and Pillow (for ICO generation).
"""

import contextlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

# Colors matching the SVG design
BG = (224, 232, 240, 255)  # #e0e8f0
FG = (42, 53, 69, 255)  # #2a3545

RASTER_SIZES = [16, 24, 32, 48, 64, 128, 256]

SHARPEN_AMOUNT = {
    24: 75,
    32: 75,
    48: 75,
    64: 100,
    128: 150,
    256: 150,
}

SHARPEN_RADIUS = 0.5

DIST_DIR = Path(__file__).resolve().parent
LOGO_DIR = DIST_DIR / "logo"
ICO_PATH = DIST_DIR / "pyscenedetect.ico"

SVG_FOR_SIZE: dict[int, Path] = {
    24: LOGO_DIR / "pyscenedetect-24-48.svg",
    32: LOGO_DIR / "pyscenedetect-32.svg",
    48: LOGO_DIR / "pyscenedetect-24-48.svg",
    64: LOGO_DIR / "pyscenedetect-64+.svg",
    128: LOGO_DIR / "pyscenedetect-64+.svg",
    256: LOGO_DIR / "pyscenedetect-64+.svg",
}


def make_icon_16() -> Image.Image:
    """Create a hand-crafted 16x16 clapperboard icon."""
    img = Image.new("RGBA", (16, 16), FG)
    px = img.load()

    # Clear 1px padding on all sides
    for i in range(16):
        px[0, i] = BG
        px[15, i] = BG
        px[i, 0] = BG
        px[i, 15] = BG

    # Arm stripe gaps (rows 2–4): clear pixels not part of a complete stripe.
    # A stripe x+y=s spans all 3 arm rows only when 5 <= s <= 16.
    for y in range(2, 5):
        for x in range(1, 15):
            if y < 4 and x < 3:
                continue
            if y > 2 and x > 12:
                continue
            if not ((x + y) % 4 < 2 and 5 <= (x + y) <= 16):
                px[x, y] = BG

    # Slate interior (rows 8–12, cols 3–12)
    for y in range(8, 13):
        for x in range(3, 13):
            px[x, y] = BG

    return img


def find_inkscape() -> str:
    """Find the Inkscape executable."""
    inkscape = shutil.which("inkscape")
    if inkscape:
        return inkscape
    # Common Windows install path
    candidate = Path(r"C:\Program Files\Inkscape\bin\inkscape.exe")
    if candidate.exists():
        return str(candidate)
    print("Error: Inkscape not found. Please install it or add it to PATH.", file=sys.stderr)
    sys.exit(1)


def render_svg(inkscape: str, svg: Path, output: Path, size: int):
    """Render an SVG to a PNG at the given size using Inkscape."""
    subprocess.run(
        [inkscape, str(svg), "--export-type=png", f"--export-filename={output}", "-w", str(size), "-h", str(size)],
        check=True,
        capture_output=True,
    )


def render_all_sizes(inkscape: str, work_dir: Path) -> list[Image.Image]:
    """Render the SVG at all icon sizes, applying sharpening where configured."""
    images = []
    for size in RASTER_SIZES:
        png_path = work_dir / f"icon_{size}.png"
        if size == 16:
            print(f"  Using hand-crafted {size}x{size} icon...")
            img = make_icon_16()
            img.save(png_path)
        else:
            svg_path = SVG_FOR_SIZE[size]
            print(f"  Rendering {size}x{size} using {svg_path.name}...")
            render_svg(inkscape, svg_path, png_path, size)
            img = Image.open(png_path).copy()
            if size in SHARPEN_AMOUNT:
                img = img.filter(ImageFilter.UnsharpMask(radius=SHARPEN_RADIUS, percent=SHARPEN_AMOUNT[size], threshold=0))
                print(f"    Sharpened {size}x{size} (USM {SHARPEN_AMOUNT[size]}%)")
                img.save(png_path)
        images.append(img)
    return images


def main():
    persist_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if persist_dir:
        persist_dir.mkdir(parents=True, exist_ok=True)
        print(f"Persisting PNGs to: {persist_dir}")

    inkscape = find_inkscape()
    print(f"Using Inkscape: {inkscape}")
    print(f"Logo directory: {LOGO_DIR}")

    ctx = contextlib.nullcontext(str(persist_dir)) if persist_dir else tempfile.TemporaryDirectory()
    with ctx as work:
        images = render_all_sizes(inkscape, Path(work))
        images[-1].save(ICO_PATH, format="ICO", append_images=images[:-1])

    print(f"Output ICO: {ICO_PATH}")


if __name__ == "__main__":
    main()
