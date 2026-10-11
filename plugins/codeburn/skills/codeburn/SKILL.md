---
name: codeburn
description: Run CodeBurn (a local tool that reads AI coding session logs) to see where Claude Code tokens and money go, then explain the results and suggest fixes. Use when the user types /codeburn or asks about their Claude Code spend, token waste, or usage report.
argument-hint: "[optimize | overview | models | yield | quota | status] [-p today|week|30days|month]"
disable-model-invocation: true
allowed-tools: Bash(npx -y codeburn@0.9.25 overview:*), Bash(npx -y codeburn@0.9.25 optimize:*), Bash(npx -y codeburn@0.9.25 models:*), Bash(npx -y codeburn@0.9.25 yield:*), Bash(npx -y codeburn@0.9.25 status:*), Bash(npx -y codeburn@0.9.25 audit:*)
---

# CodeBurn report

CodeBurn is a standalone program, pinned here to version `0.9.25`. It reads the session logs Claude Code already keeps on this computer. These commands only read; they change nothing.

## 1. The default report (already run)

When this skill loaded, Claude Code ran these two read-only commands and put their output here:

### `codeburn overview -p week`
!`NO_COLOR=1 FORCE_COLOR=0 npx -y codeburn@0.9.25 overview --no-color -p week 2>&1`

### `codeburn optimize -p week`
!`NO_COLOR=1 FORCE_COLOR=0 npx -y codeburn@0.9.25 optimize -p week 2>&1`

Ignore a line like `codeburn: skipping DSH sessions…`; it's harmless. If either block is empty or shows an error, say so and suggest running `npx -y codeburn@0.9.25 doctor` in a terminal.

## 2. If the user asked for something else

The user's arguments: `$ARGUMENTS`

- Empty, `optimize` or `overview`: use the output above. Don't run anything else.
- `models`: run `npx -y codeburn@0.9.25 models --format markdown` with the Bash tool (add `-p` if given).
- `yield`: run `npx -y codeburn@0.9.25 yield -p 30days` (or the period given).
- `status`: run `npx -y codeburn@0.9.25 status`.
- `audit`: run `npx -y codeburn@0.9.25 audit`.
- A different period (for example `-p 30days`): rerun `overview` and `optimize` with that period using the Bash tool.
- `quota`: run `npx -y codeburn@0.9.25 quota`. It asks each signed-in provider how much of its plan is left, so it isn't pre-approved: Claude Code will ask the user first.

The interactive commands (`codeburn` alone, `compare`, `context` without an id, `web`) need a keyboard and won't work here. Offer `models` or `optimize` instead.

## 3. Never change anything without asking

Never run these unless the user explicitly asks in this conversation, and confirm in full sentences first:
`optimize --apply`, `act undo`, `guard install`, `guard uninstall`, `sync`, `share`, `devices`, `menubar`, `plan set`, `model-alias`, `price-override`.

When a finding suggests a command (for example `claude mcp remove …` or moving skills), present it as a suggestion. Don't run it unless the user says to.

## 4. Report back

Read the output and give the user a short report:

1. **Headline:** total spend and period, the main model, and the health grade if `optimize` ran.
2. **Biggest wins:** the top 3 findings by savings. For each, give the saving, a plain explanation of what's wasting tokens, and the exact fix command or rule.
3. **Worth knowing:** anything surprising, such as one model taking nearly all spend, a very low or very high cache hit rate, or a project far above average.
4. **Next step:** the single change that would help most, and whether CodeBurn can apply it (`optimize --apply`) or it needs a habit change.

Be honest about uncertainty. CodeBurn labels each saving as "measured" or "estimated". Pass that on. On a subscription such as Claude Max, the dollar figures are API-equivalent costs, not a real bill. Say so once.
