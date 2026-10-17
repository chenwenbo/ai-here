# AI Here 1.7.0 附件栏设计验收

final result: passed

用户选择最近附件三稿第二张：左侧附件栏、右侧五个 Agent 双图标。实现原生桌面窗口，没有恢复网页预览。1.6历史报告保留于 docs/design/native-ui-1.6-design-qa.md。

## 对比证据

- Source visual truth: docs/design/attachment-rail-target.png，1402×1122 px；窗口裁切(56,69)-(1345,1052)，1289×983 px，等比例归一为800×610 px。
- Implementation screenshot: docs/design/attachment-rail-hover.png，1600×1256 px，Retina2×；实际窗口800×628 pt、内容800×600 pt，没有CSS viewport。
- State: 浅色、ai-here目录、三个同名示例文件、Claude桌面总结按钮悬停。实机路径为隔离目录，文件顺序沿用Finder选区，更换按钮有焦点环。
- Full-view comparison: docs/design/attachment-rail-comparison.png，源稿与实机同一输入归一并列，已实际打开检查。
- Focused comparison: docs/design/attachment-rail-files-comparison.png，同图检查附件标题、图标、文件名和移除。
- Other state: attachment-rail-changed-directory.png记录两附件仍指向原目录，cwd已更换；attachment-rail-actual.png为尺寸修正前初次三文件截图。

## 必检视觉面

| 面向 | 核验 |
| --- | --- |
| 字体 | 系统字体/中文回退；目录23 pt、Agent16 pt、附件标题18 pt、文件名14 pt、说明11–13 pt。层级明确，文件名/路径中间截断，tooltip及AX保留完整路径。 |
| 间距 | 左栏260 pt、右列表起点288 pt，所有五行十动作完整可见。附件可滚动；工具图标56 pt框，按钮48×42 pt；以细分隔线和留白分组。 |
| 颜色 | 暖白、深色文字、青绿主动作、浅灰次动作保持选定方向，原生焦点与悬停状态清楚。 |
| 图像 | 真实品牌PNG、NSWorkspace文件/目录图标、SF Symbols动作和移除；未伪造品牌或文件缩略图，无明显拉伸、模糊或截切。 |
| 文案 | 十动作保持图标/悬停名称；附件显示待带入，底部解释本地清单，没有已上传/已读取假状态。桌面准备通知要求用户发送。 |

## 迭代历史

[P2，已解决] 初次附件栏230 pt比源稿约260 pt窄，图标/按钮偏小，文件首行偏低。见attachment-rail-comparison-before-sizing.png。
调整栏宽、文件宽度/字号、右侧起点、品牌图标/按钮尺寸，并将文件首行相对上移18 pt。再次安装并捕捉同悬停状态；最终全图与附件局部比较确认比例问题已解决。

最终没有待修P0/P1/P2。P3/预期差异：原生紧凑标题栏/屏幕控制标志、应用关联决定的文件图标、Finder文件顺序、真实路径、原生提示材质及位置。附件说明改为待带入及本地清单，准确反映各Agent的传递能力；底部多一行说明，不遮挡持久操作。

## 交互及范围

68项测试通过，最终尺寸调整后Droplet双selector加载另行通过。真实Finder三文件多选进入左栏；移除、更换目录和直接动作保留正确剩余文件及剪贴板；总结请求含三文件和技能路径，发送前未初始化项目。只读Codex实际读取两文件校验内容并识别初始图片颜色，文件哈希未变。只读代码复查无阻塞。

桌面应用仍是目录打开加提示复制/预填，需要用户发送，通用原生附件注入未实现。Codex CLI常规PNG/JPEG/WebP走图片参数；逗号路径及其他材料为本地引用。完整证据、剪贴板被后一次启动覆盖的观察和未覆盖项见docs/e2e-attachments-2026-10-14.md。

检查清单：源图映射、真实资源、比例修复、同图复核、移除/目录保留、两动作路由、实际文件读取、编译签名及限制说明均完成。未测试其他OS、架构或深色主题。
