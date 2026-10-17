# AI Here 1.7.0 附件栏与文件传递验收

用户选择附件三稿第二张，精确映射exec-1826af7f-6244-49f3-8b62-d30527e7f2c6.png。左侧附件可滚动/移除，右侧Agent双图标，更换目录保留材料，移除不删除源文件。

## 实现与能力

Finder选区→runWithDirectory:references:→移除后的references→task start --action direct|summary→私有请求/提示快照→CLI参数或桌面复制/预填。

稳定Finder当前目录优先，文件父目录仅在缺少目录上下文时回退。无附件direct保留旧启动、不写快照；有附件保存reference-start，要求实际读取后等待任务。summary保存summarize，带同一清单并使用内置技能核验追加交接。失败和重放保留动作/目录/文件，启动前重查存在性。

Codex CLI对检测为PNG/JPEG/WebP的常规文件追加独立-i参数；其他文件和逗号路径为本地引用，不伪装为图片或已上传。没有增加--add-dir写权限。本机Codex0.162.0-alpha.17.2与[官方图片参数说明](https://learn.chatgpt.com/docs/developer-commands?surface=cli)一致。Claude的--file用于远端file_id资源下载，没有套用于本地路径。

Claude/Codex桌面仍打开目录并复制提示，WorkBuddy预填提示包路径。通用桌面原生附件注入未实现，没有已核实接口；打开/复制不等于上传、读取或总结完成。

## 自动化和实际检查

- 68项测试通过（16.354秒）；独立27项task、20项launcher、6项AppleScript helpers复核通过，无P0/P1/P2代码阻塞。最终尺寸调整后Droplet加载测试另行通过（4.885秒）。
- 覆盖完整路径、去重、缺失文件不启动、目录外只读语义、两动作重放、零附件兼容、安全quote、CLI实际cwd、图片argv与逗号回退。
- 真实Finder选择需求说明.md、流程图.png、接口示例.json，全部进入左栏，cwd为Finder当前目录。
- 移除JSON再更换other-project，Claude桌面direct请求mode=reference-start/cwd正确，refs仅剩原目录两文件；剪贴板与prompt.md逐字节一致、移除项不在提示、两个测试目录未初始化交接。
- Claude桌面summary请求mode=summarize/cwd=ai-here，含三文件与安装技能路径，显示准确准备通知，未发送前无初始化。检查剪贴板时它已被稍后另一Codex桌面direct启动替换，匹配后一次三文件快照。因此不声称summary即时字节比对实测通过；复制机制由direct实测和受控测试覆盖。
- 独立只读codex exec接收两本地文档和原生--image，实际返回ALPHA-732、BETA-961、附图红色及正确cwd；前后文件哈希相同。只发送虚构测试材料，没有发送用户项目内容、修改文件或执行总结技能。

本机证据：/private/tmp/ai-here-attachment-ui-direct-proof.json、ai-here-attachment-ui-summary-proof.json、ai-here-attachment-codex-read.json；模型事件留私有临时文件。测试目录/private/tmp/AIHere-Attachments-QA/。

## 视觉及未覆盖项

design-qa.md passed，源图、实机与归一同图比较见docs/design/attachment-rail-*。1.7.0已安装，最终签名/语法/源码安装一致性通过，1.6.1初始化后先cd修复保持。

没有恢复网页、改个人Skills路由或提交Git。本次真实读取覆盖Codex CLI；其他客户端全部材料读取、桌面原生附件注入和完整跨客户端交接闭环未证明。先前WorkBuddy会话超时保持原边界。
