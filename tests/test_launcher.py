"""Launcher integration tests: real handoff files, mocked clipboard and app launch."""
import base64
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
        for name in ("fake-codex", "fake-claude"):
            self.stub(name, '#!/usr/bin/python3\nimport json, os, sys\n'
                'open(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[1:]))\n'
                'if "CWD_CAPTURE" in os.environ:\n'
                '    open(os.environ["CWD_CAPTURE"], "w").write(os.getcwd())\n')
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
        (installed / "lib" / "task_request.py").write_bytes((ROOT / "lib" / "task_request.py").read_bytes())
        r = subprocess.run(["/bin/zsh", str(installed / "ai-here"), "handoff", "export", str(self.workspace)],
                           env=self.env, capture_output=True, text=True, check=True)
        self.assertIn("双击确认", r.stdout)
        r = subprocess.run(["/bin/zsh", str(installed / "ai-here"), "task", "context", "--cwd", str(self.workspace)],
                           env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout)["cwd"], str(self.workspace))

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

    def test_cli_modes_change_actual_directory_before_starting(self):
        cwd_capture = self.base / "actual-cwd"
        env = dict(self.env, CWD_CAPTURE=str(cwd_capture))
        # A decorative clear failure and a custom cd function must not redirect
        # or suppress any of the four CLI launch modes.
        self.stub("clear", '#!/bin/sh\nexit 1\n')
        for mode, expected in (("claude-cli", []), ("claude-continue", ["--continue"]),
                               ("codex-cli", ["--model", "test"]),
                               ("codex-resume", ["--model", "test", "resume", "--last"])):
            with self.subTest(mode=mode):
                line = self.call(mode, self.workspace, env=env).stdout.strip()
                subprocess.run(["/bin/zsh", "-c", 'cd() { builtin cd /; }; ' + line],
                               env=env, cwd=self.base, capture_output=True, check=True)
                self.assertEqual(cwd_capture.read_text(), str(self.workspace))
                self.assertEqual(json.loads(self.capture.read_text()), expected)
                self.assertFalse((self.workspace / "SHOULD_NOT_EXIST").exists())

    def test_failed_cd_prevents_cli_start(self):
        line = self.call("codex-cli", self.workspace).stdout.strip()
        self.workspace.rmdir()  # Disappears between selection and shell startup.
        result = subprocess.run(["/bin/zsh", "-c", line], env=self.env,
                                cwd=self.base, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.capture.exists())

    def test_iterm_session_command_changes_directory_after_shell_startup(self):
        self.config.write_text('TERMINAL_APP=iTerm\nOPEN_IN=tab\n'
                               'CODEX_CMD="fake-codex --model test"\n', encoding="utf-8")
        api_capture = self.base / "terminal-api.json"
        cwd_capture = self.base / "actual-cwd"
        self.stub("osascript", '#!/usr/bin/python3\nimport json, os, sys\n'
            'open(os.environ["API_CAPTURE"], "w").write(json.dumps('
            '{"args": sys.argv[1:], "script": sys.stdin.read()}))\n')
        env = dict(self.env, API_CAPTURE=str(api_capture), CWD_CAPTURE=str(cwd_capture),
                   SHELL="/bin/zsh", ZDOTDIR=str(self.base))
        env.pop("AI_HERE_DRY_RUN")
        # Reproduce a login shell initially landing in the wrong directory.
        (self.base / ".zshrc").write_text('builtin cd /\n', encoding="utf-8")
        self.call("codex-cli", self.workspace, env=env)
        sent = json.loads(api_capture.read_text())
        self.assertEqual(sent["args"][0], "-")
        self.assertEqual(sent["args"][2], "tab")
        self.assertIn("create tab with default profile command cmd", sent["script"])
        self.assertIn("create window with default profile command cmd", sent["script"])
        self.assertNotIn("write text", sent["script"])
        # Execute exactly the session command. EOF exits the shell retained
        # after the fake Agent, without sending input to a real application.
        subprocess.run(["/bin/zsh", "-c", sent["args"][1]], env=env, cwd=self.base,
                       stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=10)
        self.assertEqual(cwd_capture.read_text(), str(self.workspace))
        self.assertEqual(json.loads(self.capture.read_text()), ["--model", "test"])

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

    def test_task_prompt_is_one_literal_cli_argument(self):
        prompt = self.base / "提示 ' $(touch PROMPT_PATH_EXECUTED) `echo bad`.md"
        text = "检查两个文件\n中文 空格 ' \" `touch TASK_EXECUTED` $(touch TASK_EXECUTED)\n--dangerously-skip-permissions"
        prompt.write_text(text, encoding="utf-8")
        env = dict(self.env, AI_HERE_TASK_PROMPT_FILE=str(prompt))
        for mode, expected in (("claude-cli", ["--", text]),
                               ("codex-cli", ["--model", "test", "--", text])):
            line = self.call(mode, self.workspace, env=env).stdout.strip()
            self.assertNotIn(text, line)  # prompt bodies do not enter terminal launch logs
            subprocess.run(["/bin/zsh", "-c", line], env=env, cwd=self.base,
                           capture_output=True, check=True)
            self.assertEqual(json.loads(self.capture.read_text()), expected)
        for folder in (self.base, self.workspace):
            self.assertFalse((folder / "TASK_EXECUTED").exists())
            self.assertFalse((folder / "PROMPT_PATH_EXECUTED").exists())

    def test_task_launch_uses_own_launcher_and_keeps_selected_context(self):
        reference = self.workspace / "参考.txt"
        reference.write_text("真实参考材料", encoding="utf-8")
        request = self.base / "request.json"
        request.write_text(json.dumps({"version": 1, "cwd": str(self.workspace),
            "tool": "claude-cli", "references": ["参考.txt"], "task": "核对中文\n$(touch TASK_EXECUTED)",
            "handoff_id": None}, ensure_ascii=False), encoding="utf-8")
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.base / "launches"))
        result = self.call("task", "launch", "--request", request, env=env)
        self.assertIn("尚未发出启动请求", result.stdout)
        line = next(line for line in result.stdout.splitlines() if line.startswith("builtin cd "))
        subprocess.run(["/bin/zsh", "-c", line], env=env, cwd=self.base,
                       capture_output=True, check=True)
        args = json.loads(self.capture.read_text())
        self.assertEqual(args[0], "--")
        self.assertIn(str(reference), args[1])
        self.assertIn("核对中文\n$(touch TASK_EXECUTED)", args[1])
        self.assertFalse((self.workspace / "TASK_EXECUTED").exists())
        self.assertFalse((self.workspace / ".ai-here").exists())

    @unittest.skipUnless(Path("/Applications/Claude.app").exists(), "Claude not installed")
    def test_claude_desktop_task_prefills_without_clipboard(self):
        prompt = self.base / "桌面任务.md"
        text = "任务正文\n参考材料：两份文件。"
        prompt.write_text(text, encoding="utf-8")
        clipboard = self.base / "clipboard"
        self.stub("pbcopy", '#!/bin/sh\ncat > "$CLIPBOARD_CAPTURE"\n')
        env = dict(self.env, AI_HERE_TASK_PROMPT_FILE=str(prompt),
                   CLIPBOARD_CAPTURE=str(clipboard))
        self.call("claude-app", self.workspace, env=env)
        self.assertFalse(clipboard.exists())  # dry-run leaves the clipboard alone
        env.pop("AI_HERE_DRY_RUN")
        self.call("claude-app", self.workspace, env=env)
        self.assertFalse(clipboard.exists())
        url = self.capture.read_text().strip()
        self.assertIn("claude://code/new?folder=", url)
        self.assertEqual(parse_qs(urlparse(url).query)["q"], [text])

    @unittest.skipUnless(Path("/Applications/WorkBuddy.app").exists(), "WorkBuddy not installed")
    def test_workbuddy_task_url_uses_snapshot_and_keeps_full_prompt(self):
        prompt = self.base / "任务包.md"
        text = "复杂任务" * 5000
        prompt.write_text(text, encoding="utf-8")
        env = dict(self.env, AI_HERE_TASK_PROMPT_FILE=str(prompt))
        url = self.call("workbuddy", self.workspace, env=env).stdout.strip()
        args = parse_qs(urlparse(url).query)
        self.assertIn(str(prompt), args["prompt"][0])
        self.assertNotIn(text, url)
        self.assertLess(len(url), 8000)
        self.assertEqual(prompt.read_text(), text)

    def test_reference_start_delivers_images_and_literal_paths_in_both_actions(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII=")
        image = self.workspace / "截图 ' $(touch ATTACHMENT_EXECUTED) `touch ATTACHMENT_EXECUTED`.png"
        image.write_bytes(png)
        second = self.base / "目录外图片.webp"
        second.write_bytes(b"RIFF\x16\x00\x00\x00WEBPVP8 ")
        # Commas are Codex's image-list delimiter even inside shell quotes.
        comma_image = self.workspace / "截图,保持原路径.png"
        comma_image.write_bytes(png)
        document = self.workspace / "文档 ' $(touch DOC_EXECUTED).md"
        document.write_text("用户提供的本地材料", encoding="utf-8")
        changed = self.base / "更换后的 cwd"
        changed.mkdir()
        cwd_capture = self.base / "actual-cwd"
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.base / "launches"), CWD_CAPTURE=str(cwd_capture))
        for action in ("direct", "summary"):
            result = self.call("task", "start", "--cwd", changed, "--tool", "codex-cli", "--action", action,
                               "--source", "finder", "--reference", image, "--reference", second,
                               "--reference", comma_image, "--reference", document, "--reference", image, env=env)
            line = result.stdout.split("\n已准备启动预览", 1)[0].strip()
            subprocess.run(["/bin/zsh", "-c", line], env=env, cwd=self.base,
                           capture_output=True, check=True)
            arguments = json.loads(self.capture.read_text())
            self.assertEqual(arguments[:7], ["--model", "test", "-i", str(image), "-i", str(second), "--"])
            prompt = arguments[7]
            self.assertIn(str(comma_image), prompt)
            self.assertIn(str(document), prompt)
            self.assertIn("等待用户", prompt)
            self.assertIn("无法读取", prompt)
            self.assertEqual(cwd_capture.read_text(), str(changed))
            self.assertFalse((changed / ".ai-here").exists())
        for folder in (self.base, self.workspace, changed):
            self.assertFalse((folder / "ATTACHMENT_EXECUTED").exists())
            self.assertFalse((folder / "DOC_EXECUTED").exists())
        self.assertEqual(image.read_bytes(), png)

    def test_claude_cli_materials_remain_paths_without_image_flag(self):
        image = self.workspace / "图片.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.base / "launches"))
        result = self.call("task", "start", "--cwd", self.workspace, "--tool", "claude-cli", "--action", "direct",
                           "--reference", image, env=env)
        line = result.stdout.split("\n已准备启动预览", 1)[0].strip()
        subprocess.run(["/bin/zsh", "-c", line], env=env, cwd=self.base, capture_output=True, check=True)
        arguments = json.loads(self.capture.read_text())
        self.assertEqual(arguments[0], "--")
        self.assertEqual(len(arguments), 2)
        self.assertIn(str(image), arguments[1])
        self.assertNotIn("通过 Codex CLI -i", arguments[1])

    def test_missing_start_reference_prevents_agent_command_generation(self):
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.base / "launches"))
        result = subprocess.run(["/bin/zsh", str(LAUNCHER), "task", "start", "--cwd", str(self.workspace),
                                 "--tool", "codex-cli", "--action", "direct", "--reference", str(self.workspace / "missing.png")],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("builtin cd ", result.stdout)
        self.assertFalse(self.capture.exists())
        self.assertFalse((self.base / "launches").exists())

    def test_deleted_image_before_launch_prevents_agent_start(self):
        image = self.workspace / "将删除.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        request = self.base / "request.json"
        request.write_text(json.dumps({"version": 1, "cwd": str(self.workspace), "tool": "codex-cli",
                           "references": [str(image)], "task": "等待用户", "handoff_id": None,
                           "mode": "reference-start"}, ensure_ascii=False), encoding="utf-8")
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.base / "launches"))
        prepared = json.loads(self.call("task", "prepare", "--request", request, env=env).stdout)
        image.unlink()
        env.update(AI_HERE_TASK_PROMPT_FILE=prepared["prompt_file"], AI_HERE_TASK_REQUEST_FILE=prepared["request_file"])
        result = subprocess.run(["/bin/zsh", str(LAUNCHER), "codex-cli", str(self.workspace)],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("builtin cd ", result.stdout)
        self.assertFalse(self.capture.exists())

    def desktop_test_env(self):
        home = self.base / "fake home"
        (home / "Library" / "Logs").mkdir(parents=True)
        clipboard = self.base / "clipboard"
        clipboard.write_text("保持既有剪贴板", encoding="utf-8")
        self.stub("pbcopy", '#!/bin/sh\ncat > "$CLIPBOARD_CAPTURE"\n')
        self.stub("open", '#!/usr/bin/python3\nimport json, os, sys\n'
                          'open(os.environ["CAPTURE"], "w").write(json.dumps(sys.argv[1:]))\n')
        # Purpose-built test stubs exercise URL construction, never a real app.
        self.stub("mdfind", '#!/bin/sh\nprintf "/fake/Supported.app\\n"\n')
        env = dict(self.env, HOME=str(home), AI_HERE_TASK_STORE=str(self.base / "launches"),
                   CLIPBOARD_CAPTURE=str(clipboard))
        env.pop("AI_HERE_DRY_RUN")
        return env, clipboard, home / "Library" / "Logs" / "ai-here.log"

    def test_desktop_short_prefill_encodes_exact_text_without_clipboard(self):
        prompt = self.base / "短提示 &?#+ ' \".md"
        text = "准确预填：中文 & ? # + ' \"\n$(touch DESKTOP_EXECUTED)"
        prompt.write_text(text, encoding="utf-8")
        env, clipboard, log = self.desktop_test_env()
        env["AI_HERE_TASK_PROMPT_FILE"] = str(prompt)
        for tool, scheme, field in (("codex-app", "codex", "prompt"), ("claude-app", "claude", "q")):
            self.call(tool, self.workspace, env=env)
            args = json.loads(self.capture.read_text())
            self.assertEqual(len(args), 1)
            parsed = urlparse(args[0])
            self.assertEqual(parsed.scheme, scheme)
            self.assertEqual(parsed.netloc, "new" if scheme == "codex" else "code")
            query = parse_qs(parsed.query)
            self.assertEqual(query[field], [text])
            self.assertEqual(query["path" if scheme == "codex" else "folder"], [str(self.workspace)])
            self.assertFalse({"send", "autostart", "file", "action"}.intersection(query))
            self.assertLessEqual(len(args[0].encode("utf-8")), 8192)
        self.assertEqual(clipboard.read_text(), "保持既有剪贴板")
        self.assertNotIn(text, log.read_text(encoding="utf-8"))
        self.assertFalse((self.workspace / "DESKTOP_EXECUTED").exists())

    def test_desktop_direct_and_summary_refs_request_prefill_without_paste(self):
        reference = self.workspace / "附件 &?#+ ' \" 中文.md"
        reference.write_text("本地材料", encoding="utf-8")
        env, clipboard, log = self.desktop_test_env()
        for tool in ("codex-app", "claude-app", "workbuddy"):
            for action in ("direct", "summary"):
                result = self.call("task", "start", "--cwd", self.workspace, "--tool", tool,
                                   "--action", action, "--source", "finder", "--reference", reference, env=env)
                url = json.loads(self.capture.read_text())[0]
                query = parse_qs(urlparse(url).query)
                field = "q" if tool == "claude-app" else "prompt"
                path_field = {"codex-app": "path", "claude-app": "folder", "workbuddy": "cwd"}[tool]
                self.assertEqual(query[path_field], [str(self.workspace)])
                saved = max((self.base / "launches").glob("*/request.json"), key=lambda path: path.stat().st_mtime_ns)
                request = json.loads(saved.read_text(encoding="utf-8"))
                self.assertEqual(request["references"], [str(reference)])
                full_prompt = (saved.parent / "prompt.md").read_text(encoding="utf-8")
                prefill = query[field][0]
                self.assertTrue(prefill == full_prompt or str(saved.parent / "prompt.md") in prefill)
                self.assertIn("输入框预填请求", result.stdout)
                self.assertIn("尚未确认预填成功", result.stdout)
                self.assertNotIn("粘贴", result.stdout)
                self.assertFalse({"autostart", "send", "file"}.intersection(query))
                self.assertLessEqual(len(url.encode("utf-8")), 8192)
                self.assertNotIn(full_prompt, log.read_text(encoding="utf-8"))
        self.assertEqual(clipboard.read_text(), "保持既有剪贴板")
        self.assertFalse((self.workspace / ".ai-here").exists())

    def test_long_desktop_task_uses_bootstrap_preserves_prompt_and_no_clipboard(self):
        request = self.base / "长请求.json"
        task = "正文不能写到链接或日志：" + "中文&?#+\n" * 1000
        env, clipboard, log = self.desktop_test_env()
        for tool in ("codex-app", "claude-app", "workbuddy"):
            request.write_text(json.dumps({"version": 1, "cwd": str(self.workspace), "tool": tool,
                               "references": [], "task": task, "handoff_id": None}, ensure_ascii=False), encoding="utf-8")
            result = self.call("task", "launch", "--request", request, env=env)
            url = json.loads(self.capture.read_text())[0]
            field = "q" if tool == "claude-app" else "prompt"
            prefill = parse_qs(urlparse(url).query)[field][0]
            saved = max((self.base / "launches").glob("*/prompt.md"), key=lambda path: path.stat().st_mtime_ns)
            self.assertIn(str(saved), prefill)
            self.assertIn("先读取", prefill)
            self.assertIn("未读取不能宣称", prefill)
            self.assertIn(task, saved.read_text(encoding="utf-8"))
            self.assertLessEqual(len(url.encode("utf-8")), 8192)
            self.assertNotIn(task, url)
            self.assertNotIn(task, result.stdout)
            self.assertNotIn(task, log.read_text(encoding="utf-8"))
        self.assertEqual(clipboard.read_text(), "保持既有剪贴板")

    def test_desktop_open_failure_keeps_snapshot_and_never_claims_prefill(self):
        env, clipboard, _ = self.desktop_test_env()
        self.stub("open", '#!/bin/sh\nexit 7\n')
        result = subprocess.run(["/bin/zsh", str(LAUNCHER), "task", "start", "--cwd", str(self.workspace),
                                 "--tool", "codex-app", "--action", "summary"], env=env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("任务快照已保留", result.stderr)
        self.assertEqual(len(list((self.base / "launches").glob("*/prompt.md"))), 1)
        self.assertNotIn("已发出", result.stdout)
        self.assertEqual(clipboard.read_text(), "保持既有剪贴板")

    def test_codex_no_task_preserves_legacy_workspace_open(self):
        result = self.call("codex-app", self.workspace)
        self.assertIn(" app ", result.stdout)
        self.assertIn(str(self.workspace).split("'")[0], result.stdout)
        self.assertNotIn("codex://", result.stdout)


if __name__ == "__main__":
    unittest.main()
