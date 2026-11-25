const COPY_ICON_SVG =
  '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const CHECK_ICON_SVG =
  '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

/* -------------------------------------------------------------------------- *
 * 1. Light-dismiss fallback for <dialog closedby="any">
 * -------------------------------------------------------------------------- */
function initDialogLightDismissFallback() {
  if ("closedBy" in HTMLDialogElement.prototype) {
    return;
  }
  for (const dialog of document.querySelectorAll('dialog[closedby="any"]')) {
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) {
        return;
      }
      const rect = dialog.getBoundingClientRect();
      const isDialogContent =
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width;
      if (!isDialogContent) {
        dialog.close();
      }
    });
  }
}

/* -------------------------------------------------------------------------- *
 * 2. Responsive Navbar (intrinsic measurement, no hardcoded width breakpoint)
 * -------------------------------------------------------------------------- */
function initResponsiveNavbar() {
  const header = document.querySelector(".site-header");
  const inner = header?.querySelector(".header-inner");
  const menu = document.getElementById("site-menu");
  if (!header || !inner || !menu) {
    return;
  }

  let lastHeaderWidth = 0;

  const isMenuOpen = () => {
    try {
      return menu.matches(":popover-open, .\\:popover-open");
    } catch {
      return menu.classList.contains(":popover-open");
    }
  };

  const syncLayout = (forceMeasure = false) => {
    const currentWidth = header.clientWidth;
    const isCurrentlyWide = header.classList.contains("is-wide");
    if (!forceMeasure && !isCurrentlyWide && currentWidth <= lastHeaderWidth) {
      lastHeaderWidth = currentWidth;
      return;
    }
    lastHeaderWidth = currentWidth;

    const wasOpen = isMenuOpen();
    header.classList.add("is-measuring", "is-wide");
    const fits = inner.scrollWidth <= inner.clientWidth;
    header.classList.toggle("is-wide", fits);

    if (fits) {
      menu.removeAttribute("popover");
    } else {
      menu.setAttribute("popover", "auto");
      if (wasOpen && typeof menu.showPopover === "function") {
        try {
          menu.showPopover();
        } catch {
          // Ignore if polyfill is still initializing.
        }
      }
    }

    requestAnimationFrame(() => {
      header.classList.remove("is-measuring");
    });
  };

  syncLayout(true);

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => syncLayout(true)).catch(() => {});
  }

  if (typeof ResizeObserver !== "undefined") {
    const headerObserver = new ResizeObserver(() => syncLayout(false));
    headerObserver.observe(header);
  }
}

/* -------------------------------------------------------------------------- *
 * 3. Two-state persistent color-scheme toggle (syncs <meta name="color-scheme">)
 * -------------------------------------------------------------------------- */
function initThemeToggle() {
  const meta = document.querySelector('meta[name="color-scheme"]');
  const toggleBtn = document.querySelector(".theme-toggle");
  if (!meta) {
    return;
  }

  const getStored = () => {
    try {
      const value = localStorage.getItem("color-scheme");
      return value === "light" || value === "dark" ? value : null;
    } catch {
      return null;
    }
  };

  const applyMeta = (value) => {
    meta.content = value === "light" || value === "dark" ? value : "light dark";
  };

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const stored = getStored();
      const systemScheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
      const currentRendered =
        meta.content === "light" || meta.content === "dark"
          ? meta.content
          : (stored ?? systemScheme);
      const target = currentRendered === "dark" ? "light" : "dark";

      if (target !== systemScheme) {
        try {
          localStorage.setItem("color-scheme", target);
        } catch {
          // Storage blocked; still apply to current page.
        }
        applyMeta(target);
      } else {
        try {
          localStorage.removeItem("color-scheme");
        } catch {
          // Ignore storage error.
        }
        applyMeta("light dark");
      }
    });
  }

  window.addEventListener("storage", (event) => {
    if (event.key === "color-scheme" || event.key === null) {
      applyMeta(event.newValue);
    }
  });
}

/* -------------------------------------------------------------------------- *
 * 4. Accessible Tabs (roving tabindex, selection-on-focus, find-in-page sync)
 * -------------------------------------------------------------------------- */
function initTabGroups() {
  const tabActivators = new WeakMap();

  for (const tablist of document.querySelectorAll('[role="tablist"]')) {
    const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
    if (!tabs.length) {
      continue;
    }
    const hintTargetId = tablist.dataset.hintTarget;
    const hintEl = hintTargetId ? document.getElementById(hintTargetId) : null;
    const panels = tabs.map((tab) =>
      tab.id ? document.querySelector(`[role="tabpanel"][aria-labelledby="${CSS.escape(tab.id)}"]`) : null
    );

    const selectTab = (nextTab, { moveFocus = false, scroll = true, sync = false } = {}) => {
      tabs.forEach((tab, idx) => {
        const isSelected = tab === nextTab;
        tab.setAttribute("aria-selected", isSelected ? "true" : "false");
        tab.tabIndex = isSelected ? 0 : -1;
        const panel = panels[idx];
        if (panel) {
          panel.hidden = isSelected ? false : "until-found";
        }
      });
      if (hintEl && nextTab.dataset.hint) {
        hintEl.textContent = nextTab.dataset.hint;
      }
      if (scroll) {
        nextTab.scrollIntoView({ block: "nearest", inline: "nearest", container: "nearest" });
      }
      if (moveFocus) {
        nextTab.focus();
      }
      if (sync && nextTab.dataset.syncTab) {
        const syncTarget = document.getElementById(nextTab.dataset.syncTab);
        const activateTarget = syncTarget ? tabActivators.get(syncTarget) : null;
        if (activateTarget) {
          activateTarget();
        }
      }
    };

    tabs.forEach((tab, idx) => {
      tabActivators.set(tab, () => selectTab(tab, { moveFocus: false, scroll: false, sync: false }));
      tab.addEventListener("click", () => selectTab(tab, { moveFocus: false, scroll: true, sync: true }));
      tab.addEventListener("keydown", (event) => {
        let targetIdx = -1;
        if (event.key === "ArrowRight") {
          targetIdx = (idx + 1) % tabs.length;
        } else if (event.key === "ArrowLeft") {
          targetIdx = (idx - 1 + tabs.length) % tabs.length;
        } else if (event.key === "Home") {
          targetIdx = 0;
        } else if (event.key === "End") {
          targetIdx = tabs.length - 1;
        }
        if (targetIdx !== -1) {
          event.preventDefault();
          selectTab(tabs[targetIdx], { moveFocus: true, scroll: true, sync: true });
        }
      });

      const panel = panels[idx];
      if (panel) {
        panel.addEventListener("beforematch", () =>
          selectTab(tab, { moveFocus: false, scroll: false, sync: false })
        );
      }
    });
  }
}

/* Equalize tab panel heights so switching tabs never shifts content below. */
function initEqualHeightTabPanels() {
  for (const panelsWrap of document.querySelectorAll("[data-equalize-panels]")) {
    const topPanels = Array.from(panelsWrap.querySelectorAll(':scope > [role="tabpanel"]'));
    if (topPanels.length < 2) {
      continue;
    }

    let lastWidth = -1;

    const syncHeights = (force = false) => {
      const width = Math.round(panelsWrap.clientWidth);
      if (width <= 0 || (!force && width === lastWidth)) {
        return;
      }
      lastWidth = width;

      panelsWrap.style.minBlockSize = "";
      const bandGroups = new Map();
      for (const el of panelsWrap.querySelectorAll("[data-equalize-band]")) {
        el.style.minBlockSize = "";
        const key = el.dataset.equalizeBand;
        if (!bandGroups.has(key)) {
          bandGroups.set(key, []);
        }
        bandGroups.get(key).push(el);
      }

      const nestedPanels = Array.from(
        panelsWrap.querySelectorAll(':scope > [role="tabpanel"] [role="tabpanel"]')
      );
      const allPanels = [...topPanels, ...nestedPanels];
      const savedHidden = allPanels.map((panel) => panel.getAttribute("hidden"));

      for (const panel of allPanels) {
        panel.hidden = false;
      }

      for (const els of bandGroups.values()) {
        const heights = els.map((el) => Math.ceil(el.getBoundingClientRect().height));
        const maxBandH = Math.max(...heights);
        const minBandH = Math.min(...heights);
        if (maxBandH > 0 && maxBandH - minBandH <= 32) {
          for (const el of els) {
            el.style.minBlockSize = `${maxBandH}px`;
          }
        }
      }

      let maxPanelH = 0;
      for (const panel of topPanels) {
        maxPanelH = Math.max(maxPanelH, Math.ceil(panel.getBoundingClientRect().height));
      }

      allPanels.forEach((panel, idx) => {
        const prev = savedHidden[idx];
        if (prev === null) {
          panel.hidden = false;
        } else {
          panel.setAttribute("hidden", prev);
        }
      });

      if (maxPanelH > 0) {
        panelsWrap.style.minBlockSize = `${maxPanelH}px`;
      }
    };

    syncHeights(true);

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => syncHeights(true)).catch(() => {});
    }

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(() => syncHeights(false));
      observer.observe(panelsWrap);
    }
  }
}

/* -------------------------------------------------------------------------- *
 * 5. Copy-to-clipboard buttons (hero inline command + prose code blocks)
 * -------------------------------------------------------------------------- */
const copyTimers = new WeakMap();
let copyLiveRegion = null;
let lastCopyAnnouncement = "";

function announceCopyStatus(message) {
  if (!copyLiveRegion) {
    copyLiveRegion = document.createElement("span");
    copyLiveRegion.className = "visually-hidden";
    copyLiveRegion.setAttribute("role", "status");
    document.body.appendChild(copyLiveRegion);
  }
  const text = message === lastCopyAnnouncement ? `${message}\u00A0` : message;
  lastCopyAnnouncement = message;
  copyLiveRegion.textContent = "";
  requestAnimationFrame(() => {
    if (copyLiveRegion) {
      copyLiveRegion.textContent = text;
    }
  });
}

function flashCopied(button, ok) {
  const prevTimer = copyTimers.get(button);
  if (prevTimer !== undefined) {
    window.clearTimeout(prevTimer);
  }
  if (ok) {
    button.innerHTML = CHECK_ICON_SVG;
    button.classList.add("is-copied");
    announceCopyStatus("Copied");
  } else {
    announceCopyStatus("Copy failed");
  }
  const timerId = window.setTimeout(() => {
    button.innerHTML = COPY_ICON_SVG;
    button.classList.remove("is-copied");
    if (copyLiveRegion) {
      copyLiveRegion.textContent = "";
    }
    copyTimers.delete(button);
  }, 1400);
  copyTimers.set(button, timerId);
}

function initCopyButtons() {
  for (const inlineBtn of document.querySelectorAll(".copy-inline-btn")) {
    const text = inlineBtn.getAttribute("data-copy") || "";
    inlineBtn.addEventListener("click", () => {
      if (!text || !navigator.clipboard) {
        flashCopied(inlineBtn, false);
        return;
      }
      navigator.clipboard
        .writeText(text)
        .then(() => flashCopied(inlineBtn, true))
        .catch(() => flashCopied(inlineBtn, false));
    });
  }

  for (const container of document.querySelectorAll(".prose .codehilite, .platform-card .codehilite")) {
    const codeEl = container.querySelector("code") || container;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-code-btn";
    const defaultLabel = container.getAttribute("data-copy-label") || "Copy code to clipboard";
    btn.setAttribute("aria-label", defaultLabel);
    btn.innerHTML = COPY_ICON_SVG;
    btn.addEventListener("click", () => {
      const raw = (codeEl.textContent || "").trim();
      if (!raw || !navigator.clipboard) {
        flashCopied(btn, false);
        return;
      }
      navigator.clipboard
        .writeText(raw)
        .then(() => flashCopied(btn, true))
        .catch(() => flashCopied(btn, false));
    });
    container.appendChild(btn);
  }
}

/* -------------------------------------------------------------------------- *
 * 6. Right-hand TOC active section highlight
 * -------------------------------------------------------------------------- */
function initTocHighlight() {
  const tocLinks = Array.from(document.querySelectorAll(".toc-list a[href^='#']"));
  if (!tocLinks.length || typeof IntersectionObserver === "undefined") {
    return;
  }

  const linkById = new Map();
  const headings = [];
  for (const link of tocLinks) {
    const id = decodeURIComponent(link.getAttribute("href").slice(1));
    const target = document.getElementById(id);
    if (target) {
      linkById.set(id, link);
      headings.push(target);
    }
  }
  if (!headings.length) {
    return;
  }

  const setActive = (id) => {
    for (const [key, link] of linkById.entries()) {
      link.classList.toggle("is-active", key === id);
    }
  };

  setActive(headings[0].id);

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          setActive(entry.target.id);
          break;
        }
      }
    },
    { rootMargin: "-72px 0px -70% 0px", threshold: 0 }
  );

  for (const heading of headings) {
    observer.observe(heading);
  }
}

/* -------------------------------------------------------------------------- *
 * 7. Client-side search modal (Ctrl+K / '/', lazy JSON index, arrow nav)
 * -------------------------------------------------------------------------- */
function initSearchDialog() {
  const dialog = document.getElementById("search-dialog");
  const input = document.getElementById("search-input");
  const resultsEl = document.getElementById("search-results");
  const statusEl = document.getElementById("search-status");
  if (!(dialog instanceof HTMLDialogElement) || !(input instanceof HTMLInputElement) || !resultsEl) {
    return;
  }

  const announceStatus = (msg) => {
    if (statusEl) {
      statusEl.textContent = msg;
    }
  };

  let indexPromise = null;
  let searchData = [];
  let activeHitIndex = -1;

  const ensureIndex = () => {
    if (!indexPromise) {
      indexPromise = fetch(new URL("../search_index.json", import.meta.url))
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          searchData = Array.isArray(data) ? data : [];
          return searchData;
        })
        .catch(() => {
          searchData = [];
          return searchData;
        });
    }
    return indexPromise;
  };

  const renderMessage = (msg) => {
    resultsEl.textContent = "";
    const p = document.createElement("p");
    p.className = "search-empty";
    p.textContent = msg;
    resultsEl.appendChild(p);
    activeHitIndex = -1;
  };

  const updateActiveHit = (nextIdx) => {
    const hits = Array.from(resultsEl.querySelectorAll(".search-hit"));
    if (!hits.length) {
      activeHitIndex = -1;
      return;
    }
    activeHitIndex = ((nextIdx % hits.length) + hits.length) % hits.length;
    hits.forEach((el, idx) => {
      const active = idx === activeHitIndex;
      el.classList.toggle("is-active", active);
      if (active) {
        el.scrollIntoView({ block: "nearest" });
      }
    });
  };

  const runQuery = (rawQuery) => {
    const q = rawQuery.trim().toLowerCase();
    if (!q) {
      renderMessage(
        "Type a keyword to search guides, CLI options, detectors, and FAQs."
      );
      announceStatus("");
      return;
    }

    const terms = q.split(/\s+/).filter(Boolean);
    const scored = [];

    for (const item of searchData) {
      const titleL = (item.title || "").toLowerCase();
      const sectionL = (item.section || "").toLowerCase();
      const textL = (item.text || "").toLowerCase();
      const combined = `${titleL} ${sectionL} ${textL}`;

      let matchesAll = true;
      for (const term of terms) {
        if (!combined.includes(term)) {
          matchesAll = false;
          break;
        }
      }
      if (!matchesAll) {
        continue;
      }

      let score = 0;
      if (titleL === q || sectionL === q) score += 80;
      if (sectionL.startsWith(q)) score += 40;
      if (titleL.includes(q)) score += 25;
      if (sectionL.includes(q)) score += 20;
      for (const term of terms) {
        if (sectionL.includes(term)) score += 10;
        if (titleL.includes(term)) score += 8;
        if (textL.includes(term)) score += 3;
      }
      scored.push({ item, score });
    }

    scored.sort((a, b) => b.score - a.score);
    const topHits = scored.slice(0, 12);

    if (!topHits.length) {
      renderMessage(`No matching sections found for "${rawQuery.trim()}".`);
      announceStatus("No matching sections found.");
      return;
    }

    resultsEl.textContent = "";
    topHits.forEach(({ item }, idx) => {
      const link = document.createElement("a");
      link.className = idx === 0 ? "search-hit is-active" : "search-hit";
      link.href = item.url;

      const meta = document.createElement("span");
      meta.className = "search-hit-meta";
      meta.textContent =
        item.section && item.section !== item.title
          ? `${item.title}  /  ${item.section}`
          : item.title;

      const snippet = document.createElement("span");
      snippet.className = "search-hit-snippet";
      snippet.textContent = item.text || "";

      link.appendChild(meta);
      if (item.text) {
        link.appendChild(snippet);
      }
      link.addEventListener("click", () => {
        dialog.close();
      });
      resultsEl.appendChild(link);
    });
    activeHitIndex = 0;
    announceStatus(
      topHits.length === 1 ? "1 result found." : `${topHits.length} results found.`
    );
  };

  const openSearch = () => {
    if (!dialog.open) {
      dialog.showModal();
    }
    if (input.value.trim()) {
      ensureIndex().then(() => runQuery(input.value));
    }
    input.focus();
    input.select();
  };

  dialog.addEventListener("toggle", () => {
    if (dialog.open) {
      ensureIndex();
    }
  });

  const triggerBtn = document.querySelector(".search-trigger");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", openSearch);
  }

  input.addEventListener("input", () => {
    ensureIndex().then(() => runQuery(input.value));
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      updateActiveHit(activeHitIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      updateActiveHit(activeHitIndex - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const hits = resultsEl.querySelectorAll(".search-hit");
      if (activeHitIndex >= 0 && hits[activeHitIndex]) {
        const href = hits[activeHitIndex].getAttribute("href");
        dialog.close();
        if (href) {
          window.location.href = href;
        }
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearch();
      return;
    }
    if (event.key === "/" && !dialog.open && !event.ctrlKey && !event.metaKey && !event.altKey) {
      const active = document.activeElement;
      const isEditable =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        active instanceof HTMLSelectElement ||
        (active instanceof HTMLElement && active.isContentEditable);
      if (!isEditable) {
        event.preventDefault();
        openSearch();
      }
    }
  });
}

initDialogLightDismissFallback();
initResponsiveNavbar();
initThemeToggle();
initTabGroups();
initEqualHeightTabPanels();
initCopyButtons();
initTocHighlight();
initSearchDialog();
