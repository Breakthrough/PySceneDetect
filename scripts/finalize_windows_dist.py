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

Takes the signed bundle returned by SignPath and the portable .zip built by
AppVeyor, swaps the unsigned `scenedetect.exe` inside the portable .zip for
the signed copy, repacks the .zip with LZMA via 7-Zip, copies the signed MSI
alongside, and emits SHA256 manifests over the final release artifacts.

Run after the SignPath signing job completes and `scenedetect-signed.zip`
has been downloaded.

Expected inputs (in --staging-dir, default `dist/signed/`):
    scenedetect-signed.zip              - SignPath bundle (signed .exe + .msi)
    PySceneDetect-X.Y.Z-portable.zip    - portable .zip from AppVeyor

Outputs (written to the same directory):
    PySceneDetect-X.Y.Z-portable.zip    - repacked with the signed .exe
    PySceneDetect-X.Y.Z-win64.msi       - signed MSI extracted from the bundle
    PySceneDetect-X.Y.Z.manifest.json   - structured per-file SHA256 manifest
    SHA256SUMS                          - flat sha256sum -c compatible output
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import scenedetect  # noqa: E402

CHUNK = 1 << 20  # 1 MiB


def msi_version(raw: str) -> str:
    # Mirror scripts/update_installer.py / generate_manifest.py - artifact
    # filenames use the normalized X.Y.Z form, not the Python __version__.
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:4])


VERSION = msi_version(scenedetect.__version__)


def find_7zip() -> Path:
    for candidate in (
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    ):
        if candidate.exists():
            return candidate
    on_path = shutil.which("7z") or shutil.which("7z.exe")
    if on_path:
        return Path(on_path)
    sys.exit("7-Zip not found. Install from https://www.7-zip.org/.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


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


def verify_authenticode(path: Path) -> None:
    """Bail unless `path` carries a Valid Authenticode signature.

    Catches the wrong-artifact case: e.g. someone drops the AppVeyor
    pre-signing bundle into dist/signed/ instead of the SignPath output.
    PowerShell's Get-AuthenticodeSignature works on both .exe and .msi.
    """
    if sys.platform != "win32":
        print(f"  (skipping Authenticode check for {path.name} on non-Windows)")
        return
    ps_cmd = (
        f"$sig = Get-AuthenticodeSignature -FilePath '{path}'; "
        "Write-Output $sig.Status; "
        "if ($sig.SignerCertificate) { Write-Output $sig.SignerCertificate.Subject }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not lines:
        sys.exit(
            f"Authenticode check for {path.name} failed to run.\n"
            f"  stderr: {result.stderr.strip()}"
        )
    status = lines[0]
    subject = lines[1] if len(lines) > 1 else "<no certificate>"
    print(f"  Authenticode: {status} ({subject})")
    if status != "Valid":
        sys.exit(
            f"Authenticode check FAILED for {path.name}: status={status!r}. "
            "Verify scenedetect-signed.zip is the SignPath output, not an "
            "unsigned AppVeyor artifact."
        )


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


def repack_portable(portable_zip: Path, signed_exe: Path, sevenz: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        print(f"Extracting {portable_zip.name}...")
        with zipfile.ZipFile(portable_zip) as zf:
            zf.extractall(tree)
        target = tree / "scenedetect.exe"
        if not target.exists():
            sys.exit(f"scenedetect.exe not found inside {portable_zip}")
        print("  swapping in signed scenedetect.exe")
        shutil.copy2(signed_exe, target)
        # Preserve the unsigned AppVeyor zip alongside the signed output for
        # diffing / recovery. Overwrite any prior .unsigned from a re-run.
        backup = portable_zip.with_suffix(".unsigned.zip")
        if backup.exists():
            backup.unlink()
        portable_zip.rename(backup)
        print(f"  preserved original as {backup.name}")
        print(f"Repacking {portable_zip.name} (zip / Deflate / mx=9 / mt=on)...")
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
                str(portable_zip),
                *entries,
            ],
            cwd=tree,
            check=True,
            capture_output=True,
        )
        print(f"  {portable_zip.stat().st_size / (1024 * 1024):.1f} MB")


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

    manifest_path = staging / f"PySceneDetect-{VERSION}.manifest.json"
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
        help="Directory holding scenedetect-signed.zip and PySceneDetect-*-portable.zip.",
    )
    args = parser.parse_args()

    staging = args.staging_dir.resolve()
    if not staging.is_dir():
        sys.exit(f"{staging} not found")

    signed_bundle = staging / "scenedetect-signed.zip"
    portable_zip = staging / f"PySceneDetect-{VERSION}-portable.zip"
    if not signed_bundle.is_file():
        sys.exit(f"{signed_bundle} not found")
    if not portable_zip.is_file():
        sys.exit(f"{portable_zip} not found")

    sevenz = find_7zip()
    print(f"Using 7-Zip: {sevenz}")
    print(f"Staging dir: {staging}")
    print(f"Version:     {VERSION}")

    with tempfile.TemporaryDirectory() as tmp:
        signed_exe, signed_msi = extract_signed_bundle(signed_bundle, Path(tmp))
        repack_portable(portable_zip, signed_exe, sevenz)
        msi_dest = staging / signed_msi.name
        shutil.copy2(signed_msi, msi_dest)
        print(f"Copied signed MSI -> {msi_dest.name}")
        write_manifests(staging, portable_zip, msi_dest)


if __name__ == "__main__":
    main()
