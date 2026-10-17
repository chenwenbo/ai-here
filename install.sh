#!/bin/zsh
# 安装 AI Here（Claude Code / Codex / WorkBuddy）：Finder 右键服务菜单 + 工具栏按钮 + ai-here 命令
setopt err_exit no_unset

SRC=${0:A:h}
for arg in "$@"; do
  case $arg in
    -h|--help) print "用法: ./install.sh"; exit 0 ;;
    *) print -u2 -- "不支持的参数：$arg。用法: ./install.sh"; exit 2 ;;
  esac
done
INSTALL_DIR="$HOME/Library/Application Support/AIHere"
SERVICES_DIR="$HOME/Library/Services"
APP_PATH="$HOME/Applications/AI Here.app"
CONFIG="$HOME/.config/ai-here/config"
LAUNCHER="$INSTALL_DIR/ai-here"

# 标题 => 模式（标题即右键菜单里显示的名字）
typeset -a ACTIONS=(
  "AI Here · 带上下文启动" compose
  "Claude Code CLI"   claude-cli
  "Codex CLI"         codex-cli
  "Claude Code App" claude-app
  "Codex App"       codex-app
)
# WorkBuddy 只在已安装时加入右键菜单
if [[ -d /Applications/WorkBuddy.app ]] || mdfind "kMDItemCFBundleIdentifier == 'com.tencent.workbuddy.mac'" 2>/dev/null | grep -q '\.app$'; then
  ACTIONS+=("WorkBuddy" workbuddy)
else
  rm -rf "$HOME/Library/Services/WorkBuddy.workflow"
fi

FINDER_PATH=/System/Library/CoreServices/Finder.app
FINDER_ID=com.apple.finder

xml_escape() { local s=$1; s=${s//&/&amp;}; s=${s//</&lt;}; s=${s//>/&gt;}; print -r -- "$s" }

echo "==> 安装启动脚本到 $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp "$SRC/bin/ai-here" "$LAUNCHER"
chmod +x "$LAUNCHER"
mkdir -p "$INSTALL_DIR/lib"
cp "$SRC/lib/handoff.py" "$INSTALL_DIR/lib/handoff.py"
cp "$SRC/lib/task_request.py" "$INSTALL_DIR/lib/task_request.py"
mkdir -p "$INSTALL_DIR/skills/ai-here-handoff"
cp "$SRC/skills/ai-here-handoff/SKILL.md" "$INSTALL_DIR/skills/ai-here-handoff/SKILL.md"

mkdir -p "$HOME/.local/bin"
if [[ -d "$HOME/.local/bin" ]]; then
  link="$HOME/.local/bin/ai-here"
  if [[ ! -e $link || -L $link ]]; then
    ln -sf "$LAUNCHER" "$link"
    echo "    命令行可用：ai-here claude-cli ."
  fi
fi

if [[ ! -f $CONFIG ]]; then
  mkdir -p "${CONFIG:h}"
  cp "$SRC/config.example" "$CONFIG"
  echo "    已生成配置文件 $CONFIG"
fi

echo "==> 生成 Finder 右键服务到 $SERVICES_DIR"
mkdir -p "$SERVICES_DIR"
# 生成一个 Automator「快速操作」：仅在 Finder 中、对选中的文件夹可用，
# 内容是一个「运行 Shell 脚本」动作，以参数形式接收所选文件夹。
write_workflow() {
  local title=$1 mode=$2 dir=$3 input_type=com.apple.Automator.fileSystemObject.folder send_type=public.folder
  # 统一面板入口接收文件和文件夹；原工具服务保留文件夹快捷启动语义。
  if [[ $mode == compose ]]; then
    input_type=com.apple.Automator.fileSystemObject
    send_type=public.item
  fi
  local script; script=$(xml_escape "\"\$HOME/Library/Application Support/AIHere/ai-here\" $mode \"\$@\"")
  local name; name=$(xml_escape "$title")
  mkdir -p "$dir/Contents"

  cat >"$dir/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>NSServices</key>
	<array>
		<dict>
			<key>NSMenuItem</key>
			<dict>
				<key>default</key>
				<string>$name</string>
			</dict>
			<key>NSMessage</key>
			<string>runWorkflowAsService</string>
			<key>NSRequiredContext</key>
			<dict>
				<key>NSApplicationIdentifier</key>
				<string>$FINDER_ID</string>
			</dict>
			<key>NSSendFileTypes</key>
			<array>
				<string>$send_type</string>
			</array>
		</dict>
	</array>
</dict>
</plist>
EOF

  cat >"$dir/Contents/document.wflow" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AMApplicationBuild</key>
	<string>534</string>
	<key>AMApplicationVersion</key>
	<string>2.10</string>
	<key>AMDocumentVersion</key>
	<string>2</string>
	<key>actions</key>
	<array>
		<dict>
			<key>action</key>
			<dict>
				<key>AMAccepts</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Optional</key>
					<true/>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>AMActionVersion</key>
				<string>2.0.3</string>
				<key>AMApplication</key>
				<array>
					<string>Automator</string>
				</array>
				<key>AMProvides</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>ActionBundlePath</key>
				<string>/System/Library/Automator/Run Shell Script.action</string>
				<key>ActionName</key>
				<string>Run Shell Script</string>
				<key>ActionParameters</key>
				<dict>
					<key>COMMAND_STRING</key>
					<string>$script</string>
					<key>CheckedForUserDefaultShell</key>
					<true/>
					<key>inputMethod</key>
					<integer>1</integer>
					<key>shell</key>
					<string>/bin/zsh</string>
					<key>source</key>
					<string></string>
				</dict>
				<key>BundleIdentifier</key>
				<string>com.apple.RunShellScript</string>
				<key>CFBundleVersion</key>
				<string>2.0.3</string>
				<key>CanShowSelectedItemsWhenRun</key>
				<false/>
				<key>CanShowWhenRun</key>
				<true/>
				<key>Category</key>
				<array>
					<string>AMCategoryUtilities</string>
				</array>
				<key>Class Name</key>
				<string>RunShellScriptAction</string>
				<key>InputUUID</key>
				<string>$(uuidgen)</string>
				<key>OutputUUID</key>
				<string>$(uuidgen)</string>
				<key>UUID</key>
				<string>$(uuidgen)</string>
				<key>UnlocalizedApplications</key>
				<array>
					<string>Automator</string>
				</array>
				<key>isViewVisible</key>
				<integer>1</integer>
			</dict>
			<key>isViewVisible</key>
			<integer>1</integer>
		</dict>
	</array>
	<key>connectors</key>
	<dict/>
	<key>workflowMetaData</key>
	<dict>
		<key>applicationBundleID</key>
		<string>$FINDER_ID</string>
		<key>applicationPath</key>
		<string>$FINDER_PATH</string>
		<key>inputTypeIdentifier</key>
		<string>$input_type</string>
		<key>outputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>presentationMode</key>
		<integer>15</integer>
		<key>processesInput</key>
		<false/>
		<key>serviceApplicationBundleID</key>
		<string>$FINDER_ID</string>
		<key>serviceApplicationPath</key>
		<string>$FINDER_PATH</string>
		<key>serviceInputTypeIdentifier</key>
		<string>$input_type</string>
		<key>serviceOutputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>serviceProcessesInput</key>
		<false/>
		<key>systemImageName</key>
		<string>NSActionTemplate</string>
		<key>useAutomaticInputType</key>
		<false/>
		<key>workflowTypeIdentifier</key>
		<string>com.apple.Automator.servicesMenu</string>
	</dict>
</dict>
</plist>
EOF
  plutil -lint -s "$dir/Contents/Info.plist" "$dir/Contents/document.wflow"
}

for title mode in "${ACTIONS[@]}"; do
  wf="$SERVICES_DIR/$title.workflow"
  rm -rf "$wf"
  write_workflow "$title" "$mode" "$wf"
  echo "    ✓ $title"
done

# 清理旧版名称，避免更新后出现重复的 Finder 服务。
for old_title in "Claude Code（终端）" "Codex（终端）" "Claude Code（桌面版）" "Codex（桌面版）"; do
  rm -rf "$SERVICES_DIR/$old_title.workflow"
done

echo "==> 编译 Finder 工具栏按钮 $APP_PATH"
mkdir -p "${APP_PATH:h}"
command -v swiftc >/dev/null || { print -ru2 -- "构建原生界面需要 Apple Command Line Tools（swiftc）。"; exit 1 }
# Build and sign first so a compiler failure leaves the installed app intact.
native_stage=$(mktemp -d "${APP_PATH:h}/.ai-here-build.XXXXXXXX")
tmp_script="$native_stage/AIHere.applescript"
build_app="$native_stage/AI Here.app"
trap 'rm -rf "$native_stage"' EXIT
sed "s|__LAUNCHER__|$LAUNCHER|" "$SRC/src/AIHere.applescript" >"$tmp_script"
osacompile -o "$build_app" "$tmp_script"
rm -f "$tmp_script"
# Droplet 的默认图标名是 droplet，不是 applet；显式设置避免图标不生效。
cp "$SRC/src/AIHere.icns" "$build_app/Contents/Resources/AIHere.icns"
plutil -replace CFBundleIconFile -string AIHere "$build_app/Contents/Info.plist"
plutil -replace CFBundleIdentifier -string io.github.chenwenbo.ai-here "$build_app/Contents/Info.plist"
plutil -replace CFBundleShortVersionString -string 1.7.1 "$build_app/Contents/Info.plist"
plutil -replace CFBundleVersion -string 1.7.1 "$build_app/Contents/Info.plist"
osascript -l JavaScript "$SRC/src/export-tool-icons.js" "$build_app/Contents/Resources/ToolIcons"
native_bundle="$build_app/Contents/Resources/NativeUI.bundle"
mkdir -p "$native_bundle/Contents/MacOS"
cat > "$native_bundle/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>AIHereUI</string>
<key>CFBundleIdentifier</key><string>io.github.chenwenbo.ai-here.native-ui</string>
<key>CFBundlePackageType</key><string>BNDL</string>
<key>CFBundleVersion</key><string>1.7.1</string>
<key>NSPrincipalClass</key><string>AIHerePanelController</string>
</dict></plist>
EOF
swiftc -emit-library -module-name AIHereUI -target "$(uname -m)-apple-macosx13.0" \
  "$SRC/src/AIHereUI.swift" -o "$native_bundle/Contents/MacOS/AIHereUI"
codesign --force --sign - "$native_bundle" >/dev/null
# 图标及 Info.plist 改动发生在编译之后，更新本地临时签名。
codesign --force --sign - "$build_app" >/dev/null
codesign --verify --strict "$build_app"
if [[ -d "$APP_PATH" ]]; then mv "$APP_PATH" "$native_stage/previous.app"; fi
if ! mv "$build_app" "$APP_PATH"; then
  [[ -d "$native_stage/previous.app" ]] && mv "$native_stage/previous.app" "$APP_PATH"
  exit 1
fi
touch "$APP_PATH"

echo "==> 刷新系统服务菜单"
/System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true

cat <<EOF

安装完成 🎉
  • 右键任意文件夹 → 服务 → Claude Code CLI / Codex CLI / Claude Code App / Codex App / WorkBuddy
  • 检查安装状态：ai-here doctor
  • 选中文件 / 文件夹 → 服务 → AI Here · 带上下文启动，选 Agent 直接开始或总结并接续
  • 已在某个文件夹里？按住 ⌘ 把 ~/Applications/AI Here.app 拖到 Finder 工具栏，点一下即可
  • 配置（终端选择、命令参数）：$CONFIG
  • 总结并接续：Agent 使用内置 handoff 技能核验项目并保存交接；桌面工具自动预填提示，确认后发送
  • 首次使用时 macOS 会询问是否允许控制 iTerm/终端，请点“允许”
  • 若右键菜单暂未出现：系统设置 → 隐私与安全性 → 扩展 → Finder（访达）中勾选，或执行 killall Finder
EOF
