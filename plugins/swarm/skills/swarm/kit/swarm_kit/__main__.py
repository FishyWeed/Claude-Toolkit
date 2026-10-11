"""swarm_kit command line. Every build command prints a JSON result (paths, warnings) on stdout.

  python -m swarm_kit doctor [--json]
  python -m swarm_kit themes
  python -m swarm_kit deck SPEC.json [--out DIR] [--name deck] [--no-pdf]
  python -m swarm_kit preview DECK.html [--out sheet.png]      (every slide on one PNG, to check by eye)
  python -m swarm_kit doc FILE.md [--out DIR] [--name NAME] [--formats docx,pdf,html]
  python -m swarm_kit video SPEC.json [--out DIR] [--name video]
  python -m swarm_kit png SOURCE.(svg|html) OUT.png [--size 1920x1080]
  python -m swarm_kit pdf PAGE.html OUT.pdf
  python -m swarm_kit gallery FOLDER

In Python, `from swarm_kit.themes import apply_matplotlib; apply_matplotlib("ocean")` styles charts to match.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print(result) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="swarm_kit", description="Builders for the swarm plugin's specialists.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="what this machine can do for each specialist")
    p.add_argument("--json", action="store_true")
    sub.add_parser("themes", help="list the themes and their colours")

    p = sub.add_parser("deck", help="deck spec (JSON) -> HTML + PPTX + PDF")
    p.add_argument("spec", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--name", default="deck")
    p.add_argument("--no-pdf", action="store_true")

    p = sub.add_parser("preview", help="contact sheet PNG of a built deck's slides")
    p.add_argument("deck_html", type=Path)
    p.add_argument("--out", type=Path)

    p = sub.add_parser("doc", help="Markdown -> DOCX + PDF (+ HTML)")
    p.add_argument("markdown", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--name")
    p.add_argument("--formats", default="docx,pdf")

    p = sub.add_parser("video", help="video spec (JSON) -> MP4 (+ SRT)")
    p.add_argument("spec", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--name", default="video")

    p = sub.add_parser("png", help="render an SVG or HTML file to PNG")
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--size", default="1920x1080")

    p = sub.add_parser("pdf", help="print an HTML file to PDF")
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)

    p = sub.add_parser("gallery", help="write index.html for an output folder")
    p.add_argument("folder", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            from . import doctor

            rep = doctor.report()
            print(json.dumps(rep, indent=2) if args.json else doctor.text(rep))
        elif args.command == "themes":
            from .themes import THEMES

            _print({name: {"dark": t.dark, "bg": t.bg, "text": t.text, "accent": t.accent, "accent2": t.accent2} for name, t in THEMES.items()})
        elif args.command == "deck":
            from . import deck

            _print(deck.build(args.spec, args.out, args.name, pdf=not args.no_pdf))
        elif args.command == "preview":
            from . import deck

            _print(deck.preview(args.deck_html, args.out))
        elif args.command == "doc":
            from . import doc

            formats = tuple(f.strip().lower() for f in args.formats.split(",") if f.strip())
            _print(doc.build(args.markdown, args.out, args.name, formats))
        elif args.command == "video":
            from . import video

            _print(video.build(args.spec, args.out, args.name))
        elif args.command == "png":
            from .browser import screenshot

            w, h = (int(v) for v in args.size.lower().split("x"))
            _print({"png": str(screenshot(args.source, args.out, w, h))})
        elif args.command == "pdf":
            from .browser import html_to_pdf

            _print({"pdf": str(html_to_pdf(args.source, args.out))})
        elif args.command == "gallery":
            from . import gallery

            _print({"index": str(gallery.build(args.folder))})
    except SystemExit:
        raise
    except Exception as exc:  # one clear line for the agent, not a traceback wall
        _print({"error": f"{type(exc).__name__}: {exc}"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
