"""index.html for a swarm output folder: every deliverable, grouped, with previews.

Reads manifest.json when present:
{
  "title": "...", "request": "...", "created": "2026-10-10T14:03:00", "theme": "ocean",
  "deliverables": [{"title": "...", "agent": "slides-designer", "status": "done|failed|skipped",
                    "files": ["slides/deck.html", ...], "note": "..."}],
  "issues": ["Photo-realistic images need OPENROUTER_API_KEY"]
}
Without one, it groups the folder's files by kind.
"""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from .themes import THEMES, get_theme

_SKIP_DIRS = {".build", "__pycache__", ".thumbs"}
_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
_VIDEO = {".mp4", ".webm", ".mov"}

AGENT_LABEL = {
    "researcher": "Research", "data-analyst": "Data", "slides-designer": "Slides",
    "docs-writer": "Documents", "image-maker": "Images", "video-maker": "Video",
}


def _files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in _SKIP_DIRS or part.startswith(".") for part in p.relative_to(root).parts) \
                and p.name not in {"index.html", "manifest.json"}:
            out.append(p)
    return out


def _thumb(root: Path, html_file: Path, w: int, h: int) -> str | None:
    """A PNG preview of an HTML deliverable (first slide / first page), when a browser is available."""
    from .browser import screenshot

    thumbs = root / ".thumbs"
    target = thumbs / (html_file.relative_to(root).as_posix().replace("/", "__") + ".png")
    try:
        if not target.exists() or target.stat().st_mtime < html_file.stat().st_mtime:
            screenshot(html_file, target, w, h)
        return target.relative_to(root).as_posix()
    except Exception:
        return None


def _poster(root: Path, video_file: Path) -> str | None:
    """A frame from one second in, so the card is not a black box before play."""
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    target = root / ".thumbs" / (video_file.relative_to(root).as_posix().replace("/", "__") + ".jpg")
    if not target.exists() or target.stat().st_mtime < video_file.stat().st_mtime:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", "1", "-i", str(video_file), "-frames:v", "1", "-q:v", "3", str(target)],
                       capture_output=True)
    return target.relative_to(root).as_posix() if target.exists() else None


def _render_md(root: Path, md: Path) -> Path | None:
    """research.md / findings.md -> a readable HTML page beside it."""
    from . import doc

    try:
        result = doc.build(md, out_dir=root / ".thumbs", name=md.stem + "-" + md.parent.name, formats=("html",))
        return Path(result["html"])
    except Exception:
        return None


def build(folder: Path) -> Path:
    root = Path(folder).resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    theme = get_theme(manifest.get("theme"))
    if theme.dark:
        theme = THEMES["ocean"]
    files = _files(root)
    rel = lambda p: html.escape(p.relative_to(root).as_posix(), quote=True)  # noqa: E731

    cards: list[str] = []

    def link_row(paths: list[Path]) -> str:
        return "".join(f'<a class="chip" href="{rel(p)}">{html.escape(p.suffix.lstrip(".").upper() or p.name)}</a>' for p in paths)

    # Decks
    for deck_html in [p for p in files if p.suffix == ".html" and p.parent.name == "slides"]:
        siblings = [p for p in files if p.parent == deck_html.parent and p.stem == deck_html.stem and p != deck_html and p.suffix in {".pptx", ".pdf"}]
        thumb = _thumb(root, deck_html, 1280, 720)
        img = f'<img src="{html.escape(thumb)}" alt="">' if thumb else '<div class="ph">Deck</div>'
        cards.append(f'<article class="card wide"><a class="preview" href="{rel(deck_html)}">{img}</a><div class="body">'
                     f'<span class="tag">Slides</span><h3>{html.escape(deck_html.stem.replace("-", " ").title())}</h3>'
                     f'<p>Open the HTML to present (arrow keys, F for full screen).</p><div class="chips">{link_row([deck_html, *siblings])}</div></div></article>')
    # Documents
    doc_stems = sorted({p.stem for p in files if p.parent.name == "docs" and p.suffix in {".docx", ".pdf", ".html", ".md"}})
    for stem in doc_stems:
        group = [p for p in files if p.parent.name == "docs" and p.stem == stem and p.suffix in {".docx", ".pdf", ".html", ".md"}]
        page = next((p for p in group if p.suffix == ".html"), None)
        thumb = _thumb(root, page, 816, 1056) if page else None
        img = f'<img src="{html.escape(thumb)}" alt="">' if thumb else '<div class="ph">Document</div>'
        cards.append(f'<article class="card"><div class="preview">{img}</div><div class="body"><span class="tag">Document</span>'
                     f'<h3>{html.escape(stem.replace("-", " ").replace("_", " ").title())}</h3><div class="chips">{link_row(group)}</div></div></article>')
    # Research and findings
    for md in [p for p in files if p.name in {"research.md", "findings.md"}]:
        page = _render_md(root, md)
        label = "Research brief" if md.name == "research.md" else "Data findings"
        links = [md] + ([page] if page else [])
        chips = "".join(f'<a class="chip" href="{html.escape(p.relative_to(root).as_posix())}">{"Read" if p.suffix == ".html" else "MD"}</a>' for p in reversed(links))
        cards.append(f'<article class="card"><div class="body"><span class="tag">{"Research" if md.name == "research.md" else "Data"}</span>'
                     f'<h3>{label}</h3><div class="chips">{chips}</div></div></article>')
    # Video
    for v in [p for p in files if p.suffix in _VIDEO]:
        srt = [p for p in files if p.parent == v.parent and p.stem == v.stem and p.suffix == ".srt"]
        poster = _poster(root, v)
        poster_attr = f' poster="{html.escape(poster)}"' if poster else ""
        cards.append(f'<article class="card wide"><div class="preview"><video controls preload="metadata"{poster_attr} src="{rel(v)}"></video></div>'
                     f'<div class="body"><span class="tag">Video</span><h3>{html.escape(v.stem.replace("-", " ").title())}</h3>'
                     f'<div class="chips">{link_row([v, *srt])}</div></div></article>')

    images = [p for p in files if p.suffix.lower() in _IMAGE and not p.stem.endswith(("-preview", "-check")) and p.parent.name != "video"]
    image_grid = "".join(f'<a class="shot" href="{rel(p)}"><img src="{rel(p)}" alt="" loading="lazy"><span>{html.escape(p.relative_to(root).as_posix())}</span></a>' for p in images)

    shown = set()
    for p in files:
        if p.suffix.lower() in _IMAGE or p.suffix in _VIDEO or p.suffix == ".srt" or p.parent.name in {"slides", "docs"} or p.name in {"research.md", "findings.md"}:
            shown.add(p)
    others = [p for p in files if p not in shown]
    other_list = "".join(f'<li><a href="{rel(p)}">{html.escape(p.relative_to(root).as_posix())}</a></li>' for p in others)

    status_rows = ""
    for d in manifest.get("deliverables") or []:
        st = d.get("status", "done")
        status_rows += (f'<li class="st-{html.escape(st)}"><span class="dot"></span><strong>{html.escape(d.get("title", ""))}</strong>'
                        f'<span class="who">{html.escape(AGENT_LABEL.get(d.get("agent", ""), d.get("agent", "")))}</span>'
                        f'{"<em>" + html.escape(d["note"]) + "</em>" if d.get("note") else ""}</li>')
    issues = "".join(f"<li>{html.escape(x)}</li>" for x in manifest.get("issues") or [])

    title = manifest.get("title") or root.name
    created_raw = manifest.get("created") or dt.datetime.fromtimestamp(root.stat().st_mtime).isoformat(timespec="minutes")
    try:
        when = dt.datetime.fromisoformat(created_raw)
        created = f"{when.day} {when:%b %Y}, {when:%H:%M}"
    except ValueError:
        created = created_raw
    t = theme
    css = f"""
:root{{--bg:{t.bg};--surface:{t.surface};--text:{t.text};--muted:{t.muted};--accent:{t.accent};--accent2:{t.accent2};--card:#fff;
  --ok:#15803d;--bad:#b91c1c;--skip:#a16207}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1115;--surface:#1b1f27;--text:#e8eaee;--muted:#9aa3b2;--card:#161a21}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 {t.body_stack}}}
main{{max-width:1180px;margin:0 auto;padding:40px 16px 64px}}
h1{{font:700 clamp(28px,4vw,40px)/1.15 {t.heading_stack};margin:0 0 6px}}
.req{{color:var(--muted);margin:0 0 4px;max-width:70ch}}
.when{{color:var(--muted);font-size:13px;margin:0 0 28px}}
h2{{font:700 20px {t.heading_stack};margin:36px 0 14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}}
.card{{background:var(--card);border:1px solid var(--surface);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}}
.card.wide{{grid-column:span 2}}
@media (max-width:700px){{.card.wide{{grid-column:span 1}}}}
.preview{{display:block;background:var(--surface);aspect-ratio:16/9;overflow:hidden}}
.card:not(.wide) .preview{{aspect-ratio:8.5/6}}
.preview img,.preview video{{width:100%;height:100%;object-fit:cover;object-position:top;display:block}}
.ph{{display:grid;place-items:center;height:100%;color:var(--muted)}}
.body{{padding:14px 16px 16px}}
.body h3{{margin:4px 0 6px;font-size:17px}}
.body p{{margin:0 0 10px;color:var(--muted);font-size:14px}}
.tag{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--accent)}}
.chips{{display:flex;flex-wrap:wrap;gap:8px}}
.chip{{font-size:12px;font-weight:700;padding:5px 10px;border-radius:999px;background:var(--surface);color:var(--text);text-decoration:none}}
.chip:hover{{background:var(--accent);color:#fff}}
.shots{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
.shot{{display:block;background:var(--card);border:1px solid var(--surface);border-radius:12px;overflow:hidden;color:var(--muted);text-decoration:none;font-size:12px}}
.shot img{{width:100%;aspect-ratio:16/10;object-fit:contain;background:var(--surface);display:block}}
.shot span{{display:block;padding:8px 10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.status{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}
.status li{{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;background:var(--card);border:1px solid var(--surface);border-radius:10px;padding:10px 14px}}
.status .dot{{width:10px;height:10px;border-radius:50%;background:var(--ok);flex:none;align-self:center}}
.status .st-failed .dot{{background:var(--bad)}} .status .st-skipped .dot{{background:var(--skip)}}
.status .who{{color:var(--muted);font-size:13px}} .status em{{color:var(--muted);font-size:13px;flex-basis:100%}}
.issues{{background:var(--card);border-left:4px solid var(--skip);border-radius:8px;padding:12px 16px 12px 34px;margin:0}}
.files{{columns:2;color:var(--muted);font-size:14px}} .files a{{color:var(--accent)}}
@media (max-width:700px){{.files{{columns:1}}}}
"""
    sections = []
    if status_rows:
        sections.append(f"<h2>Deliverables</h2><ul class='status'>{status_rows}</ul>")
    if issues:
        sections.append(f"<h2>Needs attention</h2><ul class='issues'>{issues}</ul>")
    if cards:
        sections.append(f"<h2>Open</h2><div class='grid'>{''.join(cards)}</div>")
    if image_grid:
        sections.append(f"<h2>Charts and images</h2><div class='shots'>{image_grid}</div>")
    if other_list:
        sections.append(f"<h2>Other files</h2><ul class='files'>{other_list}</ul>")
    req = f"<p class='req'>{html.escape(manifest['request'])}</p>" if manifest.get("request") else ""
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{css}</style></head><body><main><h1>{html.escape(title)}</h1>{req}"
            f"<p class='when'>Made by the swarm · {html.escape(created)}</p>{''.join(sections)}</main></body></html>")
    out = root / "index.html"
    out.write_text(page, encoding="utf-8")
    return out
