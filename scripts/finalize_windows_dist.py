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
"""Finalize signed Windows release artifacts.

Takes the signed bundle returned by SignPath, extracts the file tree from the
signed MSI via `msiexec /a`, repacks it as the portable .zip with 7-Zip, and
emits SHA256 manifests over the final release artifacts.

Run after the SignPath signing job completes and `scenedetect-signed.zip`
has been downloaded.

Expected input (in --staging-dir, default `dist/signed/`):
    scenedetect-signed.zip                    - SignPath bundle (signed .exe + .msi)

Outputs (written to the same directory):
    PySceneDetect-X.Y.Z-win64.zip             - portable .zip rebuilt from the signed MSI
    PySceneDetect-X.Y.Z-win64.msi             - signed MSI extracted from the bundle
    PySceneDetect-X.Y.Z-win64.manifest.json   - structured per-file SHA256 manifest
    SHA256SUMS                                - flat sha256sum -c compatible output
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_release  # noqa: E402
from _release_common import (  # noqa: E402
    find_7zip,
    hash_zip_contents,
    msi_version,
    sha256_file,
    verify_authenticode,
)

import scenedetect  # noqa: E402

VERSION = msi_version(scenedetect.__version__)


def extract_signed_bundle(signed_zip: Path, dest: Path) -> tuple[Path, Path]:
    print(f"Extracting {signed_zip.name}...")
    with zipfile.ZipFile(signed_zip) as zf:
        zf.extractall(dest)
    exe = next((p for p in dest.rglob("scenedetect.exe")), None)
    msi = next((p for p in dest.rglob("PySceneDetect-*.msi")), None)
    if exe is None:
        sys.exit(f"scenedetect.exe not found inside {signed_zip}")
    if msi is None:
        sys.exit(f"PySceneDetect-*.msi not found inside {signed_zip}")
    print(f"  signed exe: {exe.name} ({exe.stat().st_size:,} bytes)")
    verify_authenticode(exe)
    print(f"  signed msi: {msi.name} ({msi.stat().st_size:,} bytes)")
    verify_authenticode(msi)
    return exe, msi


def extract_msi_tree(msi_path: Path, dest: Path) -> Path:
    """Run `msiexec /a` to extract the .msi's installed file tree without
    actually installing. Returns the directory containing scenedetect.exe
    (the app root), which sits under TARGETDIR at the .aip's APPDIR depth."""
    if sys.platform != "win32":
        sys.exit("msiexec /a is Windows-only")
    print(f"Extracting {msi_path.name} via msiexec /a...")
    # /a = administrative install: file extraction only, no registry, no admin rights.
    # /qn = silent. TARGETDIR must be absolute.
    result = subprocess.run(
        ["msiexec", "/a", str(msi_path), "/qn", f"TARGETDIR={dest}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(
            f"msiexec /a failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    exe = next((p for p in dest.rglob("scenedetect.exe")), None)
    if exe is None:
        sys.exit(f"scenedetect.exe not found anywhere under {dest} after msiexec /a")
    tree = exe.parent
    # `msiexec /a` writes an "administrative" copy of the .msi (and sometimes a
    # `Cabs/` folder) into TARGETDIR alongside the extracted app files. When
    # APPDIR == TARGETDIR (no nested install folder), these land inside the app
    # tree and would pollute the portable .zip. Strip them.
    for stray in tree.glob("*.msi"):
        print(f"  stripping admin-install artifact: {stray.name}")
        stray.unlink()
    cabs_dir = tree / "Cabs"
    if cabs_dir.is_dir():
        print("  stripping admin-install artifact: Cabs/")
        shutil.rmtree(cabs_dir)
    print(f"  app tree: {tree.relative_to(dest)}/ ({sum(1 for _ in tree.rglob('*')):,} entries)")
    return tree


def build_portable_zip(tree: Path, zip_path: Path, sevenz: Path) -> None:
    """Pack `tree`'s top-level contents into a Deflate .zip using the same
    flags AppVeyor's stage_windows_dist.py uses for the portable distribution."""
    if zip_path.exists():
        zip_path.unlink()
    print(f"Building {zip_path.name} (zip / Deflate / mx=9 / mt=on)...")
    # -mm=Deflate (not LZMA): Windows Explorer's built-in "Extract All" only
    # supports Deflate-compressed zips; LZMA needs 7-Zip/WinRAR. Portable .zip
    # ships to end users on clean Windows, so compat trumps ratio here.
    # -mfb=258 -mpass=15: max-out Deflate tuning (slow, but once per release).
    # -mmt=on: 7z parallelizes Deflate across files (not within a file), so
    # the docs/ + thirdparty/ tree gets a real speedup; the two big binaries
    # (scenedetect.exe, ffmpeg.exe) still each compress on a single thread.
    # Pass top-level entries (not '*') so we don't depend on shell globbing.
    entries = sorted(p.name for p in tree.iterdir())
    subprocess.run(
        [
            str(sevenz),
            "a",
            "-tzip",
            "-mm=Deflate",
            "-mx=9",
            "-mfb=258",
            "-mpass=15",
            "-mmt=on",
            str(zip_path),
            *entries,
        ],
        cwd=tree,
        check=True,
        capture_output=True,
    )
    print(f"  {zip_path.stat().st_size / (1024 * 1024):.1f} MB")


def write_manifests(staging: Path, portable_zip: Path, msi: Path) -> None:
    print(f"Hashing {portable_zip.name}...")
    portable_digest = sha256_file(portable_zip)
    print(f"Hashing {msi.name}...")
    msi_digest = sha256_file(msi)

    manifest = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bundles": {
            "msi": {
                "path": msi.name,
                "size": msi.stat().st_size,
                "sha256": msi_digest,
            },
            "portable_zip": {
                "path": portable_zip.name,
                "size": portable_zip.stat().st_size,
                "sha256": portable_digest,
                "contents": hash_zip_contents(portable_zip),
            },
        },
    }

    manifest_path = staging / f"PySceneDetect-{VERSION}-win64.manifest.json"
    sums_path = staging / "SHA256SUMS"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sums_path.write_text(
        f"{msi_digest}  {msi.name}\n{portable_digest}  {portable_zip.name}\n",
        encoding="utf-8",
    )
    print(f"Wrote {manifest_path.name}")
    print(f"Wrote {sums_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=REPO_DIR / "dist" / "signed",
        help="Directory holding scenedetect-signed.zip.",
    )
    args = parser.parse_args()

    staging = args.staging_dir.resolve()
    if not staging.is_dir():
        sys.exit(f"{staging} not found")

    signed_bundle = staging / "scenedetect-signed.zip"
    if not signed_bundle.is_file():
        sys.exit(f"{signed_bundle} not found")

    sevenz = find_7zip()
    print(f"Using 7-Zip: {sevenz}")
    print(f"Staging dir: {staging}")
    print(f"Version:     {VERSION}")

    portable_zip = staging / f"PySceneDetect-{VERSION}-win64.zip"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Bundle holds the SignPath outputs; signed .exe is verified for the
        # wrong-bundle check but otherwise unused (the .msi already ships its
        # own signed copy of scenedetect.exe).
        _signed_exe, signed_msi = extract_signed_bundle(signed_bundle, tmp_path / "bundle")
        msi_dest = staging / signed_msi.name
        shutil.copy2(signed_msi, msi_dest)
        print(f"Copied signed MSI -> {msi_dest.name}")
        msi_tree = extract_msi_tree(msi_dest, tmp_path / "msi-extract")
        build_portable_zip(msi_tree, portable_zip, sevenz)
        write_manifests(staging, portable_zip, msi_dest)

    print()
    print("Validating finalized artifacts...")
    validate_release.run_all_checks(staging)


if __name__ == "__main__":
    main()
