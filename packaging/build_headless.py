#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://www.scenedetect.com/docs/         ]
#
# Copyright (C) 2014 Brandon Castellano <http://www.bcastell.com>.
#

# Generates the headless variant by mutating pyproject.toml in place.
# Run this before `python -m build` to produce scenedetect-headless artifacts.
# Modifies pyproject.toml in place; revert via `git checkout pyproject.toml`.

from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

content = PYPROJECT.read_text()

assert 'name = "scenedetect"' in content
content = content.replace('name = "scenedetect"', 'name = "scenedetect-headless"', 1)

assert '"opencv-python",' in content
content = content.replace('"opencv-python",', '"opencv-python-headless",', 1)

PYPROJECT.write_text(content)

print("Generated headless pyproject.toml.")
