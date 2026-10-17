"""Context snapshots must remain explicit, shell-safe and outside project files."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "lib" / "task_request.py"
HANDOFF = ROOT / "lib" / "handoff.py"


class TaskRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ai-here-task-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.cwd = self.base / "中文 工作空间 ' $(touch BAD) `echo nope`"
        self.cwd.mkdir()
        self.store = self.base / "private launches"
        self.env = dict(os.environ, AI_HERE_TASK_STORE=str(self.store))
        self.env.pop("AI_HERE_DRY_RUN", None)
        self.env.pop("AI_HERE_LAUNCHER", None)
        self.request = self.base / "input.json"

    def run_cli(self, *args, ok=True, env=None, engine=ENGINE):
        result = subprocess.run([sys.executable, str(engine), *map(str, args)],
                                capture_output=True, text=True, env=env or self.env)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def write_request(self, **changes):
        request = {"version": 1, "cwd": str(self.cwd), "references": [], "task": "检查安装流程。",
                   "tool": "codex-cli", "handoff_id": None, "source": "finder"}
        request.update(changes)
        self.request.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        return self.request

    def prepare(self, **changes):
        return json.loads(self.run_cli("prepare", "--request", self.write_request(**changes)).stdout)

    def add_record(self, title, body="已完成；核验测试通过。"):
        result = subprocess.run([sys.executable, str(HANDOFF), "add", str(self.cwd),
                                 "--title", title, "--agent", "Codex", "--status", "completed",
                                 "--body-file", "-"], input=body, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return Path(result.stdout.strip())

    def test_context_no_handoff_does_not_write_workspace(self):
        reference = self.cwd / "参考材料.md"
        reference.write_text("原始材料", encoding="utf-8")
        before = {str(path.relative_to(self.cwd)): path.read_bytes() for path in self.cwd.rglob("*") if path.is_file()}
        result = json.loads(self.run_cli("context", "--cwd", self.cwd, "--reference", reference).stdout)
        self.assertEqual(result, {"cwd": str(self.cwd), "references": [str(reference)], "records": [], "warnings": []})
        self.prepare(references=[str(reference)])
        after = {str(path.relative_to(self.cwd)): path.read_bytes() for path in self.cwd.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertFalse((self.cwd / ".ai-here").exists())

    def test_unicode_private_snapshot_and_shell_text(self):
        task = "请检查 🌍\n$(touch BAD)\n`touch BAD`; ' \" $HOME\\\n"
        result = self.prepare(task=task)
        prompt = Path(result["prompt_file"])
        request = Path(result["request_file"])
        self.assertIn(task, prompt.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(request.read_text(encoding="utf-8"))["task"], task)
        self.assertEqual(result["prompt"], prompt.read_text(encoding="utf-8"))
        for path in (prompt, request):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        for path in (prompt.parent, self.store):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertFalse((self.cwd / "BAD").exists())
        self.assertFalse((self.base / "BAD").exists())

    def test_references_relative_deduplicated_and_outside_read_only(self):
        inside = self.cwd / "文档.md"
        inside.write_text("输入", encoding="utf-8")
        outside = self.base / "外部资料.md"
        outside.write_text("另外的输入", encoding="utf-8")
        result = self.prepare(task="", references=["文档.md", str(inside), str(outside)])
        self.assertEqual(result["references"], [str(inside), str(outside)])
        self.assertIn("不授权修改", result["prompt"])

    def test_selected_record_only_and_snapshot_is_fixed(self):
        selected = self.add_record("指定旧任务", "只属于指定记录的证据。")
        other = self.add_record("最新无关任务", "无关内容不能混入提示。")
        before = (self.cwd / ".ai-here" / "index.md").read_bytes()
        result = self.prepare(task="", handoff_id=selected.stem)
        self.assertIn("只属于指定记录的证据", result["prompt"])
        self.assertNotIn(other.stem, result["prompt"])
        self.assertNotIn("无关内容", result["prompt"])
        self.assertEqual(result["handoff_id"], selected.stem)
        selected.write_text("已被修改", encoding="utf-8")
        self.assertIn("只属于指定记录的证据", Path(result["prompt_file"]).read_text(encoding="utf-8"))
        self.assertEqual((self.cwd / ".ai-here" / "index.md").read_bytes(), before)

    def test_latest_handoff_not_automatically_selected(self):
        selected = self.add_record("不能默认加入", "不应进入提示")
        result = self.prepare()
        self.assertNotIn(selected.stem, result["prompt"])
        self.assertNotIn("不应进入提示", result["prompt"])

    def test_context_limits_records_and_skips_corrupt_and_symlink(self):
        for i in range(22):
            self.add_record("任务 {}".format(i))
        folder = self.cwd / ".ai-here" / "handoffs"
        (folder / "bad.md").write_text("损坏记录", encoding="utf-8")
        outside = self.base / "outside.md"
        outside.write_text("不可信记录", encoding="utf-8")
        (folder / "linked.md").symlink_to(outside)
        result = self.run_cli("context", "--cwd", self.cwd)
        payload = json.loads(result.stdout)
        records = payload["records"]
        self.assertEqual(len(records), 20)
        self.assertTrue(all("跳过记录" in warning for warning in payload["warnings"]))
        self.assertEqual(len(payload["warnings"]), 2)
        self.assertEqual(result.stderr, "")
        for record in records:
            self.assertEqual(set(record), {"id", "title", "agent", "created_at", "status", "label", "preview"})

    def test_missing_reference_and_record_fail_before_snapshot(self):
        self.run_cli("prepare", "--request", self.write_request(references=[str(self.cwd / "missing.md")]), ok=False)
        self.run_cli("prepare", "--request", self.write_request(handoff_id="20261013T120000123456Z-123456abcdef"), ok=False)
        self.assertFalse(self.store.exists())
        self.assertFalse((self.cwd / ".ai-here").exists())

    def test_bad_record_id_and_empty_task_fail(self):
        for changes in ({"handoff_id": "../../file"}, {"handoff_id": "latest"}, {"task": " \n"},
                        {"tool": "codex-cli;touch BAD"}, {"version": True}, {"references": "file.md"},
                        {"task": "x" * 20001}):
            with self.subTest(changes=list(changes)):
                self.run_cli("prepare", "--request", self.write_request(**changes), ok=False)
        self.assertFalse(self.store.exists())

    def test_symlink_store_and_ancestor_are_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.store.symlink_to(outside, target_is_directory=True)
        result = self.run_cli("prepare", "--request", self.write_request(), ok=False)
        self.assertIn("符号链接", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        env = dict(self.env, AI_HERE_TASK_STORE=str(self.store / "nested"))
        self.run_cli("prepare", "--request", self.write_request(), ok=False, env=env)
        self.assertEqual(list(outside.iterdir()), [])

    def test_snapshot_store_cannot_write_or_chmod_workspace(self):
        before = stat.S_IMODE(self.cwd.stat().st_mode)
        for store in (self.cwd, self.cwd / "launches", self.cwd.parent):
            result = self.run_cli("prepare", "--request", self.write_request(), ok=False,
                                  env=dict(self.env, AI_HERE_TASK_STORE=str(store)))
            self.assertIn("工作空间之外", result.stderr)
        self.assertEqual(list(self.cwd.iterdir()), [])
        self.assertEqual(stat.S_IMODE(self.cwd.stat().st_mode), before)

    def test_default_private_store_supports_home_workspace(self):
        fake_home = self.base / "fake home"
        fake_home.mkdir()
        before_mode = stat.S_IMODE(fake_home.stat().st_mode)
        request = self.write_request(cwd=str(fake_home))
        env = dict(self.env)
        env.pop("AI_HERE_TASK_STORE")
        harness = ("import runpy, sys\nfrom pathlib import Path\nfrom unittest.mock import patch\n"
                   "engine, fake_home, request = sys.argv[1:]\n"
                   "sys.path.insert(0, str(Path(engine).parent))\n"
                   "sys.argv = [engine, 'prepare', '--request', request]\n"
                   "with patch('pathlib.Path.home', return_value=Path(fake_home)):\n"
                   "    runpy.run_path(engine, run_name='__main__')\n")
        result = subprocess.run([sys.executable, "-c", harness, str(ENGINE), str(fake_home), str(request)],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        prepared = json.loads(result.stdout)
        expected_store = fake_home / "Library" / "Application Support" / "AIHere" / "launches"
        self.assertEqual(Path(prepared["prompt_file"]).parent.parent, expected_store)
        self.assertTrue(Path(prepared["prompt_file"]).is_file())
        self.assertFalse((fake_home / ".ai-here").exists())
        self.assertEqual(stat.S_IMODE(fake_home.stat().st_mode), before_mode)
        # The same path explicitly requested as a store keeps the stricter policy.
        explicit_env = dict(env, AI_HERE_TASK_STORE=str(expected_store))
        self.run_cli("prepare", "--request", request, env=explicit_env, ok=False)

    def test_unreadable_handoff_tree_is_hard_failure_not_uninitialized(self):
        outside = self.base / "memory"
        outside.mkdir()
        (outside / "index.md").write_text("外部索引", encoding="utf-8")
        (self.cwd / ".ai-here").symlink_to(outside, target_is_directory=True)
        result = self.run_cli("context", "--cwd", self.cwd, ok=False)
        self.assertEqual(result.stdout, "")
        self.assertIn("符号链接", result.stderr)
        self.run_cli("prepare", "--request", self.write_request(), ok=False)
        self.assertFalse(self.store.exists())

    def test_invalid_index_is_hard_failure(self):
        memory = self.cwd / ".ai-here"
        memory.mkdir()
        index = memory / "index.md"
        index.mkdir()
        result = self.run_cli("context", "--cwd", self.cwd, ok=False)
        self.assertIn("不是普通文件", result.stderr)
        index.rmdir()
        index.write_bytes(b"\xff\xfe")
        result = self.run_cli("context", "--cwd", self.cwd, ok=False)
        self.assertIn("无法读取工作交接", result.stderr)

    def test_prompt_utf8_budget_marks_truncated_record(self):
        selected = self.add_record("长交接", "中文🙂" * 40000)
        result = self.prepare(task="🙂" * 20000, handoff_id=selected.stem)
        self.assertLessEqual(len(result["prompt"].encode("utf-8")), 120 * 1024)
        self.assertIn("达到启动提示字节预算", result["prompt"])
        self.assertIn(str(selected), result["prompt"])
        self.assertIn("## 核验与写回", result["prompt"])

    def launcher(self, exit_code=0):
        path = self.base / "launcher script"
        path.write_text("#!{}\nimport json, os, sys\nfrom pathlib import Path\n"
                        "Path(os.environ['CAPTURE']).write_text(json.dumps({{'argv':sys.argv[1:], 'prompt':os.environ['AI_HERE_TASK_PROMPT_FILE']}}))\n"
                        "print('已复制提示，需要粘贴')\nsys.exit({})\n".format(sys.executable, exit_code), encoding="utf-8")
        path.chmod(0o755)
        capture = self.base / "capture.json"
        return dict(self.env, AI_HERE_LAUNCHER=str(path), CAPTURE=str(capture)), capture

    def test_launch_uses_argv_and_snapshot_env(self):
        env, capture = self.launcher()
        result = self.run_cli("launch", "--request", self.write_request(task="$(touch BAD)"), env=env)
        saved = json.loads(capture.read_text())
        self.assertEqual(saved["argv"], ["codex-cli", str(self.cwd)])
        self.assertIn("$(touch BAD)", Path(saved["prompt"]).read_text(encoding="utf-8"))
        self.assertIn("已发出启动请求", result.stdout)
        self.assertIn("需要粘贴", result.stdout)

    def test_dry_run_does_not_claim_actual_launch(self):
        env, capture = self.launcher()
        env["AI_HERE_DRY_RUN"] = "enabled"
        result = self.run_cli("launch", "--request", self.write_request(), env=env)
        self.assertIn("已准备启动预览", result.stdout)
        self.assertNotIn("已发出启动请求；", result.stdout)
        self.assertTrue(Path(json.loads(capture.read_text())["prompt"]).exists())

    def test_desktop_launch_reports_prefill_request_and_user_send(self):
        env, _ = self.launcher()
        for tool in ("claude-app", "codex-app", "workbuddy"):
            result = self.run_cli("launch", "--request", self.write_request(tool=tool), env=env)
            self.assertIn("输入框预填请求", result.stdout)
            self.assertIn("点击发送", result.stdout)
            self.assertIn("尚未确认预填成功", result.stdout)
            self.assertNotIn("已复制完整提示", result.stdout)
            self.assertNotIn("粘贴提示", result.stdout)

    def test_failed_launch_retains_recovery_snapshot(self):
        env, _ = self.launcher(exit_code=7)
        result = self.run_cli("launch", "--request", self.write_request(), env=env, ok=False)
        self.assertIn("任务快照已保留", result.stderr)
        self.assertIn("request.json", result.stderr)
        self.assertIn("prompt.md", result.stderr)
        self.assertEqual(len(list(self.store.glob("*/prompt.md"))), 1)

    def test_missing_launcher_still_retains_snapshot(self):
        result = self.run_cli("launch", "--request", self.write_request(), ok=False)
        self.assertIn("未配置 AI_HERE_LAUNCHER", result.stderr)
        self.assertIn("任务快照已保留", result.stderr)
        self.assertEqual(len(list(self.store.glob("*/request.json"))), 1)

    def installed_engine(self, with_skill=True):
        installed = self.base / "installed AIHere"
        library = installed / "lib"
        library.mkdir(parents=True)
        engine = library / "task_request.py"
        engine.write_bytes(ENGINE.read_bytes())
        (library / "handoff.py").write_bytes(HANDOFF.read_bytes())
        if with_skill:
            skill = installed / "skills" / "ai-here-handoff" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_bytes((ROOT / "skills" / "ai-here-handoff" / "SKILL.md").read_bytes())
        return engine

    def test_summary_missing_skill_fails_before_snapshot_or_launch(self):
        engine = self.installed_engine(with_skill=False)
        env, capture = self.launcher()
        result = self.run_cli("summarize", "--cwd", self.cwd, "--tool", "codex-cli", env=env,
                              engine=engine, ok=False)
        self.assertIn("缺少内置总结技能", result.stderr)
        self.assertFalse(capture.exists())
        self.assertFalse(self.store.exists())
        self.assertFalse((self.cwd / ".ai-here").exists())

    def test_summary_source_skill_private_snapshot_without_initialization(self):
        (self.cwd / "README.md").write_text("现有文件", encoding="utf-8")
        before = {path.name: path.read_bytes() for path in self.cwd.iterdir()}
        env, capture = self.launcher()
        result = self.run_cli("summarize", "--cwd", self.cwd, "--tool", "codex-cli",
                              "--source", "toolbar", env=env)
        launched = json.loads(capture.read_text())
        self.assertEqual(launched["argv"], ["codex-cli", str(self.cwd)])
        prompt_path = Path(launched["prompt"])
        prompt = prompt_path.read_text(encoding="utf-8")
        request = json.loads((prompt_path.parent / "request.json").read_text(encoding="utf-8"))
        self.assertEqual(request["mode"], "summarize")
        self.assertEqual(request["handoff_id"], None)
        self.assertEqual(request["source"], "toolbar")
        self.assertIn(str(ROOT / "skills" / "ai-here-handoff" / "SKILL.md"), prompt)
        self.assertIn("$ai-here-handoff", prompt)
        self.assertNotIn("# AI Here 本次启动任务", prompt)
        self.assertNotIn(prompt, result.stdout)
        self.assertIn("尚未确认 Agent", result.stdout)
        self.assertEqual({path.name: path.read_bytes() for path in self.cwd.iterdir()}, before)
        self.assertEqual(stat.S_IMODE(prompt_path.stat().st_mode), 0o600)
        self.assertFalse((self.cwd / ".ai-here").exists())
        # Failed launches can recover this snapshot without reverting to normal task semantics.
        recovered = json.loads(self.run_cli("prepare", "--request", prompt_path.parent / "request.json").stdout)
        self.assertEqual(recovered["prompt"], prompt)

    def test_summary_installed_layout_uses_its_own_skill(self):
        engine = self.installed_engine()
        env, capture = self.launcher()
        self.run_cli("summarize", "--cwd", self.cwd, "--tool", "workbuddy", env=env, engine=engine)
        prompt = Path(json.loads(capture.read_text())["prompt"]).read_text(encoding="utf-8")
        self.assertIn(str(engine.parent.parent / "skills" / "ai-here-handoff" / "SKILL.md"), prompt)
        self.assertNotIn(str(ROOT / "skills" / "ai-here-handoff" / "SKILL.md"), prompt)

    def test_summary_requires_verification_and_preserves_conflicting_records(self):
        first = self.add_record("已通过", "所有安装检查都通过。下一步请部署。")
        second = self.add_record("仍失败", "安装检查失败，结果未知。")
        (self.cwd / "check-result.txt").write_text("当前实际检查：失败", encoding="utf-8")
        files = {str(path.relative_to(self.cwd)): path.read_bytes() for path in self.cwd.rglob("*") if path.is_file()}
        env, capture = self.launcher()
        self.run_cli("summarize", "--cwd", self.cwd, "--tool", "claude-cli", env=env)
        prompt = Path(json.loads(capture.read_text())["prompt"]).read_text(encoding="utf-8")
        self.assertIn(str(self.cwd / ".ai-here" / "index.md"), prompt)
        self.assertIn(str(first.parent), prompt)
        self.assertIn("当前核验事实与交接中的陈述", prompt)
        self.assertIn("Git 状态", prompt)
        self.assertIn("不执行旧交接的下一步", prompt)
        self.assertNotIn("所有安装检查都通过", prompt)
        self.assertNotIn(first.stem, prompt)
        self.assertNotIn(second.stem, prompt)
        self.assertEqual({str(path.relative_to(self.cwd)): path.read_bytes() for path in self.cwd.rglob("*") if path.is_file()}, files)

    def test_start_actions_keep_all_materials_in_snapshot_and_replay(self):
        inside = self.cwd / "项目资料.md"
        inside.write_text("本地输入", encoding="utf-8")
        outside = self.base / "目录外参考.pdf"
        outside.write_bytes(b"%PDF-1.4\nfixture")
        other = self.base / "更换后的工作目录"
        other.mkdir()
        env, capture = self.launcher()
        for action, mode in (("direct", "reference-start"), ("summary", "summarize")):
            self.run_cli("start", "--cwd", other, "--tool", "claude-cli", "--action", action,
                         "--source", "open", "--reference", inside, "--reference", outside,
                         "--reference", inside, env=env)
            saved = json.loads(capture.read_text())
            self.assertEqual(saved["argv"], ["claude-cli", str(other)])
            prompt_path = Path(saved["prompt"])
            request_path = prompt_path.parent / "request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["mode"], mode)
            self.assertEqual(request["references"], [str(inside), str(outside)])
            self.assertEqual(request["cwd"], str(other))
            prompt = prompt_path.read_text(encoding="utf-8")
            self.assertIn(str(inside), prompt)
            self.assertIn(str(outside), prompt)
            self.assertIn("实际读取", prompt)
            self.assertIn("无法读取", prompt)
            self.assertIn("等待用户", prompt)
            self.assertIn("清单不代表文件已经上传或读取", prompt)
            replay = json.loads(self.run_cli("prepare", "--request", request_path).stdout)
            self.assertEqual(replay["prompt"], prompt)
            self.assertEqual(replay["references"], request["references"])
            self.assertFalse((other / ".ai-here").exists())

    def test_start_missing_material_never_launches_or_snapshots(self):
        env, capture = self.launcher()
        for action in ("direct", "summary"):
            result = self.run_cli("start", "--cwd", self.cwd, "--tool", "codex-cli", "--action", action,
                                  "--reference", self.cwd / "missing.png", env=env, ok=False)
            self.assertIn("路径不存在", result.stderr)
            self.assertFalse(capture.exists())
            self.assertFalse(self.store.exists())

    def test_start_direct_without_materials_keeps_legacy_no_snapshot(self):
        capture = self.base / "direct.json"
        launcher = self.base / "legacy launcher"
        launcher.write_text("#!{}\nimport json, os, sys\n"
                            "open(os.environ['CAPTURE'], 'w').write(json.dumps({{'args':sys.argv[1:], 'task':os.environ.get('AI_HERE_TASK_PROMPT_FILE')}}))\n"
                            .format(sys.executable), encoding="utf-8")
        launcher.chmod(0o755)
        env = dict(self.env, CAPTURE=str(capture), AI_HERE_LAUNCHER=str(launcher),
                   AI_HERE_TASK_PROMPT_FILE="stale")
        self.run_cli("start", "--cwd", self.cwd, "--tool", "claude-app", "--action", "direct", env=env)
        self.assertEqual(json.loads(capture.read_text()), {"args": ["claude-app", str(self.cwd)], "task": None})
        self.assertFalse(self.store.exists())

    def test_start_reference_limit_and_invalid_workspace_do_not_launch(self):
        env, capture = self.launcher()
        options = []
        for _ in range(101):
            options.extend(["--reference", str(self.cwd)])
        self.run_cli("start", "--cwd", self.cwd, "--tool", "codex-cli", "--action", "direct", *options,
                     env=env, ok=False)
        self.run_cli("start", "--cwd", self.cwd / "missing", "--tool", "codex-cli", "--action", "direct",
                     env=env, ok=False)
        self.assertFalse(capture.exists())
        self.assertFalse(self.store.exists())

    def test_desktop_prefill_limit_counts_percent_encoded_bytes(self):
        prompt = self.base / "短文件但编码后较长.md"
        text = "中" * 1000
        prompt.write_text(text, encoding="utf-8")
        self.assertLess(prompt.stat().st_size, 8192)
        for tool, field in (("codex-app", "prompt"), ("claude-app", "q")):
            result = self.run_cli("desktop-url", "--tool", tool, "--cwd", self.cwd, "--prompt-file", prompt)
            url = result.stdout.strip()
            prefill = parse_qs(urlparse(url).query)[field][0]
            self.assertLessEqual(len(url.encode("utf-8")), 8192)
            self.assertIn(str(prompt), prefill)
            self.assertNotIn(text, prefill)
            self.assertEqual(prompt.read_text(encoding="utf-8"), text)

    def test_desktop_prefill_rejects_missing_empty_and_nonfile_inputs(self):
        empty = self.base / "empty.md"
        empty.write_text("", encoding="utf-8")
        for prompt in (self.base / "missing.md", empty, self.cwd):
            self.run_cli("desktop-url", "--tool", "codex-app", "--cwd", self.cwd,
                         "--prompt-file", prompt, ok=False)
        self.assertFalse(self.store.exists())


if __name__ == "__main__":
    unittest.main()
