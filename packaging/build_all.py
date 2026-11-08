#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://www.scenedetect.com/docs/         ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
#
"""Builds the two published PySceneDetect distributions into dist/:

  - scenedetect / scenedetect-headless: the full package (code, an OpenCV variant,
    the CLI dependencies, and the `scenedetect` console script), produced by
    temporarily swapping packaging/variants/pyproject-<name>.toml into the repo
    root (restored afterwards, even on failure)

Both are standalone code-carrying packages built from the repo root, so they share the same source,
readme, and dynamic version. The root pyproject.toml is the `scenedetect` configuration plus the
development extras, and is swapped out here so the published metadata comes from the variant files.

*NOTE*: No shared "core" dist exists anymore. scenedetect-core 0.7.1 was briefly published and then
yanked. Layering packages over a shared core dist is unsafe with pip (co-installed variants
share file ownership, and converting an existing name to a metapackage breaks in-place upgrades).
See https://scenedetect.com/issues/558 for details.

Requires `build` (pip install build). Fails if dist/ ends up with any wheel/sdist besides the four
expected artifacts, so clear stale build artifacts from dist/ first.
"""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PYPROJECT = ROOT / "pyproject.toml"
VARIANTS = ("scenedetect", "scenedetect-headless")


def get_version() -> str:
    """Parse scenedetect.__version__ without importing (avoids the cv2 guard),
    normalized per PEP 440 (e.g. 0.7.1-dev0 -> 0.7.1.dev0)."""
    source = (ROOT / "scenedetect" / "__init__.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "__version__" for target in node.targets
        ):
            assert isinstance(node.value, ast.Constant)
            return str(node.value.value).replace("-", ".")
    raise SystemExit("Could not find __version__ in scenedetect/__init__.py")


def build() -> None:
    subprocess.check_call([sys.executable, "-m", "build", "--outdir", str(DIST), str(ROOT)])


def main() -> None:
    version = get_version()

    variants = {
        name: (ROOT / "packaging" / "variants" / f"pyproject-{name}.toml").read_text(
            encoding="utf-8"
        )
        for name in VARIANTS
    }
    for name, variant in variants.items():
        assert f'name = "{name}"' in variant, f"unexpected package name in variant {name}"

    original = PYPROJECT.read_text(encoding="utf-8")
    # The root config is the `scenedetect` package plus the development extras, so it
    # must name `scenedetect` and must not be a variant file left over from an
    # interrupted build (the swap below is restored in `finally`, but a crash can skip it).
    if 'name = "scenedetect"' not in original or original in variants.values():
        raise SystemExit(
            "pyproject.toml is not the development baseline - likely left over from an "
            "interrupted build. Restore it (e.g. `git checkout pyproject.toml`) and re-run."
        )

    try:
        for variant in variants.values():
            PYPROJECT.write_text(variant, encoding="utf-8")
            build()
    finally:
        PYPROJECT.write_text(original, encoding="utf-8")

    expected = set()
    for name in VARIANTS:
        normalized = name.replace("-", "_")
        expected.add(f"{normalized}-{version}.tar.gz")
        expected.add(f"{normalized}-{version}-py3-none-any.whl")
    # Only validate build artifacts: dist/ also holds tracked files (e.g. dist/logo/).
    actual = {
        path.name
        for path in DIST.iterdir()
        if path.is_file() and (path.name.endswith(".whl") or path.name.endswith(".tar.gz"))
    }
    if actual != expected:
        raise SystemExit(
            f"dist/ mismatch (stale files or failed build?)\n"
            f"  missing: {sorted(expected - actual)}\n"
            f"  unexpected: {sorted(actual - expected)}"
        )
    print(f"Built {len(expected)} artifacts for version {version}:")
    for filename in sorted(expected):
        print(f"  dist/{filename}")


if __name__ == "__main__":
    main()
