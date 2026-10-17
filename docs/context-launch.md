# 直接开始 / 总结并接续

AI Here 1.7.1 的原生工具窗口采用左侧附件栏、右侧 Agent 列表。Finder 多选文件自动进入附件栏；按命令行和桌面应用分组，每行两个图标动作，保留工作目录与更换。没有自由任务输入、交接选择或管理项。

## 使用

1. 在 Finder 选择目录或多个文件，点击 AI Here 工具栏按钮，或使用“服务 → AI Here · 带上下文启动”。拖目录到应用也可以。
2. 核对顶部工作目录，按需更换。文件作为本次材料列在左侧，可逐个移除；更换目录不清空附件。稳定 Finder 当前目录优先，拖放等没有目录上下文时使用文件父目录；多个目录需明确选择一个，一次动作只启动一个对话。
3. 在目标 Agent 那一行点击箭头图标（直接开始）或文档放大镜图标（总结并接续）。悬停按钮显示中文提示，也可按 Tab 聚焦、空格执行；Esc 或窗口关闭取消。

**直接开始**无附件时沿用普通启动方式；有附件时生成带本地材料清单的提示，要求 Agent 实际读取支持材料、指出无法读取项，再等待用户任务，不自动修改文件或调用总结技能。

**总结并接续**带入同一附件清单及固定提示：先使用内置 `ai-here-handoff` 技能，核验这个目录里已有的交接与当前文件，保存一份新的本地交接，再告诉用户已确认的进展、未知项和可继续的方向。总结结束后等待用户下一步，不擅自执行旧记录中的待办。

## Handoff 技能与可靠性

内置技能位于 `~/Library/Application Support/AIHere/skills/ai-here-handoff/SKILL.md`，源码在 `skills/ai-here-handoff/`。固定提示要求使用此技能，并提供可直接读取的绝对路径；无法读取技能或保存交接时必须报告失败，不能声称总结完成。

技能将已有交接作为待核验来源，检查当前文件、Git 状态及验证证据，明确区分旧记录陈述、实际核验和未知项。多个来源冲突时保留出处，不假定最新记录就是正在做的任务。

生成结果通过 `ai-here handoff add` 保存到 `.ai-here/handoffs/`，索引保留人工区。此前未启用交接时，由接收 Agent 在执行总结提示时建立初始记录；单击启动按钮本身不改项目规则或初始化项目。

这使用 AI Here 自己的本地技能，与 OpenGrove 的云端 Handoff 工具不同。没有安装个人技能、没有同步个人 Skills 路由、没有发布到交接服务。无法访问其他 Agent 未落盘的聊天时，必须把那部分进展写为未知；不会编造聊天摘要。

## 各工具的传递方式

- Claude Code CLI / Codex CLI：提示作为一个参数传入交互会话，沿用工具配置与权限机制；Codex CLI 为识别为 PNG/JPEG/WebP 的常规图片追加独立 -i 参数。逗号文件名不进入图片参数，作为本地参考路径处理。其他文件不伪装成图片或已上传附件，也不自动授予目录写权限。
- Codex App：通过 `codex://new?path=…&prompt=…` 打开新对话，指定工作目录并预填提示。
- Claude Code App：通过 `claude://code/new?folder=…&q=…` 打开 Code 新对话并预填提示；客户端可能要求确认目录。
- WorkBuddy：预填读取私有任务快照的短指令，用户确认后发送。

桌面入口无需复制粘贴，也不修改剪贴板。Codex / Claude 的完整提示若使百分号编码后的链接超过 8 KiB，则改为短指令，让 Agent 读取原始 `prompt.md`；快照保留完整提示和材料清单，不截断任务。若短指令仍超限，明确报错并保留快照。预填只创建草稿，三个工具都需要用户确认并发送。接口说明见 [Codex 官方深链文档](https://learn.chatgpt.com/docs/reference/commands)及 [Claude 官方深链文档](https://support.claude.com/en/articles/14729294-open-claude-desktop-with-a-link)。

启动请求、输入框预填与总结完成是不同状态。交接文档由 Agent 执行技能后生成；AI Here 不把点击按钮视为已执行总结。WorkBuddy 先前存在客户端会话创建超时，本版不将打开成功当作它已读取或执行的证明。

## 命令行与失败恢复

```bash
ai-here compose ~/项目
ai-here task start --cwd ~/项目 --tool codex-cli --action direct --reference ~/项目/需求说明.md
ai-here task start --cwd ~/项目 --tool codex-cli --action summary --reference ~/项目/流程图.png
ai-here task summarize --cwd ~/项目 --tool codex-cli
AI_HERE_DRY_RUN=1 ai-here task summarize --cwd ~/项目 --tool claude-app
```

总结提示和请求快照保存在 `~/Library/Application Support/AIHere/launches/<唯一ID>/`，目录权限 0700，文件 0600。失败时保留快照，界面返回本次目录及移除后的附件清单；启动前重新校验存在性，不能静默丢弃缺失文件。任务内容不写入普通启动日志。

`task context / prepare / launch` 与 `handoff init / add / open / copy` 等命令保留兼容用途；旧的各工具右键服务保持直接启动。桌面面板不再暴露这些高级操作。卸载保留项目里的正式交接，删除软件支持目录中的技能与任务缓存。

## 原生界面构建

安装脚本使用本机 Apple Command Line Tools 编译 Swift AppKit 界面 bundle，并与 AppleScript Droplet 一起完成本地签名。原生 bundle 只包含安装时的 CPU 架构；迁移到另一种架构的 Mac 时请在目标机器重新安装，不直接复制 App。

## 命令行工作目录

CLI 入口先执行 shell 内置的 cd，成功进入所选目录后才启动 Agent；不是仅给 Agent 指定一个目录参数。iTerm 在新窗口/标签页创建时直接指定登录 shell 的启动命令，初始化后再 cd，避免向默认会话模拟键入。目录切换失败时不会启动 Agent，清屏失败不影响启动。

Agent 退出后保留正常交互式 shell；该 shell 会读取用户初始化文件。如果用户在初始化文件中主动切换目录，退出后的提示符会遵循该设置。启动 Agent 前的目录切换始终在初始化之后执行。

附件为本地材料引用；桌面应用预填请求不等于原生附件注入或文件已读取。需要在目标应用发送提示后，由 Agent 核对实际可读性。单次最多100项，重放保留原动作与文件清单。
