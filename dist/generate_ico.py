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

# Different raster sizes to include in the ICO file.
SIZES = [16, 24, 32, 48, 64, 128, 256]

# Sharpen smaller sizes to improve ledgibility.
SHARPEN_AMOUNT = {
    16: 200,
    24: 200,
    32: 100,
    48: 50,
    64: 50,
}

DIST_DIR = Path(__file__).resolve().parent
SVG_PATH = DIST_DIR / "pyscenedetect.svg"
ICO_PATH = DIST_DIR / "pyscenedetect.ico"


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
    for size in SIZES:
        png_path = work_dir / f"icon_{size}.png"
        print(f"  Rendering {size}x{size}...")
        render_svg(inkscape, SVG_PATH, png_path, size)
        img = Image.open(png_path).copy()
        if size in SHARPEN_AMOUNT:
            img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=SHARPEN_AMOUNT[size], threshold=0))
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
    print(f"Input SVG: {SVG_PATH}")

    ctx = contextlib.nullcontext(str(persist_dir)) if persist_dir else tempfile.TemporaryDirectory()
    with ctx as work:
        images = render_all_sizes(inkscape, Path(work))
        images[-1].save(ICO_PATH, format="ICO", append_images=images[:-1])

    print(f"Output ICO: {ICO_PATH}")


if __name__ == "__main__":
    main()
