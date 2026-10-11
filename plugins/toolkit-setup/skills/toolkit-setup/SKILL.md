---
name: toolkit-setup
description: Set up the claude-toolkit on a new or existing machine. Checks what is already installed and signed in, then lists the remaining install steps, logins and API keys. Use when the user types /toolkit-setup or asks what keys or logins the toolkit needs.
disable-model-invocation: true
---

# Claude toolkit setup

Help the user get the toolkit fully working on this machine. Check what's already done, then give them a short checklist of what's left.

## Safety rules

- **Never ask the user to paste a key, token or password into the chat.** Tell them where to put it instead (see "Where keys go").
- Never print key values. When checking a key, report only "set" or "missing".
- Installing a plugin, tool or MCP server is fine when the user asks for it. Run the install commands below, one at a time, and say what each does.
- Logins (`firecrawl login`, `/mcp` authentication, `gh auth login`) must be done by the user. Give them the exact command.

## 1. Current state (checked when this skill loaded)

### Tools
!`node --version 2>&1; python --version 2>&1; uv --version 2>&1; git --version 2>&1; gh --version 2>&1 | head -1`

### Command-line tools used by the toolkit
!`firecrawl --status 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "Authenticated|Not authenticated|Credits|not found" ; graphify --version 2>&1 | tail -1`

### API keys (only "set" or "missing" is shown)
!`for k in OPENROUTER_API_KEY GOOGLE_API_KEY FAL_KEY OPENAI_API_KEY EXA_API_KEY FIRECRAWL_API_KEY SCRAPECREATORS_API_KEY XAI_API_KEY X_BEARER_TOKEN PERPLEXITY_API_KEY BRAVE_API_KEY; do if [ -n "$(printenv $k)" ]; then echo "$k: set"; else echo "$k: missing"; fi; done`

For installed plugins and MCP servers, run `claude plugin list` and `claude mcp list` with the Bash tool. `claude mcp list` can take up to a minute while it checks each server.

## 2. The full checklist

Compare the current state above (and the two list commands) against this list. Report only what's missing or not signed in.

### A. Basics (required)

| Item | Why | How |
|---|---|---|
| Claude Code, signed in | Runs everything | Install Claude Code, run `claude`, then `/login` |
| Git, signed in to GitHub | Download this private toolkit repo | Install Git. Sign in with `gh auth login` or a Git credential manager |
| Node.js 22.13 or newer | Exa, Playwright, CodeBurn, Firecrawl CLI, the mods' hooks | nodejs.org |
| Python 3.12 or newer | Swarm kit, last30days, Graphify, Laya | python.org |
| `uv` | Installs Graphify | `pip install uv` or astral.sh/uv |

### B. This toolkit's plugins (no keys needed except Swarm)

Install the marketplace once, then each plugin:

```
claude plugin marketplace add FishyWeed/Claude-Toolkit
claude plugin install prompt-enhancer@claude-toolkit
claude plugin install model-router@claude-toolkit
claude plugin install search-switch@claude-toolkit
claude plugin install mods-skills-panel@claude-toolkit
claude plugin install clear-caveman@claude-toolkit
claude plugin install design-directions@claude-toolkit
claude plugin install swarm@claude-toolkit
claude plugin install codeburn@claude-toolkit
claude plugin install toolkit-setup@claude-toolkit
```

| Plugin | Needs | Notes |
|---|---|---|
| prompt-enhancer, model-router, search-switch, mods-skills-panel | Nothing | Mods. They use your Claude login. Claude Code only |
| clear-caveman, design-directions | Nothing | Output style and skill |
| codeburn | Nothing | Runs `npx codeburn@0.9.25`, so it needs Node.js |
| swarm | All optional: `OPENROUTER_API_KEY` (AI images, image-maker), `GOOGLE_API_KEY` (Gemini images, Veo video), `FAL_KEY` (fal.ai video), `OPENAI_API_KEY` (Sora video), `EXA_API_KEY` (Exa search) | Without keys, image-maker draws SVG and video-maker makes slideshows. Needs ffmpeg for video |

### C. Third-party plugins

| Plugin | Install | Login or keys |
|---|---|---|
| Ponytail | `claude plugin marketplace add dietrichgebert/ponytail` then `claude plugin install ponytail@ponytail` | None |
| last30days | `claude plugin marketplace add mvanhorn/last30days-skill` then `claude plugin install last30days@last30days-skill` | None for Reddit, Hacker News, Polymarket, GitHub. Optional: `SCRAPECREATORS_API_KEY` (TikTok, Instagram, Threads), `XAI_API_KEY` or `X_BEARER_TOKEN` (X), `PERPLEXITY_API_KEY` or `OPENROUTER_API_KEY`, `BRAVE_API_KEY`; `yt-dlp` for YouTube. It can read browser cookies for X: run with `--preflight` first |
| Exa | `claude plugin install exa@claude-plugins-official` | Sign in: in a terminal `claude` session run `/mcp`, choose `plugin:exa:exa`, then **Authenticate**. Or use an Exa API key |
| Firecrawl | `claude plugin marketplace add firecrawl/firecrawl-claude-plugin`, `claude plugin install firecrawl@firecrawl`, then `npm install -g firecrawl-cli@1.24.6` | Sign in: `firecrawl login --browser`, or set `FIRECRAWL_API_KEY`. Check with `firecrawl --status`. Only used when the Search dropdown is set to Exa / Firecrawl |
| ECC | `claude plugin marketplace add https://github.com/affaan-m/ECC.git` then `claude plugin install ecc@ecc` | None. Adds the GateGuard hooks and the chrome-devtools MCP server |
| Flightdeck | `claude plugin marketplace add scasella/claude-flightdeck` then `claude plugin install flightdeck@claude-flightdeck` | Check its README; some features mention `OPENAI_API_KEY` |

### D. MCP servers and command-line tools

| Item | Install | Login or keys |
|---|---|---|
| Playwright MCP | `claude mcp add playwright --scope user -- cmd /c npx -y @playwright/mcp@0.0.82 --browser msedge` (Windows; on macOS or Linux drop `cmd /c`). In Git Bash, prefix with `MSYS_NO_PATHCONV=1` | None. Needs Microsoft Edge, or change `--browser` |
| Graphify | `uv tool install graphifyy==0.9.70` then `graphify install` | None for code. Optional LLM key (Gemini, Claude, OpenAI and others) only for headless `graphify extract` of docs |
| Laya | Local server in `~/.claude/laya/.venv` (laya 0.4.2). Set up per its own instructions, then `claude mcp add laya -- <path to laya-mcp-server>` | None. Downloads its model from Hugging Face on first use |
| claude.ai connectors (Claude Docs, Mobbin, Claude Design) | Nothing to install | They follow your Claude account automatically |

### E. Skills that live outside the repo

- **K-Dense Scientific Agent Skills** (about 180 skills in `~/.claude/skills`, such as `scanpy` and `rdkit`): reinstall from K-Dense's own source. A few need their own service keys; each skill's `SKILL.md` lists them.
- **Synced claude.ai plugins** (legal, frontend-design, skill-creator, security-guidance): they follow your Claude account. The legal plugin's connectors (Slack, Atlassian, DocuSign, Egnyte, Google) each need their own sign-in through `/mcp` if you use them.

## Where keys go

Pick one. **Never put keys in this repo.**

1. **Claude Code settings (simplest):** add an `env` block to `~/.claude/settings.json`, for example `"env": { "OPENROUTER_API_KEY": "..." }`. This file stays on the machine and is not part of the repo.
2. **Your operating system's environment variables:** on Windows, Settings → System → About → Advanced system settings → Environment Variables. Restart Claude Code afterwards.
3. **A tool's own login:** `firecrawl login --browser`, `/mcp` for Exa, `gh auth login` for GitHub. These store their own credentials.

## 3. Report back

Give the user one short checklist:

1. **Ready:** what's already installed and signed in, one line.
2. **To do:** each missing item with its exact command or the place to put its key. Required items first, then optional ones with what they unlock.
3. Offer to run the install commands for anything missing. Logins and keys stay with the user.
