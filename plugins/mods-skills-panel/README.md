# Mods & Skills panel

A Claude Code mod that adds a side panel listing your mods and skills, with:

- a toggle between **Mods** and **Skills** (keys `m` / `s`, `r` to refresh)
- a numbered list of names, colour-coded by where each came from; click a name to open its details, click again to close, `x` to collapse all
- each one's description, and for mods the slash commands they add
- how many times each has been used (kept across sessions)
- a **Model** button per item that cycles Default → Opus → Sonnet → Haiku
  - a skill with a model runs the rest of that reply on it
  - a mod with a model has its own model calls sent to it

Open it any time with `/mods-skills`, or with the **🧩 Skills** and **🛠 Mods** buttons just above the chat box, which open the panel on that list.

## Install

Claude Code must be installed. Run the install line in a terminal session (`claude`), not in the desktop app's Code tab.

**From this folder on your computer:**

```
/plugin install mods-skills-panel --marketplace /full/path/to/mods-skills-panel
```

**From GitHub** (after pushing this folder to a repository of your own):

```
/plugin install mods-skills-panel --marketplace <your-github-name>/<repo-name>
```

Answer `y` to add the marketplace, then press Enter to install for your user. Once installed for your user, it also loads in the desktop app's Code tab.

## Develop

```
claude --plugin-dir /full/path/to/mods-skills-panel
claude plugin validate /full/path/to/mods-skills-panel
claude plugin test /full/path/to/mods-skills-panel
```
