"""What this machine can do for each specialist: tools, packages and API keys (never their values)."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys

from . import __version__
from .browser import find_browser

KEYS = {
    "OPENROUTER_API_KEY": "AI image generation and editing (image-maker)",
    "GOOGLE_API_KEY": "Gemini images and Veo video",
    "FAL_KEY": "fal.ai video generation and effects",
    "OPENAI_API_KEY": "Sora video",
    "EXA_API_KEY": "Exa search (optional; web search works without it)",
}

PACKAGES = {"pptx": "python-pptx", "docx": "python-docx", "PIL": "pillow", "matplotlib": "matplotlib", "pandas": "pandas",
            "scipy": "scipy", "statsmodels": "statsmodels", "openpyxl": "openpyxl"}


def report() -> dict:
    packages = {}
    for module, name in PACKAGES.items():
        try:
            importlib.import_module(module)
            packages[name] = True
        except Exception:
            packages[name] = False
    ffmpeg = shutil.which("ffmpeg")
    ffmpeg_version = None
    if ffmpeg:
        try:
            first = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
            ffmpeg_version = first.split()[2] if len(first.split()) > 2 else first
        except Exception:
            pass
    browser = find_browser()
    keys = {k: bool(os.environ.get(k)) for k in KEYS}
    can = {
        "researcher": "ready",
        "data-analyst": "ready" if packages["pandas"] and packages["matplotlib"] else "missing pandas/matplotlib",
        "slides-designer": "ready" if packages["python-pptx"] else "missing python-pptx",
        "docs-writer": "ready" if packages["python-docx"] else "missing python-docx",
        "image-maker": "AI images" if keys["OPENROUTER_API_KEY"] else "drawn SVG/PNG only (set OPENROUTER_API_KEY for AI images)",
        "video-maker": ("slideshows + AI footage" if (keys["FAL_KEY"] or keys["GOOGLE_API_KEY"] or keys["OPENAI_API_KEY"]) else "slideshows and edits (no AI footage key)")
        if ffmpeg else "missing ffmpeg",
    }
    if not browser:
        can["slides-designer"] += "; no PDF (no Edge/Chrome)"
        can["docs-writer"] += "; no PDF (no Edge/Chrome)"
    return {
        "kit_version": __version__,
        "python": sys.version.split()[0],
        "python_path": sys.executable,
        "packages": packages,
        "ffmpeg": ffmpeg_version if ffmpeg else None,
        "browser": browser,
        "keys": keys,
        "specialists": can,
    }


def text(rep: dict) -> str:
    lines = [f"swarm_kit {rep['kit_version']} · Python {rep['python']} ({rep['python_path']})"]
    missing = [n for n, ok in rep["packages"].items() if not ok]
    lines.append("Packages: " + ("all present" if not missing else "missing " + ", ".join(missing)))
    lines.append(f"ffmpeg: {rep['ffmpeg'] or 'not found'}")
    lines.append(f"Browser for PDF/PNG: {rep['browser'] or 'not found'}")
    lines.append("Keys: " + ", ".join(f"{k} {'set' if v else 'unset'}" for k, v in rep["keys"].items()))
    lines.append("Specialists:")
    lines += [f"  {name}: {status}" for name, status in rep["specialists"].items()]
    return "\n".join(lines)
