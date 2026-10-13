# 跨 Agent 工作交接方案（调研稿）

## 现状与目标

AI Here 目前负责把同一目录交给 Claude Code、Codex 或 WorkBuddy。`claude --continue` 和 `codex resume --last` 只能续接各自产品的会话；WorkBuddy 的启动提示词只是预填。目录相同并不会让不同产品自动理解彼此做过什么。当前也没有独立的 ChatGPT 启动入口。

目标是让后续 Agent 能快速获知同一工作空间中**已经确认的进展**，同时能追溯来源、发现过期信息，并避免把完整聊天记录或敏感内容无差别注入每次会话。

## 建议：工作空间文件为准，产品记忆为辅

在被打开的工作目录里维护 `.ai-here/`：

```text
.ai-here/
  index.md              # 当前项目状态；短，供每次进入时阅读
  handoffs/             # 一次任务或一次交接一个文件，按时间与任务命名
    2026-10-13-agent-picker.md
```

`index.md` 只放当前目标、最近完成、未完成、关键决策及相关交接文件链接。每份交接文件记录：任务目标、来源工具和会话链接（若可用）、更新时间、已经完成的操作与产物、关键决策及理由、验证结果、未完成工作与阻塞、可能过期的假设。文件中的事实附本地文件路径、提交号或其他证据；尚未核实的内容明确标注。不要存放密钥、个人隐私或整段原始聊天。

## 各工具如何接入

| 工具 | 第一阶段的读取方式 | 限制 |
|---|---|---|
| Codex CLI / App | 在工作目录的 `AGENTS.md` 放一条简短导航：处理延续性任务时先看 `.ai-here/index.md`，按需打开对应交接文件 | `AGENTS.md` 只做入口，不复制动态状态；仍须核对当前文件和 Git 状态 |
| Claude Code | 用其项目说明文件或启动提示词指向同一个索引 | 需用当前版本实际验证项目说明文件的发现规则 |
| WorkBuddy | 利用现有工作目录深链，在预填提示词中提醒读取索引；若产品支持工作区指令，再配置为常驻导航 | AI Here 当前不会替用户发送提示词，不能承诺自动注入 |
| ChatGPT | 有本地文件访问的桌面 Work 会话可打开该目录并读取索引；普通 Chat 对话需显式上传或粘贴交接摘要 | 普通 Chat 没有可假定的本地目录访问；ChatGPT Project 记忆只在其产品边界内生效 |

上述适配都只指向同一份工作空间记录，不从各产品的私有会话数据库抓取历史。要交接的是**可验证的结果和下一步**，不是假设另一个产品的“记忆”能跨平台同步。

## 建议的落地顺序

1. 在 AI Here CLI 增加 `ai-here handoff init <目录>`，只创建 `.ai-here/index.md`、模板和可选的项目说明入口；已经存在的用户文件绝不覆盖。
2. 增加 `ai-here handoff add <目录>`，以交互式模板创建单次交接，并更新索引；支持手工修正和删除。先让用户显式触发写入，避免关闭窗口时猜测任务是否真正结束。
3. 选择器若发现索引，显示“有最近交接”并提供“打开交接记录”；启动提示词可带索引路径，但不自动发送，也不把交接内容塞入 URL。
4. 运行一轮真实跨工具验收：Codex → WorkBuddy → ChatGPT Work，检查每种工具是否读到最新记录、是否能识别未验证陈述、是否避免把旧状态当新事实。
5. 当文件方案已证明有用、且多个客户端都能可靠连接时，再考虑以 MCP 的资源/工具接口暴露索引与交接。MCP 是访问层，不应替代可读、可版本管理的工作空间文件。

并行写入时，每次交接使用独立文件，索引更新需检查修改时间或文件哈希并在冲突时要求人工合并。Git 项目可将交接文件纳入版本控制；涉及私密项目时提供忽略 `.ai-here/` 的选项。交接摘要应短且可回查，定期清理过期项。

## 参考资料

- [OpenAI：Codex 中的 AGENTS.md](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [OpenAI：ChatGPT Projects 的记忆边界](https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt)
- [OpenAI：ChatGPT Work 本地文件访问](https://help.openai.com/en/articles/20001275/)
- [WorkBuddy：记忆功能](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Memory)
- [Model Context Protocol：资源、提示词与工具](https://modelcontextprotocol.io/specification/draft/server/index)
