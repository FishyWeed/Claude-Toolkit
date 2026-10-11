# Claude Toolkit

My Claude Code setup as one plugin marketplace: mods, skills and an output style, installable on any machine.

## Install

```
claude plugin marketplace add FishyWeed/Claude-Toolkit
claude plugin install toolkit-setup@claude-toolkit
```

Then, inside Claude Code, run:

```
/toolkit-setup
```

It checks the machine, installs what you ask for, and lists every login and API key still needed. It never asks for key values in chat.

To install everything in one go:

```
claude plugin install prompt-enhancer@claude-toolkit
claude plugin install model-router@claude-toolkit
claude plugin install search-switch@claude-toolkit
claude plugin install mods-skills-panel@claude-toolkit
claude plugin install clear-caveman@claude-toolkit
claude plugin install design-directions@claude-toolkit
claude plugin install swarm@claude-toolkit
claude plugin install codeburn@claude-toolkit
```

This repo is private, so the machine must be signed in to GitHub (`gh auth login`, or Git's browser sign-in).

## What's inside

See [TOOLKIT.md](TOOLKIT.md) for every plugin: what it does, setup, and an example.

## Update

```
claude plugin marketplace update claude-toolkit
claude plugin update <plugin>@claude-toolkit
```

## Working on the toolkit

See [CLAUDE.md](CLAUDE.md). Short version: no secrets in the repo, keep `TOOLKIT.md` current, validate and test before committing.
