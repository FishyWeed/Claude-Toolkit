# Toolkit catalog

Everything in this repo, plus the third-party tools it works with. Install commands assume the marketplace is added:

```
claude plugin marketplace add FishyWeed/Claude-Toolkit
```

| Name | Type | One line |
|---|---|---|
| [toolkit-setup](#toolkit-setup) | Skill | Checks a machine and lists every install, login and key still needed |
| [prompt-enhancer](#prompt-enhancer) | Mod | Enhance button above the prompt rewrites your draft into a better prompt |
| [model-router](#model-router) | Mod | Picks Haiku, Sonnet or Opus per prompt and per subagent, swarm included |
| [search-switch](#search-switch) | Mod | Search dropdown: Native search or Exa / Firecrawl |
| [mods-skills-panel](#mods-skills-panel) | Mod | Side panel listing your mods and skills, with usage and a model per item |
| [clear-caveman](#clear-caveman) | Output style | Short, plain replies with one self-contained wrap-up after multi-step work |
| [design-directions](#design-directions) | Skill | Shows three rendered design directions instead of asking open questions |
| [swarm](#swarm) | Skill and agents | A team of specialist agents for decks, documents, research, data, images and video |
| [codeburn](#codeburn) | Skill | `/codeburn` reports where your Claude Code tokens and money go |

**Types:** a **skill** is plain instructions (`SKILL.md`), portable to claude.ai and other agent tools. A **mod** is TypeScript code that changes Claude Code itself, and only works there. An **output style** changes how Claude writes every reply.

---

## toolkit-setup

**Type:** skill · **Needs:** nothing

Checks Node, Python, `uv`, Git, the Firecrawl and Graphify tools, and which API keys are set (it shows only "set" or "missing", never values). Then it lists what's left for this toolkit and the third-party tools below: install commands, logins, and where to put each key. It can run the install commands for you. Logins and keys stay with you.

**Setup:** `claude plugin install toolkit-setup@claude-toolkit`

**Use:**
```
/toolkit-setup
```

---

## prompt-enhancer

**Type:** mod · **Needs:** nothing (uses your Claude login)

Adds **✨ Enhance** and a **Model** picker to the strip above the chat box. Enhance rewrites your draft into a clearer, more effective prompt, in place, without sending it. **Undo** restores your original. It keeps every fact you wrote, never invents details, and turns coding requests into briefs an agent can act on.

**Setup:** `claude plugin install prompt-enhancer@claude-toolkit`

**Use:**
- Type a rough draft such as `fix login bug`, click **✨ Enhance**, edit the result, then press Enter.
- Choose the rewriting model in the picker, or type `/enhance-model haiku` (or any model ID). Type `/enhance-model` alone to see the current one.

---

## model-router

**Type:** mod · **Needs:** nothing

Picks the model for each prompt you type and for each subagent Claude starts:

- Mechanical work (typos, renames, git chores, finding files) → **Haiku**
- Normal coding → **Sonnet**
- Debugging, architecture, refactors, security, research, planning → **Opus**
- Unclear → left alone

Swarm specialists get fixed defaults: `researcher`, `data-analyst`, `docs-writer`, `slides-designer` and `video-maker` → Sonnet; `image-maker` → Haiku. `Explore` → Haiku, `Plan` → Opus. A model Claude sets on purpose always wins.

**Setup:** `claude plugin install model-router@claude-toolkit`

**Use:**
- The **Router: Auto / Off** dropdown sits above the chat box and shows the model picked for your last prompt, for example `Auto · Opus`; it shows plain `Auto` when the prompt gave no clear signal.
- `/router` shows the full table.
- `/router set swarm:docs-writer opus` changes one specialist; `/router set swarm:docs-writer default` resets it.
- Start a prompt with `~` to skip routing once.

---

## search-switch

**Type:** mod · **Needs:** for Exa / Firecrawl mode, the Exa and Firecrawl plugins signed in (see [Third-party tools](#third-party-tools))

Adds a **Search: Native / Exa / Firecrawl** dropdown. It tells Claude which search tools to use and blocks the other side's tools, so the choice holds. Native uses the built-in WebSearch and WebFetch. Exa / Firecrawl uses Exa for search and the Firecrawl CLI for scraping and crawling (this uses Firecrawl credits).

**Setup:** `claude plugin install search-switch@claude-toolkit`

**Use:**
- Pick a mode in the dropdown. The choice is saved.
- Or type `/search native` or `/search exa`. Type `/search` alone to see the current mode.

---

## mods-skills-panel

**Type:** mod · **Needs:** nothing

A side panel listing your mods and skills: what each does, the commands it adds, how often it's been used, and a **Model** button per item (Default → Opus → Sonnet → Haiku). A skill with a model runs the rest of that reply on it. Also adds **🧩 Skills** and **🛠 Mods** buttons above the chat box.

**Setup:** `claude plugin install mods-skills-panel@claude-toolkit`

**Use:**
- Click **🧩 Skills** or **🛠 Mods**, or type `/mods-skills`.
- In the panel: `m` / `s` switch lists, `r` refreshes, click a name for details, `x` collapses all.

---

## clear-caveman

**Type:** output style · **Needs:** nothing

Changes how Claude writes every reply. It combines Caveman (answer first, no filler, exact code and errors, no chatter between tool calls) with Clear Answers (plain language with jargon explained in brackets). After multi-step work you get one self-contained wrap-up: what was asked, key points, what's verified, and real next steps. It's forced on while the plugin is enabled.

**Setup:** `claude plugin install clear-caveman@claude-toolkit`

**Use:** nothing to do; it applies to new sessions. Turn it off with `claude plugin disable clear-caveman@claude-toolkit`. Edit the rules in `plugins/clear-caveman/output-styles/clear-caveman.md`.

---

## design-directions

**Type:** skill · **Needs:** nothing

When you ask for a design system from scratch, Claude shows three distinct, rendered directions to choose from, rather than asking what style you want. Each preview has the same layout: palette with hex values, typography, buttons, basic components and spacing. Pick one, mix them, or tweak, then Claude builds the full system.

**Setup:** `claude plugin install design-directions@claude-toolkit`

**Use:**
```
Create a design system for a budgeting app for students, inspired by Duolingo.
```
Then: `B, but with A's typography and rounder corners.`

---

## swarm

**Type:** skill plus 6 specialist agents · **Needs:** all optional: `OPENROUTER_API_KEY` (AI images), `GOOGLE_API_KEY` (Gemini images, Veo video), `FAL_KEY` (fal.ai video), `OPENAI_API_KEY` (Sora video), `EXA_API_KEY` (Exa search). ffmpeg for video.

The main conversation acts as the coordinator. It hands work to specialist agents that run in parallel where they can: **researcher** (cited brief), **data-analyst** (charts and findings), **slides-designer** (HTML, PPTX and PDF decks), **docs-writer** (Word and PDF documents), **image-maker** (AI images, or SVG without a key), **video-maker** (slideshows, or AI footage with a key). It checks every deliverable and collects them in one folder with a gallery page.

**Setup:** `claude plugin install swarm@claude-toolkit`, then optional keys (see `/toolkit-setup`).

**Use:**
```
/swarm a pitch deck, a one-page executive summary and market research on e-bike subscriptions in Malaysia
```

Model Router sets each specialist's model automatically.

---

## codeburn

**Type:** skill · **Needs:** Node.js 22.13 or newer

`/codeburn` runs CodeBurn (`codeburn@0.9.25`, read-only) on your local Claude Code session logs before Claude sees the request. Claude then reports spend, the main model, a health grade, the top three savings with exact fixes, and the single best next step. It never applies changes unless you explicitly ask.

**Setup:** `claude plugin install codeburn@claude-toolkit`

**Use:**
- `/codeburn` gives the last 7 days: overview plus waste scan.
- `/codeburn models`, `/codeburn yield`, `/codeburn status`, or `/codeburn -p 30days`.
- `/codeburn quota` checks your live plan limits (it asks first).

---

## Third-party tools

Not in this repo. `/toolkit-setup` has the exact install commands and logins for each.

| Tool | What it adds | Login or keys |
|---|---|---|
| Ponytail | Simplest-working-code rules in every session; `/ponytail-review`, `-audit`, `-debt` | None |
| last30days | `/last30days:last30days <topic>` researches the last 30 days across Reddit, X, YouTube, Hacker News and more | Optional keys for some sources |
| Exa | Exa web search and page fetching (MCP) | Sign in via `/mcp` |
| Firecrawl | Search, scrape, crawl and map sites (CLI plus skills) | `firecrawl login --browser` |
| Playwright MCP | Claude can drive a browser (Edge) | None |
| Graphify | `/graphify .` builds a searchable map of a codebase | None for code |
| ECC | Large skill and agent pack, GateGuard hooks, chrome-devtools MCP | None |
| Flightdeck | See its README | Check its README |
| Laya | Fast local classifier for labelling many items (MCP) | None |
| K-Dense Scientific Agent Skills | About 180 science skills in `~/.claude/skills` | Some skills need their own keys |
