#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Generate pyscenedetect.ico, logo PNGs, and Windows installer branding from SVG sources.

Outputs:
  - icons: packaging/windows/pyscenedetect.ico, docs/_static/favicon.ico,
    website/pages/img/favicon.ico
  - logos:  docs/_static/, website/pages/img/
  - installer: psd_square_small.ico, installer_banner.{svg,png}, installer_logo.{svg,png} and
    scale variants for .msi creation

Usage:
  python scripts/generate_assets.py

Requires Inkscape and Pillow.
"""

import argparse
import contextlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFilter


class LogoOutput(NamedTuple):
    path: Path
    width: int
    height: int
    source: Path


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

REPO_DIR = Path(__file__).resolve().parent.parent
PACKAGING_DIR = REPO_DIR / "packaging"
LOGO_DIR = PACKAGING_DIR / "logo"
ICO_PATH = PACKAGING_DIR / "windows" / "pyscenedetect.ico"

LOGO_SVG = LOGO_DIR / "pyscenedetect-logo.svg"
LOGO_BG_SVG = LOGO_DIR / "pyscenedetect-logo-bg.svg"
SLATE_SVG = LOGO_DIR / "pyscenedetect.svg"  # slate-only icon (256x256)

INSTALLER_DIR = PACKAGING_DIR / "windows" / "installer"
GENERATED_IMAGES_DIR = INSTALLER_DIR / "Generated Images"
ARP_ICO_PATH = INSTALLER_DIR / "psd_square_small.ico"

# Classic AdvancedInstaller theme: brand mark on a colored panel.
# Banner is full-bleed light blue (BG) with the FG-bodied slate on the right;
# dialog is white with a dark (FG) strip on the left holding the inverted
# (BG-bodied) slate.
BANNER_BASE = (493, 58)
DIALOG_BASE = (493, 312)
DIALOG_STRIP_FRAC = 1.0 / 3.0  # left strip width as fraction of dialog width
BANNER_ICON_FRAC = 0.75  # icon side as fraction of banner height
DIALOG_ICON_FRAC = 0.55  # icon side as fraction of dialog strip width
SCALES: list[tuple[float, str]] = [
    (1.00, ""),
    (1.25, ".scale-125"),
    (1.50, ".scale-150"),
    (2.00, ".scale-200"),
]
TOP_LEVEL_BANNER_PNG_SIZE = (1634, 211)
TOP_LEVEL_DIALOG_PNG_SIZE = (647, 407)

# Heights match the natural SVG aspect ratio (1024x480).
# _small outputs use the -bg variant (background included).
FAVICON_OUTPUTS: list[Path] = [
    REPO_DIR / "docs" / "_static" / "favicon.ico",
    REPO_DIR / "website" / "pages" / "img" / "favicon.ico",
]

LOGO_OUTPUTS: list[LogoOutput] = [
    LogoOutput(REPO_DIR / "docs" / "_static" / "pyscenedetect_logo.png", 900, 422, LOGO_SVG),
    LogoOutput(
        REPO_DIR / "docs" / "_static" / "pyscenedetect_logo_small.png", 300, 141, LOGO_BG_SVG
    ),
    LogoOutput(
        REPO_DIR / "website" / "pages" / "img" / "pyscenedetect_logo.png", 640, 300, LOGO_BG_SVG
    ),
    LogoOutput(
        REPO_DIR / "website" / "pages" / "img" / "pyscenedetect_logo_small.png", 462, 217, LOGO_SVG
    ),
]

SVG_FOR_SIZE: dict[int, Path] = {
    24: LOGO_DIR / "pyscenedetect-24.svg",
    32: LOGO_DIR / "pyscenedetect-32.svg",
    48: LOGO_DIR / "pyscenedetect.svg",
    64: LOGO_DIR / "pyscenedetect.svg",
    128: LOGO_DIR / "pyscenedetect.svg",
    256: LOGO_DIR / "pyscenedetect.svg",
}


def make_icon_16() -> Image.Image:
    """Create a hand-crafted 16x16 clapperboard icon."""
    img = Image.new("RGBA", (16, 16), FG)
    px = img.load()
    assert px is not None

    # Clear 1px padding on all sides
    for i in range(16):
        px[0, i] = BG
        px[15, i] = BG
        px[i, 0] = BG
        px[i, 15] = BG

    # Arm stripe gaps (rows 2-4): clear pixels not part of a complete stripe.
    # A stripe x+y=s spans all 3 arm rows only when 5 <= s <= 16.
    for y in range(2, 5):
        for x in range(1, 15):
            if y < 4 and x < 3:
                continue
            if y > 2 and x > 12:
                continue
            if not ((x + y) % 4 < 2 and 5 <= (x + y) <= 16):
                px[x, y] = BG

    # Slate interior (rows 8-12, cols 3-12)
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


def render_svg(inkscape: str, svg: Path, output: Path, width: int, height: int):
    """Render an SVG to a PNG at the given dimensions using Inkscape."""
    subprocess.run(
        [
            inkscape,
            str(svg),
            "--export-type=png",
            f"--export-filename={output}",
            "-w",
            str(width),
            "-h",
            str(height),
        ],
        check=True,
        capture_output=True,
    )


def render_logos(inkscape: str):
    """Render the logo SVG to all required PNG outputs."""
    print("Rendering logo PNGs...")
    for entry in LOGO_OUTPUTS:
        rel_path = entry.path.relative_to(REPO_DIR)
        print(f"  {rel_path} ({entry.width}x{entry.height}) [source: {entry.source.name}]...")
        render_svg(inkscape, entry.source, entry.path, entry.width, entry.height)
    print(f"  Done ({len(LOGO_OUTPUTS)} files).")


def _render_slate(inkscape: str, work_dir: Path, side: int, *, inverted: bool) -> Image.Image:
    """Render the slate icon at exact size with Inkscape.

    With inverted=False, the slate renders with its native FG body / BG stripes
    (right for placing on the white banner). With inverted=True, the SVG color
    codes are swapped before rendering so the body becomes BG and the stripes
    FG - needed for the dialog's dark FG strip, where a non-inverted slate
    would blend into the background.
    """
    if inverted:
        sentinel = "__SWAP_FG__"
        svg_text = SLATE_SVG.read_text(encoding="utf-8")
        svg_text = (
            svg_text.replace("#2a3545", sentinel)
            .replace("#e0e8f0", "#2a3545")
            .replace(sentinel, "#e0e8f0")
        )
        svg_path = work_dir / f"slate_inv_{side}.svg"
        svg_path.write_text(svg_text, encoding="utf-8")
    else:
        svg_path = SLATE_SVG
    out = work_dir / f"slate_{'inv_' if inverted else ''}{side}.png"
    render_svg(inkscape, svg_path, out, side, side)
    return Image.open(out).convert("RGBA")


def _save_baseline_jpeg(img: Image.Image, path: Path) -> None:
    """Save as baseline (non-progressive) sRGB JPEG. Required by Windows Installer's
    dialog renderer; progressive JPEGs decode as solid black at install time."""
    img.convert("RGB").save(
        path, "JPEG", quality=92, optimize=True, progressive=False, subsampling=0
    )


def _compose_banner(slate_fg: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Banner = full-bleed BG (light blue) canvas with the FG slate on the right."""
    width, height = size
    canvas = Image.new("RGBA", size, BG)
    pad = max(2, round(height * 0.10))
    icon_x = width - slate_fg.width - pad
    icon_y = (height - slate_fg.height) // 2
    canvas.paste(slate_fg, (icon_x, icon_y), slate_fg)
    return canvas


def _compose_dialog(slate_bg: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Dialog = white canvas with FG strip on the left holding a BG-tinted slate."""
    width, height = size
    strip_w = round(width * DIALOG_STRIP_FRAC)
    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (strip_w, height)], fill=FG)
    icon_x = (strip_w - slate_bg.width) // 2
    icon_y = round(height * 0.20)
    canvas.paste(slate_bg, (icon_x, icon_y), slate_bg)
    return canvas


def render_installer_jpegs(inkscape: str, work_dir: Path) -> None:
    """Render the per-scale baseline JPEGs that ship inside the MSI.

    Outputs `Generated Images/installer_{banner,logo}{,.scale-125,.scale-150,.scale-200}.jpg`
    from the master SVG. These are gitignored - pre_release.py --release rebuilds
    them before each MSI build, so they always match the current logo without
    being re-committed every time.
    """
    GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    # Render the slate at the exact target size each iteration - sharper than
    # rendering once big and downsampling, and avoids Pillow's resize stub mismatch.
    for scale, suffix in SCALES:
        bw, bh = round(BANNER_BASE[0] * scale), round(BANNER_BASE[1] * scale)
        dw, dh = round(DIALOG_BASE[0] * scale), round(DIALOG_BASE[1] * scale)

        # Banner icon sized off height (the limiting dim - banner is wide & short).
        # Strip is wider than the icon, so the icon centers within it.
        banner_icon_side = round(bh * BANNER_ICON_FRAC)
        slate_fg = _render_slate(inkscape, work_dir, banner_icon_side, inverted=False)

        dialog_strip_w = round(dw * DIALOG_STRIP_FRAC)
        dialog_icon_side = round(dialog_strip_w * DIALOG_ICON_FRAC)
        slate_bg = _render_slate(inkscape, work_dir, dialog_icon_side, inverted=True)

        banner_path = GENERATED_IMAGES_DIR / f"installer_banner{suffix}.jpg"
        dialog_path = GENERATED_IMAGES_DIR / f"installer_logo{suffix}.jpg"
        print(f"  {banner_path.relative_to(REPO_DIR)} ({bw}x{bh})")
        _save_baseline_jpeg(_compose_banner(slate_fg, (bw, bh)), banner_path)
        print(f"  {dialog_path.relative_to(REPO_DIR)} ({dw}x{dh})")
        _save_baseline_jpeg(_compose_dialog(slate_bg, (dw, dh)), dialog_path)


def render_installer_static(inkscape: str, work_dir: Path) -> None:
    """Render the stable, committed installer assets - only re-run when the logo changes.

    Outputs:
      - psd_square_small.ico (copy of pyscenedetect.ico)
      - installer_banner.png, installer_logo.png (top-level audit masters)
      - installer_banner.svg, installer_logo.svg (top-level + Generated Images/, master SVG copies)
    """
    GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    top_banner = INSTALLER_DIR / "installer_banner.png"
    top_dialog = INSTALLER_DIR / "installer_logo.png"
    tbw, tbh = TOP_LEVEL_BANNER_PNG_SIZE
    tdw, tdh = TOP_LEVEL_DIALOG_PNG_SIZE
    top_slate_fg = _render_slate(inkscape, work_dir, round(tbh * BANNER_ICON_FRAC), inverted=False)
    top_dialog_strip = round(tdw * DIALOG_STRIP_FRAC)
    top_slate_bg = _render_slate(
        inkscape, work_dir, round(top_dialog_strip * DIALOG_ICON_FRAC), inverted=True
    )
    print(f"  {top_banner.relative_to(REPO_DIR)} ({tbw}x{tbh})")
    _compose_banner(top_slate_fg, TOP_LEVEL_BANNER_PNG_SIZE).save(top_banner, "PNG")
    print(f"  {top_dialog.relative_to(REPO_DIR)} ({tdw}x{tdh})")
    _compose_dialog(top_slate_bg, TOP_LEVEL_DIALOG_PNG_SIZE).save(top_dialog, "PNG")

    # SVG references: drop a copy of the master logo+bg SVG at every spot the
    # repo previously kept a reference rendering. These aren't read at MSI build
    # time (the JPGs are what ship); they exist as audit artifacts.
    for dest in (
        INSTALLER_DIR / "installer_banner.svg",
        INSTALLER_DIR / "installer_logo.svg",
        GENERATED_IMAGES_DIR / "installer_banner.svg",
        GENERATED_IMAGES_DIR / "installer_logo.svg",
    ):
        shutil.copy2(LOGO_BG_SVG, dest)
        print(f"  {dest.relative_to(REPO_DIR)} <- {LOGO_BG_SVG.name}")

    # ARP product icon: reuse pyscenedetect.ico under the filename the .aip
    # references (line 17: ARPPRODUCTICON psd_square_small).
    shutil.copy2(ICO_PATH, ARP_ICO_PATH)
    print(f"  {ARP_ICO_PATH.relative_to(REPO_DIR)} <- {ICO_PATH.name}")


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
            render_svg(inkscape, svg_path, png_path, size, size)
            img = Image.open(png_path).copy()
            if size in SHARPEN_AMOUNT:
                img = img.filter(
                    ImageFilter.UnsharpMask(
                        radius=SHARPEN_RADIUS, percent=SHARPEN_AMOUNT[size], threshold=0
                    )
                )
                print(f"    Sharpened {size}x{size} (USM {SHARPEN_AMOUNT[size]}%)")
                img.save(png_path)
        images.append(img)
    return images


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "persist_dir",
        nargs="?",
        type=Path,
        help="Optional directory to persist intermediate PNGs (default: tempdir).",
    )
    parser.add_argument(
        "--installer-jpegs",
        action="store_true",
        help=(
            "Only regenerate the per-build installer JPGs (Generated Images/*.jpg). "
            "Used by pre_release.py --release before the MSI build."
        ),
    )
    args = parser.parse_args()

    persist_dir = args.persist_dir
    if persist_dir:
        persist_dir.mkdir(parents=True, exist_ok=True)
        print(f"Persisting PNGs to: {persist_dir}")

    inkscape = find_inkscape()
    print(f"Using Inkscape: {inkscape}")
    print(f"Logo directory: {LOGO_DIR}")

    ctx = contextlib.nullcontext(str(persist_dir)) if persist_dir else tempfile.TemporaryDirectory()
    with ctx as work:
        if args.installer_jpegs:
            print("Rendering installer JPGs...")
            render_installer_jpegs(inkscape, Path(work))
            return

        images = render_all_sizes(inkscape, Path(work))
        images[-1].save(ICO_PATH, format="ICO", append_images=images[:-1])

        print(f"Output ICO: {ICO_PATH}")
        print("Copying favicons...")
        for dest in FAVICON_OUTPUTS:
            shutil.copy2(ICO_PATH, dest)
            print(f"  {dest.relative_to(REPO_DIR)}")
        render_logos(inkscape)
        print("Rendering installer branding (static assets)...")
        render_installer_static(inkscape, Path(work))
        print("Rendering installer JPGs...")
        render_installer_jpegs(inkscape, Path(work))


if __name__ == "__main__":
    main()
