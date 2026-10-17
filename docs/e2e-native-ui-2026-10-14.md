# AI Here 1.6.0 原生图标界面验收

日期：2026-10-14。本机已安装 1.6.0。用户选择 Product Design 第二版并指定按钮只用图标、悬停显示文字；网页预览不再交付。

## 实现

Swift AppKit 工具窗口按命令行/桌面应用分组，保留目录与更换按钮；五行各包含箭头（直接开始）与文档放大镜（总结并接续）。采用真实工具图标、系统目录图标及 SF Symbols。即时提示不拦截指针；同一窗口最多一个提示，底部会移到按钮上方。

AppleScript Droplet 继续取得 Finder 上下文并执行原有启动逻辑。Swift bundle 只返回 mode/action/cwd/cancelled；没有另建启动后端或浏览器。构建在临时 App 中完成，编译签名成功后替换安装目录，避免构建失败先删除旧 App。

网页预览目录、服务器脚本和当前文档入口已经移除，服务已停止。删除前备份在 `/private/tmp/ai-here-preview-removed-zwbio7zj/preview-backup.tar.gz`；历史验收保留并标明已撤除。

## 自动化与安装检查

- 53 项测试通过，完整运行 14.268 秒。原生 ABI 测试实际编译并签名 Droplet、加载 bundle、实例化 ObjC 主类并检查 runWithDirectory: selector；单一提示 owner 完成后该测试另行通过（4.885 秒）。
- 最终资产尺度调整后安装编译成功；codesign、zsh 语法、Git diff 空白检查通过，CLI/doctor 版本为 1.6.0。
- 原生 bundle 编译本机 CPU 架构，移至另一种架构的机器须在目标机器重新安装。没有生成通用二进制发行包。

## Computer Use 真实窗口检查

Finder 工具栏按钮打开当前 ai-here 目录，窗口完整显示两组五行十个动作。文字名称只在悬停/键盘聚焦时出现；无障碍名称始终包含 Agent 与动作。

完整 Tab 循环覆盖更换及十个动作；Shift+Tab 反向移动，Space 在更换按钮上打开系统目录选择。Return 不默认启动；Escape 结束面板。提示出现没有改动焦点，连续切换提示不重叠，底部不越界。

在 `/private/tmp/AIHere-Window-QA/ai-here` 隔离目录实测 Claude 桌面的两个图标：

- 箭头：启动后私有 launches 无新增记录，剪贴板摘要不变，项目没有初始化 `.ai-here`。
- 文档放大镜：显示“总结提示已准备”，新增请求 tool=claude-app、mode=summarize、cwd 正确；剪贴板字节与快照 prompt.md 一致，提示引用安装目录内的 ai-here-handoff 技能。未发送提示前项目仍没有 `.ai-here`。

核验证据留于本机 `/private/tmp/ai-here-ui-direct-proof.json`、`ai-here-ui-summary-proof.json`；仅记录模式、目录及布尔结果，没有复制剪贴板正文。没有向 Claude 或其他 Agent 发送本次测试提示。

## 视觉证据与边界

选定稿、最终实机截图、同图归一对比见 `design/`；项目根 `design-qa.md` 结果 passed，记录了提示、键盘与图标尺度迭代。

本轮主要改 UI，不重新宣称完整跨客户端闭环。CLI 路由由既有受控测试覆盖；桌面总结仍需用户粘贴并发送，WorkBuddy 仍需用户发送预填提示。之前技能实际生成交接的证据在 `e2e-simple-launch-2026-10-13.md`。其他 Agent 未落盘聊天、WorkBuddy 会话超时及先前未完成的完整接续验证仍保留原边界。
