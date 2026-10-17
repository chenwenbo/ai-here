"""Execute compiled native helpers to catch macOS path/command regressions."""
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "AIHere.applescript"


@unittest.skipUnless(shutil.which("osascript") and shutil.which("osacompile"), "macOS AppleScript required")
class PanelHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ai-here-panel-")
        cls.script = Path(cls.temp.name) / "panel.scpt"
        subprocess.run(["osacompile", "-o", str(cls.script), str(SOURCE)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_helper(self, statements, *args):
        code = 'on run argv\nset panelScript to load script (POSIX file (item 1 of argv))\n' + statements + '\nend run'
        return subprocess.check_output(["osascript", "-e", code, str(self.script), *args], text=True).strip()

    def test_directory_check_uses_available_command(self):
        file = Path(self.temp.name) / "材料 中文.txt"
        file.write_text("fixture")
        result = self.run_helper('return {panelScript\'s isDirectory(item 2 of argv), panelScript\'s isDirectory(item 3 of argv)}', self.temp.name, str(file))
        self.assertEqual(result, "true, false")

    def test_backend_and_foundation_tmp_paths_compare_equally(self):
        result = self.run_helper('return {panelScript\'s sameDirectory("/private/tmp", "/tmp"), panelScript\'s sameDirectory("/private/tmp", "/Users") }')
        self.assertEqual(result, "true, false")

    def test_stable_finder_directory_precedes_attachment_parent(self):
        cwd = Path(self.temp.name) / "工作目录"
        cwd.mkdir()
        file = Path(self.temp.name) / "参考.md"
        file.write_text("fixture")
        result = self.run_helper('return panelScript\'s directoryForFiles({item 2 of argv}, item 3 of argv)', str(file), str(cwd))
        self.assertEqual(result, str(cwd))
        fallback = self.run_helper('return panelScript\'s directoryForFiles({item 2 of argv}, missing value)', str(file))
        self.assertEqual(fallback, str(file.parent))

    def test_selected_files_preserve_original_paths_and_skip_directories(self):
        folder = Path(self.temp.name) / "参考目录"
        folder.mkdir()
        file = Path(self.temp.name) / "原始 中文.md"
        file.write_text("fixture")
        result = self.run_helper('return panelScript\'s selectedFilePaths({item 2 of argv, item 3 of argv})', str(file), str(folder))
        self.assertEqual(result, str(file))

    def test_attachment_route_quotes_paths_as_data(self):
        ref = "/tmp/中文 '材料' $(echo unsafe).md"
        code = 'return panelScript\'s commandForLaunch("codex-app", "direct", "/tmp/工作目录", {item 2 of argv})'
        args = shlex.split(self.run_helper(code, ref))
        self.assertEqual(args, ["__LAUNCHER__", "task", "start", "--cwd", "/tmp/工作目录", "--tool", "codex-app", "--action", "direct", "--source", "finder", "--reference", ref])

    def test_plain_direct_retains_legacy_and_summary_uses_start(self):
        direct = shlex.split(self.run_helper('return panelScript\'s commandForLaunch("codex-cli", "direct", "/tmp", {})'))
        self.assertEqual(direct, ["__LAUNCHER__", "codex-cli", "/tmp"])
        summary = shlex.split(self.run_helper('return panelScript\'s commandForLaunch("claude-cli", "summary", "/tmp", {})'))
        self.assertEqual(summary, ["__LAUNCHER__", "task", "start", "--cwd", "/tmp", "--tool", "claude-cli", "--action", "summary", "--source", "finder"])
