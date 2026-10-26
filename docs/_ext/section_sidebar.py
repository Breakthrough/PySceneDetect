# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
"""Sphinx extension: show only the current section (e.g. CLI or API) in the sidebar.

The root document has one named toctree per section. For every page inside a section, the
sidebar template gets ``section_toctree()``, which renders that section's toctree fully
expanded (other pages to the section's ``maxdepth``, the current page to ``current_maxdepth``),
plus ``sidebar_section`` and ``sidebar_sections`` for a switch between sections. The root
document itself renders every labelled section's tree, each pruned to
``section_sidebar_root_depth`` (by default the section's ``maxdepth``). Pages in no section
(genindex, search, py-modindex) and the singlehtml builder fall back to the regular global
toctree.

Configure with ``section_sidebar_sections`` in conf.py::

    section_sidebar_sections = {
        "clitoc": ("CLI", "cli", 2, 2),  # toctree name: (label, landing doc, depth, cur depth)
        "reftoc": (None, None, 2, 2),  # no label: every page in the section is a small link
    }
    section_sidebar_root_depth = {"apitoc": 1}  # on the root document: page titles only

A section whose label is ``None`` is not part of the switch; the template gets its pages as
``sidebar_section_docs[name]`` (a list of ``(title, docname)``) and draws them as a row of
smaller links. Its tree is only drawn on its own pages, and then holds just the current page's
headings, since the row already lists the pages.

``section_sidebar_summary`` trims what a page contributes to the tree when it is NOT the
current page: only entries (at any depth) whose text matches one of the glob patterns are
kept, together with the headings above them; an empty list keeps just the page title.
``section_sidebar_page_depth`` overrides the section's current-page depth for one page::

    section_sidebar_summary = {
        "api/backends": ["VideoStream*"],  # glob on the entry text
        "api/platform": [],  # title only
    }
    section_sidebar_page_depth = {"api/backends": 3}  # classes, but not their members
"""

import fnmatch

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.environment.adapters.toctree import TocTree
from sphinx.util import logging

logger = logging.getLogger(__name__)

_LEVEL_PREFIX = "toctree-l"
# Depth the section tree is resolved to before pruning; deeper than any configured depth.
_RESOLVE_DEPTH = 6


def _section_toctree_node(app: Sphinx, pagename: str) -> addnodes.toctree | None:
    """Root-doc toctree node whose entries contain `pagename` or one of its ancestors."""
    env = app.env
    if pagename not in env.all_docs:
        return None
    lineage = {pagename, *TocTree(env).get_toctree_ancestors(pagename)}
    for node in env.get_doctree(env.config.root_doc).findall(addnodes.toctree):
        if lineage.intersection(node["includefiles"]):
            return node
    return None


def _entry_target(item: nodes.list_item) -> str:
    """URI a toctree entry links to (page-relative, as rendered), without the anchor."""
    ref = next(item.findall(nodes.reference), None)
    return ref.get("refuri", "").split("#", 1)[0] if ref is not None else ""


def _drop_sublists(item: nodes.list_item) -> None:
    item.children = [c for c in item.children if not isinstance(c, nodes.bullet_list)]


def _entry_text(item: nodes.list_item) -> str:
    """Text of the entry itself (its first paragraph), not of the entries nested under it."""
    return item[0].astext() if len(item) else ""


def _apply_summary(top: nodes.list_item, patterns: list[str]) -> bool:
    """Keep only the entries under `top` that match `patterns`, plus the headings above them.

    Returns False if a non-empty pattern list matched nothing.
    """
    matches = [
        item
        for item in top.findall(nodes.list_item)
        if item is not top and any(fnmatch.fnmatchcase(_entry_text(item), p) for p in patterns)
    ]
    keep: set[int] = set()
    for item in matches:
        _drop_sublists(item)
        node = item
        while node is not top:
            keep.add(id(node))
            node = node.parent
    for item in list(top.findall(nodes.list_item)):
        if item is not top and id(item) not in keep and item.parent is not None:
            item.parent.remove(item)
    for empty in [bl for bl in top.findall(nodes.bullet_list) if not bl.children]:
        empty.parent.remove(empty)
    return bool(matches) or not patterns


def _entry_level(item: nodes.list_item) -> int | None:
    return next(
        (int(c[len(_LEVEL_PREFIX) :]) for c in item["classes"] if c.startswith(_LEVEL_PREFIX)),
        None,
    )


def _prune_depth(top: nodes.list_item, maxdepth: int) -> None:
    """Drop the sub-lists of every entry under `top` at `maxdepth` or deeper."""
    for item in list(top.findall(nodes.list_item)):
        level = _entry_level(item)
        if level is not None and level >= maxdepth:
            _drop_sublists(item)


def _keep_current_headings(tree: nodes.Element) -> None:
    """Replace the section's page list with the headings of the current page, one level up.

    For sections without a switch label: the link row under the switch already lists their
    pages, so the tree repeats neither the current page's title nor its siblings.
    """
    for top in list(tree.findall(nodes.list_item)):
        if "toctree-l1" not in top["classes"] or not top.get("iscurrent"):
            continue
        pages = top.parent
        headings = next((c for c in top.children if isinstance(c, nodes.bullet_list)), None)
        if headings is None:
            pages.parent.remove(pages)
            return
        for item in headings.findall(nodes.list_item):
            level = _entry_level(item)
            if level is not None:
                item["classes"].remove(f"{_LEVEL_PREFIX}{level}")
                item["classes"].append(f"{_LEVEL_PREFIX}{level - 1}")
        pages.replace_self(headings)
        return


def _prune_tree(
    tree: nodes.Element, maxdepth: int, current_maxdepth: int, summary: dict[str, list[str]]
) -> None:
    """Trim the resolved section tree to the configured depths.

    The current page is cut at `current_maxdepth`. Every other page is cut at `maxdepth`, or,
    if `summary` (keyed by rendered URI) has patterns for it, reduced to the matching entries
    (none for an empty list) plus the headings above them.
    """
    for top in list(tree.findall(nodes.list_item)):
        if "toctree-l1" not in top["classes"]:
            continue
        if top.get("iscurrent"):
            _prune_depth(top, current_maxdepth)
            continue
        patterns = summary.get(_entry_target(top))
        if patterns is None:
            _prune_depth(top, maxdepth)
        elif not _apply_summary(top, patterns):
            logger.warning(
                "section_sidebar_summary: no entry of %s matches %r",
                _entry_target(top),
                patterns,
                once=True,
            )


def _add_section_toctree(app: Sphinx, pagename: str, templatename, context, doctree) -> None:
    sections = app.config.section_sidebar_sections
    if app.builder.name == "singlehtml":
        # Everything is one page: the switch would link to itself, so hide it.
        sections = {}
    node = _section_toctree_node(app, pagename) if sections else None
    names = node.parent.get("names", []) if node is not None else []
    section = next((n for n in names if n in sections), None)
    root_nodes: list[tuple[str, addnodes.toctree]] = []
    if sections and node is None and pagename == app.env.config.root_doc:
        for root_node in app.env.get_doctree(pagename).findall(addnodes.toctree):
            name = next((n for n in root_node.parent.get("names", []) if n in sections), None)
            if name is not None:
                root_nodes.append((name, root_node))
    context["sidebar_section"] = section
    context["sidebar_sections"] = sections
    context["sidebar_section_docs"] = _section_docs(app, sections) if sections else {}

    def render(name: str, toctree_node: addnodes.toctree) -> str:
        _, _, maxdepth, current_maxdepth = sections[name]
        current_maxdepth = app.config.section_sidebar_page_depth.get(pagename, current_maxdepth)
        tree = TocTree(app.env).resolve(
            pagename,
            app.builder,
            toctree_node,
            prune=True,
            maxdepth=_RESOLVE_DEPTH,
            collapse=False,
            includehidden=True,
        )
        if tree is None:
            return ""
        # The switch and link row above the tree already name the sections; the toctree
        # caption would only repeat them (the captions still head the global toctree used by
        # the fallback pages and the singlehtml build).
        for child in [c for c in tree.children if isinstance(c, nodes.title)]:
            tree.remove(child)
        root_depth = app.config.section_sidebar_root_depth
        if pagename == app.env.config.root_doc and name in root_depth:
            # The root page has no current entry; one depth for every page, no summaries.
            _prune_tree(tree, root_depth[name], root_depth[name], {})
            return app.builder.render_partial(tree)["fragment"]
        # The resolved tree links by page-relative URI, so key the summary patterns the same way.
        summary = {
            app.builder.get_relative_uri(pagename, docname): patterns
            for docname, patterns in app.config.section_sidebar_summary.items()
        }
        _prune_tree(tree, maxdepth, current_maxdepth, summary)
        if sections[name][0] is None:
            _keep_current_headings(tree)
        return app.builder.render_partial(tree)["fragment"]

    def section_toctree() -> str:
        if section is not None:
            return render(section, node)
        return "".join(
            render(name, root_node) for name, root_node in root_nodes if sections[name][0]
        )

    context["section_toctree"] = section_toctree


def _section_docs(app: Sphinx, sections: dict) -> dict[str, list[tuple[str, str]]]:
    """(title, docname) of every page listed by each section's toctree, in order."""
    env = app.env
    docs: dict[str, list[tuple[str, str]]] = {}
    for node in env.get_doctree(env.config.root_doc).findall(addnodes.toctree):
        name = next((n for n in node.parent.get("names", []) if n in sections), None)
        if name is not None:
            docs[name] = [
                (env.titles[d].astext(), d) for d in node["includefiles"] if d in env.titles
            ]
    return docs


def _check_config(app: Sphinx, env) -> None:
    """Warn about summary / depth entries that name pages or sections which do not exist."""
    configured = set(app.config.section_sidebar_summary)
    configured |= set(app.config.section_sidebar_page_depth)
    for docname in sorted(configured - set(env.all_docs)):
        logger.warning("section_sidebar: %r is not a document in this project", docname)
    sections = set(app.config.section_sidebar_sections)
    for name in sorted(set(app.config.section_sidebar_root_depth) - sections):
        logger.warning("section_sidebar_root_depth: %r is not a configured section", name)


def setup(app: Sphinx) -> dict:
    app.add_config_value("section_sidebar_sections", {}, "html", dict)
    app.add_config_value("section_sidebar_summary", {}, "html", dict)
    app.add_config_value("section_sidebar_page_depth", {}, "html", dict)
    app.add_config_value("section_sidebar_root_depth", {}, "html", dict)
    app.connect("env-check-consistency", _check_config)
    app.connect("html-page-context", _add_section_toctree)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
