import AppKit

private final class FlippedView: NSView {
    override var isFlipped: Bool { true }
}

private final class LauncherWindow: NSWindow {
    var actionFocusViews: [NSView] = []
    weak var hintOwner: IconActionButton?

    func claimHint(for button: IconActionButton) {
        if hintOwner !== button {
            hintOwner?.resetHoverAndDismissHint()
            hintOwner = button
        }
    }

    private func moveActionFocus(backwards: Bool) {
        guard !actionFocusViews.isEmpty else { return }
        let nextIndex: Int
        if let focused = firstResponder,
           let currentIndex = actionFocusViews.firstIndex(where: { $0 === focused }) {
            let delta = backwards ? -1 : 1
            nextIndex = (currentIndex + delta + actionFocusViews.count) % actionFocusViews.count
        } else {
            nextIndex = backwards ? actionFocusViews.count - 1 : 0
        }
        let nextView = actionFocusViews[nextIndex]
        nextView.scrollToVisible(nextView.bounds)
        makeFirstResponder(nextView)
    }

    // There is deliberately no default action. Space clicks a focused button;
    // Return never starts work just because the window has been opened.
    override func sendEvent(_ event: NSEvent) {
        if event.type == .keyDown && attachedSheet == nil {
            if event.keyCode == 48 {
                moveActionFocus(backwards: event.modifierFlags.contains(.shift))
                return
            }
            if event.keyCode == 53 {
                performClose(nil)
                return
            }
            if event.keyCode == 36 || event.keyCode == 76 { return }
        }
        super.sendEvent(event)
    }
}

// Keep the directory control in the same keyboard loop as icon actions, even
// when macOS full keyboard access is disabled. Space remains NSButton's click.
private final class FocusButton: NSButton {
    override var acceptsFirstResponder: Bool { true }

    override func becomeFirstResponder() -> Bool {
        guard isEnabled else { return false }
        cell?.showsFirstResponder = true
        needsDisplay = true
        return true
    }

    override func resignFirstResponder() -> Bool {
        cell?.showsFirstResponder = false
        needsDisplay = true
        return true
    }

    override func isAccessibilityFocused() -> Bool {
        window?.firstResponder === self
    }
}

// An immediate native hint inside the existing window. It never takes focus or
// intercepts pointer events, so modal routing and action buttons remain intact.
private final class PassiveHintView: NSVisualEffectView {
    override func hitTest(_ point: NSPoint) -> NSView? { nil }
}

private final class IconActionButton: NSButton {
    private let isLaunch: Bool
    private var hovering = false
    private var pointerTracking: NSTrackingArea?
    private var pressed = false
    private var hintView: PassiveHintView?

    init(launch: Bool) {
        isLaunch = launch
        super.init(frame: .zero)
        title = ""
        setButtonType(.momentaryPushIn)
        refusesFirstResponder = false
        cell?.refusesFirstResponder = false
        isBordered = false
        imagePosition = .imageOnly
        imageScaling = .scaleProportionallyDown
        wantsLayer = true
        layer?.cornerRadius = 8
        layer?.borderWidth = launch ? 0 : 1
        layer?.borderColor = NSColor(calibratedWhite: 0.83, alpha: 0.65).cgColor
        contentTintColor = launch ? .white : NSColor(calibratedRed: 0.16, green: 0.19, blue: 0.22, alpha: 1)
        let symbol = launch ? "arrow.up.right" : "doc.text.magnifyingglass"
        image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil)?
            .withSymbolConfiguration(.init(pointSize: 18, weight: .medium))
        toolTip = launch ? "直接开始" : "总结并接续"
        focusRingType = .default
        updateAppearance()
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is unsupported") }
    override var acceptsFirstResponder: Bool { true }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let pointerTracking { removeTrackingArea(pointerTracking) }
        let tracking = NSTrackingArea(rect: bounds,
                                      options: [.activeAlways, .mouseEnteredAndExited, .mouseMoved, .inVisibleRect],
                                      owner: self, userInfo: nil)
        addTrackingArea(tracking)
        pointerTracking = tracking
    }

    override func mouseEntered(with event: NSEvent) {
        updatePointerHover()
    }

    override func mouseMoved(with event: NSEvent) {
        updatePointerHover()
    }

    override func scrollWheel(with event: NSEvent) {
        // Cursor warping plus a wheel event may not dispatch mouseEntered.
        // Only the real event location inside this button activates the hint.
        if bounds.contains(convert(event.locationInWindow, from: nil)) {
            updatePointerHover()
        }
        super.scrollWheel(with: event)
    }

    private func updatePointerHover() {
        guard let window, window.isVisible, NSApp.isActive,
              window.attachedSheet == nil, !isHidden, isEnabled else {
            hovering = false
            updateAppearance()
            dismissHint()
            return
        }
        hovering = true
        updateAppearance()
        if hintView == nil { showHint() }
    }

    override func mouseExited(with event: NSEvent) {
        hovering = false
        updateAppearance()
        dismissHint()
    }

    override func highlight(_ flag: Bool) {
        super.highlight(flag)
        pressed = flag
        updateAppearance()
    }

    override func becomeFirstResponder() -> Bool {
        guard isEnabled else { return false }
        // Avoid NSButton's global full-keyboard-access preference gate.
        cell?.showsFirstResponder = true
        needsDisplay = true
        showHint()
        return true
    }

    override func resignFirstResponder() -> Bool {
        cell?.showsFirstResponder = false
        needsDisplay = true
        dismissHint()
        return true
    }

    override func isAccessibilityFocused() -> Bool {
        window?.firstResponder === self
    }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        if window?.firstResponder === self && NSApp.isActive {
            NSGraphicsContext.saveGraphicsState()
            NSFocusRingPlacement.only.set()
            NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 7, yRadius: 7).fill()
            NSGraphicsContext.restoreGraphicsState()
        }
    }

    func resetHoverAndDismissHint() {
        hovering = false
        updateAppearance()
        dismissHint()
    }

    func dismissHint() {
        hintView?.removeFromSuperview()
        hintView = nil
        if let launcherWindow = window as? LauncherWindow,
           launcherWindow.hintOwner === self {
            launcherWindow.hintOwner = nil
        }
    }

    private func showHint() {
        guard let window, window.isVisible, NSApp.isActive,
              window.attachedSheet == nil,
              let content = window.contentView, !isHidden, isEnabled else {
            dismissHint()
            return
        }
        if let launcherWindow = window as? LauncherWindow {
            launcherWindow.claimHint(for: self)
        }
        if hintView?.superview === content { return }
        // Remove only this button's obsolete view; preserve its newly claimed ownership.
        hintView?.removeFromSuperview()
        hintView = nil
        let text = isLaunch ? "直接开始" : "总结并接续"
        let caption = NSTextField(labelWithString: text)
        caption.font = .systemFont(ofSize: 12, weight: .medium)
        caption.textColor = .labelColor
        caption.maximumNumberOfLines = 1
        caption.sizeToFit()
        let size = NSSize(width: ceil(caption.frame.width) + 20, height: 28)
        let buttonRect = convert(bounds, to: content)
        let margin: CGFloat = 8
        let gap: CGFloat = 5
        let x = max(margin, min(buttonRect.midX - size.width / 2,
                                 content.bounds.maxX - margin - size.width))
        var y: CGFloat
        if content.isFlipped {
            y = buttonRect.maxY + gap
            if y + size.height > content.bounds.maxY - margin {
                y = buttonRect.minY - gap - size.height
            }
        } else {
            y = buttonRect.minY - gap - size.height
            if y < content.bounds.minY + margin { y = buttonRect.maxY + gap }
        }
        y = max(content.bounds.minY + margin,
                min(y, content.bounds.maxY - margin - size.height))
        let hint = PassiveHintView(frame: NSRect(origin: NSPoint(x: x, y: y), size: size))
        hint.material = .popover
        hint.blendingMode = .withinWindow
        hint.state = .active
        hint.wantsLayer = true
        hint.layer?.cornerRadius = 6
        hint.layer?.masksToBounds = true
        hint.layer?.borderWidth = 1
        hint.layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.55).cgColor
        caption.frame = NSRect(x: 10, y: 6, width: size.width - 20, height: 17)
        hint.addSubview(caption)
        content.addSubview(hint, positioned: .above, relativeTo: nil)
        hintView = hint
    }

    private func updateAppearance() {
        if isLaunch {
            layer?.backgroundColor = NSColor(calibratedRed: 0.05,
                                             green: hovering || pressed ? 0.46 : 0.56,
                                             blue: hovering || pressed ? 0.40 : 0.48,
                                             alpha: 1).cgColor
        } else {
            layer?.backgroundColor = NSColor(calibratedWhite: hovering || pressed ? 0.88 : 0.935,
                                             alpha: 1).cgColor
        }
        needsDisplay = true
    }
}

/// Loaded by the existing AppleScript Droplet; owns UI only, never starts tools.
@objc(AIHerePanelController)
public final class AIHerePanelController: NSObject, NSWindowDelegate {
    private struct Tool {
        let name: String
        let mode: String
        let kind: String
        let icon: String
    }
    private let tools = [
        Tool(name: "Claude Code", mode: "claude-cli", kind: "CLI", icon: "claude"),
        Tool(name: "Codex", mode: "codex-cli", kind: "CLI", icon: "codex"),
        Tool(name: "Claude", mode: "claude-app", kind: "桌面", icon: "claude"),
        Tool(name: "Codex", mode: "codex-app", kind: "桌面", icon: "codex"),
        Tool(name: "WorkBuddy", mode: "workbuddy", kind: "桌面", icon: "workbuddy")
    ]
    private let surface = NSColor(calibratedRed: 0.985, green: 0.979, blue: 0.967, alpha: 1)
    private let ink = NSColor(calibratedRed: 0.10, green: 0.12, blue: 0.14, alpha: 1)
    private let muted = NSColor(calibratedRed: 0.47, green: 0.48, blue: 0.49, alpha: 1)
    private var panelWindow: LauncherWindow?
    private var directory = ""
    private var referencePaths: [String] = []
    private var referenceScrollView: NSScrollView?
    private var referenceDocumentView: FlippedView?
    private var referenceCountLabel: NSTextField?
    private var referenceRemoveButtons: [FocusButton] = []
    private var directoryChangeButton: FocusButton?
    private var directoryName: NSTextField?
    private var directoryPath: NSTextField?
    private var directoryIcon: NSImageView?
    private var result: NSDictionary = [:]
    private var modalActive = false
    private var actionButtons: [IconActionButton] = []
    private var activityObserver: NSObjectProtocol?

    @objc public override init() {
        super.init()
        activityObserver = NotificationCenter.default.addObserver(
            forName: NSApplication.didResignActiveNotification,
            object: nil, queue: .main
        ) { [weak self] _ in self?.dismissHints() }
    }

    deinit {
        if let activityObserver { NotificationCenter.default.removeObserver(activityObserver) }
    }

    /// Exact Objective-C selector: runWithDirectory:
    /// cancelled=true includes the last selected directory; no mode/action is run.
    @objc(runWithDirectory:)
    public func runWithDirectory(_ selectedDirectory: String) -> NSDictionary {
        runWithDirectory(selectedDirectory, references: [])
    }

    /// Exact Objective-C selector: runWithDirectory:references:
    /// Reference strings are local paths awaiting delivery, not uploaded files.
    @objc(runWithDirectory:references:)
    public func runWithDirectory(_ selectedDirectory: String, references: NSArray) -> NSDictionary {
        precondition(Thread.isMainThread, "AIHerePanelController must run on the main thread")
        dismissHints()
        directory = selectedDirectory
        referencePaths = references.compactMap { $0 as? String }
        result = cancelledResult()
        let window = makeWindow()
        panelWindow = window // NSWindow delegate is weak; controller and window stay owned.
        window.delegate = self
        window.center()
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(nil)
        NSApp.activate(ignoringOtherApps: true)
        modalActive = true
        NSApp.runModal(for: window)
        modalActive = false
        dismissHints()
        window.orderOut(nil)
        return result
    }

    public func windowShouldClose(_ sender: NSWindow) -> Bool {
        dismissHints()
        result = cancelledResult()
        if modalActive { NSApp.stopModal(withCode: .cancel) }
        return true
    }

    private func cancelledResult() -> NSDictionary {
        ["mode": "", "action": "", "cwd": directory,
         "references": referencePaths, "cancelled": true]
    }

    private func makeWindow() -> LauncherWindow {
        let window = LauncherWindow(contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
                                    styleMask: [.titled, .closable, .miniaturizable],
                                    backing: .buffered, defer: false)
        window.title = "AI Here"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.backgroundColor = surface
        window.isReleasedWhenClosed = false
        window.hasShadow = true
        window.acceptsMouseMovedEvents = true
        window.setAccessibilityLabel("AI Here 启动面板")

        let titleAccessory = NSTitlebarAccessoryViewController()
        titleAccessory.layoutAttribute = .left
        let titleView = NSView(frame: NSRect(x: 0, y: 0, width: 190, height: 30))
        let appIcon = NSImageView(frame: NSRect(x: 9, y: 4, width: 22, height: 22))
        appIcon.image = resourceImage("AIHere.icns")
        appIcon.imageScaling = .scaleProportionallyDown
        titleView.addSubview(appIcon)
        titleView.addSubview(label("AI Here", size: 14, weight: .semibold, color: ink,
                                  frame: NSRect(x: 40, y: 6, width: 145, height: 20)))
        titleAccessory.view = titleView
        window.addTitlebarAccessoryViewController(titleAccessory)

        let content = FlippedView(frame: NSRect(x: 0, y: 0, width: 800, height: 600))
        content.wantsLayer = true
        content.layer?.backgroundColor = surface.cgColor
        window.contentView = content
        addLine(to: content, at: 0, x: 0, width: 800)
        let folderIcon = NSImageView(frame: NSRect(x: 24, y: 22, width: 60, height: 60))
        folderIcon.imageScaling = .scaleProportionallyUpOrDown
        content.addSubview(folderIcon)
        directoryIcon = folderIcon
        let name = label("", size: 23, weight: .semibold, color: ink,
                         frame: NSRect(x: 102, y: 22, width: 535, height: 29))
        let path = label("", size: 13, weight: .regular, color: muted,
                         frame: NSRect(x: 102, y: 58, width: 535, height: 21))
        path.lineBreakMode = .byTruncatingMiddle
        path.setAccessibilityLabel("工作目录完整路径")
        content.addSubview(name)
        content.addSubview(path)
        directoryName = name
        directoryPath = path
        updateDirectory()
        let changeButton = FocusButton(title: "更换…", target: self, action: #selector(changeDirectory(_:)))
        changeButton.frame = NSRect(x: 678, y: 37, width: 100, height: 32)
        changeButton.bezelStyle = .rounded
        changeButton.refusesFirstResponder = false
        changeButton.cell?.refusesFirstResponder = false
        changeButton.font = .systemFont(ofSize: 12, weight: .medium)
        changeButton.setAccessibilityLabel("更换工作目录")
        content.addSubview(changeButton)
        directoryChangeButton = changeButton
        addLine(to: content, at: 105, x: 0, width: 800)

        let divider = NSView(frame: NSRect(x: 260, y: 106, width: 1, height: 468))
        divider.wantsLayer = true
        divider.layer?.backgroundColor = NSColor(calibratedWhite: 0.85, alpha: 0.7).cgColor
        content.addSubview(divider)
        let countLabel = label("", size: 18, weight: .semibold, color: ink,
                               frame: NSRect(x: 22, y: 128, width: 190, height: 24))
        content.addSubview(countLabel)
        referenceCountLabel = countLabel
        content.addSubview(label("待带入本次对话", size: 12, weight: .regular, color: muted,
                                 frame: NSRect(x: 22, y: 158, width: 190, height: 20)))
        let referenceScroll = NSScrollView(frame: NSRect(x: 0, y: 169, width: 260, height: 394))
        referenceScroll.hasVerticalScroller = true
        referenceScroll.hasHorizontalScroller = false
        referenceScroll.autohidesScrollers = true
        referenceScroll.drawsBackground = false
        referenceScroll.borderType = .noBorder
        referenceScroll.setAccessibilityLabel("待带入的本地文件")
        content.addSubview(referenceScroll)
        referenceScrollView = referenceScroll
        let referenceDocument = FlippedView(frame: NSRect(x: 0, y: 0, width: 260, height: 394))
        referenceDocument.autoresizingMask = [.width]
        referenceScroll.documentView = referenceDocument
        referenceDocumentView = referenceDocument

        content.addSubview(label("命令行", size: 13, weight: .semibold, color: muted,
                                 frame: NSRect(x: 288, y: 128, width: 300, height: 20)))
        addLine(to: content, at: 156, x: 288, width: 490)
        content.addSubview(label("桌面应用", size: 13, weight: .semibold, color: muted,
                                 frame: NSRect(x: 288, y: 316, width: 300, height: 20)))
        addLine(to: content, at: 346, x: 288, width: 490)
        var buttons: [IconActionButton] = []
        for (index, tool) in tools.enumerated() {
            let y = index < 2 ? 162 + CGFloat(index) * 66 : 352 + CGFloat(index - 2) * 66
            let icon = NSImageView(frame: NSRect(x: 288, y: y + 5, width: 56, height: 56))
            icon.image = resourceImage("ToolIcons/\(tool.icon).png")
            icon.imageScaling = .scaleProportionallyDown
            content.addSubview(icon)
            content.addSubview(label(tool.name, size: 16, weight: .semibold, color: ink,
                                     frame: NSRect(x: 352, y: y + 21, width: 295, height: 24)))
            for (actionIndex, launch) in [true, false].enumerated() {
                let button = IconActionButton(launch: launch)
                button.frame = NSRect(x: launch ? 670 : 730, y: y + 12, width: 48, height: 42)
                button.tag = index * 2 + actionIndex
                button.target = self
                button.action = #selector(selectAction(_:))
                let actionLabel = launch ? "直接开始" : "总结并接续"
                button.setAccessibilityLabel("\(tool.name) \(tool.kind) · \(actionLabel)")
                button.setAccessibilityHelp(launch ? "在当前工作目录打开工具并带入文件清单。" : "由目标工具按技能执行总结、保存文档并接续工作。")
                content.addSubview(button)
                buttons.append(button)
            }
            if index != 1 && index != 4 { addLine(to: content, at: y + 66, x: 288, width: 490) }
        }
        actionButtons = buttons
        addLine(to: content, at: 574, x: 0, width: 800)
        content.addSubview(label("带入本地文件清单，启动后由工具读取。", size: 11, weight: .regular, color: muted,
                                 frame: NSRect(x: 24, y: 581, width: 752, height: 16)))
        window.autorecalculatesKeyViewLoop = false
        window.initialFirstResponder = changeButton
        // The controller has not published this window yet; list rebuilding uses it explicitly.
        rebuildReferenceList(in: window)
        return window
    }

    private func rebuildReferenceList(in window: LauncherWindow? = nil) {
        guard let document = referenceDocumentView, let scroll = referenceScrollView else { return }
        document.subviews.forEach { $0.removeFromSuperview() }
        referenceRemoveButtons = []
        referenceCountLabel?.stringValue = "附件 · \(referencePaths.count)"
        document.frame.size = NSSize(width: 260,
                                    height: max(scroll.contentSize.height, CGFloat(referencePaths.count) * 64))
        if referencePaths.isEmpty {
            document.addSubview(label("尚未选择文件", size: 13, weight: .regular, color: muted,
                                      frame: NSRect(x: 22, y: 18, width: 184, height: 24)))
            let help = label("可在 Finder 中选中文件后打开 AI Here。", size: 11, weight: .regular, color: muted,
                             frame: NSRect(x: 22, y: 49, width: 184, height: 44))
            help.maximumNumberOfLines = 0
            help.lineBreakMode = .byWordWrapping
            document.addSubview(help)
        }
        for (index, reference) in referencePaths.enumerated() {
            let y = CGFloat(index) * 64
            let icon = NSImageView(frame: NSRect(x: 20, y: y + 12, width: 32, height: 38))
            icon.image = NSWorkspace.shared.icon(forFile: reference)
            icon.imageScaling = .scaleProportionallyUpOrDown
            document.addSubview(icon)
            let fileName = (reference as NSString).lastPathComponent
            let name = label(fileName, size: 14, weight: .medium, color: ink,
                             frame: NSRect(x: 62, y: y + 21, width: 160, height: 23))
            name.lineBreakMode = .byTruncatingMiddle
            name.toolTip = reference
            name.setAccessibilityLabel("附件：\(fileName)")
            name.setAccessibilityHelp(reference)
            document.addSubview(name)
            let remove = FocusButton(title: "", target: self, action: #selector(removeReference(_:)))
            remove.frame = NSRect(x: 229, y: y + 21, width: 22, height: 22)
            remove.isBordered = false
            remove.refusesFirstResponder = false
            remove.cell?.refusesFirstResponder = false
            remove.image = NSImage(systemSymbolName: "xmark", accessibilityDescription: nil)?
                .withSymbolConfiguration(.init(pointSize: 11, weight: .regular))
            remove.imagePosition = .imageOnly
            remove.contentTintColor = muted
            remove.toolTip = "移除附件"
            remove.setAccessibilityLabel("移除附件：\(fileName)")
            remove.tag = index
            document.addSubview(remove)
            referenceRemoveButtons.append(remove)
        }
        updateKeyLoop(in: window ?? panelWindow)
    }

    private func updateKeyLoop(in window: LauncherWindow?) {
        guard let window, let changeButton = directoryChangeButton else { return }
        let focusables: [NSView] = [changeButton] + referenceRemoveButtons + actionButtons
        for (index, view) in focusables.enumerated() {
            view.nextKeyView = focusables[(index + 1) % focusables.count]
        }
        window.actionFocusViews = focusables
    }

    @objc private func removeReference(_ sender: FocusButton) {
        guard referencePaths.indices.contains(sender.tag) else { return }
        let wasFocused = panelWindow?.firstResponder === sender
        let removedIndex = sender.tag
        referencePaths.remove(at: removedIndex)
        rebuildReferenceList()
        if wasFocused {
            let next = referenceRemoveButtons.isEmpty ? directoryChangeButton :
                referenceRemoveButtons[min(removedIndex, referenceRemoveButtons.count - 1)]
            panelWindow?.makeFirstResponder(next)
        }
    }

    private func updateDirectory() {
        let path = directory as NSString
        directoryName?.stringValue = path.lastPathComponent.isEmpty ? "/" : path.lastPathComponent
        directoryPath?.stringValue = directory
        directoryPath?.toolTip = directory
        directoryName?.toolTip = directory
        directoryIcon?.image = NSWorkspace.shared.icon(forFile: directory)
    }

    @objc private func changeDirectory(_ sender: NSButton) {
        guard let window = panelWindow else { return }
        dismissHints()
        let picker = NSOpenPanel()
        picker.canChooseFiles = false
        picker.canChooseDirectories = true
        picker.allowsMultipleSelection = false
        picker.prompt = "选择"
        picker.message = "选择工作目录"
        picker.directoryURL = URL(fileURLWithPath: directory, isDirectory: true)
        picker.beginSheetModal(for: window) { [weak self] response in
            guard response == .OK, let self, let url = picker.url else { return }
            self.directory = url.path
            self.updateDirectory()
        }
    }

    private func dismissHints() {
        actionButtons.forEach { $0.resetHoverAndDismissHint() }
    }

    @objc private func selectAction(_ sender: IconActionButton) {
        let index = sender.tag / 2
        guard tools.indices.contains(index), modalActive else { return }
        dismissHints()
        result = ["mode": tools[index].mode,
                  "action": sender.tag % 2 == 0 ? "direct" : "summary",
                  "cwd": directory,
                  "references": referencePaths,
                  "cancelled": false]
        NSApp.stopModal(withCode: .OK)
    }

    private func label(_ text: String, size: CGFloat, weight: NSFont.Weight,
                       color: NSColor, frame: NSRect) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.frame = frame
        field.font = .systemFont(ofSize: size, weight: weight)
        field.textColor = color
        field.maximumNumberOfLines = 1
        field.lineBreakMode = .byTruncatingTail
        return field
    }

    private func addLine(to parent: NSView, at y: CGFloat, x: CGFloat, width: CGFloat) {
        let line = NSView(frame: NSRect(x: x, y: y, width: width, height: 1))
        line.wantsLayer = true
        line.layer?.backgroundColor = NSColor(calibratedWhite: 0.85, alpha: 0.7).cgColor
        parent.addSubview(line)
    }

    private func resourceImage(_ filename: String) -> NSImage? {
        guard let path = Bundle.main.resourcePath else { return nil }
        return NSImage(contentsOfFile: (path as NSString).appendingPathComponent(filename))
    }
}
