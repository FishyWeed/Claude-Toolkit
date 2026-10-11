# Clear Caveman

Claude Code plugin. Combines Caveman (short, no filler, exact technical details) with Clear Answers (plain language, self-contained wrap-up after multi-step work).

One output style: `output-styles/clear-caveman.md`. It's forced on while the plugin is enabled (`force-for-plugin: true`) and keeps Claude's normal coding behaviour (`keep-coding-instructions: true`).

## Install
claude plugin marketplace add "C:\Users\Admin\Documents\Claude\Mods\clear-caveman"
claude plugin install clear-caveman@clear-caveman-mods --scope user

## On / off
claude plugin disable clear-caveman@clear-caveman-mods
claude plugin enable clear-caveman@clear-caveman-mods

## Edit
Change `output-styles/clear-caveman.md`, then start a new session. No reinstall needed: the plugin is read from this folder.
