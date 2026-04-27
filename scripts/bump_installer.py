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
"""Bump the AdvancedInstaller .aip project for a release.

Usage:
    python scripts/bump_installer.py             # version bump only
    python scripts/bump_installer.py --sync-files  # bump + re-sync APPDIR
    python scripts/bump_installer.py --sync-only   # re-sync APPDIR only (CI)
    python scripts/bump_installer.py --version 0.7.0  # explicit version override

The version-bump path rewrites ProductVersion / ProductCode / PackageFileName.
--sync-files additionally walks dist/scenedetect/ (pyinstaller output) and
rewrites the project's directory + component + file tables to match, which
is needed when bundled dependencies change. --sync-only does the resync
without touching version/identity fields - intended for CI, where the .aip
is already at the release version and we just want the file list to match
CI's pyinstaller output (rather than the developer's local one).

All paths shell out to AdvancedInstaller.com so the .aip's invariants
(line endings, attribute ordering, GUID casing) stay intact. The CLI lives
under "C:\\Program Files (x86)\\Caphyon\\Advanced Installer ..\\bin\\x86\\".
Override discovery with the ADVINST environment variable.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import scenedetect  # noqa: E402

INSTALLER_AIP = REPO_DIR / "packaging" / "windows" / "installer" / "PySceneDetect.aip"
DIST_TREE = REPO_DIR / "dist" / "scenedetect"


def msi_version(raw: str) -> str:
    # AdvancedInstaller's ProductVersion only accepts numeric X[.Y[.Z[.B]]].
    # Strip Python-style suffixes ("0.7-dev0" -> "0.7"; "1.0.0-rc1" -> "1.0.0")
    # and pad to three components so the resulting MSI filename is consistent.
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    if not all(p.isdigit() for p in parts if p):
        sys.exit(f"Cannot derive numeric MSI version from {raw!r}")
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:4])


def find_advinst() -> Path:
    if env := os.environ.get("ADVINST"):
        path = Path(env)
        if not path.exists():
            sys.exit(f"ADVINST={env} does not exist.")
        return path
    candidates = sorted(
        Path(r"C:\Program Files (x86)\Caphyon").glob(
            "Advanced Installer*/bin/x86/AdvancedInstaller.com"
        )
    )
    if not candidates:
        sys.exit(
            "AdvancedInstaller.com not found under C:\\Program Files (x86)\\Caphyon. "
            "Set the ADVINST environment variable to its full path."
        )
    return candidates[-1]


def run(advinst: Path, *edit_args: str, check: bool = True) -> int:
    cmd = [str(advinst), "/edit", str(INSTALLER_AIP), *edit_args]
    print(">", " ".join(cmd))
    return subprocess.run(cmd, check=check).returncode


def resync_appdir(advinst: Path) -> None:
    if not DIST_TREE.exists():
        sys.exit(
            f"{DIST_TREE} not found. Run `pyinstaller packaging/windows/scenedetect.spec` first."
        )
    # /ResetSync errors out if APPDIR isn't already a synced folder
    # (true on the first run); /NewSync will fail if it IS synced. So
    # try the reset but tolerate failure, then sync.
    run(advinst, "/ResetSync", "APPDIR", check=False)
    run(advinst, "/NewSync", "APPDIR", str(DIST_TREE))


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--sync-files",
        action="store_true",
        help="Bump version/GUIDs AND re-sync APPDIR from dist/scenedetect/.",
    )
    mode.add_argument(
        "--sync-only",
        action="store_true",
        help="Re-sync APPDIR only; leave version/GUID fields untouched (CI use).",
    )
    parser.add_argument(
        "--version",
        dest="version_override",
        help="MSI version override (default: derived from scenedetect.__version__).",
    )
    args = parser.parse_args()

    advinst = find_advinst()
    print(f"Using {advinst}")

    if args.sync_only:
        print(f"Re-syncing APPDIR in {INSTALLER_AIP.name}")
        resync_appdir(advinst)
        return

    raw_version = args.version_override or scenedetect.__version__
    version = msi_version(raw_version)
    if version != raw_version:
        print(f"Normalized {raw_version!r} -> {version!r} for AdvancedInstaller")
    print(f"Bumping {INSTALLER_AIP.name} to {version}")

    run(advinst, "/SetVersion", version)
    run(advinst, "/SetProductCode", "-langid", "1033")
    run(
        advinst,
        "/SetPackageName",
        f"PySceneDetect-{version}-win64.msi",
        "-buildname",
        "DefaultBuild",
    )

    if args.sync_files:
        resync_appdir(advinst)


if __name__ == "__main__":
    main()
