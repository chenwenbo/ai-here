# AI Here

**Right-click any folder in macOS Finder to open it in Claude Code, Codex or WorkBuddy — CLI or desktop app.**
**在 macOS Finder 里右键文件夹，一键用 Claude Code / Codex / WorkBuddy 打开 —— 命令行版或桌面版都行。**

[English](#english) · [中文](#中文) · [Agent 接入 / For AI agents](#agent-接入--for-ai-agents)

---

## English

### Why

Before: select a folder → right-click "New Terminal at Folder" → type `claude` / `codex`. For the desktop apps it's even worse: copy the path, create a project, paste it in.

Now: **right-click the folder → Services → pick one.** Done.

### Install

```bash
git clone https://github.com/chenwenbo/ai-here.git
cd ai-here
./install.sh            # add --skill to also install the Agent Skill (see below)
ai-here doctor          # check what was found and installed
```

Requirements: macOS 13+ (tested on macOS 26), with [Claude Code](https://docs.claude.com/en/docs/claude-code) and/or [Codex CLI](https://github.com/openai/codex) installed. The desktop modes need the Claude / Codex / WorkBuddy desktop apps. No Xcode, no code signing — just shell, Automator and AppleScript.

### Three ways in

| When | Do |
|---|---|
| A folder is selected | Right-click → **Services** → `Claude Code（终端）` / `Codex（终端）` / `Claude Code（桌面版）` / `Codex（桌面版）` / `WorkBuddy` |
| You're already *inside* a folder (nothing selected) | Click the **AI Here** button in the Finder toolbar → pick a tool (also offers "continue last session") |
| In a terminal, or from an AI agent | `ai-here claude-cli .`, `ai-here codex-app ~/project`, `ai-here workbuddy ~/project`, … |

Menu labels: `终端` = Terminal (CLI), `桌面版` = Desktop app. The `WorkBuddy` item is only added when WorkBuddy is installed. To use English labels, edit the `ACTIONS` list at the top of `install.sh` (and the matching names in `uninstall.sh`), then re-run `./install.sh`.

To add the toolbar button, hold **⌘** and drag `~/Applications/AI Here.app` onto any Finder window's toolbar. You can also drop folders onto it.

### What each mode does

| Mode | How |
|---|---|
| `claude-cli` / `codex-cli` | Opens a new iTerm window (falls back to Terminal.app) and runs `cd <folder> && claude` (or `codex`) in your interactive shell, so your PATH and aliases work as usual |
| `claude-continue` / `codex-resume` | `claude --continue` / `codex resume --last` |
| `claude-app` | Opens `claude://code/new?folder=<folder>`, which starts a new session in the Claude desktop app's Code tab, rooted at that folder |
| `codex-app` | Runs `codex app <folder>`, which opens the folder as a workspace in the Codex desktop app |
| `workbuddy` | Opens `workbuddy://task?action=start&cwd=<folder>&prompt=…`: WorkBuddy starts a new task with that folder as its working directory. The prompt is only pre-filled, never sent |

Selecting several folders opens one session each. If a file is selected, its parent folder is used.

### Configuration

`~/.config/ai-here/config` (changes apply immediately):

```sh
TERMINAL_APP=auto      # auto | iTerm | Terminal
OPEN_IN=window         # window | tab (iTerm only)
CLAUDE_CMD="claude"    # e.g. "claude --model opus"
CODEX_CMD="codex"
WORKBUDDY_PROMPT="我们在「%s」这个文件夹里工作，先帮我看看里面有什么。"   # %s = folder name
WORKBUDDY_MODE=""      # code | work | design (empty = WorkBuddy decides)
```

### Keyboard shortcuts (optional)

System Settings → Keyboard → Keyboard Shortcuts → Services → Files and Folders. Assign a shortcut to e.g. `Claude Code（终端）`, then select a folder and press it.

### Update / uninstall

```bash
git pull && ./install.sh   # update
./uninstall.sh             # uninstall; add --purge to also delete the config
```

Installed to: `~/Library/Services/*.workflow`, `~/Library/Application Support/AIHere/ai-here`, `~/Applications/AI Here.app`, `~/.local/bin/ai-here` (and `<agent>/skills/ai-here` with `--skill`). Log: `~/Library/Logs/ai-here.log`.

### Troubleshooting

- **The menu items don't show up**: System Settings → Privacy & Security → Extensions → Finder, and enable them. Or run `killall Finder`.
- **"… wants to control iTerm/Terminal" on first use**: click Allow. If you clicked Don't Allow, re-enable it under System Settings → Privacy & Security → Automation.
- **Two Claude desktop entries in the menu**: recent Claude desktop versions ship their own `New Claude Code Session Here`, which does the same thing. Turn one of them off under System Settings → Keyboard → Keyboard Shortcuts → Services.

---

## 中文

### 为什么做这个

以前：选中文件夹 → 右键用终端打开 → 输入 `claude` / `codex`；桌面版更麻烦，要复制路径、新建项目、再粘贴进去。

现在：**右键文件夹 → 服务 → 选一个**，完事。

### 安装

```bash
git clone https://github.com/chenwenbo/ai-here.git
cd ai-here
./install.sh            # 加 --skill 会同时安装 Agent Skill（见下文）
ai-here doctor          # 查看检测到的工具和已安装的右键菜单
```

依赖：macOS 13+（在 macOS 26 上测试），已安装 [Claude Code](https://docs.claude.com/en/docs/claude-code) 和/或 [Codex CLI](https://github.com/openai/codex)；桌面版模式需要对应的 Claude / Codex / WorkBuddy 桌面应用。无需 Xcode、无需签名，纯 shell + Automator + AppleScript。

### 三个入口

| 场景 | 操作 |
|---|---|
| 选中了某个文件夹 | 右键 → **服务** → `Claude Code（终端）` / `Codex（终端）` / `Claude Code（桌面版）` / `Codex（桌面版）` / `WorkBuddy` |
| 已经在某个文件夹里面（没选中任何东西） | 点 Finder 工具栏上的 **AI Here** 按钮 → 选择工具（也提供“继续上次会话”） |
| 在终端里，或让 AI Agent 调用 | `ai-here claude-cli .`、`ai-here codex-app ~/项目`、`ai-here workbuddy ~/项目` 等 |

`WorkBuddy` 菜单项只在检测到已安装 WorkBuddy 时才会添加。工具栏按钮的安装：按住 **⌘** 把 `~/Applications/AI Here.app` 拖到任意 Finder 窗口的工具栏上。也可以把文件夹直接拖到这个按钮上。

### 各模式做了什么

| 模式 | 实现 |
|---|---|
| `claude-cli` / `codex-cli` | 在 iTerm（没有则用系统终端）新窗口里 `cd <目录> && claude`（或 `codex`），走你的交互式 shell，PATH/别名与平时一致 |
| `claude-continue` / `codex-resume` | `claude --continue` / `codex resume --last` |
| `claude-app` | 打开 `claude://code/new?folder=<目录>`，Claude 桌面版的 Code 标签页直接以该目录新建会话 |
| `codex-app` | 执行 `codex app <目录>`，Codex 桌面版直接打开该工作区 |
| `workbuddy` | 打开 `workbuddy://task?action=start&cwd=<目录>&prompt=…`，WorkBuddy 以该文件夹为工作目录新建任务；提示词只预填、不会自动发送 |

选中多个文件夹时会各开一个；选中的是文件则使用其所在文件夹。

### 配置

`~/.config/ai-here/config`（改完立即生效）：

```sh
TERMINAL_APP=auto      # auto | iTerm | Terminal
OPEN_IN=window         # window | tab（仅 iTerm）
CLAUDE_CMD="claude"    # 例如 "claude --model opus"
CODEX_CMD="codex"
WORKBUDDY_PROMPT="我们在「%s」这个文件夹里工作，先帮我看看里面有什么。"   # %s = 文件夹名
WORKBUDDY_MODE=""      # code | work | design（留空由 WorkBuddy 决定）
```

### 键盘快捷键（可选）

系统设置 → 键盘 → 键盘快捷键 → 服务 → 文件和文件夹，给 `Claude Code（终端）` 等设置快捷键，之后选中文件夹按快捷键即可。

### 更新 / 卸载

```bash
git pull && ./install.sh   # 更新
./uninstall.sh             # 卸载，加 --purge 同时删除配置
```

安装位置：`~/Library/Services/*.workflow`、`~/Library/Application Support/AIHere/ai-here`、`~/Applications/AI Here.app`、`~/.local/bin/ai-here`（加 `--skill` 时还有 `<agent>/skills/ai-here`）。日志：`~/Library/Logs/ai-here.log`。

### 常见问题

- **右键菜单里没出现**：系统设置 → 隐私与安全性 → 扩展 → 访达（Finder）里勾选；或执行 `killall Finder`。
- **第一次使用弹出“想要控制 iTerm/终端”**：点“允许”。如果误点了拒绝：系统设置 → 隐私与安全性 → 自动化 中重新勾选。
- **右键菜单有两个 Claude 桌面版入口**：较新版本的 Claude 桌面版自带 `New Claude Code Session Here`，功能相同，可在 系统设置 → 键盘 → 键盘快捷键 → 服务 中取消勾选其中一个。

---

## Agent 接入 / For AI agents

AI Here 不只给人用，也可以交给 Claude Code、Codex、WorkBuddy 这类 AI Agent 安装和调用。
AI Here is built to be installed and driven by AI agents (Claude Code, Codex, WorkBuddy, …) too.

### 1. 让 Agent 帮你安装 / Let your agent install it

把下面这段话直接发给你的 Agent / Paste this to your agent:

```text
请帮我安装 AI Here（https://github.com/chenwenbo/ai-here）：
1. 把仓库 clone 到 ~/ai-here（已存在就 git pull）
2. 在仓库目录运行 ./install.sh --skill
3. 运行 ai-here doctor，告诉我检测到了哪些工具、右键菜单里装了哪些选项
4. 提醒我：第一次使用时 macOS 会询问是否允许控制 iTerm/终端，要点“允许”
```

### 2. Agent Skill

仓库自带一个 Agent Skill：[`skills/ai-here/SKILL.md`](skills/ai-here/SKILL.md)。装上之后，你可以直接对 Agent 说「在 Codex 桌面版里打开这个项目」「新开一个终端，用 Claude Code 跑 ~/xxx」，Agent 就知道该怎么调用。
The repo ships an Agent Skill. With it installed, you can tell your agent "open this project in the Codex desktop app" and it knows what to run.

```bash
./install.sh --skill
```

`--skill` 会把它复制到本机已存在的这些目录 / copies it into whichever of these exist:

| Agent | Skill 目录 |
|---|---|
| Claude Code | `~/.claude/skills/ai-here` |
| Codex | `~/.codex/skills/ai-here` |
| WorkBuddy | `~/.workbuddy/skills/ai-here` |
| 通用 / shared | `~/.agents/skills/ai-here` |

### 3. 命令行接口 / CLI for agents

Agent 调用时用这几个命令就够了 / Everything an agent needs:

```bash
ai-here doctor --json                       # 机器可读的安装状态 / machine-readable status
ai-here <mode> <绝对路径/absolute path>      # 打开文件夹 / open a folder
AI_HERE_DRY_RUN=1 ai-here claude-app <path> # 只打印深链、不打开 / print the deep link only
```

`doctor --json` 示例 / example:

```json
{"version":"1.1.0","claude_cli":"/Users/you/.local/bin/claude","codex_cli":"/Users/you/.local/bin/codex",
 "claude_app":"/Applications/Claude.app","codex_app":"/Applications/Codex.app","workbuddy_app":"/Applications/WorkBuddy.app",
 "terminal":"iTerm","config":"/Users/you/.config/ai-here/config","services":["Claude Code（终端）","…","WorkBuddy"]}
```

字段为空字符串表示没找到该工具。模式列表同上文：`claude-cli`、`claude-continue`、`codex-cli`、`codex-resume`、`claude-app`、`codex-app`、`workbuddy`。
An empty string means the tool was not found. Modes are listed above.

约定 / Conventions:

- 传绝对路径；传文件会自动用它所在的文件夹 / Pass absolute paths; a file resolves to its folder.
- 这些命令会在用户屏幕上打开窗口，只在用户要求时调用 / These open windows on the user's screen; only run them when asked.
- 退出码 0 表示已发出打开请求；出错时会写日志并弹 macOS 通知 / Exit code 0 means the open request was sent; errors go to the log and a macOS notification.

---

## Project layout / 项目结构

```
bin/ai-here               Core launcher; every entry point calls it  核心启动脚本（所有入口最终都调用它）
src/AIHere.applescript    Finder toolbar button (compiled to AI Here.app)  Finder 工具栏按钮
skills/ai-here/SKILL.md   Agent Skill for Claude Code / Codex / WorkBuddy  Agent 技能说明
install.sh                Generates the Finder services, toolbar app, CLI (--skill: Agent Skill)  安装
uninstall.sh              Uninstaller  卸载
config.example            Config template  配置模板
```

## License

MIT
