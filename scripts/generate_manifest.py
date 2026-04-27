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
"""Generate a SHA256 audit manifest for the Windows release artifacts.

Walks the pyinstaller output tree, the built MSI, and the portable ZIP
(if present), hashes every file, and writes:

    dist/PySceneDetect-X.Y.Z.manifest.json   - structured per-file manifest
    dist/SHA256SUMS                          - flat sha256sum -c compatible

Run after both `pyinstaller packaging/windows/scenedetect.spec` and the
AdvancedInstaller MSI build have completed. Attach both outputs to the
GitHub release so users can verify what they downloaded.
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import scenedetect  # noqa: E402


def msi_version(raw: str) -> str:
    # Mirror scripts/bump_installer.py - the artifact filename uses the
    # normalized X.Y.Z form, not the Python __version__ string.
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:4])


VERSION = msi_version(scenedetect.__version__)
DIST_DIR = REPO_DIR / "dist"
PYINSTALLER_TREE = DIST_DIR / "scenedetect"
MSI_PATH = REPO_DIR / "packaging" / "windows" / "installer" / f"PySceneDetect-{VERSION}-win64.msi"
PORTABLE_ZIP = DIST_DIR / f"PySceneDetect-{VERSION}-portable.zip"

CHUNK = 1 << 20  # 1 MiB


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def hash_tree(root: Path) -> list[dict]:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def hash_zip_contents(zip_path: Path) -> list[dict]:
    entries = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            if info.is_dir():
                continue
            h = hashlib.sha256()
            with zf.open(info) as f:
                for block in iter(lambda: f.read(CHUNK), b""):
                    h.update(block)
            entries.append(
                {
                    "path": info.filename,
                    "size": info.file_size,
                    "sha256": h.hexdigest(),
                }
            )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DIST_DIR / f"PySceneDetect-{VERSION}.manifest.json",
        help="Path to the JSON manifest output.",
    )
    parser.add_argument(
        "--sums",
        type=Path,
        default=DIST_DIR / "SHA256SUMS",
        help="Path to the flat sha256sum-compatible output.",
    )
    args = parser.parse_args()

    bundles: dict[str, dict] = {}
    top_level: list[tuple[str, str]] = []  # (sha256, relpath) for SHA256SUMS

    if PYINSTALLER_TREE.is_dir():
        print(f"Hashing pyinstaller tree: {PYINSTALLER_TREE}")
        bundles["pyinstaller_tree"] = {
            "path": PYINSTALLER_TREE.relative_to(REPO_DIR).as_posix(),
            "files": hash_tree(PYINSTALLER_TREE),
        }
    else:
        print(f"WARNING: {PYINSTALLER_TREE} missing - skipping.")

    if MSI_PATH.is_file():
        print(f"Hashing MSI: {MSI_PATH}")
        digest = sha256_file(MSI_PATH)
        bundles["msi"] = {
            "path": MSI_PATH.relative_to(REPO_DIR).as_posix(),
            "size": MSI_PATH.stat().st_size,
            "sha256": digest,
        }
        top_level.append((digest, MSI_PATH.name))
    else:
        print(f"WARNING: {MSI_PATH} missing - skipping.")

    if PORTABLE_ZIP.is_file():
        print(f"Hashing portable zip: {PORTABLE_ZIP}")
        digest = sha256_file(PORTABLE_ZIP)
        bundles["portable_zip"] = {
            "path": PORTABLE_ZIP.relative_to(REPO_DIR).as_posix(),
            "size": PORTABLE_ZIP.stat().st_size,
            "sha256": digest,
            "contents": hash_zip_contents(PORTABLE_ZIP),
        }
        top_level.append((digest, PORTABLE_ZIP.name))
    else:
        print(f"WARNING: {PORTABLE_ZIP} missing - skipping.")

    if not bundles:
        sys.exit("No artifacts found to hash.")

    manifest = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bundles": bundles,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")

    if top_level:
        args.sums.write_text(
            "".join(f"{sha}  {name}\n" for sha, name in top_level),
            encoding="utf-8",
        )
        print(f"Wrote {args.sums}")


if __name__ == "__main__":
    main()
