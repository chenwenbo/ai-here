-- AI Here：Finder 工具栏、统一服务和拖放入口共用极简原生启动面板。
use AppleScript version "2.4"
use framework "Foundation"
use framework "AppKit"
use scripting additions

property launcher : "__LAUNCHER__"
property launchSource : "finder"

on run
	set launchSource to "finder"
	set picked to {}
	set finderCwd to missing value
	set hasFinderWindow to false
	tell application "Finder"
		try
			repeat with selectedItem in (selection as alias list)
				set end of picked to POSIX path of selectedItem
			end repeat
		end try
		set hasFinderWindow to (count of Finder windows) > 0
		if hasFinderWindow then
			try
				set finderCwd to POSIX path of ((target of front Finder window) as alias)
			end try
		end if
	end tell
	if hasFinderWindow and finderCwd is missing value and (count of picked) = 0 then
		set finderCwd to my askForDirectory("此 Finder 位置不是稳定的文件夹，请选择工作目录。")
		if finderCwd is missing value then return
	else if not hasFinderWindow and (count of picked) = 0 then
		set finderCwd to POSIX path of (path to desktop folder)
	end if
	my chooseAndLaunch(picked, finderCwd)
end run

on open droppedItems
	set launchSource to "open"
	set picked to {}
	repeat with f in droppedItems
		set end of picked to POSIX path of f
	end repeat
	my chooseAndLaunch(picked, missing value)
end open

on askForDirectory(promptText)
	try
		return POSIX path of (choose folder with prompt promptText)
	on error number -128
		return missing value
	end try
end askForDirectory

on normalizedPath(pathText)
	return (current application's NSString's stringWithString:(pathText as text))'s stringByStandardizingPath() as text
end normalizedPath

on sameDirectory(firstPath, secondPath)
	if firstPath is "" or secondPath is "" then return false
	return (my normalizedPath(firstPath)) is (my normalizedPath(secondPath))
end sameDirectory

on isDirectory(pathText)
	try
		do shell script "/bin/test -d " & quoted form of (pathText as text)
		return true
	on error
		return false
	end try
end isDirectory

on commonParent(paths)
	if (count of paths) = 0 then return missing value
	set candidate to (current application's NSString's stringWithString:(item 1 of paths))'s stringByDeletingLastPathComponent() as text
	repeat with p in paths
		set parentPath to (current application's NSString's stringWithString:(p as text))'s stringByDeletingLastPathComponent() as text
		repeat while candidate is not "/" and parentPath is not candidate and parentPath does not start with (candidate & "/")
			set candidate to (current application's NSString's stringWithString:candidate)'s stringByDeletingLastPathComponent() as text
		end repeat
	end repeat
	return candidate
end commonParent

-- Keep the original file paths for handoff; only directory comparison is normalized.
on selectedFilePaths(picked)
	set filePaths to {}
	repeat with p in picked
		set originalPath to p as text
		if not my isDirectory(my normalizedPath(originalPath)) then
			if originalPath is not in filePaths then set end of filePaths to originalPath
		end if
	end repeat
	return filePaths
end selectedFilePaths

on directoryForFiles(filePaths, finderCwd)
	if finderCwd is not missing value then return finderCwd
	if (count of filePaths) > 0 then return my commonParent(filePaths)
	return missing value
end directoryForFiles

on chooseAndLaunch(picked, finderCwd)
	set folderPaths to {}
	set filePaths to my selectedFilePaths(picked)
	repeat with p in picked
		set cleanPath to my normalizedPath(p as text)
		if my isDirectory(cleanPath) then
			if cleanPath is not in folderPaths then set end of folderPaths to cleanPath
		end if
	end repeat
	set initialCwd to finderCwd
	if (count of folderPaths) = 1 then
		set initialCwd to item 1 of folderPaths
	else if (count of folderPaths) > 1 then
		set folderChoice to choose from list folderPaths with title "选择工作目录" with prompt "请选择一个工作目录。本次只打开一个工具，不会同时启动多个任务。" default items {item 1 of folderPaths}
		if folderChoice is false then return
		set initialCwd to item 1 of folderChoice
	else if (count of filePaths) > 0 then
		-- Stable Finder location remains the workspace; selected files become attachments.
		set initialCwd to my directoryForFiles(filePaths, finderCwd)
	end if
	if initialCwd is missing value then set initialCwd to my askForDirectory("请选择工作目录。")
	if initialCwd is missing value then return
	my showLaunchPanel(my normalizedPath(initialCwd), filePaths)
end chooseAndLaunch

-- The dynamically loaded bundle only collects a selection; all launching stays here.
on showLaunchPanel(initialCwd, initialReferences)
	set resourcesPath to current application's NSBundle's mainBundle()'s resourcePath() as text
	set uiBundle to current application's NSBundle's bundleWithPath:(resourcesPath & "/NativeUI.bundle")
	if uiBundle is missing value then
		my showNativeMessage("AI Here 界面不可用", "未找到 NativeUI.bundle，请重新安装 AI Here。", "好", true)
		return
	end if
	if not (uiBundle's load()) as boolean then
		my showNativeMessage("AI Here 界面不可用", "无法加载原生界面组件，请重新安装 AI Here。", "好", true)
		return
	end if
	set panelClass to uiBundle's principalClass()
	if panelClass is missing value then
		my showNativeMessage("AI Here 界面不可用", "未找到 AIHerePanelController，请重新安装 AI Here。", "好", true)
		return
	end if
	set panelController to panelClass's alloc()'s init()
	set selectedCwd to initialCwd
	set selectedReferences to initialReferences
	repeat
		set panelResult to panelController's runWithDirectory:selectedCwd |references|:selectedReferences
		set selectedCwd to (panelResult's objectForKey:"cwd") as text
		set selectedReferences to (panelResult's objectForKey:"references") as list
		if (panelResult's objectForKey:"cancelled") as boolean then exit repeat
		set mode to (panelResult's objectForKey:"mode") as text
		set actionName to (panelResult's objectForKey:"action") as text
		try
			my launchSelection(mode, actionName, selectedCwd, selectedReferences)
			exit repeat
		on error errorMessage
			my showNativeMessage("AI Here 未启动", errorMessage, "返回", true)
		end try
	end repeat
end showLaunchPanel

on commandForLaunch(mode, actionName, cwdText, selectedReferences)
	if actionName is not "direct" and actionName is not "summary" then error "未知的启动操作。"
	if actionName is "direct" and (count of selectedReferences) = 0 then
		return quoted form of launcher & " " & quoted form of mode & " " & quoted form of cwdText
	end if
	set launchCommand to quoted form of launcher & " task start --cwd " & quoted form of cwdText & " --tool " & quoted form of mode & " --action " & quoted form of actionName & " --source " & quoted form of launchSource
	repeat with refPath in selectedReferences
		set launchCommand to launchCommand & " --reference " & quoted form of (refPath as text)
	end repeat
	return launchCommand
end commandForLaunch

on launchSelection(mode, actionName, selectedCwd, selectedReferences)
	set cwdText to my normalizedPath(selectedCwd)
	if cwdText does not start with "/" then error "工作目录必须是完整的绝对路径。"
	if not my isDirectory(cwdText) then error "工作目录不存在或不是文件夹，请更换目录。"
	do shell script (my commandForLaunch(mode, actionName, cwdText, selectedReferences)) & " 2>&1"
	-- CLI receives the prompt as an argument; desktop clients receive a draft
	-- through their supported deep links. Successful launch needs no extra alert.
end launchSelection

on showNativeMessage(titleText, messageText, buttonText, isWarning)
	set messageAlert to current application's NSAlert's alloc()'s init()
	messageAlert's setMessageText:titleText
	messageAlert's setInformativeText:messageText
	if isWarning then
		messageAlert's setAlertStyle:(current application's NSAlertStyleWarning)
	else
		messageAlert's setAlertStyle:(current application's NSAlertStyleInformational)
	end if
	messageAlert's addButtonWithTitle:buttonText
	(messageAlert's |window|())'s setTitle:"AI Here"
	current application's NSApplication's sharedApplication()'s activateIgnoringOtherApps:true
	messageAlert's runModal()
end showNativeMessage
