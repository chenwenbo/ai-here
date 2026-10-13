"""Launcher integration tests: real handoff files, mocked clipboard and app launch."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "ai-here"


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.workspace = self.base / "中文 空间 ' $(touch SHOULD_NOT_EXIST) `echo danger`"
        self.workspace.mkdir()
        self.tools = self.base / "tools"
        self.tools.mkdir()
        self.config = self.base / "config"
        self.config.write_text('TERMINAL_APP=Terminal\nCODEX_CMD="fake-codex --model test"\nCLAUDE_CMD="fake-claude"\n', encoding="utf-8")
        self.env = dict(os.environ, AI_HERE_CONFIG=str(self.config), AI_HERE_DRY_RUN="1")
        self.env["PATH"] = str(self.tools) + os.pathsep + self.env["PATH"]
        # AppleScript and URL encoding run normally; only clipboard / open are mocked.
        self.stub("pbcopy", '#!/bin/sh\ncat > "$CAPTURE"\n')
        self.stub("open", '#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
        self.stub("fake-codex", '#!/usr/bin/python3\nimport json, os, sys\nopen(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[1:]))\n')
        self.stub("fake-claude", '#!/usr/bin/python3\nimport json, os, sys\nopen(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[1:]))\n')
        self.stub("clear", '#!/bin/sh\nexit 0\n')
        self.capture = self.base / "capture"
        self.env["CAPTURE"] = str(self.capture)

    def stub(self, name, source):
        file = self.tools / name
        file.write_text(source, encoding="utf-8")
        file.chmod(0o755)

    def call(self, *args, data=None, env=None):
        return subprocess.run(["/bin/zsh", str(LAUNCHER), *map(str, args)], input=data,
                              text=True, capture_output=True, env=env or self.env, check=True)

    def enable(self):
        self.call("handoff", "init", self.workspace, "--instructions")
        self.call("handoff", "add", self.workspace, "--title", "选择器完成",
                  "--agent", "codex", "--status", "completed", "--body-file", "-",
                  data="## 已完成\n双击确认。\n## 验证\n编译通过。\n## 下一步\nWorkBuddy 接续。\n")

    def test_cli_and_installed_layout(self):
        self.enable()
        self.assertIn("选择器完成", self.call("handoff", "list", self.workspace).stdout)
        installed = self.base / "installed"
        (installed / "lib").mkdir(parents=True)
        (installed / "ai-here").write_bytes(LAUNCHER.read_bytes())
        (installed / "lib" / "handoff.py").write_bytes((ROOT / "lib" / "handoff.py").read_bytes())
        r = subprocess.run(["/bin/zsh", str(installed / "ai-here"), "handoff", "export", str(self.workspace)],
                           env=self.env, capture_output=True, text=True, check=True)
        self.assertIn("双击确认", r.stdout)

    def test_terminal_notice_is_shell_safe_and_preserves_command(self):
        self.enable()
        line = self.call("codex-cli", self.workspace).stdout.strip()
        env = dict(self.env)
        subprocess.run(["/bin/zsh", "-c", line], env=env, cwd=self.base, capture_output=True, check=True)
        self.assertEqual(json.loads(self.capture.read_text()), ["--model", "test"])
        self.assertFalse((self.base / "SHOULD_NOT_EXIST").exists())
        self.assertFalse((self.workspace / "SHOULD_NOT_EXIST").exists())

    def test_continue_keeps_original_arguments(self):
        self.enable()
        line = self.call("claude-continue", self.workspace).stdout.strip()
        subprocess.run(["/bin/zsh", "-c", line], env=self.env, capture_output=True, check=True)
        self.assertEqual(json.loads(self.capture.read_text()), ["--continue"])

    def test_copy_open_and_multiple_workspaces(self):
        self.enable()
        env = dict(self.env)
        env.pop("AI_HERE_DRY_RUN")
        self.call("handoff", "copy", self.workspace, env=env)
        self.assertIn("双击确认", self.capture.read_text())
        self.call("handoff", "open", self.workspace, env=env)
        self.assertIn(str(self.workspace / ".ai-here" / "index.md"), self.capture.read_text())
        other = self.base / "第二个目录"
        other.mkdir()
        self.call("handoff", "init", other)
        combined = self.call("handoff-copy", self.workspace, other).stdout
        self.assertIn(str(other), combined)
        self.assertIn("双击确认", combined)

    @unittest.skipUnless(Path("/Applications/WorkBuddy.app").exists(), "WorkBuddy not installed")
    def test_workbuddy_only_prefills_path_and_instruction(self):
        self.enable()
        url = self.call("workbuddy", self.workspace).stdout.strip()
        args = parse_qs(urlparse(url).query)
        self.assertEqual(args["cwd"], [str(self.workspace)])
        self.assertIn(".ai-here/index.md", args["prompt"][0])
        self.assertNotIn("双击确认", args["prompt"][0])
        self.assertEqual(args["action"], ["start"])

    def test_uninitialized_launch_does_not_create_memory(self):
        line = self.call("claude-cli", self.workspace).stdout
        self.assertNotIn("index.md", line)
        self.assertFalse((self.workspace / ".ai-here").exists())

    def test_unreadable_handoff_does_not_block_agent_launch(self):
        outside = self.base / "linked-memory"
        outside.mkdir()
        (outside / "index.md").write_text("不可自动读取的交接资料。", encoding="utf-8")
        (self.workspace / ".ai-here").symlink_to(outside, target_is_directory=True)
        result = self.call("claude-cli", self.workspace)
        self.assertIn("fake-claude", result.stdout)
        self.assertIn("符号链接", result.stderr)

    def test_toolbar_init_success_is_independent_of_notifications(self):
        self.stub("osascript", '#!/bin/sh\nexit 17\n')
        result = self.call("handoff-init", self.workspace)
        self.assertTrue((self.workspace / ".ai-here" / "index.md").exists())
        self.assertTrue((self.workspace / "AGENTS.md").exists())
        self.assertIn("index.md", result.stdout)

    def test_toolbar_init_failure_still_returns_nonzero(self):
        self.stub("osascript", '#!/bin/sh\nexit 17\n')
        outside = self.base / "outside"
        outside.mkdir()
        (self.workspace / ".ai-here").symlink_to(outside, target_is_directory=True)
        result = subprocess.run(["/bin/zsh", str(LAUNCHER), "handoff-init", str(self.workspace)],
                                env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((outside / "index.md").exists())


if __name__ == "__main__":
    unittest.main()
