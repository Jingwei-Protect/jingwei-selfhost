"""Record the real ProvenPix HoloCard CSS — do not reimplement the look.

Serves frontend/src/holo-card/holo-card.css as-is, then drives the same
--holo-x / --holo-y / --holo-on variables as HoloCard.tsx setVars().
"""

from __future__ import annotations

import http.server
import io
import math
import os
import shutil
import socketserver
import tempfile
import threading
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_HTML = ROOT / "frontend" / "src" / "holo-card" / "capture.html"


def holo_pose(t: float) -> tuple[float, float, float]:
    """Slow rock plus a foil sweep for the downloadable clip.

    Keeps --holo-on up so the laser stays visible while the card tilts.
    """
    t = min(1.0, max(0.0, t))
    phase = 2.0 * math.pi * (0.35 + 1.15 * t)
    x = 0.5 + 0.34 * math.sin(phase)
    y = 0.5 + 0.22 * math.sin(phase * 0.82 + 0.55)
    on = 0.38 + 0.40 * (0.5 + 0.5 * math.sin(phase * 2.0))
    return (
        min(1.0, max(0.0, x)),
        min(1.0, max(0.0, y)),
        min(1.0, max(0.0, on)),
    )


def _even_crop(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    return rgb[: h - (h % 2), : w - (w % 2)]


def _tight_crop_frames(frames: list[np.ndarray], *, margin: int = 56) -> list[np.ndarray]:
    """Crop shared empty canvas so the card fills the clip."""
    bg = np.array([247, 249, 252], dtype=np.int16)
    ys_all: list[int] = []
    xs_all: list[int] = []
    for frame in frames:
        diff = np.abs(frame.astype(np.int16) - bg).sum(axis=2)
        ys, xs = np.where(diff > 22)
        if ys.size:
            ys_all.extend((int(ys.min()), int(ys.max())))
            xs_all.extend((int(xs.min()), int(xs.max())))
    if not ys_all:
        return [_even_crop(f) for f in frames]
    h, w = frames[0].shape[:2]
    y0 = max(0, min(ys_all) - margin)
    y1 = min(h, max(ys_all) + margin + 1)
    x0 = max(0, min(xs_all) - margin)
    x1 = min(w, max(xs_all) + margin + 1)
    return [_even_crop(f[y0:y1, x0:x1]) for f in frames]


class _RootHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _existing_bin(*candidates: str) -> str | None:
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def chrome_launch_paths() -> tuple[str | None, str | None]:
    """Resolve Chrome / Chromium and chromedriver for laptops and Docker."""
    binary = os.environ.get("CHROME_BIN") or _existing_bin(
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    )
    driver = os.environ.get("CHROMEDRIVER") or _existing_bin("/usr/bin/chromedriver")
    return binary, driver


def apply_capture_chrome_flags(options: object, *, window_size: str, scale: float) -> None:
    """Headless flags that work on a desktop and inside the production container."""
    add = getattr(options, "add_argument")
    add("--headless=new")
    add(f"--window-size={window_size}")
    add("--hide-scrollbars")
    add(f"--force-device-scale-factor={max(1.0, float(scale)):.3f}")
    add("--allow-file-access-from-files")
    add("--no-sandbox")
    add("--disable-dev-shm-usage")
    add("--disable-gpu")
    add("--disable-extensions")


def _serve_root() -> tuple[socketserver.TCPServer, str]:
    handler = lambda *a, **k: _RootHandler(*a, directory=str(ROOT), **k)  # noqa: E731
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def capture_css_frames(
    image_path: Path,
    *,
    n_frames: int = 60,
    scale: float = 2.0,
    window_size: str = "780,1040",
) -> list[np.ndarray]:
    """Open headless Chrome, drive HoloCard CSS variables, return RGB frames."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:
        raise RuntimeError("需要 selenium：pip install selenium") from exc

    if not CAPTURE_HTML.is_file():
        raise FileNotFoundError(CAPTURE_HTML)
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise FileNotFoundError(image_path)

    rel_html = CAPTURE_HTML.relative_to(ROOT).as_posix()
    tmp_dir: str | None = None
    try:
        rel_img = image_path.relative_to(ROOT).as_posix()
    except ValueError:
        tmp_dir = tempfile.mkdtemp(prefix="jw_holo_in_", dir=str(ROOT))
        dest = Path(tmp_dir) / "face.jpg"
        shutil.copyfile(image_path, dest)
        rel_img = dest.relative_to(ROOT).as_posix()
    server, origin = _serve_root()
    url = f"{origin}/{rel_html}?img=/{rel_img}"

    options = Options()
    apply_capture_chrome_flags(options, window_size=window_size, scale=scale)
    binary, driver_path = chrome_launch_paths()
    if binary:
        options.binary_location = binary
    service = None
    if driver_path:
        from selenium.webdriver.chrome.service import Service

        service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(options=options, service=service) if service else webdriver.Chrome(options=options)
    frames: list[np.ndarray] = []
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return typeof window.setHolo === 'function'"))
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script(
                "const i=document.getElementById('face');"
                "return !!(i && i.complete && i.naturalWidth > 0);"
            )
        )
        pad = driver.find_element(By.CSS_SELECTOR, ".stage-pad")
        for i in range(n_frames):
            x, y, on = holo_pose(i / max(1, n_frames - 1))
            driver.execute_script(
                "window.setHolo(arguments[0], arguments[1], arguments[2])",
                x,
                y,
                on,
            )
            png = pad.screenshot_as_png
            frame = np.array(Image.open(io.BytesIO(png)).convert("RGB"), dtype=np.uint8)
            frames.append(frame)
    finally:
        driver.quit()
        server.shutdown()
        server.server_close()
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if len(frames) != n_frames:
        raise RuntimeError("CSS capture produced no frames.")
    return _tight_crop_frames(frames)
