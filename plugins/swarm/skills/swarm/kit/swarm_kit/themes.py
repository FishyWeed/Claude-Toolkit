"""One visual system shared by decks, documents, videos and the gallery."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    name: str
    dark: bool
    bg: str  # slide / page background
    surface: str  # cards, table bands
    text: str
    muted: str
    accent: str  # titles' accent bar, links, chart series 1
    accent2: str  # second accent, chart series 2
    on_accent: str  # text drawn on an accent fill
    heading_font: str = "Georgia"
    body_font: str = "Calibri"

    @property
    def heading_stack(self) -> str:
        return f'"{self.heading_font}", Georgia, "Times New Roman", serif'

    @property
    def body_stack(self) -> str:
        return f'"{self.body_font}", "Segoe UI", system-ui, -apple-system, sans-serif'

    @property
    def chart_colors(self) -> list[str]:
        """Series colours for matplotlib, in order; colour-blind-safe after the two accents."""
        return [self.accent, self.accent2, "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]


THEMES: dict[str, Theme] = {
    "midnight": Theme(
        name="midnight", dark=True,
        bg="#0F172A", surface="#1E293B", text="#F1F5F9", muted="#94A3B8",
        accent="#38BDF8", accent2="#F472B6", on_accent="#0F172A",
    ),
    "paper": Theme(
        name="paper", dark=False,
        bg="#FAFAF7", surface="#F0EEE8", text="#1C1917", muted="#6B6560",
        accent="#C2410C", accent2="#0F766E", on_accent="#FFFFFF",
    ),
    "ocean": Theme(
        name="ocean", dark=False,
        bg="#F8FAFC", surface="#E8EEF5", text="#0F172A", muted="#5B6B80",
        accent="#0369A1", accent2="#0D9488", on_accent="#FFFFFF",
    ),
    "forest": Theme(
        name="forest", dark=False,
        bg="#F7F9F5", surface="#E7EDE3", text="#1A2E1A", muted="#5C6B5C",
        accent="#2F6B3B", accent2="#B45309", on_accent="#FFFFFF",
    ),
    "ember": Theme(
        name="ember", dark=True,
        bg="#1A1412", surface="#2A211E", text="#FAF3EE", muted="#B8A79D",
        accent="#FB923C", accent2="#FACC15", on_accent="#1A1412",
    ),
}

DEFAULT_THEME = "ocean"


def get_theme(name: str | None) -> Theme:
    if not name:
        return THEMES[DEFAULT_THEME]
    key = name.strip().lower()
    if key not in THEMES:
        raise SystemExit(f"Unknown theme '{name}'. Choose one of: {', '.join(THEMES)}")
    return THEMES[key]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


# --- Fonts for raster work (Pillow): the theme's fonts where installed, else matplotlib's DejaVu ---

_FONT_FILES = {
    ("Calibri", False): ["calibri.ttf"],
    ("Calibri", True): ["calibrib.ttf"],
    ("Georgia", False): ["georgia.ttf", "Georgia.ttf"],
    ("Georgia", True): ["georgiab.ttf", "Georgia Bold.ttf"],
}


def _font_dirs() -> list[Path]:
    dirs: list[Path] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(Path(windir) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs += [Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    else:
        dirs += [Path("/usr/share/fonts"), Path.home() / ".fonts"]
    return dirs


def font_path(family: str, bold: bool = False) -> str:
    for name in _FONT_FILES.get((family, bold), []):
        for folder in _font_dirs():
            candidate = folder / name
            if candidate.exists():
                return str(candidate)
    import matplotlib

    fallback = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    if family == "Georgia":
        fallback = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    return str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / fallback)


def apply_matplotlib(theme_name: str | None = None) -> Theme:
    """Style matplotlib charts to match the theme. Call before plotting."""
    import matplotlib as mpl
    from cycler import cycler

    theme = get_theme(theme_name)
    mpl.rcParams.update({
        "figure.figsize": (8, 4.5),
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "figure.facecolor": theme.bg,
        "axes.facecolor": theme.bg,
        "savefig.facecolor": theme.bg,
        "axes.edgecolor": theme.muted,
        "axes.labelcolor": theme.text,
        "axes.titlecolor": theme.text,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": theme.surface,
        "grid.linewidth": 0.8,
        "xtick.color": theme.muted,
        "ytick.color": theme.muted,
        "text.color": theme.text,
        "legend.frameon": False,
        "font.size": 11,
        "axes.prop_cycle": cycler(color=theme.chart_colors),
    })
    return theme
