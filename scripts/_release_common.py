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
"""Shared helpers for Windows release-finalization and validation scripts."""

import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

CHUNK = 1 << 20  # 1 MiB


def msi_version(raw: str) -> str:
    # AdvancedInstaller's MSI ProductVersion field requires numeric X.Y.Z[.B];
    # strip Python-style suffixes ("0.7-dev0" -> "0.7") and pad to three parts.
    # Use this ONLY for the /SetVersion value passed to AdvancedInstaller, not
    # for artifact filenames - those should use display_version() to match the
    # Python package version (e.g. PyPI "0.7", not "0.7.0").
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:4])


def display_version(raw: str) -> str:
    # Filename-facing version: matches scenedetect.__version__ component count,
    # with Python-style suffixes stripped ("0.7-dev0" -> "0.7", "0.7" -> "0.7",
    # "0.7.1" -> "0.7.1"). Use for .msi/.zip/manifest filenames so artifacts
    # line up with the PyPI package and git tag.
    parts = [re.split(r"[^\d]", p, maxsplit=1)[0] for p in raw.split(".")]
    return ".".join(p for p in parts[:4] if p)


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
            f"Authenticode check for {path.name} failed to run.\n  stderr: {result.stderr.strip()}"
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
