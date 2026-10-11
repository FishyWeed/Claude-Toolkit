"""A headless Chromium (Edge or Chrome) for HTML -> PDF and HTML/SVG -> PNG."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_browser() -> str | None:
    env = os.environ.get("SWARM_BROWSER")
    if env and Path(env).exists():
        return env
    candidates: list[str] = []
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if not base:
                continue
            candidates += [
                str(Path(base) / "Microsoft/Edge/Application/msedge.exe"),
                str(Path(base) / "Google/Chrome/Application/chrome.exe"),
            ]
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    for name in ("msedge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _run(args: list[str], out: Path, timeout: int = 120) -> None:
    browser = find_browser()
    if not browser:
        raise RuntimeError("No Edge or Chrome found for rendering. Install one, or set SWARM_BROWSER to its path.")
    with tempfile.TemporaryDirectory(prefix="swarm-browser-") as profile:
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--hide-scrollbars", f"--user-data-dir={profile}",
            "--virtual-time-budget=4000", *args,
        ]
        if out.exists():
            out.unlink()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"The browser did not write {out}")


def html_to_pdf(html: Path, pdf: Path) -> Path:
    html, pdf = Path(html).resolve(), Path(pdf).resolve()
    pdf.parent.mkdir(parents=True, exist_ok=True)
    _run(["--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={pdf}", html.as_uri()], pdf)
    return pdf


_CHROME_SLACK = 240  # headless windows lose some height to browser chrome; render taller, then crop


def screenshot(source: Path, png: Path, width: int, height: int, fragment: str = "") -> Path:
    """Renders an HTML or SVG file at exactly width x height to a PNG.

    The page is loaded into a frame of that exact size (so its viewport is right whatever the
    browser's window chrome takes), the window is made taller, and the shot is cropped back.
    `fragment` is appended to the URL, e.g. "#3" for a deck's third slide.
    """
    from PIL import Image

    source, png = Path(source).resolve(), Path(png).resolve()
    png.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".svg":
        inner = f"<img src='{source.as_uri()}' style='display:block;width:{width}px;height:{height}px;object-fit:contain'>"
    else:
        inner = f"<iframe scrolling='no' src='{source.as_uri()}{fragment}' style='display:block;border:0;width:{width}px;height:{height}px'></iframe>"
    with tempfile.TemporaryDirectory(prefix="swarm-shot-") as tmp:
        wrapper = Path(tmp) / "frame.html"
        wrapper.write_text(
            "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;padding:0;overflow:hidden;background:transparent}</style>" + inner,
            encoding="utf-8",
        )
        raw = Path(tmp) / "raw.png"
        _run([f"--window-size={width + _CHROME_SLACK},{height + _CHROME_SLACK}", "--default-background-color=00000000",
              "--allow-file-access-from-files", f"--screenshot={raw}", wrapper.as_uri()], raw)
        with Image.open(raw) as im:
            im.crop((0, 0, width, height)).save(png)
    return png
