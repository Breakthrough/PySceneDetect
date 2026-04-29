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
"""Stages Windows distribution assets into dist/scenedetect/.

Sequence in a release to generate the installer:

```bash
    python scripts/pre_release.py
    pyinstaller packaging/windows/scenedetect.spec
    python scripts/stage_windows_dist.py --ffmpeg-dir <dir>
    python scripts/update_installer.py --sync-files
    AdvancedInstaller.com /build packaging/windows/installer/PySceneDetect.aip
    python scripts/generate_manifest.py
```

This script assumes it is run on a Windows machine.
"""

# TODO: This should be called from the Github Actions workflow as well, right now it's only
# done from the appveyor one. When that's done it should be merged with update_installer.py
# into a combined "prepare_windows_dist.py".

import argparse
import re
import shutil
import subprocess
import sys
import zipfile

if sys.platform != "win32":
    print("Error: stage_windows_dist.py must be run on Windows.", file=sys.stderr)
    sys.exit(1)
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import scenedetect  # noqa: E402

DIST_DIR = REPO_DIR / "dist"
DIST_TREE = DIST_DIR / "scenedetect"
PACKAGING_WIN = REPO_DIR / "packaging" / "windows"
DOCS_DIR = REPO_DIR / "docs"
THIRDPARTY_LICENSES = REPO_DIR / "scenedetect" / "_thirdparty"


def msi_version(raw: str) -> str:
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:4])


def find_7zip() -> Path:
    for candidate in (
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    ):
        if candidate.exists():
            return candidate
    sys.exit("7-Zip not found. Install from https://www.7-zip.org/.")


def _rel(p: Path) -> str:
    # Display paths relative to the repo when possible, else fall back to the
    # absolute path (e.g. --ffmpeg-dir pointing outside the repo on CI).
    try:
        return str(p.relative_to(REPO_DIR))
    except ValueError:
        return str(p)


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"WARNING: {src} missing - skipping {dst.name}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {_rel(src)} -> {_rel(dst)}")


def stage_ffmpeg(ffmpeg_dir: Path | None) -> None:
    thirdparty = DIST_TREE / "thirdparty"
    thirdparty.mkdir(parents=True, exist_ok=True)
    if ffmpeg_dir is not None:
        print(f"Copying ffmpeg from {ffmpeg_dir}")
        copy_file(ffmpeg_dir / "ffmpeg.exe", DIST_TREE / "ffmpeg.exe")
        copy_file(ffmpeg_dir / "LICENSE", thirdparty / "LICENSE-FFMPEG")
        return
    archive = PACKAGING_WIN / "thirdparty.7z"
    if not archive.exists():
        sys.exit(f"No --ffmpeg-dir given and {archive} missing.")
    sevenz = find_7zip()
    staging = DIST_TREE / "_thirdparty_extract"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    print(f"Extracting {archive.name} (bundled fallback)...")
    subprocess.run(
        [str(sevenz), "x", str(archive), f"-o{staging}", "windows/ffmpeg.exe", "-y"],
        check=True,
        capture_output=True,
    )
    src = staging / "windows" / "ffmpeg.exe"
    if src.exists():
        shutil.move(str(src), str(DIST_TREE / "ffmpeg.exe"))
        print("  ffmpeg.exe -> dist/scenedetect/ffmpeg.exe")
    shutil.rmtree(staging)
    # The bundled archive predates LICENSE-FFMPEG; emit a stub pointing at upstream.
    stub = thirdparty / "LICENSE-FFMPEG"
    stub.write_text(
        "FFmpeg is licensed under the LGPL/GPL. See https://ffmpeg.org/legal.html "
        "for the canonical license text matching the bundled binary.\n",
        encoding="utf-8",
    )
    print(f"  (stub) -> {stub.relative_to(REPO_DIR)}")


def build_docs() -> None:
    if not (DOCS_DIR / "Makefile").exists():
        print("WARNING: docs/Makefile missing - skipping docs build")
        return
    print("Building Sphinx docs (singlehtml)...")
    target = DIST_TREE / "docs"
    if target.exists():
        shutil.rmtree(target)
    subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "singlehtml", str(DOCS_DIR), str(target)],
        check=True,
    )
    print("  docs -> dist/scenedetect/docs/")


def stage_thirdparty_licenses() -> None:
    target = DIST_TREE / "thirdparty"
    target.mkdir(parents=True, exist_ok=True)
    print("Staging third-party licenses...")
    for src in sorted(THIRDPARTY_LICENSES.glob("LICENSE-*")):
        copy_file(src, target / src.name)
    copy_file(PACKAGING_WIN / "LICENSE-PYTHON", target / "LICENSE-PYTHON")


def make_portable_zip(version: str) -> None:
    zip_path = DIST_DIR / f"PySceneDetect-{version}-portable.zip"
    manifest_path = DIST_DIR / f"PySceneDetect-{version}-portable.manifest.txt"
    if zip_path.exists():
        zip_path.unlink()
    print(f"Creating {zip_path.relative_to(REPO_DIR)}...")
    files = sorted(p for p in DIST_TREE.rglob("*") if p.is_file())
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(DIST_TREE))
    print(f"  {zip_path.stat().st_size / (1024 * 1024):.1f} MB")
    manifest_path.write_text(
        "\n".join(str(p.relative_to(DIST_TREE)) for p in files) + "\n",
        encoding="utf-8",
    )
    print(f"  manifest -> {manifest_path.relative_to(REPO_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--ffmpeg-dir",
        type=Path,
        help="Directory containing ffmpeg.exe and its LICENSE. "
        "If omitted, ffmpeg is extracted from packaging/windows/thirdparty.7z.",
    )
    args = parser.parse_args()

    if not DIST_TREE.exists():
        sys.exit(f"{DIST_TREE} not found. Run pyinstaller first.")

    print(f"Staging into {DIST_TREE.relative_to(REPO_DIR)}")
    stage_ffmpeg(args.ffmpeg_dir)
    print("Copying root files...")
    copy_file(REPO_DIR / "LICENSE", DIST_TREE / "LICENSE")
    copy_file(PACKAGING_WIN / "README.txt", DIST_TREE / "README.txt")
    stage_thirdparty_licenses()
    build_docs()
    make_portable_zip(msi_version(scenedetect.__version__))


if __name__ == "__main__":
    main()
