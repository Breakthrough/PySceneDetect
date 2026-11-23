# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
"""Shared documentation version list loader for Sphinx (docs/conf.py) and website/build.py."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_DOC_LINK_RE = re.compile(r"^-\s*\[([^\]]+)\]\(/docs/([^/]+)/\)")


def _entry(slug: str, label: str, group: str) -> dict[str, Any]:
    """One version entry. Only the legacy group uses a different page layout."""
    return {"slug": slug, "label": label, "group": group, "same_layout": group != "legacy"}


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

    entries = [
        _entry("latest", f"v{latest_ver} (latest)", "channel"),
        _entry("head", "dev (head)", "channel"),
    ]
    # Avoid duplicating `latest` as a separate row when it is the current stable release.
    entries += [_entry(slug, f"v{slug}", "release") for slug in stable_slugs if slug != latest_ver]
    if legacy_slugs:
        entries.append(_entry(legacy_slugs[0], f"v{legacy_slugs[0]} (legacy)", "legacy"))
    return latest_ver, entries
