# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
"""Shared documentation version list loader for Sphinx (docs/conf.py) and website/build.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_DOC_LINK_RE = re.compile(r"^-\s*\[([^\]]+)\]\(/docs/([^/]+)/\)")


def load_doc_versions(
    repo_dir: Path, fallback_version: str = ""
) -> tuple[str, list[dict[str, Any]]]:
    """Load (latest_version, version_entries) from docs/LATEST_VERSION and website/pages/docs.md."""
    latest_file = repo_dir / "docs" / "LATEST_VERSION"
    latest_ver = (
        latest_file.read_text(encoding="utf-8").strip().lstrip("v")
        if latest_file.is_file()
        else fallback_version.lstrip("v")
    )

    stable_slugs: list[str] = []
    legacy_slugs: list[str] = []
    docs_md = repo_dir / "website" / "pages" / "docs.md"
    if docs_md.is_file():
        section = ""
        for raw_line in docs_md.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                section = line[3:].strip().lower()
                continue
            match = _DOC_LINK_RE.match(line)
            if not match:
                continue
            slug = match.group(2).strip()
            if slug in {"latest", "head"}:
                continue
            if section == "legacy":
                legacy_slugs.append(slug)
            else:
                stable_slugs.append(slug)

    if not stable_slugs and latest_ver:
        stable_slugs = [latest_ver, "0.7"]
    if not legacy_slugs:
        legacy_slugs = ["0.6.7"]

    entries: list[dict[str, Any]] = [
        {
            "slug": "latest",
            "label": f"v{latest_ver} (latest)",
            "group": "channel",
            "same_layout": True,
        },
        {
            "slug": "head",
            "label": "dev (head)",
            "group": "channel",
            "same_layout": True,
        },
    ]
    for slug in stable_slugs:
        entries.append(
            {
                "slug": slug,
                "label": f"v{slug}",
                "group": "release",
                "same_layout": True,
            }
        )
    if legacy_slugs:
        latest_legacy = legacy_slugs[0]
        entries.append(
            {
                "slug": latest_legacy,
                "label": f"v{latest_legacy} (legacy)",
                "group": "legacy",
                "same_layout": False,
            }
        )
    return latest_ver, entries
