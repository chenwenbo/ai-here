#!/bin/zsh
# 卸载 AI Here（保留 ~/.config/ai-here/config，如需一并删除请加 --purge）
for t in "Claude Code（终端）" "Codex（终端）" "Claude Code（桌面版）" "Codex（桌面版）"; do
  rm -rf "$HOME/Library/Services/$t.workflow" && echo "已移除快速操作：$t"
done
rm -rf "$HOME/Applications/AI Here.app" && echo "已移除 AI Here.app"
link="$HOME/.local/bin/ai-here"
[[ -L $link ]] && rm -f "$link" && echo "已移除命令 ai-here"
rm -rf "$HOME/Library/Application Support/AIHere"
[[ ${1:-} == --purge ]] && rm -rf "$HOME/.config/ai-here" && echo "已删除配置"
/System/Library/CoreServices/pbs -flush >/dev/null 2>&1
echo "卸载完成。（若 Finder 工具栏里还有按钮，按住 ⌘ 把它拖出即可）"
