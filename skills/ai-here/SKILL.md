---
name: ai-here
description: Open a local folder in Claude Code, Codex or WorkBuddy (terminal or desktop app) on macOS via the AI Here tool, check its install status, or install it. Use when the user asks to "open this folder/project in Codex / Claude desktop / WorkBuddy / a new terminal with claude", to hand the current project off to another AI coding tool, or to install / verify the AI Here Finder right-click menu.
---

# AI Here

AI Here (https://github.com/chenwenbo/ai-here) adds Finder right-click items and an `ai-here` command that open a folder directly in Claude Code, Codex or WorkBuddy. macOS only.

## 1. Check first

```bash
ai-here doctor --json
```

Returns JSON: `version`, `claude_cli`, `codex_cli`, `claude_app`, `codex_app`, `workbuddy_app` (empty string = not found), `terminal`, `config`, and `services` (installed right-click items). If `ai-here` is not on PATH, install it (section 3).

## 2. Open a folder

```bash
ai-here <mode> <absolute-folder-path> [more folders...]
```

| mode | What happens |
|---|---|
| `claude-cli` | New iTerm/Terminal window: `cd <folder> && claude` |
| `claude-continue` | Same, with `claude --continue` |
| `codex-cli` | New iTerm/Terminal window: `cd <folder> && codex` |
| `codex-resume` | Same, with `codex resume --last` |
| `claude-app` | Claude desktop app: new Claude Code session rooted at the folder |
| `codex-app` | Codex desktop app opens the folder as a workspace (`codex app <folder>`) |
| `workbuddy` | WorkBuddy: new task with the folder as working directory; a prompt is pre-filled, never auto-sent |

Rules:

- Pass absolute paths. A file path is fine: its parent folder is used. With no path, the current directory is used.
- Preview without opening anything: `AI_HERE_DRY_RUN=1 ai-here claude-app <folder>` prints the deep link (desktop modes).
- These commands open windows on the user's screen. Run them only when the user asked to open something; say which app and folder you opened.
- Do not use AI Here to start work inside your own session; it is for handing a folder to another tool or window.

## 3. Install / update / uninstall

```bash
git clone https://github.com/chenwenbo/ai-here.git ~/ai-here   # or: cd ~/ai-here && git pull
cd ~/ai-here && ./install.sh                                    # add --skill to also install this skill
ai-here doctor
```

`./uninstall.sh` removes everything (`--purge` also deletes `~/.config/ai-here`). After installing, tell the user: right-click a folder in Finder → 服务 (Services) → pick a tool; on first use macOS asks to allow controlling iTerm/Terminal.

## 4. Configure

`~/.config/ai-here/config` (zsh syntax, applies immediately): `TERMINAL_APP` (auto | iTerm | Terminal), `OPEN_IN` (window | tab), `CLAUDE_CMD`, `CODEX_CMD`, `WORKBUDDY_PROMPT` (`%s` = folder name), `WORKBUDDY_MODE` (code | work | design). Log: `~/Library/Logs/ai-here.log`.
