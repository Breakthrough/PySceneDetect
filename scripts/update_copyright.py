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
"""One-shot rewrite of project copyright headers.

Replaces every ``Copyright (C) 2014-YYYY Brandon Castellano`` notice in the
repository with a single year. Source/test/script files are stamped with the
year of their first commit (per ``git log``); project-wide files (LICENSE,
README, build config, CLI ``--license`` text, etc.) get the project birth year.

Run from the repo root:

    python scripts/update_copyright.py            # rewrite in place
    python scripts/update_copyright.py --dry-run  # show what would change
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

PROJECT_BIRTH_YEAR = "2014"

# Files that represent the project as a whole and should always carry the
# project birth year, regardless of when their content was first committed.
PROJECT_LEVEL_FILES = {
    "LICENSE",
    "README.md",
    "THIRD-PARTY.md",
    "pyproject.toml",
    "setup.py",
    "docs/index.rst",
    "website/mkdocs.yml",
    "website/pages/copyright.md",
    "scenedetect/_cli/__init__.py",
    "dist/package-info.rst",
}

# Foreign-licensed files we never modify. The _thirdparty package's own
# __init__.py is excluded from this list — it carries the project header.
SKIP_PATHS = {
    "scenedetect/_thirdparty/simpletable.py",  # vendored from third party
}
SKIP_PREFIXES = ("scenedetect/_thirdparty/LICENSE-",)


def is_skipped(rel: str) -> bool:
    return rel in SKIP_PATHS or rel.startswith(SKIP_PREFIXES)


# Matches the standard PySceneDetect header line. Tolerates an optional comma
# after the year range (the website copyright page uses one) and the HTML-entity
# variant ``Copyright &copy;`` used in the rendered website footer.
RANGE_PATTERN = re.compile(r"Copyright (\(C\)|&copy;) 2014-\d{4}(,?) Brandon Castellano")

# The LICENSE file uses a single-year form with comma: "Copyright (C) 2024, Brandon Castellano".
LICENSE_PATTERN = re.compile(r"Copyright \(C\) \d{4}, Brandon Castellano")


def git_files() -> list[str]:
    """Return tracked + untracked-but-not-ignored files, deduplicated."""
    out = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], text=True
    )
    seen: set[str] = set()
    result: list[str] = []
    for line in out.splitlines():
        rel = line.strip()
        if rel and rel not in seen:
            seen.add(rel)
            result.append(rel)
    return result


def first_commit_year(path: str) -> str | None:
    """Return the four-digit year of the first commit that touched ``path``.

    We deliberately do **not** use ``--follow``: when a file is renamed or split
    out of an older module, ``--follow`` returns the original file's birth
    year, which mis-stamps the new file. The year-at-current-path is what we
    want for copyright purposes.
    """
    result = subprocess.run(
        ["git", "log", "--reverse", "--format=%aI", "--", path],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines[0][:4] if lines else None


def rewrite(path: Path, year: str) -> bool:
    """Replace the year-range header in ``path`` with ``year``. Returns True if changed."""
    text = path.read_text(encoding="utf-8")
    # Preserve the original "(C)" / "&copy;" form and any trailing comma.
    new_text = RANGE_PATTERN.sub(rf"Copyright \1 {year}\2 Brandon Castellano", text)
    if path.as_posix().endswith("LICENSE"):
        new_text = LICENSE_PATTERN.sub(f"Copyright (C) {year}, Brandon Castellano", new_text)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    changed: list[tuple[str, str]] = []

    for rel in git_files():
        if is_skipped(rel):
            continue
        path = repo_root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not RANGE_PATTERN.search(text) and rel != "LICENSE":
            continue

        if rel in PROJECT_LEVEL_FILES or rel == "LICENSE":
            year = PROJECT_BIRTH_YEAR
        else:
            year = first_commit_year(rel) or str(datetime.date.today().year)

        if args.dry_run:
            changed.append((rel, year))
            continue
        if rewrite(path, year):
            changed.append((rel, year))

    for rel, year in changed:
        print(f"{year}  {rel}")
    print(f"\n{len(changed)} file(s) {'would be' if args.dry_run else ''} updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
