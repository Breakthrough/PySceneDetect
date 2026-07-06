#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://www.scenedetect.com/docs/         ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
#
"""Builds all three PySceneDetect distributions into dist/:

  - scenedetect-core: minimal dependencies (numpy only, no OpenCV variant declared,
    no console script) - built from the repo root pyproject.toml
  - scenedetect / scenedetect-headless: the same code plus an OpenCV variant, the
    CLI dependencies, and the `scenedetect` console script

All three are code-carrying packages built from the repo root, so they share the
same source, readme, and dynamic version. The scenedetect / scenedetect-headless
variants are produced by temporarily swapping packaging/variants/pyproject-<name>.toml
into the repo root (restored afterwards, even on failure).

Requires `build` (pip install build). Fails if dist/ ends up with any wheel/sdist
besides the six expected artifacts, so clear stale build artifacts from dist/ first.
(Other dist/ contents are ignored - e.g. dist/logo/ is tracked website assets.)
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

    original = PYPROJECT.read_text(encoding="utf-8")
    if 'name = "scenedetect-core"' not in original:
        raise SystemExit(
            "pyproject.toml is not the scenedetect-core baseline - likely left over "
            "from an interrupted build. Restore it (e.g. `git checkout pyproject.toml`) "
            "and re-run."
        )

    build()  # scenedetect-core from the unmodified repo root.
    try:
        for name in VARIANTS:
            variant = (ROOT / "packaging" / "variants" / f"pyproject-{name}.toml").read_text(
                encoding="utf-8"
            )
            assert f'name = "{name}"' in variant, f"unexpected package name in variant {name}"
            PYPROJECT.write_text(variant, encoding="utf-8")
            build()
    finally:
        PYPROJECT.write_text(original, encoding="utf-8")

    expected = set()
    for name in ("scenedetect-core", *VARIANTS):
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
