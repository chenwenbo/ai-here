# 跨 Agent 工作交接指南

AI Here 1.3.0 将工作交接保存在同一工作目录，供 Codex、Claude Code、WorkBuddy 和 ChatGPT 接续。当前 Agent 或用户写入记录，下一位 Agent 阅读并核验；完整聊天历史仍由各产品管理。

## 一次启用

在 Finder 工具栏的 AI Here 选择器中选 **启用 / 修复工作交接**，或运行：

```bash
ai-here handoff init ~/项目 --instructions
```

命令创建 `.ai-here/index.md`、`handoffs/` 和 `templates/handoff.md`。`--instructions` 给 `AGENTS.md` 与 `CLAUDE.md` 附加带标记的简短指令，引导 Agent 阅读交接并在结束前记录进展。现有内容保留，重复执行不会重复添加入口。只想创建交接文件时，省略该参数。

交接功能使用 Python 3.9+ 标准库；`ai-here doctor` 的 `handoff_runtime` 显示本机 Python 位置。

```text
项目/
  AGENTS.md               # Codex 项目指令中的交接入口（可选）
  CLAUDE.md               # Claude Code 的交接入口（可选）
  .ai-here/
    index.md              # 手工当前状态 + 自动维护的最近 20 条交接链接
    handoffs/             # 每个任务或每次交接一个 Markdown 文件
    templates/handoff.md  # 目标、产物、决策、验证、下一步与过期假设
    .gitignore            # 忽略锁和临时文件
```

## 当前 Agent 结束前写入

已安装项目指令的 Agent 会收到写交接的要求。用户也可运行 `ai-here handoff add .`，按提示输入标题、来源工具和正文，完成正文后按 Ctrl-D。

Agent 或脚本可提供正文文件，或从标准输入传入：

```bash
ai-here handoff add . --title "Agent 选择器支持双击" --agent Codex \
  --status completed --body-file - <<'EOF'
## 任务目标
选择 Agent 时可以双击确认。

## 已完成的操作与产物
修改 src/AIHere.applescript，双击触发确认按钮。

## 关键决策及理由
复用原有确认流程。

## 验证结果与证据
AppleScript 编译通过；附对应提交号与实测结果。

## 未完成工作、阻塞与下一步
列出尚未验证的客户端行为及接续任务。

## 可能过期的假设
明确哪些信息需要后续 Agent 再核查。
EOF
```

`--status` 可选 `active`（默认，仍有工作）、`completed`（该任务完成）或 `blocked`（阻塞）；`--session` 可记录会话 URL。一条任务完成不表示整个项目完成。每次写入生成唯一文件，包含来源工具、时间、任务状态和正文，命令输出记录路径。

需要跟踪项目当前目标、进展、决策时，更新 `index.md` 的手工区。自动命令只更新 `ai-here:recent` 标记之间的清单。文件路径、提交号和实际检查结果是交接证据；推测与未验证项须明确标注。

## 下一个 Agent 怎样接续

| 工具 | 读取入口 | 使用边界 |
|---|---|---|
| Codex CLI / App | `AGENTS.md` 指向索引；CLI 同时显示阅读提醒 | 阅读后核对文件与 Git 状态；`resume` 仍续接 Codex 自己的会话 |
| Claude Code CLI / App | `CLAUDE.md` 指向同一索引；CLI 显示提醒 | 使用 Claude Code 项目说明能力；`--continue` 仍续接 Claude 自己的会话 |
| WorkBuddy | 预填提示词追加索引路径和结束前写交接的要求 | 用户发送后由 Agent 阅读；启动 URL 只带路径，不含交接正文 |
| ChatGPT 普通对话 | 点 **复制交接摘要 · 用于 ChatGPT 等**，粘贴到对话 | 无本地权限时，接续结果需复制到本地后写入交接 |
| ChatGPT 桌面 Work | 在授权目录中读取同一文件，或粘贴摘要 | 取决于本地目录权限；AI Here 没有自动创建 ChatGPT Work 会话 |

从普通 ChatGPT 带回结果时，将其交接正文保存为本地 Markdown 后运行：

```bash
ai-here handoff add ~/项目 --title "需求分析结果" --agent ChatGPT \
  --status active --body-file ~/Downloads/chatgpt-handoff.md
```

`HANDOFF_HINTS=0` 可关闭终端提醒及 WorkBuddy 追加提示，项目说明中的交接入口仍保留。未启用的目录不会因启动工具自动生成记录。读取提示失败会报告问题，工具仍可打开。

## 查看、复制与维护

```bash
ai-here handoff list .                     # 从现存记录扫描清单
ai-here handoff show . latest              # 查看最新一条
ai-here handoff show . <记录ID>             # 查看指定记录
ai-here handoff open .                     # 用默认应用打开索引
ai-here handoff copy .                     # 复制摘要到剪贴板
ai-here handoff export . --limit 3 --max-chars 8000  # 输出摘要
ai-here handoff prompt .                   # 输出简短读取/写入提示
ai-here handoff init .                     # 刷新最近清单，保留手工状态
```

摘要默认包含索引和最近 5 条正文，上限 12,000 字符；达到上限会明确提示截断，来源路径与时间随记录提供。选择器多选工作空间时，“复制交接摘要”会合并各目录摘要。

可编辑 Markdown 正文、状态或删除记录，再运行 `init` 刷新清单。首行 JSON 注释保存 ID、标题、工具和创建时间，请保留合法格式；损坏记录会警告并跳过，原文件不会被删除。更推荐追加更正记录以便追溯。

写命令使用跨进程锁，交接文件独立保存，索引原子替换并检查外部修改。若与编辑器冲突，已经写入的记录会保留，可核对后运行 `init` 刷新。管理区标记不完整时不会覆盖用户内容；符号链接写入目标会被拒绝。

## 私密项目与卸载

```bash
ai-here handoff init ~/私密项目 --instructions --ignore
```

`--ignore` 在所在 Git 仓库的 `.gitignore` 追加该工作空间的 `.ai-here/` 路径，保留原内容。已经被 Git 跟踪的文件不会自动取消跟踪。记录避免包含密钥、个人隐私与完整聊天；复制后发送给另一个产品的内容由你决定。

卸载 AI Here 保留各工作空间的记录与项目说明；不再需要时，可删除 `.ai-here/` 和 `AGENTS.md`、`CLAUDE.md` 内 `ai-here:instructions` 标记包围的入口。

## 后续扩展与验证边界

本版实现文件交接与启动入口。多个客户端需要实时查询、更新同一份状态时，可在该存储之上加 MCP 资源与工具接口。真实客户端是否读取、是否写回取决于其版本、权限与 Agent 执行情况，文件管理与启动提示不构成这些行为的保证。

## 参考资料

- [OpenAI：Codex 项目指令](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [Claude Code：项目记忆与 CLAUDE.md](https://code.claude.com/docs/en/memory)
- [OpenAI：ChatGPT Work 本地文件访问](https://help.openai.com/en/articles/20001275/)
- [WorkBuddy：内置记忆](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Memory)
