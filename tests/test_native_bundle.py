"""Load the Swift UI in the actual Droplet ABI, without opening a window."""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(shutil.which(tool) for tool in ("swiftc", "osacompile", "codesign")),
                     "macOS native build tools required")
class NativeBundleTests(unittest.TestCase):
    def test_droplet_can_load_and_dispatch_native_controller(self):
        with tempfile.TemporaryDirectory(prefix="ai-here-native-test-") as temp:
            base = Path(temp)
            app = base / "BridgeCheck.app"
            script = base / "BridgeCheck.applescript"
            report = base / "result.txt"
            # osascript is an arm64e platform binary on modern macOS. It is not
            # the same ABI/security context as our osacompile-generated Droplet.
            script.write_text('''use framework "Foundation"
use scripting additions
on open ignoredItems
    my checkBridge()
end open
on run
    my checkBridge()
end run
on checkBridge()
    try
        set rootPath to current application's NSBundle's mainBundle()'s resourcePath() as text
        set uiBundle to current application's NSBundle's bundleWithPath:(rootPath & "/NativeUI.bundle")
        if not (uiBundle's load()) as boolean then error "bundle-load-failed"
        set controllerType to uiBundle's principalClass()
        set controller to controllerType's alloc()'s init()
        set selectorPresent to controller's respondsToSelector:"runWithDirectory:"
        if not selectorPresent as boolean then error "selector-missing"
        set referencesSelectorPresent to controller's respondsToSelector:"runWithDirectory:references:"
        if not referencesSelectorPresent as boolean then error "references-selector-missing"
        set resultText to "loaded-and-dispatchable"
    on error errorText
        set resultText to "error: " & errorText
    end try
    do shell script "/usr/bin/printf %s " & quoted form of resultText & " > " & quoted form of "__REPORT__"
end checkBridge
'''.replace("__REPORT__", str(report).replace("\\", "\\\\").replace('"', '\\"')))
            subprocess.run(["osacompile", "-o", str(app), str(script)], check=True, capture_output=True)
            bundle = app / "Contents/Resources/NativeUI.bundle"
            binary = bundle / "Contents/MacOS/AIHereUI"
            binary.parent.mkdir(parents=True)
            (bundle / "Contents/Info.plist").write_text('''<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>AIHereUI</string>
<key>CFBundlePackageType</key><string>BNDL</string>
<key>CFBundleIdentifier</key><string>local.ai-here.test-native</string>
<key>NSPrincipalClass</key><string>AIHerePanelController</string>
</dict></plist>''')
            subprocess.run(["swiftc", "-emit-library", "-module-name", "AIHereUI",
                            "-target", platform.machine() + "-apple-macosx13.0",
                            str(ROOT / "src/AIHereUI.swift"), "-o", str(binary)],
                           check=True, capture_output=True)
            for path in (bundle, app):
                subprocess.run(["codesign", "--force", "--sign", "-", str(path)],
                               check=True, capture_output=True)
            subprocess.run([str(app / "Contents/MacOS/droplet")], check=True,
                           capture_output=True, timeout=20)
            self.assertEqual(report.read_text(), "loaded-and-dispatchable")
