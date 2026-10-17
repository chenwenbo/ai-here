# AI Here 1.7.1 桌面自动预填验收（2026-10-14）

## 本轮结果

带材料的直接开始、总结并接续不再通过剪贴板中转。Codex 使用 `codex://new?path=…&prompt=…`，Claude Code 使用 `claude://code/new?folder=…&q=…`，WorkBuddy 使用 `workbuddy://task?action=start&cwd=…&prompt=…` 的短快照指令。Codex/Claude 编码后全文链接超过8KiB时改用读取原 `prompt.md` 的短指令，不截断任务。用户仍需确认并发送；没有模拟粘贴、自动发送或原生文件附件注入。

原生面板选择后的成功弹窗和通知已移除，错误仍保留原目录与材料并允许返回。无材料的直接开始保留原普通入口；主动 `handoff copy` 命令仍可用。

接口依据：[Codex 官方 commands](https://learn.chatgpt.com/docs/reference/commands)、[Claude 官方 Code 深链](https://support.claude.com/en/articles/14729294-open-claude-desktop-with-a-link)。WorkBuddy 来源为本机5.3.12客户端深链解析及预填协调代码，只证明支持的参数与预填行为。

## 验证

- `python3 -m unittest discover -s tests -v`：75项全部通过，20.854秒。包含两动作文件清单、中文和特殊字符、百分号编码后的字节限额、长提示保留原文、无剪贴板写入、失败快照保留、CLI实际cwd、原生bundle ABI加载。
- 独立审查员只读复核上述桌面实现与官方参数，并独立运行25项launcher、29项task测试：54项全部通过，无阻塞问题。
- zsh语法通过；`./install.sh`成功编译并安装1.7.1；`codesign --verify --deep --strict`通过，已安装launcher和task helper与源码逐字一致。
- 真实Finder在 `/private/tmp/AIHere-Attachments-QA/ai-here` 选择三个无隐私测试文件，通过工具栏进入原生附件栏并点击Claude桌面直接开始。新快照为reference-start、claude-app、目标目录及三条材料路径准确，request权限0600、提示1260字节。没有成功弹窗阻断切换；Claude显示需要Pro/Max才能使用桌面Code，账户为Free，故不能确认实际composer预填。本轮没有发送给Agent，没有初始化测试目录交接。

## 证明范围与限制

open成功只证明已发出请求。Claude真实验证受到客户端套餐限制；Codex桌面和iTerm沿用此前Computer Use操作限制，本轮未绕过。Codex与WorkBuddy本轮使用受控open测试，未宣称三客户端实际输入框闭环通过。CLI既有自动参数与图片入口仍通过回归，未重复真实模型调用。

普通文件是明确的本地引用，发送后由Agent核验能否读取；长提示依赖目标Agent可访问私有快照。桌面原生附件chip/文件上传未实现。网页预览保持移除。此前1.7.0报告保留历史，不把旧复制流程当作当前行为。
