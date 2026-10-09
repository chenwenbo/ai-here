-- AI Here：放在 Finder 工具栏（按住 ⌘ 拖进去）。
-- 点击：对“当前 Finder 窗口所在的文件夹”（或选中的文件夹）弹出菜单，选择用哪个工具打开。
-- 也可以把文件夹直接拖到图标上。

property launcher : "__LAUNCHER__"

property menuItems : {"Claude Code（终端）", "Codex（终端）", "Claude Code（桌面版）", "Codex（桌面版）", "Claude Code 继续上次会话（终端）", "Codex 继续上次会话（终端）"}
property menuModes : {"claude-cli", "codex-cli", "claude-app", "codex-app", "claude-continue", "codex-resume"}
property lastChoice : "Claude Code（终端）"

on run
	set targetPaths to my currentFinderFolders()
	my chooseAndLaunch(targetPaths)
end run

on open droppedItems
	set targetPaths to {}
	repeat with f in droppedItems
		set end of targetPaths to POSIX path of f
	end repeat
	my chooseAndLaunch(targetPaths)
end open

on currentFinderFolders()
	tell application "Finder"
		set sel to selection as alias list
		set picked to {}
		repeat with s in sel
			if (class of item s) is folder then set end of picked to POSIX path of s
		end repeat
		if (count of picked) > 0 then return picked
		try
			return {POSIX path of ((target of front Finder window) as alias)}
		on error
			return {POSIX path of (path to desktop folder)}
		end try
	end tell
end currentFinderFolders

on chooseAndLaunch(targetPaths)
	if (count of targetPaths) = 0 then return
	set label to item 1 of targetPaths
	if (count of targetPaths) > 1 then set label to label & " 等 " & (count of targetPaths) & " 个文件夹"
	activate
	set picked to choose from list menuItems with title "AI Here" with prompt ("在这里打开：" & return & label) default items {lastChoice} OK button name "打开" cancel button name "取消"
	if picked is false then return
	set choice to item 1 of picked
	set lastChoice to choice
	set mode to ""
	repeat with i from 1 to count of menuItems
		if item i of menuItems is choice then set mode to item i of menuModes
	end repeat
	set cmd to quoted form of launcher & " " & mode
	repeat with p in targetPaths
		set cmd to cmd & " " & quoted form of (p as text)
	end repeat
	do shell script cmd & " >/dev/null 2>&1"
end chooseAndLaunch
