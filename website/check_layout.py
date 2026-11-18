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
"""Zero-dependency headless Chromium layout verifier and screenshot generator."""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import html
import http.server
import json
import os
import posixpath
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WEBSITE_DIR = Path(__file__).resolve().parent
DEFAULT_BUILD_DIR = WEBSITE_DIR / "build"

VIEWPORTS: list[tuple[str, int, int, bool, float]] = [
    ("Mobile 320x568", 320, 568, True, 2.0),
    ("Mobile 375x812", 375, 812, True, 3.0),
    ("Mobile 390x844", 390, 844, True, 3.0),
    ("Tablet 768x1024", 768, 1024, True, 2.0),
    ("Desktop 1280x800", 1280, 800, False, 1.0),
]

SPHINX_SAMPLE_PAGES: tuple[str, ...] = (
    "index.html",
    "cli.html",
    "api.html",
    "api/detectors.html",
    "examples.html",
    "changelog.html",
)

AUDIT_JS_TEMPLATE = """
(() => {
  const vw = __EXPECTED_VW__;
  const vh = window.innerHeight;
  const docScrollW = document.documentElement.scrollWidth;
  const overflows = [];
  if (docScrollW > vw + 1) {
    for (const el of document.querySelectorAll('*')) {
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      const r = el.getBoundingClientRect();
      const unclippedScroll =
        (style.overflowX === 'visible' || style.overflowX === '') &&
        el.clientWidth > 0 &&
        el.scrollWidth > el.clientWidth + 1 &&
        el !== document.documentElement &&
        el !== document.body;
      if ((r.width > 0 && r.right > vw + 0.5) || unclippedScroll) {
        let p = el.parentElement;
        let clipped = false;
        while (p && p !== document.documentElement) {
          const ox = getComputedStyle(p).overflowX;
          if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') {
            if (p.getBoundingClientRect().right <= vw + 0.5) {
              clipped = true;
              break;
            }
          }
          p = p.parentElement;
        }
        if (!clipped) {
          overflows.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className && typeof el.className === 'string') ? el.className : '',
            right: Math.round(r.right * 10) / 10,
            width: Math.round(Math.max(r.width, el.scrollWidth) * 10) / 10,
            text: (el.textContent || '').trim().slice(0, 40)
          });
        }
      }
    }
    if (overflows.length === 0) {
      const cands = [];
      for (const el of document.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > vw - 18 && el.children.length <= 2) {
          cands.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className && typeof el.className === 'string') ? el.className : '',
            right: Math.round(r.right * 10) / 10,
            width: Math.round(r.width * 10) / 10,
            text: (el.textContent || '').trim().slice(0, 40)
          });
        }
      }
      cands.sort((a, b) => b.right - a.right);
      overflows.push(...cands.slice(0, 6));
    }
  }

  const header = document.querySelector('.site-header, .psd-topbar');
  const isWide = header ? header.classList.contains('is-wide') : null;
  const selectors = [
    '.brand-link',
    '.menu-button',
    '.search-trigger',
    '.theme-toggle',
    '.icon-link',
    '.psd-brand',
    '.psd-version-btn',
    '.psd-theme-toggle'
  ];
  const controls = [];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    controls.push({
      sel,
      isButton: sel !== '.brand-link' && sel !== '.psd-brand',
      w: Math.round(r.width * 10) / 10,
      h: Math.round(r.height * 10) / 10,
      left: Math.round(r.left * 10) / 10,
      right: Math.round(r.right * 10) / 10
    });
  }

  let headerOverlap = false;
  for (let i = 0; i < controls.length; i++) {
    for (let j = i + 1; j < controls.length; j++) {
      const a = controls[i];
      const b = controls[j];
      if (Math.max(a.left, b.left) < Math.min(a.right, b.right) - 0.5) {
        headerOverlap = true;
      }
    }
  }

  return {
    vw,
    vh,
    docScrollW,
    isWide,
    headerOverlap,
    controls,
    overflows: overflows.slice(0, 6)
  };
})()
"""


@dataclass(frozen=True)
class ShotRecord:
    """Metadata for a captured screenshot card in the HTML contact sheet."""

    group: str
    filename: str
    label: str
    route: str
    viewport: str
    scheme: str
    width: int
    height: int


def normalize_base_path(raw: str) -> str:
    """Normalize an optional URL base path (e.g. 'staging/' -> '/staging', '/' -> '')."""
    cleaned = raw.strip().strip("/")
    return f"/{cleaned}" if cleaned else ""


def find_browser(explicit: str | None = None) -> Path:
    """Locate a local Chrome, Chromium, or Edge executable across Linux, macOS, and Windows."""
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    env_bin = os.environ.get("CHROME_BIN")
    if env_bin:
        candidates.append(env_bin)

    for binary_name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "microsoft-edge-stable",
        "msedge",
    ):
        found = shutil.which(binary_name)
        if found:
            candidates.append(found)

    if sys.platform == "win32":
        for root_var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
            root = os.environ.get(root_var)
            if root:
                candidates.append(
                    str(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
                )
                candidates.append(
                    str(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
                )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        )

    for cand in candidates:
        path = Path(cand)
        if path.is_file():
            return path

    raise FileNotFoundError(
        "No Chrome, Chromium, or Edge binary found. Pass --browser PATH or set CHROME_BIN."
    )


class SimpleWS:
    """Minimal RFC 6455 WebSocket client over stdlib socket for local CDP JSON-RPC."""

    def __init__(self, ws_url: str) -> None:
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        self.sock = socket.create_connection((host, port), timeout=20.0)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket handshake closed prematurely")
            buf += chunk
        header, self._leftover = buf.split(b"\r\n\r\n", 1)
        if b"101" not in header.splitlines()[0]:
            raise RuntimeError(f"WebSocket handshake failed: {header.decode('latin1')}")
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        )
        if expected not in header:
            raise RuntimeError("Invalid Sec-WebSocket-Accept")
        self._next_id = 1
        self.events: list[dict[str, Any]] = []

    def _recv_exact(self, n: int) -> bytes:
        out = bytearray()
        if self._leftover:
            take = min(n, len(self._leftover))
            out.extend(self._leftover[:take])
            self._leftover = self._leftover[take:]
        while len(out) < n:
            chunk = self.sock.recv(max(4096, n - len(out)))
            if not chunk:
                raise RuntimeError("WebSocket closed while reading frame")
            need = n - len(out)
            out.extend(chunk[:need])
            if len(chunk) > need:
                self._leftover += chunk[need:]
        return bytes(out)

    def send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        header.extend(mask)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv_frame(self) -> str:
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            mask_key = self._recv_exact(4) if masked else b""
            data = self._recv_exact(length)
            if masked:
                data = bytes(b ^ mask_key[i & 3] for i, b in enumerate(data))
            if opcode == 0x8:
                raise RuntimeError("WebSocket closed by server")
            if opcode == 0x9:
                pong = bytearray([0x8A, 0x80 | len(data)])
                m = os.urandom(4)
                pong.extend(m)
                pong.extend(bytes(b ^ m[i & 3] for i, b in enumerate(data)))
                self.sock.sendall(bytes(pong))
                continue
            if opcode == 0x1:
                return data.decode("utf-8")

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        msg_id = self._next_id
        self._next_id += 1
        self.send_text(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            raw = self.recv_frame()
            msg = json.loads(raw)
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP error on {method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.sock.close()


def _resolve_mounted_file(root_dir: Path, rel_posix: str) -> Path | None:
    """Safely resolve a URL path fragment inside root_dir without directory traversal."""
    norm = posixpath.normpath("/" + rel_posix.lstrip("/")).lstrip("/")
    candidate = (root_dir / norm).resolve() if norm else (root_dir / "index.html").resolve()
    root_resolved = root_dir.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        return None
    if candidate.is_dir():
        index_file = candidate / "index.html"
        return index_file if index_file.is_file() else None
    return candidate if candidate.is_file() else None


def start_local_server(
    build_dir: Path,
    base_path: str,
    sphinx_dir: Path | None,
    http_errors: list[str],
) -> tuple[http.server.ThreadingHTTPServer, int]:
    """Serve build_dir at base_path (plus optional sphinx_dir at /docs/head/ & /docs/latest/)."""
    expected_404 = f"{base_path}/404.html"

    class MultiMountHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(build_dir), **kwargs)

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def _locate_target(self, url_path: str) -> Path | None:
            if sphinx_dir is not None:
                for mount in ("/docs/head", "/docs/latest"):
                    if url_path == mount or url_path.startswith(mount + "/"):
                        sub = url_path[len(mount) :]
                        return _resolve_mounted_file(sphinx_dir, sub or "/index.html")
                if url_path in {"/versions.json", "/favicon.ico", "/img/favicon.ico"}:
                    fallback_name = (
                        "favicon.ico" if url_path.endswith("favicon.ico") else "versions.json"
                    )
                    fb = build_dir / fallback_name
                    if fb.is_file():
                        return fb

            if base_path:
                if url_path == base_path:
                    return _resolve_mounted_file(build_dir, "/index.html")
                prefix = f"{base_path}/"
                if not url_path.startswith(prefix):
                    return None
                local_rel = url_path[len(base_path) :]
                return _resolve_mounted_file(build_dir, local_rel)

            return _resolve_mounted_file(build_dir, url_path)

        def do_GET(self) -> None:
            url_path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            target = self._locate_target(url_path)
            if target is None:
                if url_path != expected_404 and not url_path.endswith("/favicon.ico"):
                    http_errors.append(f"HTTP 404 for local request: {url_path}")
                not_found = build_dir / "404.html"
                if not_found.is_file():
                    body = not_found.read_bytes()
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404)
                return

            ctype = self.guess_type(str(target))
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MultiMountHandler)
    port = int(server.server_address[1])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def eval_js(cdp: SimpleWS, expr: str) -> Any:
    res = cdp.call(
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
    )
    if "exceptionDetails" in res:
        raise RuntimeError(f"JS eval exception: {res['exceptionDetails']}")
    return res.get("result", {}).get("value")


def navigate(cdp: SimpleWS, url: str) -> None:
    cdp.events.clear()
    cdp.call("Page.navigate", {"url": url})
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if eval_js(cdp, "document.readyState") == "complete":
            break
        time.sleep(0.04)
    eval_js(
        cdp,
        "new Promise(r => requestAnimationFrame(() => "
        "requestAnimationFrame(() => setTimeout(r, 35))))",
    )


def set_viewport(
    cdp: SimpleWS,
    width: int,
    height: int,
    mobile: bool,
    dpr: float = 2.0,
    scheme: str = "light",
) -> None:
    cdp.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": dpr,
            "mobile": mobile,
        },
    )
    cdp.call(
        "Emulation.setTouchEmulationEnabled",
        {"enabled": True, "maxTouchPoints": 5} if mobile else {"enabled": False},
    )
    cdp.call(
        "Emulation.setEmulatedMedia",
        {"features": [{"name": "prefers-color-scheme", "value": scheme}]},
    )


def click_point(cdp: SimpleWS, x: float, y: float) -> None:
    cdp.call(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
    )
    cdp.call(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
    )


def save_screenshot(cdp: SimpleWS, out_path: Path) -> None:
    data_b64 = cdp.call("Page.captureScreenshot", {"format": "png"})["data"]
    out_path.write_bytes(base64.b64decode(data_b64))


def discover_routes(build_dir: Path, base_path: str, sphinx_dir: Path | None) -> list[str]:
    """Collect all built website HTML routes plus representative Sphinx routes when provided."""
    routes: list[str] = []
    for html_file in sorted(build_dir.rglob("*.html")):
        rel = html_file.relative_to(build_dir).as_posix()
        if rel == "index.html":
            routes.append(f"{base_path}/")
        elif rel.endswith("/index.html"):
            slug = rel[: -len("/index.html")]
            routes.append(f"{base_path}/{slug}/")
        else:
            routes.append(f"{base_path}/{rel}")

    routes.sort(key=lambda r: (0 if r == f"{base_path}/" else 1, r))

    if sphinx_dir is not None:
        for sample in SPHINX_SAMPLE_PAGES:
            if (sphinx_dir / sample).is_file():
                routes.append(f"/docs/head/{sample}")

    return routes


def write_contact_sheet(
    shots_dir: Path,
    shots: list[ShotRecord],
    total_checks: int,
    route_count: int,
    failures: list[str],
) -> None:
    """Write a self-contained HTML5 visual contact sheet with light/dark support."""
    groups: dict[str, list[ShotRecord]] = {}
    for shot in shots:
        groups.setdefault(shot.group, []).append(shot)

    status_label = "PASSED" if not failures else f"FAILED ({len(failures)} issue(s))"
    status_cls = "badge-pass" if not failures else "badge-fail"

    failure_html = ""
    if failures:
        items = "\n".join(f"      <li><code>{html.escape(f)}</code></li>" for f in failures)
        failure_html = (
            '  <section class="failures" aria-label="Recorded failures">\n'
            "    <h2>Recorded Issues</h2>\n"
            f"    <ul>\n{items}\n    </ul>\n"
            "  </section>\n"
        )

    sections_html: list[str] = []
    for group_name, items in groups.items():
        cards: list[str] = []
        for s in items:
            cards.append(
                f'      <figure class="card">\n'
                f'        <a class="thumb-link" href="{html.escape(s.filename)}">\n'
                f'          <img src="{html.escape(s.filename)}" alt="{html.escape(s.label)}" '
                f'width="{s.width}" height="{s.height}" loading="lazy">\n'
                "        </a>\n"
                "        <figcaption>\n"
                f"          <strong>{html.escape(s.label)}</strong>\n"
                f'          <span class="meta"><code>{html.escape(s.route)}</code> &middot; '
                f"{html.escape(s.viewport)} &middot; {html.escape(s.scheme)}</span>\n"
                "        </figcaption>\n"
                "      </figure>"
            )
        sections_html.append(
            f"  <section>\n"
            f"    <h2>{html.escape(group_name)}</h2>\n"
            f'    <div class="grid">\n' + "\n".join(cards) + "\n    </div>\n  </section>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <title>PySceneDetect Layout &amp; Screenshot Report</title>
  <style>
    :root {{
      --bg-light: #f8fafc;
      --bg-dark: #0f172a;
      --surface-light: #ffffff;
      --surface-dark: #1e293b;
      --fg-light: #0f172a;
      --fg-dark: #f1f5f9;
      --muted-light: #475569;
      --muted-dark: #94a3b8;
      --border-light: #cbd5e1;
      --border-dark: #334155;
      --pass-bg: #15803d;
      --fail-bg: #b91c1c;
      --bg: var(--bg-light);
      --surface: var(--surface-light);
      --fg: var(--fg-light);
      --muted: var(--muted-light);
      --border: var(--border-light);
      color-scheme: light dark;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: var(--bg-dark);
        --surface: var(--surface-dark);
        --fg: var(--fg-dark);
        --muted: var(--muted-dark);
        --border: var(--border-dark);
      }}
    }}
    @supports (color: light-dark(white, black)) {{
      :root {{
        --bg: light-dark(var(--bg-light), var(--bg-dark));
        --surface: light-dark(var(--surface-light), var(--surface-dark));
        --fg: light-dark(var(--fg-light), var(--fg-dark));
        --muted: light-dark(var(--muted-light), var(--muted-dark));
        --border: light-dark(var(--border-light), var(--border-dark));
      }}
    }}
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 2rem 1.25rem 4rem;
      max-inline-size: 86rem;
      margin-inline: auto;
      background: var(--bg);
      color: var(--fg);
      font-family: system-ui, -apple-system, sans-serif;
      line-height: 1.5;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding-block-end: 1.25rem;
      border-block-end: 1px solid var(--border);
      margin-block-end: 2rem;
    }}
    h1 {{ margin: 0; font-size: 1.5rem; }}
    h2 {{ margin: 2rem 0 1rem; font-size: 1.2rem; }}
    .summary {{ color: var(--muted); font-size: 0.92rem; margin: 0.25rem 0 0; }}
    .badge {{
      display: inline-block;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      color: #ffffff;
      font-weight: 600;
      font-size: 0.85rem;
    }}
    .badge-pass {{ background: var(--pass-bg); }}
    .badge-fail {{ background: var(--fail-bg); }}
    .failures {{
      padding: 1rem 1.25rem;
      border: 1px solid var(--fail-bg);
      border-radius: 0.5rem;
      background: var(--surface);
      margin-block-end: 2rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr));
      gap: 1.25rem;
      align-items: start;
    }}
    .card {{
      margin: 0;
      border: 1px solid var(--border);
      border-radius: 0.6rem;
      background: var(--surface);
      overflow: hidden;
    }}
    .thumb-link {{
      display: block;
      background: var(--bg);
      border-block-end: 1px solid var(--border);
    }}
    .card img {{
      display: block;
      inline-size: 100%;
      block-size: auto;
      max-block-size: 26rem;
      object-fit: cover;
      object-position: top center;
    }}
    figcaption {{
      padding: 0.75rem 0.9rem;
      display: grid;
      gap: 0.2rem;
    }}
    figcaption strong {{ font-size: 0.92rem; }}
    .meta {{ color: var(--muted); font-size: 0.8rem; }}
    code {{ font-family: ui-monospace, monospace; font-size: 0.88em; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>PySceneDetect Layout &amp; Screenshot Report</h1>
      <p class="summary">Audited {route_count} routes across {len(VIEWPORTS)} viewports
      ({total_checks} layout renders) &middot; {len(shots)} screenshots captured.</p>
    </div>
    <span class="badge {status_cls}">{html.escape(status_label)}</span>
  </header>
{failure_html}{chr(10).join(sections_html)}
</body>
</html>
"""
    (shots_dir / "index.html").write_text(doc, encoding="utf-8")


def capture_curated_pack(
    cdp: SimpleWS,
    base_url: str,
    base_path: str,
    sphinx_dir: Path | None,
    shots_dir: Path,
) -> list[ShotRecord]:
    """Capture a curated desktop, mobile, interactive, and Sphinx screenshot pack."""
    shots_dir.mkdir(parents=True, exist_ok=True)
    records: list[ShotRecord] = []

    def grab(
        group: str,
        filename: str,
        label: str,
        route: str,
        width: int,
        height: int,
        mobile: bool,
        scheme: str,
    ) -> None:
        set_viewport(cdp, width, height, mobile, 2.0, scheme)
        navigate(cdp, f"{base_url}{route}")
        eval_js(cdp, "localStorage.removeItem('color-scheme')")
        save_screenshot(cdp, shots_dir / filename)
        records.append(
            ShotRecord(
                group=group,
                filename=filename,
                label=label,
                route=route,
                viewport=f"{width}x{height}",
                scheme=scheme,
                width=width,
                height=height,
            )
        )

    # Desktop views (1280x800)
    grab(
        "Desktop (1280x800)",
        "desktop-home-light.png",
        "Home (Light)",
        f"{base_path}/",
        1280,
        800,
        False,
        "light",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-home-dark.png",
        "Home (Dark)",
        f"{base_path}/",
        1280,
        800,
        False,
        "dark",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-features-light.png",
        "Features (Light)",
        f"{base_path}/features/",
        1280,
        800,
        False,
        "light",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-download-dark.png",
        "Download (Dark)",
        f"{base_path}/download/",
        1280,
        800,
        False,
        "dark",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-cli-light.png",
        "CLI Overview (Light)",
        f"{base_path}/cli/",
        1280,
        800,
        False,
        "light",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-benchmarks-dark.png",
        "Benchmarks (Dark)",
        f"{base_path}/benchmarks/",
        1280,
        800,
        False,
        "dark",
    )
    grab(
        "Desktop (1280x800)",
        "desktop-gallery-light.png",
        "Project Gallery (Light)",
        f"{base_path}/gallery/",
        1280,
        800,
        False,
        "light",
    )

    # Mobile views (390x844 and 320x568)
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-home-light.png",
        "Home Mobile (Light)",
        f"{base_path}/",
        390,
        844,
        True,
        "light",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-home-dark.png",
        "Home Mobile (Dark)",
        f"{base_path}/",
        390,
        844,
        True,
        "dark",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-320-home-dark.png",
        "Home Ultra-Narrow 320px (Dark)",
        f"{base_path}/",
        320,
        568,
        True,
        "dark",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-cli-dark.png",
        "CLI Overview Mobile (Dark)",
        f"{base_path}/cli/",
        390,
        844,
        True,
        "dark",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-benchmarks-light.png",
        "Benchmarks Mobile (Light)",
        f"{base_path}/benchmarks/",
        390,
        844,
        True,
        "light",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-download-light.png",
        "Download Mobile (Light)",
        f"{base_path}/download/",
        390,
        844,
        True,
        "light",
    )
    grab(
        "Mobile (390x844 & 320x568)",
        "mobile-404-light.png",
        "404 Not Found Mobile (Light)",
        f"{base_path}/404.html",
        390,
        844,
        True,
        "light",
    )

    # Interactive UI states
    set_viewport(cdp, 390, 844, True, 2.0, "light")
    navigate(cdp, f"{base_url}{base_path}/")
    pt = eval_js(
        cdp,
        "(() => { const r = document.querySelector('.menu-button').getBoundingClientRect(); "
        "return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()",
    )
    click_point(cdp, pt["x"], pt["y"])
    time.sleep(0.1)
    save_screenshot(cdp, shots_dir / "mobile-menu-open.png")
    records.append(
        ShotRecord(
            group="Interactive Overlays",
            filename="mobile-menu-open.png",
            label="Mobile Navigation Popover Open",
            route=f"{base_path}/",
            viewport="390x844",
            scheme="light",
            width=390,
            height=844,
        )
    )

    set_viewport(cdp, 390, 844, True, 2.0, "dark")
    navigate(cdp, f"{base_url}{base_path}/")
    eval_js(cdp, "document.querySelector('.search-trigger').click()")
    _wait_for_search_hits(cdp, "save-otio")
    save_screenshot(cdp, shots_dir / "mobile-search-open.png")
    records.append(
        ShotRecord(
            group="Interactive Overlays",
            filename="mobile-search-open.png",
            label="Mobile Search Modal (save-otio)",
            route=f"{base_path}/",
            viewport="390x844",
            scheme="dark",
            width=390,
            height=844,
        )
    )

    set_viewport(cdp, 1280, 800, False, 2.0, "dark")
    navigate(cdp, f"{base_url}{base_path}/")
    eval_js(cdp, "document.querySelector('.search-trigger').click()")
    _wait_for_search_hits(cdp, "AdaptiveDetector")
    save_screenshot(cdp, shots_dir / "desktop-search-open.png")
    records.append(
        ShotRecord(
            group="Interactive Overlays",
            filename="desktop-search-open.png",
            label="Desktop Search Modal (AdaptiveDetector)",
            route=f"{base_path}/",
            viewport="1280x800",
            scheme="dark",
            width=1280,
            height=800,
        )
    )

    # Sphinx Reference pages (when built Sphinx docs are provided)
    if sphinx_dir is not None:
        if (sphinx_dir / "index.html").is_file():
            grab(
                "Sphinx Reference Manual",
                "sphinx-desktop-home-dark.png",
                "Sphinx Manual Home (Dark)",
                "/docs/head/index.html",
                1280,
                800,
                False,
                "dark",
            )
        if (sphinx_dir / "cli.html").is_file():
            grab(
                "Sphinx Reference Manual",
                "sphinx-desktop-cli-light.png",
                "Sphinx CLI Reference (Light)",
                "/docs/head/cli.html",
                1280,
                800,
                False,
                "light",
            )
            set_viewport(cdp, 390, 844, True, 2.0, "dark")
            navigate(cdp, f"{base_url}/docs/head/cli.html")
            vpt = eval_js(
                cdp,
                "(() => { const r = document.querySelector('.psd-version-btn')"
                ".getBoundingClientRect(); "
                "return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()",
            )
            click_point(cdp, vpt["x"], vpt["y"])
            time.sleep(0.12)
            save_screenshot(cdp, shots_dir / "sphinx-mobile-cli-versions-dark.png")
            records.append(
                ShotRecord(
                    group="Sphinx Reference Manual",
                    filename="sphinx-mobile-cli-versions-dark.png",
                    label="Sphinx Mobile CLI + Version Switcher (Dark)",
                    route="/docs/head/cli.html",
                    viewport="390x844",
                    scheme="dark",
                    width=390,
                    height=844,
                )
            )
        if (sphinx_dir / "api" / "detectors.html").is_file():
            grab(
                "Sphinx Reference Manual",
                "sphinx-mobile-detectors-light.png",
                "Sphinx Mobile API Detectors (Light)",
                "/docs/head/api/detectors.html",
                390,
                844,
                True,
                "light",
            )

    return records


def _wait_for_search_hits(cdp: SimpleWS, query: str) -> dict[str, Any]:
    """Type query into #search-input and poll briefly until search_index.json renders hits."""
    eval_js(
        cdp,
        f"""(() => {{
          const input = document.getElementById('search-input');
          input.value = {json.dumps(query)};
          input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""",
    )
    deadline = time.time() + 2.0
    state: dict[str, Any] = {}
    while time.time() < deadline:
        state = eval_js(
            cdp,
            """(() => {
              const dlg = document.getElementById('search-dialog');
              const r = dlg.getBoundingClientRect();
              const hits = [...document.querySelectorAll('.search-hit')].map(
                a => a.getAttribute('href')
              );
              return {
                open: dlg.open,
                left: Math.round(r.left),
                right: Math.round(r.right),
                top: Math.round(r.top),
                bottom: Math.round(r.bottom),
                hitCount: hits.length,
                topHit: hits[0] || null
              };
            })()""",
        )
        if state.get("hitCount", 0) > 0:
            break
        time.sleep(0.05)
    return state


def run_audit(
    build_dir: Path,
    base_path: str,
    sphinx_dir: Path | None,
    screenshots_dir: Path | None,
    browser_bin: Path,
) -> int:
    """Run headless responsive layout audit and optional screenshot generation."""
    if not build_dir.is_dir():
        print(f"[ERROR] Build directory does not exist: {build_dir}", file=sys.stderr)
        return 1
    if sphinx_dir is not None and not sphinx_dir.is_dir():
        print(f"[ERROR] Sphinx directory does not exist: {sphinx_dir}", file=sys.stderr)
        return 1

    routes = discover_routes(build_dir, base_path, sphinx_dir)
    if not routes:
        print(f"[ERROR] No HTML files found in {build_dir}", file=sys.stderr)
        return 1

    http_errors: list[str] = []
    server, http_port = start_local_server(build_dir, base_path, sphinx_dir, http_errors)
    base_url = f"http://127.0.0.1:{http_port}"

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ws_url: str | None = None
    proc: subprocess.Popen[bytes] | None = None
    profile_dir: Path | None = None
    stderr_log = ""

    for _attempt in range(2):
        cdp_port = get_free_port()
        profile_dir = Path(tempfile.mkdtemp(prefix="psd-layout-cdp-"))
        stderr_path = profile_dir / "browser-stderr.log"
        browser_cmd = [
            str(browser_bin),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-crash-reporter",
            "--password-store=basic",
            "--use-mock-keychain",
            "--no-proxy-server",
            "--window-size=1280,900",
            f"--user-data-dir={profile_dir}",
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={cdp_port}",
        ]
        if sys.platform.startswith("linux"):
            browser_cmd.extend(["--no-sandbox", "--disable-dev-shm-usage", "--disable-dbus"])
        browser_cmd.append("about:blank")

        with stderr_path.open("wb") as err_fh:
            proc = subprocess.Popen(browser_cmd, stdout=subprocess.DEVNULL, stderr=err_fh)

        deadline = time.time() + 25.0
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with opener.open(f"http://127.0.0.1:{cdp_port}/json", timeout=1.0) as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    for target in targets:
                        if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                            ws_url = str(target["webSocketDebuggerUrl"])
                            break
                    if ws_url:
                        break
            except Exception:
                time.sleep(0.15)

        if ws_url:
            break

        proc.kill()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)
        with contextlib.suppress(OSError):
            stderr_log = stderr_path.read_text(encoding="utf-8", errors="replace")[-1500:]
        shutil.rmtree(profile_dir, ignore_errors=True)

    if not ws_url or proc is None or profile_dir is None:
        server.shutdown()
        server.server_close()
        print(
            "[ERROR] Timed out waiting for headless browser CDP endpoint.\n"
            f"Browser stderr tail:\n{stderr_log}",
            file=sys.stderr,
        )
        return 1

    failures: list[str] = []
    total_checks = 0
    cdp = SimpleWS(ws_url)
    try:
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call("Log.enable")

        print(f"Using browser: {browser_bin}")
        print(f"Auditing {len(routes)} routes across {len(VIEWPORTS)} viewports...")

        for vp_name, width, height, is_mobile, dpr in VIEWPORTS:
            set_viewport(cdp, width, height, is_mobile, dpr, "light")
            vp_issues = 0
            for route in routes:
                navigate(cdp, f"{base_url}{route}")
                total_checks += 1

                for ev in cdp.events:
                    if ev.get("method") == "Runtime.exceptionThrown":
                        failures.append(f"[JS EXCEPTION] {vp_name} {route}: {ev.get('params')}")
                        vp_issues += 1

                info = eval_js(cdp, AUDIT_JS_TEMPLATE.replace("__EXPECTED_VW__", str(width)))
                if info["docScrollW"] > width + 1:
                    failures.append(
                        f"[OVERFLOW] {vp_name} {route}: "
                        f"scrollWidth={info['docScrollW']} > {width}; "
                        f"offenders={info['overflows']}"
                    )
                    vp_issues += 1
                if info["headerOverlap"]:
                    failures.append(
                        f"[HEADER OVERLAP] {vp_name} {route}: controls={info['controls']}"
                    )
                    vp_issues += 1

                is_sphinx = route.startswith("/docs/head/")
                if not is_sphinx:
                    if width <= 768 and info["isWide"]:
                        failures.append(
                            f"[NAVBAR] {vp_name} {route}: expected collapsed menu, got is-wide=True"
                        )
                        vp_issues += 1
                    if width >= 1280 and not info["isWide"]:
                        failures.append(
                            f"[NAVBAR] {vp_name} {route}: "
                            "expected inline wide nav, got is-wide=False"
                        )
                        vp_issues += 1

                for ctrl in info["controls"]:
                    if ctrl["left"] < -1 or ctrl["right"] > width + 1:
                        failures.append(
                            f"[CLIPPED CONTROL] {vp_name} {route}: {ctrl['sel']} bounds "
                            f"[{ctrl['left']}, {ctrl['right']}] outside [0, {width}]"
                        )
                        vp_issues += 1
                    if is_mobile and ctrl["isButton"] and (ctrl["w"] < 36 or ctrl["h"] < 36):
                        failures.append(
                            f"[TOUCH TARGET] {vp_name} {route}: {ctrl['sel']} is "
                            f"{ctrl['w']}x{ctrl['h']}px (< 36px)"
                        )
                        vp_issues += 1

            print(f"  {vp_name:18} -> {len(routes)} routes checked (issues: {vp_issues})")

        # Interactive mobile component checks (390x844)
        home_route = f"{base_path}/"
        set_viewport(cdp, 390, 844, True, 3.0, "light")
        navigate(cdp, f"{base_url}{home_route}")

        tabs_ok = eval_js(
            cdp,
            """(() => {
              const cli = document.getElementById('hero-tab-cli');
              const docker = document.getElementById('hero-tab-docker');
              const py = document.getElementById('hero-tab-python');
              if (!cli || !docker || !py) return false;
              cli.click();
              const cOk = !document.getElementById('hero-panel-cli').hidden;
              docker.click();
              const dOk = !document.getElementById('hero-panel-docker').hidden;
              py.click();
              const noOverflow = document.documentElement.scrollWidth <= window.innerWidth + 1;
              return cOk && dOk && noOverflow;
            })()""",
        )
        if not tabs_ok:
            failures.append(f"[INTERACTIVE] Hero quickstart tabs failed on {home_route}")

        theme_res = eval_js(
            cdp,
            """(() => {
              const beforeBg = getComputedStyle(document.body).backgroundColor;
              document.querySelector('.theme-toggle').click();
              const afterBg = getComputedStyle(document.body).backgroundColor;
              const meta = document.querySelector('meta[name="color-scheme"]').content;
              localStorage.removeItem('color-scheme');
              document.querySelector('meta[name="color-scheme"]').content = 'light dark';
              return { changed: beforeBg !== afterBg, meta };
            })()""",
        )
        if not theme_res.get("changed") or theme_res.get("meta") != "dark":
            failures.append(f"[INTERACTIVE] Theme toggle failed: {theme_res}")

        menu_pt = eval_js(
            cdp,
            "(() => { const r = document.querySelector('.menu-button').getBoundingClientRect(); "
            "return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()",
        )
        click_point(cdp, menu_pt["x"], menu_pt["y"])
        time.sleep(0.1)
        menu_state = eval_js(
            cdp,
            """(() => {
              const m = document.getElementById('site-menu');
              const r = m.getBoundingClientRect();
              return {
                open: m.matches(':popover-open'),
                left: Math.round(r.left),
                right: Math.round(r.right)
              };
            })()""",
        )
        if not menu_state["open"] or menu_state["left"] < 0 or menu_state["right"] > 390:
            failures.append(f"[INTERACTIVE] Mobile menu popover geometry invalid: {menu_state}")
        click_point(cdp, 15, 500)
        time.sleep(0.1)
        if eval_js(cdp, "document.getElementById('site-menu').matches(':popover-open')"):
            failures.append(
                "[INTERACTIVE] Mobile menu popover did not light-dismiss on outside tap"
            )

        eval_js(cdp, "document.querySelector('.search-trigger').click()")
        search_state = _wait_for_search_hits(cdp, "save-otio")
        expected_prefix = f"{base_path}/"
        top_hit = search_state.get("topHit") or ""
        if (
            not search_state.get("open")
            or search_state.get("hitCount", 0) == 0
            or not top_hit.startswith(expected_prefix)
            or search_state.get("left", -1) < 0
            or search_state.get("right", 999) > 390
        ):
            failures.append(f"[INTERACTIVE] Mobile search modal check failed: {search_state}")
        backdrop_y = min(820, int(search_state.get("bottom", 400)) + 40)
        click_point(cdp, 195, backdrop_y)
        time.sleep(0.1)
        if eval_js(cdp, "document.getElementById('search-dialog').open"):
            failures.append("[INTERACTIVE] Mobile search modal did not dismiss on backdrop tap")

        if sphinx_dir is not None and (sphinx_dir / "cli.html").is_file():
            navigate(cdp, f"{base_url}/docs/head/cli.html")
            vpt = eval_js(
                cdp,
                "(() => { const r = document.querySelector('.psd-version-btn')"
                ".getBoundingClientRect(); "
                "return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()",
            )
            click_point(cdp, vpt["x"], vpt["y"])
            time.sleep(0.12)
            vmenu = eval_js(
                cdp,
                """(() => {
                  const m = document.getElementById('psd-version-menu');
                  const r = m.getBoundingClientRect();
                  return {
                    open: m.matches(':popover-open'),
                    left: Math.round(r.left),
                    right: Math.round(r.right)
                  };
                })()""",
            )
            if not vmenu["open"] or vmenu["left"] < 0 or vmenu["right"] > 390:
                failures.append(f"[INTERACTIVE] Sphinx version switcher failed: {vmenu}")

        for err in http_errors:
            failures.append(f"[LOCAL ASSET] {err}")

        if screenshots_dir is not None:
            print(f"Capturing screenshot pack into {screenshots_dir} ...")
            shots = capture_curated_pack(cdp, base_url, base_path, sphinx_dir, screenshots_dir)
            write_contact_sheet(screenshots_dir, shots, total_checks, len(routes), failures)
            print(f"Wrote {len(shots)} screenshots + {screenshots_dir / 'index.html'}")

    finally:
        cdp.close()
        proc.kill()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)
        server.shutdown()
        server.server_close()
        shutil.rmtree(profile_dir, ignore_errors=True)

    if failures:
        print(f"\nLayout verification FAILED with {len(failures)} issue(s):", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print(
        f"Layout verification passed ({total_checks} viewport checks "
        "+ interactive flows, 0 issues)."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify PySceneDetect responsive website layout and capture screenshots."
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_BUILD_DIR,
        help="Built website directory (default: website/build).",
    )
    parser.add_argument(
        "--base-path",
        default="",
        help="URL prefix where --build-dir is mounted (e.g. '/staging').",
    )
    parser.add_argument(
        "--sphinx-dir",
        type=Path,
        default=None,
        help="Optional built Sphinx HTML directory mounted at /docs/head/ and /docs/latest/.",
    )
    parser.add_argument(
        "--screenshots",
        type=Path,
        default=None,
        help="Optional output directory for PNG screenshots and index.html contact sheet.",
    )
    parser.add_argument(
        "--browser",
        default=None,
        help="Optional path to Chrome, Chromium, or Edge executable.",
    )
    args = parser.parse_args(argv)

    try:
        browser_bin = find_browser(args.browser)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return run_audit(
        build_dir=args.build_dir.resolve(),
        base_path=normalize_base_path(args.base_path),
        sphinx_dir=args.sphinx_dir.resolve() if args.sphinx_dir else None,
        screenshots_dir=args.screenshots.resolve() if args.screenshots else None,
        browser_bin=browser_bin,
    )


if __name__ == "__main__":
    raise SystemExit(main())
