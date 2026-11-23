#
# Configuration file for the Sphinx documentation builder.
#
# Only the html and singlehtml builders are used.

# -- Path setup --------------------------------------------------------------

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("_ext"))

from doc_versions import load_doc_versions

from scenedetect import __version__ as scenedetect_version

_REPO_DIR = Path(__file__).resolve().parent.parent
_psd_latest_version, _psd_doc_versions = load_doc_versions(
    _REPO_DIR, fallback_version=scenedetect_version.split("-dev")[0]
)

# -- Project information -----------------------------------------------------

project = "PySceneDetect"
copyright = "2014, Brandon Castellano"
author = "Brandon Castellano"

version = scenedetect_version
release = scenedetect_version

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    "section_sidebar",  # docs/_ext: sidebar shows only the CLI or API section
]

autoclass_content = "both"
autodoc_member_order = "groupwise"
autodoc_typehints = "description"
autodoc_typehints_format = "short"

add_module_names = False
python_use_unqualified_type_names = True
# Sidebar entries for autodoc objects show the member name only (e.g. `process_frame()`
# instead of `AdaptiveDetector.process_frame()`) so they fit in the sidebar.
toc_object_entries_show_parents = "hide"

templates_path = ["_templates"]

# Treat bare single-backtick text (`scenedetect`, `ffmpeg`, parameter names in docstrings)
# as inline code literals instead of docutils' default italic <cite> title-reference role.
default_role = "literal"

source_suffix = ".rst"

root_doc = "index"

language = "en"

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

html_static_path = ["_static"]
html_css_files = ["pyscenedetect.css"]
html_favicon = "_static/favicon.ico"

# The section tree is long, so the search box goes above it.
html_sidebars = {"**": ["about.html", "searchbox.html", "navigation.html"]}

# -- Theme -------------------------------------------------

html_theme = "alabaster"
html_theme_options = {
    "page_width": "1080px",
    "sidebar_width": "255px",
    "show_relbar_bottom": True,
    "font_family": '"Noto Sans", "Segoe UI", system-ui, -apple-system, sans-serif',
    "head_font_family": '"Noto Sans", "Segoe UI", system-ui, -apple-system, sans-serif',
    "code_font_family": (
        '"JetBrains Mono", "Cascadia Code", "Cascadia Mono", "Consolas", ui-monospace, monospace'
    ),
}

html_context = {
    "psd_doc_versions": _psd_doc_versions,
    "psd_latest_version": _psd_latest_version,
}


# Options for docs/_ext/section_sidebar.py: toctree `:name:` in index.rst -> (show_on_root,
# depth for other pages in the section, depth for the current page). The Examples page spans
# both halves, so it is its own one-page section showing only its on-page headings.
section_sidebar_sections = {
    "clitoc": (True, 2, 3),
    "apitoc": (True, 2, 4),
    # Standalone page: omitted from the root sidebar, shows only the current page's headings.
    "reftoc": (False, 2, 2),
}
# The index page shows every labelled section; keep the API tree to page titles there (the
# CLI tree keeps its default depth of 2, which is only 12 entries).
section_sidebar_root_depth = {"apitoc": 1}

# What each page contributes to the sidebar when it is NOT the current page: glob patterns on
# the entry text ([] = page title only). The current page is always expanded in full.
section_sidebar_summary = {
    "api/common": ["FrameTimecode", "SceneList", "CutList"],
    "api/scene_manager": ["SceneManager", "get_scenes_from_cuts()"],
    "api/detector": ["SceneDetector"],
    "api/video_stream": ["VideoStream"],
    "api/stats_manager": ["StatsManager"],
    "api/backends": ["VideoStream*"],
    "api/platform": [],
    "api/migration_guide": [],
}
# Current-page depth overrides (the section default is 4): backends lists its classes but not
# their members, which are the same for every VideoStream; each detector's section already has
# the class name, so listing the class and its members again under it only repeats things.
section_sidebar_page_depth = {"api/backends": 3, "api/detectors": 2}
