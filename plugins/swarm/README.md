# Swarm

An OpenSwarm-style team for Claude Code, modelled on [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm). Type one request: Claude plans it, hands the work to specialist agents (in parallel where it can), checks every deliverable, and collects them in one folder with a gallery page.

```
/swarm a briefing on US home battery storage for homeowners: a 7-slide deck, a one-page executive summary, a price-trend chart and a 20-second teaser video
```

## What you get

```
swarm-output/2026-10-11-home-batteries/
  index.html            ← open this: every deliverable with previews
  manifest.json         what was asked, who made what, anything that needs you
  research.md           cited research brief
  charts/*.png          themed charts      analysis/  findings + the script
  slides/deck.html      present in a browser (arrow keys, F for full screen)
  slides/deck.pptx      PowerPoint, with speaker notes
  slides/deck.pdf
  docs/*.docx  *.pdf    Word and PDF
  images/*.png          illustrations
  video/video.mp4       slideshow video (+ .srt captions)
```

Everything in one run shares a theme: `ocean` (default), `paper`, `midnight`, `forest` or `ember`.

## The team

| Agent | Makes | Needs |
| --- | --- | --- |
| `researcher` | Cited research brief with a key-figures table | — |
| `data-analyst` | Charts styled to the theme, findings, the analysis script | — |
| `slides-designer` | HTML deck + PPTX + PDF, checked slide by slide | — |
| `docs-writer` | Word + PDF documents, checked by eye | — |
| `image-maker` | AI images with a key; otherwise clean drawn SVG/PNG illustrations | `OPENROUTER_API_KEY` for AI images |
| `video-maker` | Slideshow/explainer videos with pans, crossfades, captions, music; clip edits | ffmpeg; `FAL_KEY` / `GOOGLE_API_KEY` / `OPENAI_API_KEY` for AI footage |

PDFs and previews are rendered with Microsoft Edge or Chrome, headless.

## The panel

A **Swarm** panel opens when the first specialist starts: one row per specialist, colour-coded, with its task, elapsed time, step count and what it is doing right now. `c` clears finished rows; `/swarm-panel` reopens it.

## How it is built

- `skills/swarm/SKILL.md` — the orchestrator: plan, waves, briefs, quality checks, gallery.
- `agents/*.md` — the six specialists.
- `skills/swarm/kit/` — `swarm_kit`, the shared builders (decks, documents, videos, previews, gallery, doctor). Installed into its own Python environment at `~/.claude/swarm/.venv` by `skills/swarm/scripts/setup.py`, which `/swarm` runs on every call (it does nothing when already current).
- `hooks/register.tsx` — the progress panel.

Check what this machine can do:

```
python skills/swarm/scripts/setup.py
~/.claude/swarm/.venv/Scripts/python -m swarm_kit doctor
```

## Install

```
/plugin marketplace add C:\Users\Admin\Documents\Claude\Mods\swarm
/plugin install swarm@swarm-mods
```

## Develop

```
claude plugin validate .
claude plugin test .                                   # the panel
~/.claude/swarm/.venv/Scripts/python skills/swarm/kit/tests/test_kit.py   # every builder
```
