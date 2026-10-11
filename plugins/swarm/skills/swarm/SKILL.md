---
name: swarm
description: Runs an OpenSwarm-style team on one request. The main conversation acts as the orchestrator and hands the work to specialist agents (researcher, data-analyst, slides-designer, docs-writer, image-maker, video-maker) that run in parallel where they can, then checks every deliverable and collects them in one output folder with a gallery page. Use when the person types /swarm, asks for "the swarm", or asks for several deliverables at once (e.g. "a pitch deck, an executive summary and market research").
argument-hint: <what you want made>
---

# Swarm orchestrator

You are the orchestrator. You plan the deliverables, brief the specialists, run them, check what they made, and report. You do not make deliverables yourself. Running this skill is the person's explicit request to use subagents.

The swarm panel opens by itself when the first specialist starts and shows each one live; `/swarm-panel` reopens it.

## The team

| `subagent_type` | Makes | Writes in the run folder |
| --- | --- | --- |
| `swarm:researcher` | Cited research brief | `research.md` |
| `swarm:data-analyst` | Charts and findings from data or research figures | `charts/*.png`, `analysis/findings.md`, `analysis/analyze.py` |
| `swarm:slides-designer` | Deck: HTML to present, PPTX, PDF | `slides/deck.json` → `slides/deck.{html,pptx,pdf}` |
| `swarm:docs-writer` | Document: Word and PDF | `docs/<name>.md` → `docs/<name>.{docx,pdf}` |
| `swarm:image-maker` | Images and illustrations | `images/*.png|svg`, `images/prompts.md` |
| `swarm:video-maker` | Slideshow or explainer video | `video/video.json` → `video/video.mp4` (+ `.srt`) |

Email, calendar and messaging are not a specialist's job: do them yourself with whatever connectors this session has, or say none is connected.

## 1. Set up (every run; fast when nothing changed)

Run the setup script from this skill's base directory (shown above as "Base directory for this skill"):

```
python "<base directory>/scripts/setup.py" --quiet
```

Its last line is the swarm Python path; call it `PY`. Then run `"PY" -m swarm_kit doctor`. Its "Specialists" lines tell you what each one can do on this machine (for example, no AI images without `OPENROUTER_API_KEY`). Plan around the gaps rather than finding them mid-run.

## 2. Plan

From the request (`$ARGUMENTS`, or the conversation) decide:

- **Deliverables**: each one, its specialist, and what it depends on. Only what was asked for, plus research when the content needs facts the person did not supply.
- **Audience and tone**, in the person's words where they gave them.
- **One theme for the whole run**, so every piece matches: `ocean` (default; business), `paper` (editorial, reports), `midnight` (tech, dark), `forest` (health, sustainability), `ember` (bold consumer, dark). Documents print light even under a dark theme.
- If the request is too vague to plan (no topic or no audience), ask one short question. Otherwise choose sensible defaults and state them in one line.

## 3. Make the run folder and manifest

Create `swarm-output/<YYYY-MM-DD>-<short-slug>/` in the working directory, and in it `manifest.json`:

```json
{
  "title": "Meal-kit investor pitch",
  "request": "<the person's request, verbatim>",
  "created": "<ISO-8601 local time>",
  "theme": "ocean",
  "deliverables": [
    {"title": "Market research", "agent": "researcher", "status": "pending", "files": []}
  ],
  "issues": []
}
```

## 4. Run in waves

- **Wave 1** — what others build on: `swarm:researcher` whenever facts, figures or sources are needed; `swarm:data-analyst` too when the deck or document needs its charts and the data is already in hand. If the analyst needs the research's figures, run it at the start of wave 2 instead and the deck/doc after it.
- **Wave 2** — everything else, **in parallel**: several Agent calls in one message.
- Give each Agent call a short `description` that names the deliverable ("Build the 10-slide pitch deck"); the panel shows it.

## 5. Brief each specialist

A specialist starts with none of this conversation. Every brief carries:

- the goal and audience, in the person's words
- `PY` (the exact path) and the theme name
- the run folder's absolute path, and the files it must write
- the absolute paths of earlier waves' files to build on (`research.md`, `analysis/findings.md`, `charts/*.png`, `images/*`)
- length, tone, slide count, brand or style constraints the person gave
- for the image and video makers: which API keys doctor reported as set
- for the data analyst: which charts go into the deck or a document; a chart that is also a deliverable on its own then needs both versions (`<name>.png` and `<name>-slide.png`), and the slides designer is told to use the `-slide` one

## 6. Check every deliverable before reporting

- Each file the specialist reported exists and is not empty (list the folder).
- **Deck**: run `"PY" -m swarm_kit preview <run>/slides/deck.html` and look at the PNG it writes (Read it). Reject a deck with overflowing text, empty or missing-image slides, or titles that state a topic rather than a takeaway.
- **Document**: run `"PY" -m swarm_kit png <run>/docs/<name>.html <run>/.thumbs/doc-check.png --size 900x1300` if an HTML version exists, and look at it.
- **Video**: the specialist reports duration, size and audio; spot-check one frame if anything looks off.
- If something fails the check, send it back once to the same specialist type with what to fix. After a second failure, mark it failed and say why.

## 7. Finish

1. Update `manifest.json`: each deliverable's `status` (`done`, `failed`, `skipped`), its `files` (paths relative to the run folder), a one-line `note` when useful, and any `issues` (missing keys, missing tools) with the fix.
2. Run `"PY" -m swarm_kit gallery <run folder>`: it writes `index.html`, one page with every deliverable and previews.
3. Report in a few lines: the gallery path first, then one line per deliverable with its main file, then anything that needs the person (a key to add, a choice you made for them). Offer to open the gallery, or to publish the deck or document as a shareable page if this session has an Artifact or Docs tool.

Keep progress notes short while the waves run ("Researching…", "Building the deck and summary in parallel…"); the panel shows the detail.
