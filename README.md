# AI Here — 在 Finder 里一键用 Claude Code / Codex 打开文件夹

> Right-click any folder in macOS Finder to open it in **Claude Code** or **Codex** — CLI (in iTerm / Terminal) or desktop app. No more `cd` + typing `claude`, no more copying paths into the desktop app. Plus a Finder toolbar button for the folder you're currently in.

以前：选中文件夹 → 右键用终端打开 → 输入 `claude` / `codex`；桌面版还要复制路径、新建项目。
现在：**右键文件夹 → 快速操作 → 选一个**，完事。

## 安装

```bash
git clone https://github.com/chenwenbo/ai-here.git
cd ai-here
./install.sh
```

依赖：macOS（13+，在 macOS 26 上测试），已安装 [Claude Code](https://docs.claude.com/en/docs/claude-code) 和/或 [Codex CLI](https://github.com/openai/codex)；桌面版模式需要对应的 Claude / Codex 桌面应用。无需 Xcode、无需签名，纯 shell + Automator + AppleScript。

## 三个入口

| 场景 | 操作 |
|---|---|
| 选中了某个文件夹 | 右键 → **快速操作** → `Claude Code（终端）` / `Codex（终端）` / `Claude Code（桌面版）` / `Codex（桌面版）` |
| 已经在某个文件夹里面（没选中任何东西） | 点 Finder 工具栏上的 **AI Here** 按钮 → 选择工具（也提供“继续上次会话”） |
| 在终端里 | `ai-here claude-cli .`、`ai-here codex-app ~/项目` 等 |

工具栏按钮的安装：按住 **⌘** 把 `~/Applications/AI Here.app` 拖到任意 Finder 窗口的工具栏上。也可以把文件夹直接拖到这个按钮上。

## 各模式做了什么

| 模式 | 实现 |
|---|---|
| `claude-cli` / `codex-cli` | 在 iTerm（没有则用系统终端）新窗口里 `cd <目录> && claude`（或 `codex`），走你的交互式 shell，PATH/别名与平时一致 |
| `claude-continue` / `codex-resume` | `claude --continue` / `codex resume --last` |
| `claude-app` | 打开 `claude://code/new?folder=<目录>`，Claude 桌面版的 Code 标签页直接以该目录新建会话 |
| `codex-app` | 执行 `codex app <目录>`，Codex 桌面版直接打开该工作区 |

选中多个文件夹时会各开一个；选中的是文件则使用其所在文件夹。

## 配置

`~/.config/ai-here/config`（改完立即生效）：

```sh
TERMINAL_APP=auto      # auto | iTerm | Terminal
OPEN_IN=window         # window | tab（iTerm）
CLAUDE_CMD="claude"    # 例如 "claude --model opus"
CODEX_CMD="codex"
```

## 键盘快捷键（可选）

系统设置 → 键盘 → 键盘快捷键 → 服务 → 文件和文件夹，给 `Claude Code（终端）` 等设置快捷键，之后选中文件夹按快捷键即可。

## 更新 / 卸载

```bash
git pull && ./install.sh   # 更新
./uninstall.sh             # 卸载，加 --purge 同时删除配置
```

安装位置：`~/Library/Services/*.workflow`、`~/Library/Application Support/AIHere/ai-here`、`~/Applications/AI Here.app`、`~/.local/bin/ai-here`。日志：`~/Library/Logs/ai-here.log`。

## 常见问题

- **右键菜单里没出现**：系统设置 → 隐私与安全性 → 扩展 → 访达（Finder）里勾选；或执行 `killall Finder`。
- **第一次使用弹出“想要控制 iTerm/终端”**：点“允许”。如果误点了拒绝：系统设置 → 隐私与安全性 → 自动化 中重新勾选。
- **右键菜单有两个 Claude 桌面版入口**：较新版本的 Claude 桌面版自带 `New Claude Code Session Here`，功能相同，可在 系统设置 → 键盘 → 键盘快捷键 → 服务 中取消勾选其中一个。

## 项目结构

```
bin/ai-here               核心启动脚本（所有入口最终都调用它）
src/AIHere.applescript    Finder 工具栏按钮（安装时编译为 AI Here.app）
install.sh                生成 4 个快速操作、编译工具栏按钮、安装命令
uninstall.sh              卸载
config.example            配置模板
```

## License

MIT
