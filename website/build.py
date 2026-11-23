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
"""Static site builder, link verifier, and preview server for scenedetect.com."""

from __future__ import annotations

import argparse
import html
import html.parser
import http.server
import json
import posixpath
import re
import shutil
import struct
import sys
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import jinja2
import markdown
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docs" / "_ext"))

from doc_versions import load_doc_versions  # type: ignore[import-not-found]

WEBSITE_DIR = Path(__file__).resolve().parent
REPO_DIR = WEBSITE_DIR.parent

SITE_URL = "https://www.scenedetect.com"
REPO_URL = "https://github.com/Breakthrough/PySceneDetect"
PYPI_URL = "https://pypi.org/project/scenedetect/"
DEFAULT_RELEASE_DATE = "November 8, 2026"
DEFAULT_DESCRIPTION = (
    "Fast, frame-accurate video scene detection and splitting tool in Python "
    "with a command-line interface and Python API."
)

PAGES_DIR = WEBSITE_DIR / "pages"
IMG_SRC_DIR = PAGES_DIR / "img"
THEME_DIR = WEBSITE_DIR / "theme"
BUILD_DIR = WEBSITE_DIR / "build"


@dataclass(frozen=True)
class PageSpec:
    """One page of the site.

    The sidebar shows `title`. The top bar shows `nav_label`, or `title` if `nav_label` is empty.
    """

    slug: str
    title: str
    nav_label: str = ""
    is_primary: bool = False
    description: str = DEFAULT_DESCRIPTION

    @property
    def label(self) -> str:
        return self.nav_label or self.title

    @property
    def is_home(self) -> bool:
        return self.slug == ""

    @property
    def src_name(self) -> str:
        return f"{self.slug or 'index'}.md"

    @property
    def url_path(self) -> str:
        return "/" if self.is_home else f"/{self.slug}/"

    @property
    def out_rel_path(self) -> Path:
        return Path("index.html") if self.is_home else Path(self.slug) / "index.html"


NAV_GROUPS: list[tuple[str, list[PageSpec]]] = [
    (
        "PySceneDetect",
        [
            PageSpec(
                "",
                "Home",
                is_primary=True,
                description=DEFAULT_DESCRIPTION,
            ),
            PageSpec(
                "features",
                "Features",
                is_primary=True,
                description=(
                    "Explore PySceneDetect features: five built-in scene detectors, "
                    "video splitting, still-frame previews, and timeline export formats."
                ),
            ),
            PageSpec(
                "download",
                "Download",
                is_primary=True,
                description=(
                    "Install PySceneDetect via pip, uv, pipx, Windows 64-bit MSI/ZIP builds, "
                    "or the official Docker container image."
                ),
            ),
            PageSpec(
                "changelog",
                "Changelog",
                description=(
                    "Release history, new features, bug fixes, and upgrade notes for PySceneDetect."
                ),
            ),
        ],
    ),
    (
        "Guides",
        [
            PageSpec(
                "docs",
                "Documentation Versions",
                description=(
                    "Browse stable, development, and legacy PySceneDetect CLI and Python API "
                    "reference manuals."
                ),
            ),
            PageSpec(
                "cli",
                "Command-Line Interface",
                "CLI",
                is_primary=True,
                description=(
                    "Get started with the scenedetect command-line interface: examples, "
                    "detectors, video splitting, config files, and threshold tuning."
                ),
            ),
            PageSpec(
                "api",
                "Python API",
                is_primary=True,
                description=(
                    "Learn how PySceneDetect's built-in detectors work and how to build "
                    "custom scene detectors using the Python API."
                ),
            ),
            PageSpec(
                "benchmarks",
                "Benchmarks",
                is_primary=True,
                description=(
                    "Accuracy benchmarks and parameter sweeps for PySceneDetect detectors "
                    "on BBC Planet Earth, AutoShot, and ClipShots datasets."
                ),
            ),
        ],
    ),
    (
        "Community",
        [
            PageSpec(
                "faq",
                "Frequently Asked Questions",
                "FAQ",
                is_primary=True,
                description=(
                    "Answers to common PySceneDetect questions on installation, OpenCV, "
                    "threshold tuning, variable frame rate video, and video splitting."
                ),
            ),
            PageSpec(
                "contributing",
                "Contributing & Support",
                "Contributing",
                description=(
                    "How to report bugs, contribute code, and support PySceneDetect development."
                ),
            ),
            PageSpec(
                "projects",
                "Projects & Research",
                "Projects",
                description=(
                    "Open-source projects, academic papers, and similar video shot-boundary "
                    "detection tools related to PySceneDetect."
                ),
            ),
            PageSpec(
                "copyright",
                "License & Copyright",
                "License",
                description=(
                    "PySceneDetect BSD 3-Clause license agreement and third-party software "
                    "licenses."
                ),
            ),
        ],
    ),
]

PAGES: list[PageSpec] = [page for _, group in NAV_GROUPS for page in group]
KNOWN_SLUGS: set[str] = {page.slug for page in PAGES}

# Legacy URLs merged into consolidated pages -> (target path, link label).
LEGACY_REDIRECTS: dict[str, tuple[str, str]] = {
    "gallery": ("/projects/#projects-using-pyscenedetect", "Projects & Research"),
    "literature": ("/projects/#research-and-literature", "Projects & Research"),
    "similar": ("/projects/#similar-programs", "Projects & Research"),
    "supporting": ("/contributing/#project-support-and-credits", "Contributing & Support"),
}

HERO_SNIPPETS: list[tuple[str, str, str, str, str]] = [
    (
        "python",
        "Python API",
        "AdaptiveDetector",
        "python",
        (
            "from scenedetect import (\n"
            "    detect, AdaptiveDetector, split_video_ffmpeg,\n"
            ")\n\n"
            "# Find scene cuts and split the video with ffmpeg\n"
            'scenes = detect("goldeneye.mp4", AdaptiveDetector())\n'
            'split_video_ffmpeg("goldeneye.mp4", scenes)\n'
        ),
    ),
    (
        "cli",
        "Command Line",
        "scenedetect",
        "bash",
        (
            "# Split a video at each detected cut\n"
            "scenedetect -i goldeneye.mp4 split-video\n\n"
            "# Export a CSV scene list, still frames, and an HTML report\n"
            "scenedetect -i goldeneye.mp4 list-scenes save-images save-html\n"
        ),
    ),
    (
        "docker",
        "Docker",
        "ghcr.io",
        "bash",
        (
            "# CLI, ffmpeg, mkvmerge, PyAV, and MoviePy in one container\n"
            'docker run --rm -v "$(pwd):/files" \\\n'
            "    ghcr.io/breakthrough/pyscenedetect \\\n"
            "    -i /files/goldeneye.mp4 split-video -o /files\n"
        ),
    ),
]

SPHINX_ABS_RE = re.compile(r"^/docs/(?:latest|head|\d+\.\d+(?:\.\d+)?)(?:/.*)?$")
IMG_PATH_RE = re.compile(r"^(?:\./|\.\./|/)*img/(.+)$")
ATTR_RE = re.compile(
    r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?"""
)
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")


@dataclass
class TocItem:
    """Right-hand 'On this page' anchor entry."""

    id: str
    title: str
    children: list[TocItem] = field(default_factory=list)


def strip_tags(fragment: str) -> str:
    """Remove HTML tags and unescape entities into collapsed plain text."""
    no_tags = re.sub(r"<[^>]+>", " ", fragment)
    unescaped = html.unescape(no_tags).replace("\xa0", " ")
    return re.sub(r"\s+", " ", unescaped).strip()


def get_image_dimensions(img_path: Path) -> tuple[int, int] | None:
    """Read intrinsic (width, height) in pixels for local PNG and SVG assets."""
    data = img_path.read_bytes()
    suffix = img_path.suffix.lower()

    if suffix == ".png" and len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)

    if suffix == ".svg":
        head_txt = data[:4096].decode("utf-8", errors="ignore")
        svg_match = re.search(r"<svg\b[^>]*>", head_txt, re.IGNORECASE | re.DOTALL)
        if svg_match:
            svg_tag = svg_match.group(0)
            w_px = _parse_svg_length(svg_tag, "width")
            h_px = _parse_svg_length(svg_tag, "height")
            if w_px and h_px:
                return w_px, h_px

    return None


def _parse_svg_length(svg_tag: str, attr_name: str) -> int | None:
    """Parse an SVG width/height attribute (px, pt, or unitless) to integer pixels."""
    match = re.search(
        rf'\b{attr_name}\s*=\s*["\']\s*([\d.]+)\s*(px|pt|)?\s*["\']',
        svg_tag,
        re.IGNORECASE,
    )
    if not match:
        return None
    val = float(match.group(1))
    if (match.group(2) or "").lower() == "pt":
        val *= 96.0 / 72.0
    return max(1, round(val))


def normalize_base_path(raw: str) -> str:
    """Normalize an optional URL base path (e.g. 'staging/' -> '/staging', '/' -> '')."""
    cleaned = raw.strip().strip("/")
    return f"/{cleaned}" if cleaned else ""


def rewrite_internal_href(href: str, base_path: str = "") -> str:
    """Normalize Markdown and relative internal links to site-root paths."""
    raw = href.strip()
    if not raw or raw.startswith(("#", *EXTERNAL_SCHEMES)):
        return href

    path_part, sep, frag = raw.partition("#")
    suffix = f"#{frag}" if sep else ""
    clean_path = path_part.split("?", 1)[0]

    if SPHINX_ABS_RE.match(clean_path):
        return href

    img_match = IMG_PATH_RE.match(clean_path)
    if img_match:
        return f"{base_path}/img/{img_match.group(1)}{suffix}"

    if clean_path.endswith(".md"):
        stem = posixpath.basename(clean_path)[:-3]
        if stem == "index":
            return f"{base_path}/{suffix}"
        if stem in KNOWN_SLUGS:
            return f"{base_path}/{stem}/{suffix}"
        if stem in LEGACY_REDIRECTS:
            target_path, _ = LEGACY_REDIRECTS[stem]
            return f"{base_path}{target_path}"

    slug_candidate = clean_path.strip("/")
    if slug_candidate in KNOWN_SLUGS:
        target = f"{base_path}/" if slug_candidate == "" else f"{base_path}/{slug_candidate}/"
        return f"{target}{suffix}"
    if slug_candidate in LEGACY_REDIRECTS:
        target_path, _ = LEGACY_REDIRECTS[slug_candidate]
        return f"{base_path}{target_path}"

    return href


def _parse_attrs(attr_str: str) -> list[tuple[str, str | None]]:
    """Parse HTML tag attributes preserving order."""
    attrs: list[tuple[str, str | None]] = []
    for match in ATTR_RE.finditer(attr_str):
        name = match.group(1)
        if match.group(2) is not None:
            val: str | None = match.group(2)
        elif match.group(3) is not None:
            val = match.group(3)
        elif match.group(4) is not None:
            val = match.group(4)
        else:
            val = None
        attrs.append((name, val))
    return attrs


def _format_attrs(attrs: list[tuple[str, str | None]]) -> str:
    """Serialize HTML tag attributes cleanly."""
    parts: list[str] = []
    for name, val in attrs:
        if val is None:
            parts.append(name)
        else:
            escaped = html.escape(html.unescape(val), quote=True)
            parts.append(f'{name}="{escaped}"')
    return (" " + " ".join(parts)) if parts else ""


def postprocess_html(
    rendered_html: str,
    img_dims: dict[str, tuple[int, int]],
    base_path: str = "",
) -> str:
    """Apply accessibility, CLS, code-block, table, and link transforms."""

    def _normalize_pre(match: re.Match[str]) -> str:
        attrs = _parse_attrs(match.group(1))
        if not any(k.lower() == "tabindex" for k, _ in attrs):
            attrs.append(("tabindex", "0"))
        inner = re.sub(r"^(\s*)<span></span>", r"\1", match.group(2), count=1)
        return f"<pre{_format_attrs(attrs)}>{inner}</pre>"

    out = re.sub(
        r"<pre\b([^>]*)>(.*?)</pre>", _normalize_pre, rendered_html, flags=re.DOTALL | re.IGNORECASE
    )

    out = _wrap_tables_with_regions(out)

    def _rewrite_anchor(match: re.Match[str]) -> str:
        attrs = _parse_attrs(match.group(1))
        new_attrs = [
            (
                k,
                rewrite_internal_href(v, base_path) if k.lower() == "href" and v is not None else v,
            )
            for k, v in attrs
        ]
        return f"<a{_format_attrs(new_attrs)}>"

    out = re.sub(r"<a\b([^>]*)>", _rewrite_anchor, out, flags=re.IGNORECASE)

    def _rewrite_img(match: re.Match[str]) -> str:
        attrs = _parse_attrs(match.group(1))
        attr_map = {k.lower(): v for k, v in attrs}
        src = attr_map.get("src") or ""
        local_img_name: str | None = None

        if src and not src.startswith(EXTERNAL_SCHEMES):
            clean_src = src.split("#", 1)[0].split("?", 1)[0]
            img_match = IMG_PATH_RE.match(clean_src)
            if img_match:
                local_img_name = img_match.group(1)
                src = f"{base_path}/img/{local_img_name}"

        rebuilt = [("src", src) if k.lower() == "src" else (k, v) for k, v in attrs]
        filled = {k.lower() for k, v in attrs if v}

        if local_img_name and local_img_name in img_dims:
            w, h = img_dims[local_img_name]
            if "width" not in filled:
                rebuilt.append(("width", str(w)))
            if "height" not in filled:
                rebuilt.append(("height", str(h)))

        if "loading" not in filled and attr_map.get("fetchpriority") != "high":
            rebuilt.append(("loading", "lazy"))

        return f"<img{_format_attrs(rebuilt)}>"

    return re.sub(r"<img\b([^>]*?)\s*/?>", _rewrite_img, out, flags=re.IGNORECASE)


def _upgrade_table_semantics(table_html: str) -> str:
    """Ensure <th scope='col'> semantics inside <thead>."""

    def _scope_thead(match: re.Match[str]) -> str:
        def _add_col_scope(th_match: re.Match[str]) -> str:
            attrs = _parse_attrs(th_match.group(1))
            if not any(k.lower() == "scope" for k, _ in attrs):
                attrs.insert(0, ("scope", "col"))
            return f"<th{_format_attrs(attrs)}>"

        return re.sub(r"<th\b([^>]*)>", _add_col_scope, match.group(0), flags=re.IGNORECASE)

    return re.sub(
        r"<thead\b[^>]*>.*?</thead>",
        _scope_thead,
        table_html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _wrap_tables_with_regions(html_text: str) -> str:
    """Wrap every <table> in an accessible scrollable .table-wrapper named by preceding heading."""
    token_re = re.compile(
        r"(<h[1-6]\b[^>]*>.*?</h[1-6]>)|(<table\b[^>]*>.*?</table>)",
        re.DOTALL | re.IGNORECASE,
    )
    last_heading = "Data table"
    pieces: list[str] = []
    pos = 0

    for match in token_re.finditer(html_text):
        pieces.append(html_text[pos : match.start()])
        pos = match.end()
        if match.group(1):
            h_text = strip_tags(match.group(1))
            if h_text:
                last_heading = h_text
            pieces.append(match.group(1))
        elif match.group(2):
            upgraded = _upgrade_table_semantics(match.group(2))
            label = html.escape(last_heading, quote=True)
            pieces.append(
                f'<div tabindex="0" role="region" aria-label="{label}" '
                f'class="table-wrapper">{upgraded}</div>'
            )

    pieces.append(html_text[pos:])
    return "".join(pieces)


def extract_toc(html_text: str) -> list[TocItem]:
    """Extract h2 and nested h3 headings from final article HTML for 'On this page'."""
    items: list[TocItem] = []
    heading_re = re.compile(r"<h([23])\b([^>]*)>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
    for match in heading_re.finditer(html_text):
        level = int(match.group(1))
        attrs = dict(_parse_attrs(match.group(2)))
        hid = attrs.get("id") or ""
        title = strip_tags(match.group(3))
        if not hid or not title:
            continue
        if level == 2 or not items:
            items.append(TocItem(id=hid, title=title))
        else:
            items[-1].children.append(TocItem(id=hid, title=title))
    return items


def extract_search_entries(
    spec: PageSpec,
    html_text: str,
    base_path: str = "",
) -> list[dict[str, str]]:
    """Chunk a page's HTML by h1/h2/h3 sections for instant client-side jump search."""
    heading_re = re.compile(r"<h([123])\b([^>]*)>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
    matches = list(heading_re.finditer(html_text))
    entries: list[dict[str, str]] = []
    page_url = f"{base_path}{spec.url_path}"

    for idx, match in enumerate(matches):
        level = int(match.group(1))
        attrs = dict(_parse_attrs(match.group(2)))
        hid = attrs.get("id") or ""
        sec_title = strip_tags(match.group(3)) or spec.title
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(html_text)
        chunk_text = strip_tags(html_text[start:end])
        url = page_url if (level == 1 and idx == 0) or not hid else f"{page_url}#{hid}"
        entries.append(
            {
                "title": spec.title,
                "section": sec_title,
                "url": url,
                "text": chunk_text[:600],
            }
        )

    if spec.is_home:
        entries.insert(
            0,
            {
                "title": "Home",
                "section": "Overview & Quickstart",
                "url": f"{base_path}/",
                "text": (
                    "Fast, frame-accurate scene cut detection for video. Detect fast cuts and "
                    "fades. pip install scenedetect AdaptiveDetector ContentDetector HashDetector "
                    "HistogramDetector ThresholdDetector split-video ffmpeg mkvmerge Docker."
                ),
            },
        )

    return entries


def render_hero_tabs() -> list[dict[str, str]]:
    """Pre-highlight the 3 interactive quickstart code tabs with Pygments."""
    formatter = HtmlFormatter(nowrap=True)
    tabs: list[dict[str, str]] = []
    for tab_id, label, hint, lang, code in HERO_SNIPPETS:
        highlighted = highlight(code, get_lexer_by_name(lang), formatter).rstrip("\n")
        tabs.append(
            {
                "id": tab_id,
                "label": label,
                "hint": hint,
                "html": highlighted,
            }
        )
    return tabs


def load_release_date(pages_dir: Path, version: str) -> str:
    """Parse the release date for `version` from changelog.md, falling back to default."""
    changelog_path = pages_dir / "changelog.md"
    if changelog_path.is_file() and version:
        pattern = re.compile(
            rf"^###\s+(?:PySceneDetect\s+)?{re.escape(version)}\s*\(([^)]+)\)",
            re.MULTILINE,
        )
        match = pattern.search(changelog_path.read_text(encoding="utf-8"))
        if match:
            candidate = match.group(1).strip()
            try:
                datetime.strptime(candidate, "%B %d, %Y")
                return candidate
            except ValueError:
                pass
    return DEFAULT_RELEASE_DATE


def _validate_out_dir(out_dir: Path) -> Path:
    """Resolve `out_dir` and refuse to overwrite protected repository directories."""
    resolved_out = out_dir.resolve()
    protected = {
        REPO_DIR.resolve(),
        WEBSITE_DIR.resolve(),
        PAGES_DIR.resolve(),
        THEME_DIR.resolve(),
    }
    if resolved_out in protected or any(resolved_out in p.parents for p in protected):
        raise ValueError(f"Refusing to overwrite protected directory: {resolved_out}")
    return resolved_out


def build_site(base_path: str = "", out_dir: Path = BUILD_DIR) -> None:
    """Cleanly generate out_dir from website/pages/ and website/theme/."""
    base_path = normalize_base_path(base_path)
    out_dir = _validate_out_dir(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assets_out = out_dir / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(THEME_DIR / "site.css", assets_out / "site.css")
    shutil.copy2(THEME_DIR / "site.js", assets_out / "site.js")

    shutil.copytree(IMG_SRC_DIR, out_dir / "img")
    shutil.copy2(IMG_SRC_DIR / "favicon.ico", out_dir / "favicon.ico")

    img_dims: dict[str, tuple[int, int]] = {}
    for img_file in IMG_SRC_DIR.iterdir():
        if img_file.is_file():
            dims = get_image_dimensions(img_file)
            if dims is not None:
                img_dims[img_file.name] = dims

    latest_ver, doc_versions = load_doc_versions(REPO_DIR)
    release_date = load_release_date(PAGES_DIR, latest_ver)
    rel_dt = datetime.strptime(release_date, "%B %d, %Y")

    site_ctx = {
        "url": SITE_URL,
        "base_path": base_path,
        "repo_url": REPO_URL,
        "pypi_url": PYPI_URL,
        "version": f"v{latest_ver}",
        "version_num": latest_ver,
        "win64_msi_url": (
            f"{REPO_URL}/releases/download/v{latest_ver}/PySceneDetect-{latest_ver}-win64.msi"
        ),
        "win64_zip_url": (
            f"{REPO_URL}/releases/download/v{latest_ver}/PySceneDetect-{latest_ver}-win64.zip"
        ),
        "release_date_short": f"{rel_dt:%b} {rel_dt.day}, {rel_dt.year}",
    }

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(THEME_DIR)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    base_tmpl = env.get_template("base.html")
    home_tmpl = env.get_template("home.html")
    not_found_tmpl = env.get_template("404.html")

    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "attr_list",
            "admonition",
            "sane_lists",
        ],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "codehilite"},
        },
    )

    hero_tabs = render_hero_tabs()
    hero_snippets = {tab["id"]: tab for tab in hero_tabs}
    search_index: list[dict[str, str]] = []

    for idx, spec in enumerate(PAGES):
        md.reset()
        raw_md = (PAGES_DIR / spec.src_name).read_text(encoding="utf-8")
        processed_html = postprocess_html(md.convert(raw_md), img_dims, base_path)
        toc_items = extract_toc(processed_html)
        search_index.extend(extract_search_entries(spec, processed_html, base_path))

        prev_spec = PAGES[idx - 1] if idx > 0 else None
        next_spec = PAGES[idx + 1] if idx + 1 < len(PAGES) else None

        page_ctx = {
            "html_title": (
                "PySceneDetect | Video Scene Cut Detection & Analysis"
                if spec.is_home
                else f"{spec.title} | PySceneDetect"
            ),
            "description": spec.description,
            "slug": spec.slug,
            "canonical_path": spec.url_path,
            "content": Markup(processed_html),
            "toc": toc_items,
            "prev_page": (
                {"title": prev_spec.title, "href": f"{base_path}{prev_spec.url_path}"}
                if prev_spec
                else None
            ),
            "next_page": (
                {"title": next_spec.title, "href": f"{base_path}{next_spec.url_path}"}
                if next_spec
                else None
            ),
            "edit_url": f"{REPO_URL}/blob/main/website/pages/{spec.src_name}",
        }

        tmpl = home_tmpl if spec.is_home else base_tmpl
        rendered_page = tmpl.render(
            site=site_ctx,
            page=page_ctx,
            hero_tabs=hero_tabs,
            hero_snippets=hero_snippets,
            nav_groups=NAV_GROUPS,
            pages=PAGES,
        )

        out_file = out_dir / spec.out_rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(rendered_page, encoding="utf-8")

    rendered_404 = not_found_tmpl.render(
        site=site_ctx,
        page={
            "html_title": "Page Not Found | PySceneDetect",
            "description": DEFAULT_DESCRIPTION,
            "slug": None,
            "canonical_path": None,
        },
        nav_groups=NAV_GROUPS,
        pages=PAGES,
    )
    (out_dir / "404.html").write_text(rendered_404, encoding="utf-8")

    for old_slug, (target_path, target_label) in LEGACY_REDIRECTS.items():
        href = f"{base_path}{target_path}"
        canonical = f"{SITE_URL}{target_path.split('#', 1)[0]}"
        safe_href = html.escape(href, quote=True)
        safe_canonical = html.escape(canonical, quote=True)
        safe_label = html.escape(target_label)
        stub = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            "  <title>Redirecting | PySceneDetect</title>\n"
            '  <meta name="robots" content="noindex">\n'
            f'  <link rel="canonical" href="{safe_canonical}">\n'
            f'  <meta http-equiv="refresh" content="0; url={safe_href}">\n'
            "</head>\n"
            "<body>\n"
            "  <h1>Redirecting...</h1>\n"
            f'  <p>This page moved to <a href="{safe_href}">{safe_label}</a>.</p>\n'
            "</body>\n"
            "</html>\n"
        )
        stub_file = out_dir / old_slug / "index.html"
        stub_file.parent.mkdir(parents=True, exist_ok=True)
        stub_file.write_text(stub, encoding="utf-8")

    (out_dir / "search_index.json").write_text(
        json.dumps(search_index, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
    (out_dir / "versions.json").write_text(
        json.dumps(
            {"latest": latest_ver, "versions": doc_versions},
            ensure_ascii=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *(f"  <url><loc>{SITE_URL}{spec.url_path}</loc></url>" for spec in PAGES),
        "</urlset>",
    ]
    (out_dir / "sitemap.xml").write_text("\n".join(sitemap_lines) + "\n", encoding="utf-8")


class _PageInspector(html.parser.HTMLParser):
    """Collect element IDs, headings, links, and asset references from built HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.h1_count = 0
        self.links: list[str] = []
        self.assets: list[tuple[str, str]] = []
        self.imgs_missing_alt: list[str] = []
        self.imgs_missing_dims: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        elem_id = attr_dict.get("id")
        if elem_id:
            self.ids.add(elem_id)
        if tag == "h1":
            self.h1_count += 1
        if tag == "a":
            href = attr_dict.get("href")
            if href is not None:
                self.links.append(href)
        elif tag == "img":
            src = attr_dict.get("src") or ""
            if src:
                self.assets.append(("img", src))
            if "alt" not in attr_dict or attr_dict["alt"] is None:
                self.imgs_missing_alt.append(src or "<img without src>")
            if (
                src
                and not src.startswith(EXTERNAL_SCHEMES)
                and (not attr_dict.get("width") or not attr_dict.get("height"))
            ):
                self.imgs_missing_dims.append(src)
        elif tag == "link":
            rel = (attr_dict.get("rel") or "").lower()
            href = attr_dict.get("href")
            if href and rel != "canonical":
                self.assets.append(("link", href))
        elif tag == "script":
            src = attr_dict.get("src")
            if src:
                self.assets.append(("script", src))


def _strip_base_path(site_path: str, base_path: str) -> str | None:
    """Strip base_path prefix from a resolved site path, or return None if missing."""
    if not base_path:
        return site_path
    if site_path == base_path:
        return "/"
    prefix = f"{base_path}/"
    if site_path.startswith(prefix):
        return site_path[len(base_path) :]
    return None


def verify_build(base_path: str = "", build_dir: Path = BUILD_DIR) -> list[str]:
    """Strictly validate routes, internal links, #fragment anchors, and asset paths."""
    base_path = normalize_base_path(base_path)
    errors: list[str] = []
    required_files = [
        *(build_dir / spec.out_rel_path for spec in PAGES),
        *(build_dir / slug / "index.html" for slug in LEGACY_REDIRECTS),
        build_dir / "404.html",
        build_dir / "assets" / "site.css",
        build_dir / "assets" / "site.js",
        build_dir / "favicon.ico",
        build_dir / "search_index.json",
        build_dir / "versions.json",
        build_dir / "sitemap.xml",
    ]
    for req in required_files:
        if not req.is_file():
            errors.append(f"Missing expected output file: {req}")

    html_files = sorted(build_dir.rglob("*.html"))
    inspectors: dict[Path, _PageInspector] = {}
    for html_file in html_files:
        parser = _PageInspector()
        parser.feed(html_file.read_text(encoding="utf-8"))
        inspectors[html_file] = parser
        rel_label = html_file.relative_to(build_dir).as_posix()
        if parser.h1_count != 1:
            errors.append(f"{rel_label}: expected exactly 1 <h1>, found {parser.h1_count}")
        for bad_img in parser.imgs_missing_alt:
            errors.append(f"{rel_label}: <img> missing alt attribute ({bad_img})")
        for bad_dim in parser.imgs_missing_dims:
            errors.append(f"{rel_label}: local <img> missing width/height ({bad_dim})")

    for html_file, parser in inspectors.items():
        rel_file = html_file.relative_to(build_dir)
        rel_label = rel_file.as_posix()
        parent_posix = rel_file.parent.as_posix()
        base_url_dir = f"{base_path}/" if parent_posix == "." else f"{base_path}/{parent_posix}/"

        for href in parser.links:
            if not href or href.startswith(EXTERNAL_SCHEMES):
                continue
            if href.startswith("#"):
                frag = urllib.parse.unquote(href[1:])
                if frag and frag not in parser.ids:
                    errors.append(f"{rel_label}: broken same-page anchor '{href}'")
                continue

            path_part, sep, frag = href.partition("#")
            path_part = path_part.split("?", 1)[0]
            site_path = _resolve_site_path(base_url_dir, path_part)

            if SPHINX_ABS_RE.match(site_path):
                continue

            local_site_path = _strip_base_path(site_path, base_path)
            if local_site_path is None:
                errors.append(
                    f"{rel_label}: internal link '{href}' missing base_path '{base_path}' "
                    f"(resolved to '{site_path}')"
                )
                continue

            target_file = _map_site_path_to_file(local_site_path, build_dir)
            if target_file is None or not target_file.is_file():
                errors.append(
                    f"{rel_label}: broken internal link '{href}' (resolved to '{site_path}')"
                )
                continue

            if sep and frag and target_file in inspectors:
                decoded_frag = urllib.parse.unquote(frag)
                if decoded_frag not in inspectors[target_file].ids:
                    target_label = target_file.relative_to(build_dir).as_posix()
                    errors.append(
                        f"{rel_label}: broken fragment '{href}' "
                        f"(id '{decoded_frag}' not found in {target_label})"
                    )

        for tag_name, src in parser.assets:
            if src.startswith(EXTERNAL_SCHEMES):
                continue
            clean_src = src.split("#", 1)[0].split("?", 1)[0]
            site_path = _resolve_site_path(base_url_dir, clean_src)
            local_site_path = _strip_base_path(site_path, base_path)
            if local_site_path is None:
                errors.append(
                    f"{rel_label}: <{tag_name}> asset '{src}' missing base_path '{base_path}' "
                    f"(resolved to '{site_path}')"
                )
                continue
            target_file = build_dir / local_site_path.lstrip("/")
            if not target_file.is_file():
                errors.append(
                    f"{rel_label}: missing <{tag_name}> asset '{src}' (resolved to '{site_path}')"
                )

    return errors


def _resolve_site_path(base_url_dir: str, path_part: str) -> str:
    """Resolve a root-relative or page-relative URL path into a normalized site path."""
    if path_part.startswith("/"):
        norm = posixpath.normpath(path_part)
        if path_part.endswith("/") and not norm.endswith("/"):
            norm += "/"
        return norm

    joined = posixpath.normpath(posixpath.join(base_url_dir, path_part))
    is_dir_ref = path_part in {".", "./", "..", "../"} or path_part.endswith("/")
    if is_dir_ref and not joined.endswith("/"):
        joined += "/"
    return joined


def _map_site_path_to_file(site_path: str, build_dir: Path = BUILD_DIR) -> Path | None:
    """Map a normalized site path (e.g. '/cli/') to an existing file path in build_dir."""
    stripped = site_path.lstrip("/")
    if site_path.endswith("/"):
        return (build_dir / stripped / "index.html") if stripped else (build_dir / "index.html")
    candidate = build_dir / stripped
    if candidate.is_dir():
        return candidate / "index.html"
    return candidate


def serve_site(port: int, base_path: str = "", build_dir: Path = BUILD_DIR) -> None:
    """Serve build_dir locally on 127.0.0.1:<port> with custom 404.html handling."""
    base_path = normalize_base_path(base_path)

    class PreviewHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(build_dir), **kwargs)

        def do_GET(self) -> None:
            if base_path and self.path in {"/", base_path}:
                self.send_response(302)
                self.send_header("Location", f"{base_path}/")
                self.end_headers()
                return
            if base_path:
                parsed = urllib.parse.urlsplit(self.path)
                local_path = _strip_base_path(parsed.path, base_path)
                if local_path is None:
                    self.send_error(404)
                    return
                self.path = urllib.parse.urlunsplit(
                    ("", "", local_path, parsed.query, parsed.fragment)
                )
            super().do_GET()

        def send_error(
            self,
            code: int,
            message: str | None = None,
            explain: str | None = None,
        ) -> None:
            not_found_path = build_dir / "404.html"
            if code == 404 and not_found_path.is_file():
                body = not_found_path.read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().send_error(code, message, explain)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)
    mount = f"{base_path}/" if base_path else "/"
    print(f"Serving {build_dir} at http://127.0.0.1:{port}{mount} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped preview server.")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for building, strictly validating, and serving scenedetect.com."""
    parser = argparse.ArgumentParser(description="Build the PySceneDetect static website.")
    parser.add_argument(
        "--base-path",
        default="",
        help="Optional URL path prefix (e.g. '/staging' for scenedetect.com/staging/).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=BUILD_DIR,
        help="Output directory for generated static files (default: website/build).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Verify all expected routes, internal links, #fragment anchors, and assets.",
    )
    parser.add_argument(
        "--serve",
        nargs="?",
        const=8000,
        type=int,
        metavar="PORT",
        help="Build and serve output locally on 127.0.0.1:PORT (default: 8000).",
    )
    args = parser.parse_args(argv)
    base_path = normalize_base_path(args.base_path)
    out_dir = args.out_dir.resolve()

    build_site(base_path=base_path, out_dir=out_dir)
    prefix_note = f" (base_path={base_path})" if base_path else ""
    print(f"Built {len(PAGES)} pages + 404 + search index into {out_dir}{prefix_note}")

    if args.strict:
        errors = verify_build(base_path=base_path, build_dir=out_dir)
        if errors:
            for err in errors:
                print(f"[STRICT ERROR] {err}", file=sys.stderr)
            print(f"Strict check failed with {len(errors)} error(s).", file=sys.stderr)
            return 1
        print("Strict verification passed (all routes, anchors, and assets verified).")

    if args.serve is not None:
        serve_site(args.serve, base_path=base_path, build_dir=out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
