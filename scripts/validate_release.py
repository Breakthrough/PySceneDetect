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
"""Validate finalized Windows release artifacts.

Runs against the staging directory produced by `scripts/finalize_windows_dist.py`
(default `dist/signed/`) and verifies the artifacts that go up to a GitHub
release. Catches regressions that only manifest in the post-build artifact, not
in unit tests:

    1. Filename presence and `-win64` suffix consistency
    2. SHA256 of `.zip` and `.msi` matches `SHA256SUMS` and `manifest.json`,
       and per-file hashes inside the portable .zip match the manifest
    3. Authenticode signatures on the `.msi` and the `scenedetect.exe` inside
       the portable `.zip`
    4. MSI / portable-zip parity: every file in the portable .zip exists in
       the MSI (matched by SHA256, name-agnostic to tolerate MSI mangling)
    5. Frozen `.exe` smoke tests:
       - `scenedetect.exe version` prints the expected version
       - No required dependency is reported as "Not Installed"
       - A short `detect-content` invocation succeeds (skipped if the test
         video resource is absent)
       - Default error path produces a clean error, not a Python traceback

Re-run standalone after fixing any failure:
    python scripts/validate_release.py [--staging-dir DIR]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_common import (  # noqa: E402
    display_version,
    find_7zip,
    hash_zip_contents,
    sha256_file,
    verify_authenticode,
)

import scenedetect  # noqa: E402

VERSION = display_version(scenedetect.__version__)

# Mirrors `third_party_packages` in `scenedetect/platform.py:get_system_version_info()`.
# Keep these two lists in sync: any package added there should be classified here as
# either REQUIRED (must report a version in the frozen .exe) or OPTIONAL (one of a
# mutually-exclusive pair that legitimately reports "Not Installed" in the bundle).
REQUIRED_PACKAGES = (
    "scenedetect",
    "av",
    "click",
    "imageio",
    "imageio-ffmpeg",
    "moviepy",
    "numpy",
    "platformdirs",
    "tqdm",
)
# Exactly one of these must report a version. The frozen Windows build ships
# `opencv-python-headless` only, so `opencv-python` legitimately reports "Not Installed".
OPENCV_VARIANTS = ("opencv-python", "opencv-python-headless")

NOT_INSTALLED = "Not Installed"


def fail(message: str) -> None:
    """Print FAIL marker and bubble out as a SystemExit so finalize stops."""
    sys.exit(f"VALIDATION FAILED: {message}")


def section(name: str) -> None:
    print()
    print(f"[{name}]")


def check_filenames(staging: Path) -> tuple[Path, Path, Path]:
    """Step 1: required artifacts present, no stray inconsistent suffixes."""
    section("Filenames")
    portable_zip = staging / f"PySceneDetect-{VERSION}-win64.zip"
    msi = staging / f"PySceneDetect-{VERSION}-win64.msi"
    manifest = staging / f"PySceneDetect-{VERSION}-win64.manifest.json"
    sums = staging / "SHA256SUMS"

    for required in (portable_zip, msi, manifest, sums):
        if not required.is_file():
            fail(f"missing required artifact: {required.name}")
        print(f"  found {required.name}")

    # Reject filename patterns that proved problematic during v0.7 release smoke testing.
    # Both bugs were caused by inconsistent suffixes between portable .zip and .msi.
    stray_suffixed = list(staging.glob("PySceneDetect-*-portable.zip"))
    if stray_suffixed:
        fail(
            "found stale '-portable' artifacts (inconsistency caught in commit 550a5ad): "
            + ", ".join(p.name for p in stray_suffixed)
        )
    for zip_path in staging.glob("PySceneDetect-*.zip"):
        # Allow the canonical name + the .unsigned.zip backup written by finalize.
        if zip_path == portable_zip or zip_path.name.endswith(".unsigned.zip"):
            continue
        fail(
            f"unexpected portable .zip without '-win64' suffix: {zip_path.name} "
            "(suffix inconsistency caught in commit 9421592)"
        )
    for msi_path in staging.glob("PySceneDetect-*.msi"):
        if msi_path == msi:
            continue
        fail(
            f"unexpected stray MSI: {msi_path.name} "
            "(only one canonical PySceneDetect-X.Y.Z-win64.msi expected)"
        )

    return portable_zip, msi, manifest


def check_hashes(staging: Path, portable_zip: Path, msi: Path, manifest_path: Path) -> dict:
    """Step 2: SHA256 of .zip / .msi matches SHA256SUMS and manifest.json,
    and per-file hashes inside the portable .zip match the manifest."""
    section("Hashes")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("version") != VERSION:
        fail(f"manifest version {manifest.get('version')!r} != expected {VERSION!r}")

    portable_actual = sha256_file(portable_zip)
    msi_actual = sha256_file(msi)
    print(f"  {portable_zip.name}: {portable_actual}")
    print(f"  {msi.name}: {msi_actual}")

    if manifest["bundles"]["portable_zip"]["sha256"] != portable_actual:
        fail(f"manifest portable_zip sha256 mismatch ({portable_zip.name})")
    if manifest["bundles"]["msi"]["sha256"] != msi_actual:
        fail(f"manifest msi sha256 mismatch ({msi.name})")

    sums_text = (staging / "SHA256SUMS").read_text(encoding="utf-8")
    expected_lines = {
        f"{msi_actual}  {msi.name}",
        f"{portable_actual}  {portable_zip.name}",
    }
    actual_lines = {line.strip() for line in sums_text.splitlines() if line.strip()}
    if expected_lines != actual_lines:
        fail(
            "SHA256SUMS does not match recomputed digests.\n"
            f"  expected: {sorted(expected_lines)}\n"
            f"  actual:   {sorted(actual_lines)}"
        )
    print("  SHA256SUMS matches")

    print(f"  re-hashing {portable_zip.name} contents...")
    actual_contents = hash_zip_contents(portable_zip)
    expected_contents = manifest["bundles"]["portable_zip"]["contents"]
    actual_by_path = {entry["path"]: entry for entry in actual_contents}
    expected_by_path = {entry["path"]: entry for entry in expected_contents}
    if actual_by_path.keys() != expected_by_path.keys():
        only_actual = sorted(actual_by_path.keys() - expected_by_path.keys())
        only_manifest = sorted(expected_by_path.keys() - actual_by_path.keys())
        fail(
            "manifest contents file list does not match portable .zip:\n"
            f"  only in zip:      {only_actual}\n"
            f"  only in manifest: {only_manifest}"
        )
    for path, expected in expected_by_path.items():
        actual = actual_by_path[path]
        if actual["sha256"] != expected["sha256"] or actual["size"] != expected["size"]:
            fail(f"manifest content mismatch for {path}: {expected} vs {actual}")
    print(f"  manifest matches all {len(actual_by_path)} entries inside portable .zip")
    return manifest


def check_signatures(portable_zip: Path, msi: Path) -> None:
    """Step 3: Authenticode on .msi and on scenedetect.exe inside the portable .zip."""
    section("Signatures")
    print(f"  verifying {msi.name}")
    verify_authenticode(msi)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(portable_zip) as zf:
            try:
                zf.extract("scenedetect.exe", tmp_path)
            except KeyError:
                fail(f"scenedetect.exe not found at root of {portable_zip.name}")
        exe_path = tmp_path / "scenedetect.exe"
        print(f"  verifying scenedetect.exe inside {portable_zip.name}")
        verify_authenticode(exe_path)


def _hashes_in_dir(root: Path) -> set[str]:
    return {sha256_file(p) for p in root.rglob("*") if p.is_file()}


def check_msi_zip_parity(portable_zip: Path, msi: Path, sevenz: Path) -> None:
    """Step 4: every file in the portable .zip should exist (by content)
    inside the MSI. We compare SHA256 sets to be name-agnostic - 7-Zip's MSI
    extraction can mangle filenames, so name-by-name diffs are unreliable, but
    content hashes are exact."""
    section("MSI / portable-zip parity")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        msi_dir = tmp_path / "msi"
        zip_dir = tmp_path / "zip"
        msi_dir.mkdir()
        zip_dir.mkdir()

        # Extract MSI (which may produce inner .cab archives that themselves need
        # extracting to recover the actual installed file tree).
        print(f"  extracting {msi.name} with 7-Zip...")
        subprocess.run(
            [str(sevenz), "x", str(msi), f"-o{msi_dir}", "-y"],
            check=True,
            capture_output=True,
        )
        cabs = list(msi_dir.rglob("*.cab"))
        for cab in cabs:
            print(f"    expanding inner archive: {cab.name}")
            subprocess.run(
                [str(sevenz), "x", str(cab), f"-o{cab.parent}", "-y"],
                check=True,
                capture_output=True,
            )
            cab.unlink()

        print(f"  extracting {portable_zip.name}...")
        with zipfile.ZipFile(portable_zip) as zf:
            zf.extractall(zip_dir)

        msi_hashes = _hashes_in_dir(msi_dir)
        zip_hashes = _hashes_in_dir(zip_dir)
        missing_from_msi = zip_hashes - msi_hashes
        if missing_from_msi:
            # Re-walk the portable zip to attach names to the missing hashes.
            zip_by_hash = {}
            for p in zip_dir.rglob("*"):
                if p.is_file():
                    zip_by_hash.setdefault(sha256_file(p), p.relative_to(zip_dir).as_posix())
            named = sorted(zip_by_hash.get(h, h) for h in missing_from_msi)
            fail(
                f"{len(missing_from_msi)} file(s) present in portable .zip but not in MSI:\n"
                + "\n".join(f"    {n}" for n in named[:25])
                + (f"\n    ... ({len(named) - 25} more)" if len(named) > 25 else "")
            )
        print(
            f"  all {len(zip_hashes)} files in portable .zip are present in MSI "
            f"({len(msi_hashes)} files in MSI total)"
        )


def _parse_packages_section(version_output: str) -> dict[str, str]:
    """Parse the 'Packages' section of `scenedetect version` output."""
    packages: dict[str, str] = {}
    in_section = False
    for raw in version_output.splitlines():
        line = raw.rstrip()
        if not in_section:
            if line.strip() == "Packages":
                in_section = True
            continue
        # Section ends on blank line, separator, or next header.
        if not line.strip() or line.strip().startswith("---") or line.strip() == "Tools":
            if line.strip() == "Tools":
                break
            continue
        # Format: "<name padded to N><space><value>". Split on first run of >=2 spaces.
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        name, value = parts[0].strip(), parts[1].strip()
        packages[name] = value
    return packages


def check_frozen_exe(portable_zip: Path) -> None:
    """Step 5: extract portable .zip, run scenedetect.exe, verify version,
    package detection, smoke detect, and clean error path."""
    section("Frozen .exe smoke tests")
    if sys.platform != "win32":
        print("  (skipping .exe smoke tests on non-Windows)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(portable_zip) as zf:
            zf.extractall(tmp_path)
        exe = tmp_path / "scenedetect.exe"
        if not exe.is_file():
            fail(f"scenedetect.exe not found at root of {portable_zip.name}")

        # 5a. `version` prints VERSION and well-formed package table.
        result = subprocess.run(
            [str(exe), "version"],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
        )
        if result.returncode != 0:
            fail(f"`scenedetect.exe version` exited {result.returncode}\n{result.stderr}")
        packages = _parse_packages_section(result.stdout)
        scenedetect_reported = packages.get("scenedetect", "")
        # Normalize both sides through display_version() so a raw __version__
        # like "0.7-dev0" matches the artifact-name VERSION of "0.7".
        if display_version(scenedetect_reported) != VERSION:
            fail(
                f"`scenedetect.exe version` reports scenedetect=={scenedetect_reported!r}, "
                f"expected {VERSION!r} (raw __version__ normalized)"
            )
        print(f"  scenedetect=={scenedetect_reported}")

        # 5b. No required dependency reports "Not Installed" - the bug fixed in c6a4145.
        broken = [name for name in REQUIRED_PACKAGES if packages.get(name) == NOT_INSTALLED]
        if broken:
            fail(
                "frozen .exe reports required packages as 'Not Installed' "
                "(commit c6a4145 regression):\n    " + ", ".join(broken)
            )
        opencv_present = [
            v for v in OPENCV_VARIANTS if packages.get(v, NOT_INSTALLED) != NOT_INSTALLED
        ]
        if not opencv_present:
            fail(
                "neither opencv-python nor opencv-python-headless reported a version "
                "(at least one must be present in the bundle)"
            )
        print(f"  opencv variant present: {opencv_present[0]}=={packages[opencv_present[0]]}")
        for name in REQUIRED_PACKAGES:
            print(f"  {name}=={packages[name]}")

        # 5c. Functional smoke: short detect-content run on the test video, if available.
        test_video = REPO_DIR / "tests" / "resources" / "testvideo.mp4"
        if test_video.is_file():
            out_dir = tmp_path / "smoke_output"
            out_dir.mkdir()
            print(f"  running detect-content on {test_video.name}...")
            result = subprocess.run(
                [
                    str(exe),
                    "-i",
                    str(test_video),
                    "-o",
                    str(out_dir),
                    "detect-content",
                    "time",
                    "-e",
                    "2s",
                    "list-scenes",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=tmp_path,
            )
            if result.returncode != 0:
                fail(
                    f"detect-content smoke run exited {result.returncode}\n"
                    f"  stdout: {result.stdout}\n  stderr: {result.stderr}"
                )
            outputs = list(out_dir.iterdir())
            if not outputs:
                fail("detect-content smoke run produced no output files")
            print(f"  detect-content OK ({len(outputs)} output file(s))")
        else:
            print(
                f"  (skipping detect-content smoke; {test_video.relative_to(REPO_DIR)} "
                "not present locally)"
            )

        # 5d. Clean error path: SCENEDETECT_DEBUG unset must produce a logger-formatted
        # error, not a Python traceback. Catches the __debug__ regression in c6a4145
        # (PyInstaller's -O bytecode makes `if __debug__:` always-False, so the wrong
        # branch fired and tracebacks leaked to end users).
        nonexistent = tmp_path / "definitely-not-a-video.mp4"
        clean_env = dict(os.environ)
        clean_env.pop("SCENEDETECT_DEBUG", None)
        result = subprocess.run(
            [str(exe), "-i", str(nonexistent), "detect-content"],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp_path,
            env=clean_env,
        )
        if result.returncode == 0:
            fail("error path: scenedetect.exe exited 0 on a missing input file")
        if "Traceback" in result.stderr or "Traceback" in result.stdout:
            fail(
                "error path: scenedetect.exe surfaced a Python traceback to the user "
                "(commit c6a4145 __debug__ regression):\n"
                f"  stderr: {result.stderr.strip()[:500]}"
            )
        print("  error path: clean exit (no traceback)")


def run_all_checks(staging: Path) -> None:
    """Entrypoint shared with `finalize_windows_dist.py`. Raises SystemExit on failure."""
    if not staging.is_dir():
        fail(f"staging directory not found: {staging}")
    print(f"Validating release artifacts in: {staging}")
    print(f"Expected version: {VERSION}")

    portable_zip, msi, manifest_path = check_filenames(staging)
    check_hashes(staging, portable_zip, msi, manifest_path)
    check_signatures(portable_zip, msi)
    sevenz = find_7zip()
    check_msi_zip_parity(portable_zip, msi, sevenz)
    check_frozen_exe(portable_zip)

    print()
    print("All validation checks passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=REPO_DIR / "dist" / "signed",
        help="Directory containing finalized artifacts (default: dist/signed/).",
    )
    args = parser.parse_args()
    run_all_checks(args.staging_dir.resolve())


if __name__ == "__main__":
    main()
