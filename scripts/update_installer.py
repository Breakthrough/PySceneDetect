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
"""Update the AdvancedInstaller .aip project for a release.

Usage:
    python scripts/update_installer.py                    # version bump only
    python scripts/update_installer.py --sync-files       # bump + re-sync APPDIR
    python scripts/update_installer.py --sync-only        # re-sync APPDIR only (CI)
    python scripts/update_installer.py --sync-only --dev  # CI dev build (renames MSI)
    python scripts/update_installer.py --version 0.7.0    # explicit version override
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_common import display_version, msi_version  # noqa: E402

import scenedetect  # noqa: E402

INSTALLER_AIP = REPO_DIR / "packaging" / "windows" / "installer" / "PySceneDetect.aip"
DIST_TREE = REPO_DIR / "dist" / "scenedetect"


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
        "--dev",
        action="store_true",
        help=(
            "Rename the MSI to PySceneDetect-{ver}-dev-win64.msi so dev-build artifacts "
            "are distinguishable from release artifacts. Only valid with --sync-only."
        ),
    )
    parser.add_argument(
        "--version",
        dest="version_override",
        help="MSI version override (default: derived from scenedetect.__version__).",
    )
    args = parser.parse_args()

    if args.dev and not args.sync_only:
        sys.exit("--dev is only valid in combination with --sync-only.")

    advinst = find_advinst()
    print(f"Using {advinst}")

    if args.sync_only:
        print(f"Re-syncing APPDIR in {INSTALLER_AIP.name}")
        resync_appdir(advinst)
        if args.dev:
            raw_version = args.version_override or scenedetect.__version__
            file_version = display_version(raw_version)
            dev_name = f"PySceneDetect-{file_version}-dev-win64.msi"
            print(f"Renaming MSI package to {dev_name} (dev build)")
            run(advinst, "/SetPackageName", dev_name, "-buildname", "DefaultBuild")
        return

    raw_version = args.version_override or scenedetect.__version__
    product_version = msi_version(raw_version)
    file_version = display_version(raw_version)
    if not all(p.isdigit() for p in product_version.split(".") if p):
        sys.exit(f"Cannot derive numeric MSI version from {raw_version!r}")
    if product_version != raw_version:
        print(f"Normalized {raw_version!r} -> {product_version!r} for AdvancedInstaller")
    print(f"Bumping {INSTALLER_AIP.name} to {product_version} (filename: {file_version})")

    run(advinst, "/SetVersion", product_version)
    run(advinst, "/SetProductCode", "-langid", "1033")
    run(
        advinst,
        "/SetPackageName",
        f"PySceneDetect-{file_version}-win64.msi",
        "-buildname",
        "DefaultBuild",
    )

    if args.sync_files:
        resync_appdir(advinst)


if __name__ == "__main__":
    main()
