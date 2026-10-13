import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ENGINE = Path(__file__).resolve().parents[1] / "lib" / "handoff.py"
SPEC = importlib.util.spec_from_file_location("handoff", ENGINE)
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ai-here-test-")
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, command, *options, body=None, ok=True, root=None):
        result = subprocess.run([sys.executable, str(ENGINE), command, str(root or self.root)] + list(options), input=body, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def add(self, title="测试任务", body="已验证：测试。\n", **kwargs):
        return self.run_cli("add", "--title", title, "--agent", "Codex", "--body-file", "-", body=body, **kwargs)

    def test_init_preserves_user_files_and_is_idempotent(self):
        agents = self.root / "AGENTS.md"
        agents.write_text("# 既有规则\n请用中文。\n", encoding="utf-8")
        self.run_cli("init", "--instructions")
        index = self.root / ".ai-here" / "index.md"
        original = index.read_text(encoding="utf-8").replace("## 当前目标（手工维护）", "## 当前目标（手工维护）\n\n交付用户项目。")
        index.write_text(original, encoding="utf-8")
        instructions = agents.read_bytes()
        self.run_cli("init", "--instructions")
        self.assertEqual(index.read_text(encoding="utf-8"), original)
        self.assertEqual(agents.read_bytes(), instructions)
        self.assertTrue(instructions.startswith("# 既有规则".encode()))
        self.assertIn(".lock", (index.parent / ".gitignore").read_text())

    def test_stdin_preserves_dangerous_shell_characters(self):
        text = "验证\n$(touch /tmp/ai-here-never-execute)\n`rm -rf nowhere`; $HOME ' \" \\ \n"
        result = self.add(title="任务 `echo nope` [带括号]", body=text)
        path = Path(result.stdout.strip())
        self.assertIn(text.rstrip(), path.read_text(encoding="utf-8"))
        self.assertIn("任务", self.run_cli("show", "latest").stdout)
        self.assertIn(path.stem, self.run_cli("list").stdout)
        self.assertIn("读取工作空间", self.run_cli("prompt").stdout)

    def test_noninteractive_requires_title_agent_and_body(self):
        self.run_cli("add", "--agent", "Codex", "--body-file", "-", body="正文", ok=False)
        self.run_cli("add", "--title", "题", "--agent", "Codex", ok=False)
        self.add(body="  \n", ok=False)
        self.assertFalse((self.root / ".ai-here").exists())

    def test_body_file_and_record_metadata(self):
        source = self.root / "body with spaces.md"
        source.write_text("提交：123456；检查通过。", encoding="utf-8")
        result = self.run_cli("add", "--title", "完成", "--agent", "ChatGPT", "--status", "completed", "--session", "https://example.com/session", "--body-file", str(source))
        record = handoff.records(self.root)[0]
        self.assertEqual(record["meta"]["status"], "completed")
        self.assertEqual(record["meta"]["session"], "https://example.com/session")
        self.assertIn("提交：123456", record["body"])
        self.assertIn(record["meta"]["id"], result.stdout)

    def test_parallel_add_and_recent_limit(self):
        processes = [subprocess.Popen([sys.executable, str(ENGINE), "add", str(self.root), "--title", "任务{}".format(i), "--agent", "Codex", "--body-file", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(24)]
        for process in processes:
            stdout, stderr = process.communicate("完成并行任务。")
            self.assertEqual(process.returncode, 0, stderr)
            self.assertTrue(Path(stdout.strip()).exists())
        self.assertEqual(len(handoff.records(self.root)), 24)
        index = (self.root / ".ai-here" / "index.md").read_text(encoding="utf-8")
        self.assertEqual(index.count("](handoffs/"), 20)
        self.assertEqual(len(self.run_cli("list").stdout.splitlines()), 24)

    def test_manual_deletion_and_bad_metadata_are_reconciled(self):
        old = Path(self.add(title="将删除").stdout.strip())
        retained = Path(self.add(title="保留").stdout.strip())
        old.unlink()
        corrupt = retained.parent / "broken.md"
        corrupt.write_text("<!-- ai-here-metadata: null -->\n无效\n", encoding="utf-8")
        listing = self.run_cli("list")
        self.assertIn("跳过记录", listing.stderr)
        self.assertNotIn(old.stem, listing.stdout)
        self.run_cli("init")
        index = (retained.parent.parent / "index.md").read_text(encoding="utf-8")
        self.assertNotIn(old.stem, index)
        self.assertIn(retained.stem, index)

    def test_export_budget_and_evidence(self):
        self.add(body="证据：file.py:10\n" + "很多内容。" * 2000)
        result = self.run_cli("export", "--max-chars", "1000").stdout
        self.assertLessEqual(len(result), 1000)
        self.assertIn("字符预算", result)
        self.assertIn(str(self.root), result)
        self.assertIn("来源：", result)

    def test_broken_index_keeps_appended_record(self):
        self.run_cli("init")
        index = self.root / ".ai-here" / "index.md"
        index.write_text("用户手工内容\n", encoding="utf-8")
        result = self.add(ok=False)
        self.assertIn("交接记录已保留", result.stderr)
        self.assertEqual(len(handoff.records(self.root)), 1)
        self.assertEqual(index.read_text(encoding="utf-8"), "用户手工内容\n")

    def test_export_reconciles_deleted_and_edited_records_without_writing(self):
        deleted = Path(self.add(title="将删除的旧任务").stdout.strip())
        edited = Path(self.add(title="正在维护的任务").stdout.strip())
        index = edited.parent.parent / "index.md"
        before = index.read_bytes()
        deleted.unlink()
        first, body = edited.read_text(encoding="utf-8").split("\n", 1)
        meta = json.loads(first[len(handoff.META):-4])
        meta["status"] = "completed"
        edited.write_text(handoff.META + json.dumps(meta, ensure_ascii=False) + " -->\n" + body, encoding="utf-8")
        exported = self.run_cli("export").stdout
        self.assertNotIn(deleted.stem, exported)
        self.assertNotIn("将删除的旧任务", exported)
        self.assertNotIn("· active", exported)
        self.assertIn("· completed", exported)
        self.assertIn("文件修改：", exported)
        self.assertEqual(index.read_bytes(), before)

    def test_atomic_update_detects_editor_conflict(self):
        self.run_cli("init")
        index = self.root / ".ai-here" / "index.md"
        old = index.read_bytes()
        index.write_text("编辑器的新内容\n", encoding="utf-8")
        with self.assertRaises(handoff.HandoffError):
            handoff.atomic_update(index, old, "自动生成内容", self.root)
        self.assertEqual(index.read_text(encoding="utf-8"), "编辑器的新内容\n")
        self.assertEqual(list(index.parent.glob(".*.tmp")), [])

    def test_instruction_marker_corruption_is_not_overwritten(self):
        agents = self.root / "AGENTS.md"
        agents.write_text("用户内容\n" + handoff.INSTRUCTION_START + "\n", encoding="utf-8")
        before = agents.read_bytes()
        self.run_cli("init", "--instructions", ok=False)
        self.assertEqual(agents.read_bytes(), before)

    def test_symlink_write_and_record_traversal_are_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".ai-here").symlink_to(outside, target_is_directory=True)
        self.run_cli("init", ok=False)
        self.assertEqual(list(outside.iterdir()), [])
        (self.root / ".ai-here").unlink()
        (self.root / "AGENTS.md").symlink_to(outside / "rules.md")
        self.run_cli("init", "--instructions", ok=False)
        self.assertFalse((outside / "rules.md").exists())
        self.run_cli("show", "../../outside", ok=False)

    def test_symlink_index_and_lock_are_rejected(self):
        self.run_cli("init")
        index = self.root / ".ai-here" / "index.md"
        target = self.root / "keep.md"
        target.write_text("保持内容", encoding="utf-8")
        index.unlink()
        index.symlink_to(target)
        self.add(ok=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "保持内容")
        index.unlink()
        lock = index.parent / ".lock"
        lock.unlink()
        lock.symlink_to(target)
        self.run_cli("init", ok=False)
        self.assertEqual(target.read_text(encoding="utf-8"), "保持内容")

    def test_gitignore_nested_repository_is_idempotent(self):
        (self.root / ".git").mkdir()
        ignore = self.root / ".gitignore"
        ignore.write_text("node_modules/\n", encoding="utf-8")
        nested = self.root / "sub workspace"
        nested.mkdir()
        self.run_cli("init", "--ignore", root=nested)
        before = ignore.read_bytes()
        self.run_cli("init", "--ignore", root=nested)
        self.assertEqual(ignore.read_bytes(), before)
        self.assertIn("/sub\\ workspace/.ai-here/", before.decode())
        self.assertTrue(before.startswith(b"node_modules/\n"))


if __name__ == "__main__":
    unittest.main()
