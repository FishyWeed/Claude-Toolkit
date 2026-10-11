"""Slideshow / explainer video from a JSON spec, with ffmpeg.

Spec:
{
  "size": "1920x1080",            (or "1080x1920" vertical, "1080x1080" square)
  "fps": 30, "theme": "ocean", "transition": 0.6,
  "title":  {"text": "...", "subtitle": "...", "duration": 3.5},
  "slides": [{"image": "charts/a.png", "duration": 5, "caption": "...",
              "motion": "zoom-in|zoom-out|pan-left|pan-right|none", "fit": "auto|contain|cover"}],
  "outro":  {"text": "...", "subtitle": "...", "duration": 3},
  "music": "audio/bed.mp3", "music_volume": 0.25
}
Paths are relative to the spec file. Writes <name>.mp4 and <name>.srt (when there are captions).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .themes import Theme, font_path, get_theme, hex_to_rgb

MOTIONS = {"zoom-in", "zoom-out", "pan-left", "pan-right", "none"}


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg is not installed or not on PATH.")
    return exe


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _card(theme: Theme, size: tuple[int, int], text: str, subtitle: str, out: Path, scale: int = 2) -> None:
    """A title or outro card, rendered at `scale`x for sharp zooms."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = size[0] * scale, size[1] * scale
    img = Image.new("RGB", (w, h), hex_to_rgb(theme.bg))
    draw = ImageDraw.Draw(img)
    unit = min(w, h)
    margin = int(w * 0.09)
    title_font = ImageFont.truetype(font_path(theme.heading_font, True), int(unit * 0.085))
    sub_font = ImageFont.truetype(font_path(theme.body_font), int(unit * 0.04))
    lines = _wrap(draw, text, title_font, w - 2 * margin)
    sub_lines = _wrap(draw, subtitle, sub_font, w - 2 * margin) if subtitle else []
    line_h = int(title_font.size * 1.12)
    sub_h = int(sub_font.size * 1.3)
    bar_gap = int(unit * 0.05)
    block = len(lines) * line_h + (bar_gap * 2 + len(sub_lines) * sub_h if sub_lines else bar_gap)
    y = (h - block) // 2
    for ln in lines:
        draw.text((margin, y), ln, font=title_font, fill=hex_to_rgb(theme.text))
        y += line_h
    y += bar_gap // 2
    draw.rounded_rectangle([margin, y, margin + int(unit * 0.12), y + int(unit * 0.009)], radius=int(unit * 0.005), fill=hex_to_rgb(theme.accent))
    y += bar_gap
    for ln in sub_lines:
        draw.text((margin, y), ln, font=sub_font, fill=hex_to_rgb(theme.muted))
        y += sub_h
    img.save(out)


def _scene(theme: Theme, size: tuple[int, int], image: Path, fit: str, out: Path, scale: int = 2) -> None:
    from PIL import Image

    w, h = size[0] * scale, size[1] * scale
    canvas = Image.new("RGB", (w, h), hex_to_rgb(theme.bg))
    with Image.open(image) as src:
        src = src.convert("RGBA")
        iw, ih = src.size
        if fit == "auto":
            fit = "cover" if abs((iw / ih) / (w / h) - 1) < 0.15 and not image.parent.name.startswith("chart") else "contain"
        if fit == "cover":
            s = max(w / iw, h / ih)
            pad = 0
        else:
            pad = int(min(w, h) * 0.06)
            s = min((w - 2 * pad) / iw, (h - 2 * pad) / ih)
        nw, nh = int(iw * s), int(ih * s)
        resized = src.resize((nw, nh), Image.LANCZOS)
        canvas.paste(resized, ((w - nw) // 2, (h - nh) // 2), resized)
    canvas.save(out)


def _caption(theme: Theme, size: tuple[int, int], text: str, out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    unit = min(w, h)
    font = ImageFont.truetype(font_path(theme.body_font, True), max(28, int(unit * 0.042)))
    max_w = int(w * 0.8)
    lines = _wrap(draw, text, font, max_w)[:3]
    line_h = int(font.size * 1.25)
    pad_x, pad_y = int(font.size * 0.9), int(font.size * 0.55)
    text_w = max(int(draw.textlength(ln, font=font)) for ln in lines)
    box_w, box_h = text_w + 2 * pad_x, len(lines) * line_h + 2 * pad_y
    x0 = (w - box_w) // 2
    y0 = h - int(h * 0.07) - box_h  # inside the title-safe area
    r, g, b = hex_to_rgb(theme.surface if not theme.dark else theme.bg)
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=int(font.size * 0.4), fill=(r, g, b, 225))
    draw.rectangle([x0, y0, x0 + int(font.size * 0.18), y0 + box_h], fill=(*hex_to_rgb(theme.accent), 255))
    y = y0 + pad_y
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        draw.text(((w - lw) // 2, y), ln, font=font, fill=(*hex_to_rgb(theme.text), 255))
        y += line_h
    img.save(out)


def _zoompan(motion: str, frames: int, size: tuple[int, int], fps: int) -> str:
    n = max(frames - 1, 1)
    z = {"zoom-in": f"1+0.10*on/{n}", "zoom-out": f"1.10-0.10*on/{n}", "pan-left": "1.08", "pan-right": "1.08", "none": "1"}[motion]
    x = {"pan-left": f"(iw-iw/zoom)*(1-on/{n})", "pan-right": f"(iw-iw/zoom)*on/{n}"}.get(motion, "iw/2-(iw/zoom/2)")
    y = "ih/2-(ih/zoom/2)"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={size[0]}x{size[1]}:fps={fps}"


def _srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def build(spec_path: Path, out_dir: Path | None = None, name: str = "video") -> dict:
    ffmpeg = _ffmpeg()
    spec_path = Path(spec_path).resolve()
    base = spec_path.parent
    out_dir = Path(out_dir).resolve() if out_dir else base
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    theme = get_theme(spec.get("theme"))
    width, height = (int(v) for v in str(spec.get("size", "1920x1080")).lower().split("x"))
    size = (width - width % 2, height - height % 2)
    fps = int(spec.get("fps", 30))
    trans = float(spec.get("transition", 0.6))
    warnings: list[str] = []

    scenes: list[dict] = []
    if spec.get("title"):
        scenes.append({"kind": "card", **spec["title"], "duration": float(spec["title"].get("duration", 3.5)), "motion": "zoom-in"})
    for i, s in enumerate(spec.get("slides") or [], 1):
        img = base / s.get("image", "")
        if not img.is_file():
            warnings.append(f"Slide {i}: image not found ({s.get('image')}); skipped.")
            continue
        motion = s.get("motion", ["zoom-in", "pan-right", "zoom-out", "pan-left"][i % 4])
        if motion not in MOTIONS:
            warnings.append(f"Slide {i}: unknown motion '{motion}', using zoom-in.")
            motion = "zoom-in"
        scenes.append({"kind": "image", "image": img, "duration": float(s.get("duration", 5)), "caption": s.get("caption", ""),
                       "motion": motion, "fit": s.get("fit", "auto")})
    if spec.get("outro"):
        scenes.append({"kind": "card", **spec["outro"], "duration": float(spec["outro"].get("duration", 3)), "motion": "none"})
    if not scenes:
        raise SystemExit("Nothing to render: the spec has no title, slides or outro.")

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.mp4"
    with tempfile.TemporaryDirectory(prefix="swarm-video-") as tmp_name:
        tmp = Path(tmp_name)
        segments = []
        for k, sc in enumerate(scenes):
            frames = max(2, int(round(sc["duration"] * fps)))
            bg = tmp / f"bg{k}.png"
            if sc["kind"] == "card":
                _card(theme, size, sc.get("text", ""), sc.get("subtitle", ""), bg)
            else:
                _scene(theme, size, sc["image"], sc["fit"], bg)
            seg = tmp / f"seg{k}.mp4"
            cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(bg)]
            graph = f"[0:v]{_zoompan(sc['motion'], frames, size, fps)},setsar=1[bg]"
            if sc.get("caption"):
                cap = tmp / f"cap{k}.png"
                _caption(theme, size, sc["caption"], cap)
                cmd += ["-loop", "1", "-i", str(cap)]
                graph += ";[1:v]format=rgba[cap];[bg][cap]overlay=0:0:shortest=1,format=yuv420p[v]"
            else:
                graph += ";[bg]format=yuv420p[v]"
            cmd += ["-filter_complex", graph, "-map", "[v]", "-frames:v", str(frames), "-r", str(fps),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(seg)]
            _run(cmd)
            segments.append((seg, sc["duration"]))

        # Join with crossfades
        n = len(segments)
        t = min(trans, *(d / 2 for _, d in segments)) if n > 1 else 0
        total = sum(d for _, d in segments) - t * (n - 1)
        cmd = [ffmpeg, "-y", "-loglevel", "error"]
        for seg, _ in segments:
            cmd += ["-i", str(seg)]
        parts, last, offset = [], "0:v", 0.0
        for k in range(1, n):
            offset += segments[k - 1][1] - t
            label = f"v{k}"
            parts.append(f"[{last}][{k}:v]xfade=transition=fade:duration={t:.3f}:offset={offset:.3f}[{label}]")
            last = label
        music = base / spec["music"] if spec.get("music") else None
        if music and not music.is_file():
            warnings.append(f"Music not found ({spec['music']}); the video has a silent track.")
            music = None
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(music)]
            vol = float(spec.get("music_volume", 0.25))
            fade_out = max(0.0, total - 2)
            parts.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=1,afade=t=out:st={fade_out:.3f}:d=2,volume={vol}[a]")
        else:
            cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            parts.append(f"[{n}:a]anull[a]")
        video_label = f"[{last}]" if n > 1 else "[0:v]"
        cmd += ["-filter_complex", ";".join(parts), "-map", video_label, "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps),
                "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
        _run(cmd)

    # Captions as a sidecar SRT, timed to the crossfaded cut
    srt_path = None
    cues, start = [], 0.0
    for k, sc in enumerate(scenes):
        if sc.get("caption"):
            cues.append((start + (t / 2 if k else 0), start + sc["duration"] - t / 2, sc["caption"]))
        start += sc["duration"] - t
    if cues:
        srt_path = out_dir / f"{name}.srt"
        srt_path.write_text("\n".join(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{text}\n" for i, (a, b, text) in enumerate(cues, 1)), encoding="utf-8")

    probe = probe_video(out)
    result = {"mp4": str(out), "duration": probe.get("duration"), "size": probe.get("size"), "audio": probe.get("audio"), "warnings": warnings}
    if srt_path:
        result["srt"] = str(srt_path)
    return result


def probe_video(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    proc = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                          capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration": round(float(data.get("format", {}).get("duration", 0)), 2),
        "size": f"{video.get('width')}x{video.get('height')}" if video else None,
        "audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }
