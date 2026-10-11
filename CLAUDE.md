# Claude Toolkit: working in this repo

This repo is a Claude Code plugin marketplace. Each folder in `plugins/` is one plugin: a mod (TypeScript hooks), a skill, or an output style. `.claude-plugin/marketplace.json` lists them all.

## When the toolkit is added to a machine

Tell the user to run `/toolkit-setup`. It checks what's installed and signed in, and lists the remaining installs, logins and API keys. Never ask for key values in chat.

## Rules for changing the toolkit

- **No secrets in the repo.** Keys go in `~/.claude/settings.json` (`env` block), the OS environment, or a tool's own login. `.gitignore` blocks common key files; still check every diff.
- **Keep the catalog current.** When you add, remove or change a plugin, update `TOOLKIT.md` (what it is, setup, example) and, if it needs a key or login, `plugins/toolkit-setup/skills/toolkit-setup/SKILL.md`.
- **New plugin:** create `plugins/<name>/.claude-plugin/plugin.json`, then add an entry to `.claude-plugin/marketplace.json` with `"source": "./plugins/<name>"`.
- **Bump `version`** in a plugin's `plugin.json` when you change it, so installed copies update.
- **Pin third-party versions** (npm, PyPI, MCP servers) to a release at least two weeks old, never `@latest`.
- **Mods share the strip above the prompt.** An `AbovePrompt` render hook must call `next(e)` and include the result, so other mods' controls stay visible.

## Checks before committing

```
claude plugin validate .
claude plugin validate plugins/<name>
claude plugin test plugins/<name>
```

Mods with tests: prompt-enhancer, model-router, search-switch, mods-skills-panel, swarm. Run their tests after any change to them.

## Using a local copy instead of GitHub

To test changes before pushing: `claude plugin marketplace add <path to this folder>`. Claude Code then reads plugins straight from the folder; run `/reload-plugins` after edits.
