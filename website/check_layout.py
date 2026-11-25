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
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

WEBSITE_DIR = Path(__file__).resolve().parent
DEFAULT_BUILD_DIR = WEBSITE_DIR / "build"

DEVICE_SCALE_FACTOR = 2.0
SPHINX_PREFIX = "/docs/head/"

VIEWPORTS: list[tuple[str, int, int, bool]] = [
    ("Mobile 320x568", 320, 568, True),
    ("Mobile 375x812", 375, 812, True),
    ("Mobile 390x844", 390, 844, True),
    ("Tablet 768x1024", 768, 1024, True),
    ("Desktop 1280x800", 1280, 800, False),
]

# Screenshot devices: width, height, mobile.
DEVICES: dict[str, tuple[int, int, bool]] = {
    "desktop": (1280, 800, False),
    "mobile": (390, 844, True),
    "mobile-320": (320, 568, True),
}

SPHINX_SAMPLE_PAGES: tuple[str, ...] = (
    "index.html",
    "cli.html",
    "api.html",
    "api/detectors.html",
    "examples.html",
)

AUDIT_JS_TEMPLATE = """
(() => {
  const vw = __EXPECTED_VW__;
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
    docScrollW,
    isWide,
    headerOverlap,
    controls,
    overflows: overflows.slice(0, 6)
  };
})()
"""


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
        fragments = bytearray()
        message_opcode: int | None = None
        while True:
            b1, b2 = self._recv_exact(2)
            fin = bool(b1 & 0x80)
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
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                if message_opcode is not None:
                    raise RuntimeError("Unexpected WebSocket text frame before previous FIN")
                if fin:
                    return data.decode("utf-8")
                message_opcode = 0x1
                fragments.extend(data)
            elif opcode == 0x0:
                if message_opcode is None:
                    raise RuntimeError("Unexpected WebSocket continuation frame")
                fragments.extend(data)
                if fin:
                    payload = bytes(fragments)
                    fragments.clear()
                    if message_opcode == 0x1:
                        return payload.decode("utf-8")
                    message_opcode = None
            elif opcode == 0x2:
                if message_opcode is not None:
                    raise RuntimeError("Unexpected WebSocket binary frame before previous FIN")
                if not fin:
                    message_opcode = 0x2
                    fragments.extend(data)

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
    sphinx_dir: Path | None,
    http_errors: list[str],
) -> tuple[http.server.ThreadingHTTPServer, int]:
    """Serve build_dir at / (plus optional sphinx_dir at /docs/head/ & /docs/latest/)."""

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

            return _resolve_mounted_file(build_dir, url_path)

        def do_GET(self) -> None:
            url_path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            target = self._locate_target(url_path)
            if target is None:
                if url_path != "/404.html" and not url_path.endswith("/favicon.ico"):
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
    scheme: str,
) -> None:
    cdp.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": DEVICE_SCALE_FACTOR,
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


def discover_routes(build_dir: Path, sphinx_dir: Path | None) -> list[str]:
    """Collect all built website HTML routes plus representative Sphinx routes when provided."""
    routes: list[str] = []
    for html_file in sorted(build_dir.rglob("*.html")):
        if 'http-equiv="refresh"' in html_file.read_text(encoding="utf-8", errors="ignore"):
            continue
        rel = html_file.relative_to(build_dir).as_posix()
        if rel == "index.html":
            routes.append("/")
        elif rel.endswith("/index.html"):
            slug = rel[: -len("/index.html")]
            routes.append(f"/{slug}/")
        else:
            routes.append(f"/{rel}")

    routes.sort(key=lambda r: (0 if r == "/" else 1, r))

    if sphinx_dir is not None:
        for sample in SPHINX_SAMPLE_PAGES:
            if (sphinx_dir / sample).is_file():
                routes.append(f"{SPHINX_PREFIX}{sample}")

    return routes


def click_selector(cdp: SimpleWS, selector: str) -> None:
    """Click the centre of the first element that matches selector."""
    pt = eval_js(
        cdp,
        f"(() => {{ const r = document.querySelector({json.dumps(selector)})"
        ".getBoundingClientRect(); "
        "return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()",
    )
    click_point(cdp, pt["x"], pt["y"])


def popover_state(cdp: SimpleWS, element_id: str) -> dict[str, Any]:
    """Return whether the popover is open, plus its left and right bounds."""
    return eval_js(
        cdp,
        f"""(() => {{
          const m = document.getElementById({json.dumps(element_id)});
          const r = m.getBoundingClientRect();
          return {{
            open: m.matches(':popover-open'),
            left: Math.round(r.left),
            right: Math.round(r.right)
          }};
        }})()""",
    )


class BrowserLaunchError(RuntimeError):
    """Raised when the headless browser does not expose a CDP endpoint."""


@contextlib.contextmanager
def launch_browser(browser_bin: Path) -> Iterator[str]:
    """Start a headless browser and yield the CDP WebSocket URL of its first page."""
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
        raise BrowserLaunchError(
            "Timed out waiting for headless browser CDP endpoint.\n"
            f"Browser stderr tail:\n{stderr_log}"
        )

    try:
        yield ws_url
    finally:
        proc.kill()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)
        shutil.rmtree(profile_dir, ignore_errors=True)


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


def _open_mobile_menu(cdp: SimpleWS) -> None:
    click_selector(cdp, ".menu-button")
    time.sleep(0.1)


def _open_search(query: str) -> Callable[[SimpleWS], None]:
    def action(cdp: SimpleWS) -> None:
        eval_js(cdp, "document.querySelector('.search-trigger').click()")
        _wait_for_search_hits(cdp, query)

    return action


def _open_version_menu(cdp: SimpleWS) -> None:
    click_selector(cdp, ".psd-version-btn")
    time.sleep(0.12)


# Each row: file name, route, device, colour scheme, optional action before the shot.
SHOTS: list[tuple[str, str, str, str, Callable[[SimpleWS], None] | None]] = [
    ("desktop-home-light.png", "/", "desktop", "light", None),
    ("desktop-home-dark.png", "/", "desktop", "dark", None),
    ("desktop-features-light.png", "/features/", "desktop", "light", None),
    ("desktop-download-dark.png", "/download/", "desktop", "dark", None),
    ("desktop-cli-light.png", "/cli/", "desktop", "light", None),
    ("desktop-benchmarks-dark.png", "/benchmarks/", "desktop", "dark", None),
    ("desktop-projects-light.png", "/projects/", "desktop", "light", None),
    ("mobile-home-light.png", "/", "mobile", "light", None),
    ("mobile-home-dark.png", "/", "mobile", "dark", None),
    ("mobile-320-home-dark.png", "/", "mobile-320", "dark", None),
    ("mobile-cli-dark.png", "/cli/", "mobile", "dark", None),
    ("mobile-benchmarks-light.png", "/benchmarks/", "mobile", "light", None),
    ("mobile-download-light.png", "/download/", "mobile", "light", None),
    ("mobile-404-light.png", "/404.html", "mobile", "light", None),
    ("mobile-menu-open.png", "/", "mobile", "light", _open_mobile_menu),
    ("mobile-search-open.png", "/", "mobile", "dark", _open_search("save-otio")),
    ("desktop-search-open.png", "/", "desktop", "dark", _open_search("AdaptiveDetector")),
    ("sphinx-desktop-home-dark.png", "/docs/head/index.html", "desktop", "dark", None),
    ("sphinx-desktop-cli-light.png", "/docs/head/cli.html", "desktop", "light", None),
    (
        "sphinx-mobile-cli-versions-dark.png",
        "/docs/head/cli.html",
        "mobile",
        "dark",
        _open_version_menu,
    ),
    ("sphinx-mobile-detectors-light.png", "/docs/head/api/detectors.html", "mobile", "light", None),
]


def capture_curated_pack(
    cdp: SimpleWS,
    base_url: str,
    sphinx_dir: Path | None,
    shots_dir: Path,
) -> int:
    """Capture the screenshot pack from SHOTS and return the number of PNG files written."""
    shots_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for filename, route, device, scheme, before in SHOTS:
        is_sphinx = route.startswith(SPHINX_PREFIX)
        if is_sphinx and (
            sphinx_dir is None or not (sphinx_dir / route[len(SPHINX_PREFIX) :]).is_file()
        ):
            continue
        width, height, mobile = DEVICES[device]
        set_viewport(cdp, width, height, mobile, scheme)
        navigate(cdp, f"{base_url}{route}")
        if before is not None:
            before(cdp)
        save_screenshot(cdp, shots_dir / filename)
        count += 1
    return count


def audit_page(
    cdp: SimpleWS, vp_name: str, route: str, width: int, is_mobile: bool, base_url: str
) -> list[str]:
    """Load one route at the current viewport and return its layout failure messages."""
    navigate(cdp, f"{base_url}{route}")
    issues: list[str] = []

    for ev in cdp.events:
        if ev.get("method") == "Runtime.exceptionThrown":
            issues.append(f"[JS EXCEPTION] {vp_name} {route}: {ev.get('params')}")

    info = eval_js(cdp, AUDIT_JS_TEMPLATE.replace("__EXPECTED_VW__", str(width)))
    if info["docScrollW"] > width + 1:
        issues.append(
            f"[OVERFLOW] {vp_name} {route}: "
            f"scrollWidth={info['docScrollW']} > {width}; "
            f"offenders={info['overflows']}"
        )
    if info["headerOverlap"]:
        issues.append(f"[HEADER OVERLAP] {vp_name} {route}: controls={info['controls']}")

    if not route.startswith(SPHINX_PREFIX):
        if width <= 768 and info["isWide"]:
            issues.append(f"[NAVBAR] {vp_name} {route}: expected collapsed menu, got is-wide=True")
        if width >= 1280 and not info["isWide"]:
            issues.append(
                f"[NAVBAR] {vp_name} {route}: expected inline wide nav, got is-wide=False"
            )

    for ctrl in info["controls"]:
        if ctrl["left"] < -1 or ctrl["right"] > width + 1:
            issues.append(
                f"[CLIPPED CONTROL] {vp_name} {route}: {ctrl['sel']} bounds "
                f"[{ctrl['left']}, {ctrl['right']}] outside [0, {width}]"
            )
        if is_mobile and ctrl["isButton"] and (ctrl["w"] < 36 or ctrl["h"] < 36):
            issues.append(
                f"[TOUCH TARGET] {vp_name} {route}: {ctrl['sel']} is "
                f"{ctrl['w']}x{ctrl['h']}px (< 36px)"
            )
    return issues


def run_checks(
    cdp: SimpleWS,
    base_url: str,
    routes: list[str],
    sphinx_dir: Path | None,
    screenshots_dir: Path | None,
    http_errors: list[str],
) -> tuple[list[str], int]:
    """Run all viewport and interactive checks. Return the failures and the viewport check count."""
    failures: list[str] = []
    total_checks = 0
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")

    print(f"Auditing {len(routes)} routes across {len(VIEWPORTS)} viewports...")

    for vp_name, width, height, is_mobile in VIEWPORTS:
        set_viewport(cdp, width, height, is_mobile, "light")
        vp_failures: list[str] = []
        for route in routes:
            total_checks += 1
            vp_failures.extend(audit_page(cdp, vp_name, route, width, is_mobile, base_url))
        failures.extend(vp_failures)
        print(f"  {vp_name:18} -> {len(routes)} routes checked (issues: {len(vp_failures)})")

    # Interactive mobile component checks on the home page (390x844)
    set_viewport(cdp, 390, 844, True, "light")
    navigate(cdp, f"{base_url}/")

    platform_tabs_ok = eval_js(
        cdp,
        """(() => {
          const hitOk = (el) => {
            if (!el) return false;
            el.scrollIntoView({ block: 'center', inline: 'nearest' });
            const r = el.getBoundingClientRect();
            const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return Boolean(top && (top === el || el.contains(top)));
          };
          const py = document.getElementById('platform-tab-python');
          const win = document.getElementById('platform-tab-windows');
          const doc = document.getElementById('platform-tab-docker');
          const card = document.querySelector('.platform-card');
          if (!py || !win || !doc || !card) return false;
          const hPy = Math.round(card.getBoundingClientRect().height);
          const pyHit = hitOk(document.getElementById('install-tab-uv'))
            && hitOk(document.getElementById('hero-tab-cli'))
            && hitOk(document.getElementById('hero-tab-api'))
            && hitOk(document.querySelector('#install-panel-pip .copy-inline-btn'));
          win.click();
          const hWin = Math.round(card.getBoundingClientRect().height);
          const wOk = !document.getElementById('platform-panel-windows').hidden
            && Boolean(document.getElementById('platform-panel-python').hidden)
            && hitOk(document.querySelector('#platform-panel-windows .install-dl-btn'));
          doc.click();
          const hDoc = Math.round(card.getBoundingClientRect().height);
          const dOk = !document.getElementById('platform-panel-docker').hidden
            && Boolean(document.getElementById('platform-panel-windows').hidden)
            && hitOk(document.querySelector('#platform-panel-docker .copy-inline-btn'));
          py.click();
          const copyBtns = document.querySelectorAll('.platform-card .copy-code-btn').length;
          const sameHeight = Math.abs(hPy - hWin) <= 1 && Math.abs(hPy - hDoc) <= 1;
          const noOverflow = document.documentElement.scrollWidth <= window.innerWidth + 1;
          return pyHit && wOk && dOk && copyBtns === 6 && sameHeight && noOverflow;
        })()""",
    )
    if not platform_tabs_ok:
        failures.append("[INTERACTIVE] Hero platform tabs failed on /")

    python_subtabs_ok = eval_js(
        cdp,
        """(() => {
          const pip = document.getElementById('install-tab-pip');
          const uv = document.getElementById('install-tab-uv');
          const pipx = document.getElementById('install-tab-pipx');
          const cli = document.getElementById('hero-tab-cli');
          const api = document.getElementById('hero-tab-api');
          if (!pip || !uv || !pipx || !api || !cli) return false;
          const defaultCliOk = cli.nextElementSibling === api
            && cli.getAttribute('aria-selected') === 'true'
            && !document.getElementById('install-panel-pip').hidden
            && !document.getElementById('hero-panel-cli').hidden
            && Boolean(document.getElementById('hero-panel-api').hidden);
          uv.click();
          const uOk = !document.getElementById('install-panel-uv').hidden
            && !document.getElementById('hero-panel-cli').hidden;
          pipx.click();
          const pOk = !document.getElementById('install-panel-pipx').hidden
            && !document.getElementById('hero-panel-cli').hidden;
          pip.click();
          const pipStayCliOk = !document.getElementById('install-panel-pip').hidden
            && !document.getElementById('hero-panel-cli').hidden;
          api.click();
          const manualApiOk = !document.getElementById('hero-panel-api').hidden
            && !document.getElementById('install-panel-pip').hidden;
          uv.click();
          const uvSyncCliOk = !document.getElementById('install-panel-uv').hidden
            && !document.getElementById('hero-panel-cli').hidden;
          pip.click();
          const noOverflow = document.documentElement.scrollWidth <= window.innerWidth + 1;
          return defaultCliOk && uOk && pOk && pipStayCliOk && manualApiOk
            && uvSyncCliOk && noOverflow;
        })()""",
    )
    if not python_subtabs_ok:
        failures.append("[INTERACTIVE] Hero Python install/example tabs failed on /")

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

    _open_mobile_menu(cdp)
    menu_state = popover_state(cdp, "site-menu")
    if not menu_state["open"] or menu_state["left"] < 0 or menu_state["right"] > 390:
        failures.append(f"[INTERACTIVE] Mobile menu popover geometry invalid: {menu_state}")
    click_point(cdp, 15, 500)
    time.sleep(0.1)
    if eval_js(cdp, "document.getElementById('site-menu').matches(':popover-open')"):
        failures.append("[INTERACTIVE] Mobile menu popover did not light-dismiss on outside tap")

    eval_js(cdp, "document.querySelector('.search-trigger').click()")
    search_state = _wait_for_search_hits(cdp, "save-otio")
    top_hit = search_state.get("topHit") or ""
    if (
        not search_state.get("open")
        or search_state.get("hitCount", 0) == 0
        or not top_hit.startswith("/")
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
        navigate(cdp, f"{base_url}{SPHINX_PREFIX}cli.html")
        _open_version_menu(cdp)
        vmenu = popover_state(cdp, "psd-version-menu")
        if not vmenu["open"] or vmenu["left"] < 0 or vmenu["right"] > 390:
            failures.append(f"[INTERACTIVE] Sphinx version switcher failed: {vmenu}")

    for err in http_errors:
        failures.append(f"[LOCAL ASSET] {err}")

    if screenshots_dir is not None:
        print(f"Capturing screenshot pack into {screenshots_dir} ...")
        shot_count = capture_curated_pack(cdp, base_url, sphinx_dir, screenshots_dir)
        print(f"Wrote {shot_count} screenshots to {screenshots_dir}")

    return failures, total_checks


def run_audit(
    build_dir: Path,
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

    routes = discover_routes(build_dir, sphinx_dir)
    if not routes:
        print(f"[ERROR] No HTML files found in {build_dir}", file=sys.stderr)
        return 1

    http_errors: list[str] = []
    server, http_port = start_local_server(build_dir, sphinx_dir, http_errors)
    base_url = f"http://127.0.0.1:{http_port}"

    try:
        with launch_browser(browser_bin) as ws_url:
            cdp = SimpleWS(ws_url)
            try:
                print(f"Using browser: {browser_bin}")
                failures, total_checks = run_checks(
                    cdp, base_url, routes, sphinx_dir, screenshots_dir, http_errors
                )
            finally:
                cdp.close()
    except BrowserLaunchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        server.shutdown()
        server.server_close()

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
        "--sphinx-dir",
        type=Path,
        default=None,
        help="Optional built Sphinx HTML directory mounted at /docs/head/ and /docs/latest/.",
    )
    parser.add_argument(
        "--screenshots",
        type=Path,
        default=None,
        help="Optional output directory for PNG screenshots.",
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
        sphinx_dir=args.sphinx_dir.resolve() if args.sphinx_dir else None,
        screenshots_dir=args.screenshots.resolve() if args.screenshots else None,
        browser_bin=browser_bin,
    )


if __name__ == "__main__":
    raise SystemExit(main())
