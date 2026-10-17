# AI Here

<img src="src/AIHere.png" width="128" height="128" alt="AI Here app icon">

**Right-click any folder in macOS Finder to open it in Claude Code, Codex or WorkBuddy — CLI or desktop app.**
**在 macOS Finder 里右键文件夹，一键用 Claude Code / Codex / WorkBuddy 打开 —— 命令行版或桌面版都行。**

[English](#english) · [中文](#中文) · [Agent 接入 / For AI agents](#agent-接入--for-ai-agents)

跨 Codex、Claude Code、WorkBuddy 和 ChatGPT 的工作交接用法见 [工作交接指南](docs/cross-agent-handoff.md)。

1.7.1 支持 Finder 多选文件带入原生附件栏；左侧核对、移除文件，右侧按命令行与桌面应用分组，两个图标按钮悬停显示文字：[直接开始 / 总结并接续](docs/context-launch.md)。总结入口预置内置 `ai-here-handoff` 技能提示，核验并保存本地交接后继续对话。


首次启用、切换 Agent、ChatGPT 结果带回和隔天接续等具体步骤，见 [交接用户场景与操作路径](docs/handoff-user-scenarios.md)。

---

## English

### Why

Before: select a folder → right-click "New Terminal at Folder" → type `claude` / `codex`. For the desktop apps it's even worse: copy the path, create a project, paste it in.

Now: **right-click the folder → Services → pick one.** Done.

### Install

```bash
git clone https://github.com/chenwenbo/ai-here.git
cd ai-here
./install.sh
ai-here doctor          # check what was found and installed
```

Requirements: macOS 13+ (tested on macOS 26), with [Claude Code](https://docs.claude.com/en/docs/claude-code) and/or [Codex CLI](https://github.com/openai/codex) installed. The desktop modes need the Claude / Codex / WorkBuddy desktop apps. Building the native UI requires Apple Command Line Tools (swiftc), without the full Xcode app. Local ad-hoc signing is handled by the installer.

### Three ways in

| When | Do |
|---|---|
| Multiple files are selected | Click **AI Here** in the Finder toolbar → check the attachment rail → choose an Agent action |
| A folder is selected | Right-click → **Services** → `Claude Code CLI` / `Codex CLI` / `Claude Code App` / `Codex App` / `WorkBuddy` |
| You're already *inside* a folder (nothing selected) | Click the **AI Here** button in the Finder toolbar → pick a tool, then Start directly or Summarize & continue |
| In a terminal, or from an AI agent | `ai-here claude-cli .`, `ai-here codex-app ~/project`, `ai-here workbuddy ~/project`, … |

Menu labels: `CLI` = command-line tool, `App` = desktop app. The `WorkBuddy` item is only added when WorkBuddy is installed. To use English labels, edit the `ACTIONS` list at the top of `install.sh` (and the matching names in `uninstall.sh`), then re-run `./install.sh`.

To add the toolbar button, hold **⌘** and drag `~/Applications/AI Here.app` onto any Finder window's toolbar. You can also drop folders onto it.

The native window shows selected Finder files in a removable attachment rail and groups five launch targets into CLI and desktop apps. Each row has two icon buttons: an arrow for **Start directly**, and a document with magnifier for **Summarize & continue**. Hover reveals labels; keyboard and accessibility names are provided. Without files, the first opens a conversation normally. With files, it passes an explicit local material list and asks the Agent to read it before waiting for your task. The second sends a fixed instruction to use the bundled local `ai-here-handoff` skill, verify workspace records and current files, append a handoff document, and report readiness for your next instruction. It does not read other tools' private chat histories or automatically execute old next steps.

CLI tools receive the prompt as one argument; Codex CLI additionally receives detected PNG/JPEG/WebP images through its image option. Other material remains an explicit local reference, not an uploaded attachment. Codex and Claude desktop apps open a new conversation with the workspace and prompt pre-filled. Long prompts use a short instruction to read the private task snapshot; WorkBuddy always uses this snapshot instruction. Review and send in the target app; no clipboard copy is needed. Opening a tool is not proof it completed the summary. See the [launch guide](docs/context-launch.md).

### Workspace handoffs

Handoff management remains available in the CLI:

```bash
ai-here handoff init ~/project --instructions
ai-here handoff open ~/project
ai-here handoff copy ~/project
ai-here task summarize --cwd ~/project --tool codex-cli
```

The summary skill writes a new local record through the existing handoff commands; it does not overwrite project rules or initialize handoffs until the receiving Agent executes the instruction. With no saved progress, it records an initial verified state and explicitly marks missing conversation evidence. The built-in skill is installed with AI Here, separate from personal skills. See the [handoff guide](docs/cross-agent-handoff.md).

### What each mode does

| Mode | How |
|---|---|
| `claude-cli` / `codex-cli` | Opens a new iTerm window (falls back to Terminal.app) and runs the login shell, changes into the folder first, then starts Claude or Codex; iTerm creates the session with this command instead of typing into an existing shell |
| `claude-continue` / `codex-resume` | `claude --continue` / `codex resume --last` |
| `claude-app` | Opens `claude://code/new?folder=<folder>`, which starts a new session in the Claude desktop app's Code tab, rooted at that folder |
| `codex-app` | Runs `codex app <folder>`, which opens the folder as a workspace in the Codex desktop app |
| `workbuddy` | Opens `workbuddy://task?action=start&cwd=<folder>&prompt=…`: WorkBuddy starts a new task with that folder as its working directory. The prompt is only pre-filled, never sent |

The toolbar panel starts one conversation per action and asks you to choose a directory when several folders are selected. Legacy direct services and CLI commands retain their multiple-directory behavior. A selected file supplies its parent directory.

### Configuration

`~/.config/ai-here/config` (changes apply immediately):

```sh
TERMINAL_APP=auto      # auto | iTerm | Terminal
OPEN_IN=window         # window | tab (iTerm only)
CLAUDE_CMD="claude"    # e.g. "claude --model opus"
CODEX_CMD="codex"
WORKBUDDY_PROMPT="我们在「%s」这个文件夹里工作，先帮我看看里面有什么。"   # %s = folder name
WORKBUDDY_MODE=""      # code | work | design (empty = WorkBuddy decides)
HANDOFF_HINTS=1        # reading reminders for enabled workspaces
```

### Keyboard shortcuts (optional)

System Settings → Keyboard → Keyboard Shortcuts → Services → Files and Folders. Assign a shortcut to e.g. `Claude Code CLI`, then select a folder and press it.

### Update / uninstall

```bash
git pull && ./install.sh   # update
./uninstall.sh             # uninstall; add --purge to also delete the config
```

Installed to: `~/Library/Services/*.workflow`, `~/Library/Application Support/AIHere/ai-here`, `~/Applications/AI Here.app`, `~/.local/bin/ai-here`. Log: `~/Library/Logs/ai-here.log`.

### Troubleshooting

- **Codex is installed but Finder cannot find `codex`**: AI Here also checks the CLI bundled inside the installed Codex desktop app. CLI modes preserve your terminal's `codex` command and configured arguments, and use the bundled executable when it is absent from PATH.
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
./install.sh
ai-here doctor          # 查看检测到的工具和已安装的右键菜单
```

依赖：macOS 13+（在 macOS 26 上测试），已安装 [Claude Code](https://docs.claude.com/en/docs/claude-code) 和/或 [Codex CLI](https://github.com/openai/codex)；桌面版模式需要对应的 Claude / Codex / WorkBuddy 桌面应用。构建原生界面需要 Apple Command Line Tools（swiftc），无需完整 Xcode；安装脚本自动完成本地签名。

### 三个入口

| 场景 | 操作 |
|---|---|
| 选中了某个文件夹 | 右键 → **服务** → `Claude Code CLI` / `Codex CLI` / `Claude Code App` / `Codex App` / `WorkBuddy` |
| 已经在某个文件夹里面（没选中任何东西） | 点 Finder 工具栏上的 **AI Here** 按钮 → 选择工具的“直接开始”或“总结并接续” |
| 在终端里，或让 AI Agent 调用 | `ai-here claude-cli .`、`ai-here codex-app ~/项目`、`ai-here workbuddy ~/项目` 等 |

`WorkBuddy` 菜单项只在检测到已安装 WorkBuddy 时才会添加。工具栏按钮的安装：按住 **⌘** 把 `~/Applications/AI Here.app` 拖到任意 Finder 窗口的工具栏上。也可以把文件夹直接拖到这个按钮上。

原生窗口按命令行和桌面应用列出五个入口。每行右侧两个图标按钮：箭头表示 **直接开始**，文档放大镜表示 **总结并接续**；悬停显示文字提示，支持键盘与无障碍名称。左侧自动列出 Finder 选中的文件，可逐个移除；更换工作目录仍保留附件。不填写自由任务或选择交接记录。

### 直接开始 / 总结并接续

**直接开始**：没有附件时按原方式打开；有附件时带入完整本地文件清单，让 Agent 先核对并读取，再等待你给任务。

**总结并接续**：预置提示，要求接收 Agent 使用随应用安装的 `ai-here-handoff` 本地技能，核验项目记录与当前文件、保存新的交接文档，再告知准备情况，等待你的下一步指令。没有落盘的其他 Agent 聊天不能被当作已知进展；没有交接时生成初始核验记录，明确未知项。

两个动作都会带上附件清单。Codex CLI 的常规 PNG/JPEG/WebP 图片另外使用原生图片参数，其他材料作为本地路径供读取，不等于上传。CLI 接收完整提示；Codex App / Claude App 自动打开新对话并预填工作目录与提示；长提示使用读取私有任务快照的短指令，WorkBuddy 始终使用快照指令。无需复制粘贴，在目标应用确认后发送；Claude 可能另需确认目录访问。按钮点击成功不代表总结已经完成。详细步骤见[启动指南](docs/context-launch.md)。

### 跨 Agent 工作交接

高级管理操作保留在命令行：

```bash
ai-here handoff init ~/项目 --instructions
ai-here handoff open ~/项目
ai-here handoff copy ~/项目
ai-here task summarize --cwd ~/项目 --tool codex-cli
```

总结技能使用现有命令保存本地交接，未执行提示之前不初始化项目，不改写项目规则。已有 `AGENTS.md`、`CLAUDE.md` 保持原内容。技能作为软件内置资源安装，不向个人 Skills 目录添加副本。

写入、编辑、刷新和各工具的接入边界见[工作交接指南](docs/cross-agent-handoff.md)。

### 各模式做了什么

| 模式 | 实现 |
|---|---|
| `claude-cli` / `codex-cli` | 在新终端中先进入目标目录，再启动 Claude 或 Codex；iTerm 在创建会话时指定登录 shell 命令，避免向未准备好的会话模拟键入 |
| `claude-continue` / `codex-resume` | `claude --continue` / `codex resume --last` |
| `claude-app` | 打开 `claude://code/new?folder=<目录>`；带上下文时追加 `q` 预填提示，用户确认目录后发送 |
| `codex-app` | 普通入口执行 `codex app <目录>`；带上下文时通过 `codex://new?path=<目录>&prompt=…` 新建并预填对话 |
| `workbuddy` | 打开 `workbuddy://task?action=start&cwd=<目录>&prompt=…`，WorkBuddy 以该文件夹为工作目录新建任务；提示词只预填、不会自动发送 |

桌面面板一次动作只启动一个对话；多目录需选择其中一个。旧的工具快捷服务与 CLI 保留多目录启动行为。选中的是文件则使用其所在文件夹。

### 配置

`~/.config/ai-here/config`（改完立即生效）：

```sh
TERMINAL_APP=auto      # auto | iTerm | Terminal
OPEN_IN=window         # window | tab（仅 iTerm）
CLAUDE_CMD="claude"    # 例如 "claude --model opus"
CODEX_CMD="codex"
WORKBUDDY_PROMPT="我们在「%s」这个文件夹里工作，先帮我看看里面有什么。"   # %s = 文件夹名
WORKBUDDY_MODE=""      # code | work | design（留空由 WorkBuddy 决定）
HANDOFF_HINTS=1        # 已启用交接的工作空间显示读取提醒
```

### 键盘快捷键（可选）

系统设置 → 键盘 → 键盘快捷键 → 服务 → 文件和文件夹，给 `Claude Code CLI` 等设置快捷键，之后选中文件夹按快捷键即可。

### 更新 / 卸载

```bash
git pull && ./install.sh   # 更新
./uninstall.sh             # 卸载，加 --purge 同时删除配置
```

安装位置：`~/Library/Services/*.workflow`、`~/Library/Application Support/AIHere/ai-here`、`~/Applications/AI Here.app`、`~/.local/bin/ai-here`。日志：`~/Library/Logs/ai-here.log`。

### 常见问题

- **已安装 Codex，但 Finder 找不到 `codex` 命令**：AI Here 会自动查找 Codex 桌面应用内置的 CLI。终端模式优先保留原有 `codex` 命令及配置参数，PATH 中没有命令时使用应用内置的可执行文件。
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
2. 在仓库目录运行 ./install.sh
3. 运行 ai-here doctor，告诉我检测到了哪些工具、右键菜单里装了哪些选项
4. 提醒我：第一次使用时 macOS 会询问是否允许控制 iTerm/终端，要点“允许”
```

### 2. 命令行接口 / CLI for agents

Agent 调用时用这几个命令就够了 / Everything an agent needs:

```bash
ai-here doctor --json                       # 机器可读的安装状态 / machine-readable status
ai-here <mode> <绝对路径/absolute path>      # 打开文件夹 / open a folder
AI_HERE_DRY_RUN=1 ai-here claude-app <path> # 只打印深链、不打开 / print the deep link only
ai-here handoff init <path> --instructions # 启用工作空间交接 / enable handoffs
ai-here handoff add <path> --title "任务标题" --agent codex --status completed --body-file -
ai-here handoff list <path>                # 查看记录 / list records
ai-here handoff export <path>              # 输出摘要 / export summary
```

`doctor --json` 示例 / example:

```json
{"version":"1.7.1","claude_cli":"/Users/you/.local/bin/claude","codex_cli":"/Users/you/.local/bin/codex",
 "claude_app":"/Applications/Claude.app","codex_app":"/Applications/Codex.app","workbuddy_app":"/Applications/WorkBuddy.app",
 "terminal":"iTerm","config":"/Users/you/.config/ai-here/config","handoff_runtime":"/usr/bin/python3","services":["Claude Code CLI","…","WorkBuddy"]}
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
src/AIHere.applescript    Finder entry + launch routing  Finder 入口与启动逻辑
src/AIHereUI.swift        Native AppKit window + icon actions  原生窗口与图标按钮
src/AIHere.icns           App icon (all macOS sizes)  应用图标
src/AIHere.png            App icon source / preview  应用图标原图
src/export-tool-icons.js  Copies locally installed tool icons into the app  提取本机工具图标
lib/handoff.py            Workspace handoff records, index and exports  工作交接管理
lib/task_request.py       Context requests, prompt snapshots and dispatch  带上下文启动
tests/                    Handoff and launcher integration checks  交接与启动器测试
install.sh                Generates the Finder services, toolbar app and CLI  安装
uninstall.sh              Uninstaller  卸载
config.example            Config template  配置模板
```

## License

MIT
