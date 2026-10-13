-- AI Here：放在 Finder 工具栏（按住 ⌘ 拖进去）。
-- 点击：对“当前 Finder 窗口所在的文件夹”（或选中的文件夹）弹出菜单，选择用哪个工具打开。
-- 也可以把文件夹直接拖到图标上。

use AppleScript version "2.4"
use framework "Foundation"
use framework "AppKit"
use scripting additions

property launcher : "__LAUNCHER__"

property menuItems : {"Claude Code（终端）", "Codex（终端）", "Claude Code（桌面版）", "Codex（桌面版）", "WorkBuddy", "Claude Code 继续上次会话（终端）", "Codex 继续上次会话（终端）"}
property menuModes : {"claude-cli", "codex-cli", "claude-app", "codex-app", "workbuddy", "claude-continue", "codex-resume"}
property lastChoice : "Claude Code（终端）"
property menuIcons : missing value
property menuTable : missing value

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
	set choice to my chooseWithIcons(label)
	if choice is missing value then return
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

-- 使用原生 AppKit 列表：每一行都有图标，支持鼠标选择、方向键、回车及 Esc。
on chooseWithIcons(folderLabel)
	set iconNames to {"claude", "codex", "claude", "codex", "workbuddy", "claude", "codex"}
	set menuIcons to current application's NSMutableArray's array()
	repeat with iconName in iconNames
		menuIcons's addObject:(my toolIcon(iconName as text))
	end repeat

	set menuTable to current application's NSTableView's alloc()'s initWithFrame:{{0, 0}, {460, 308}}
	menuTable's setHeaderView:(missing value)
	menuTable's setRowHeight:44
	menuTable's setIntercellSpacing:{8, 0}
	menuTable's setAllowsMultipleSelection:false
	menuTable's setAllowsEmptySelection:false
	menuTable's setSelectionHighlightStyle:(current application's NSTableViewSelectionHighlightStyleRegular)
	menuTable's setAccessibilityLabel:"选择 AI 工具"

	set iconColumn to current application's NSTableColumn's alloc()'s initWithIdentifier:"icon"
	iconColumn's setWidth:40
	iconColumn's setEditable:false
	set iconCell to current application's NSImageCell's alloc()'s init()
	iconCell's setImageScaling:(current application's NSImageScaleProportionallyUpOrDown)
	iconColumn's setDataCell:iconCell
	menuTable's addTableColumn:iconColumn

	set titleColumn to current application's NSTableColumn's alloc()'s initWithIdentifier:"title"
	titleColumn's setWidth:400
	titleColumn's setEditable:false
	(titleColumn's dataCell())'s setFont:(current application's NSFont's systemFontOfSize:14)
	menuTable's addTableColumn:titleColumn
	menuTable's setDataSource:me
	menuTable's reloadData()
	set selectedIndex to 0
	repeat with i from 1 to count of menuItems
		if item i of menuItems is lastChoice then set selectedIndex to i - 1
	end repeat
	menuTable's selectRowIndexes:(current application's NSIndexSet's indexSetWithIndex:selectedIndex) byExtendingSelection:false

	set listView to current application's NSScrollView's alloc()'s initWithFrame:{{0, 0}, {460, 308}}
	listView's setDocumentView:menuTable
	listView's setHasVerticalScroller:false
	listView's setBorderType:(current application's NSBezelBorder)

	set chooser to current application's NSAlert's alloc()'s init()
	chooser's setMessageText:"在这里打开"
	chooser's setInformativeText:folderLabel
	chooser's setAccessoryView:listView
	set resourcesPath to current application's NSBundle's mainBundle()'s resourcePath() as text
	set appIcon to current application's NSImage's alloc()'s initWithContentsOfFile:(resourcesPath & "/AIHere.icns")
	if appIcon is not missing value then chooser's setIcon:appIcon
	chooser's addButtonWithTitle:"打开"
	chooser's addButtonWithTitle:"取消"
	(chooser's |window|())'s setTitle:"AI Here"
	(chooser's |window|())'s makeFirstResponder:menuTable
	current application's NSApplication's sharedApplication()'s activateIgnoringOtherApps:true
	set response to chooser's runModal()
	set selectedRow to menuTable's selectedRow() as integer
	set menuTable to missing value
	set menuIcons to missing value
	if response as integer is not 1000 or selectedRow < 0 then return missing value
	return item (selectedRow + 1) of menuItems
end chooseWithIcons

on toolIcon(iconName)
	set resourcesPath to current application's NSBundle's mainBundle()'s resourcePath() as text
	set iconImage to current application's NSImage's alloc()'s initWithContentsOfFile:(resourcesPath & "/ToolIcons/" & iconName & ".png")
	if iconImage is missing value then
		set symbolName to "terminal"
		if iconName is "workbuddy" then set symbolName to "person.crop.square"
		set iconImage to current application's NSImage's imageWithSystemSymbolName:symbolName accessibilityDescription:iconName
	end if
	return iconImage
end toolIcon

on numberOfRowsInTableView_(aTable)
	return count of menuItems
end numberOfRowsInTableView_

on tableView_objectValueForTableColumn_row_(aTable, aColumn, rowIndex)
	if (aColumn's identifier() as text) is "icon" then return menuIcons's objectAtIndex:rowIndex
	return item ((rowIndex as integer) + 1) of menuItems
end tableView_objectValueForTableColumn_row_
