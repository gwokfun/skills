"""Integration checks against disposable Git repositories, never the caller's index."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[2] / "skills/engineering/code-review/scripts/review_snapshot.py"
SPEC = importlib.util.spec_from_file_location("review_snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


class ReviewSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="matt-codex-review-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        environment = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            environment.pop(key, None)
        self.env = patch.dict(os.environ, environment, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.filemode", "false")
        for name in ("committed.txt", "staged.txt", "dirty.txt", "deleted.txt", "other.txt"):
            self.write(name, b"baseline\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "baseline")
        self.base = self.git("rev-parse", "HEAD").decode().strip()
        self.output = self.root / "review"

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True).stdout

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def capture(self, paths):
        return snapshot.capture(self.repo, self.base, paths, self.output)

    def test_freezes_all_task_states_without_mutating_git(self):
        self.write("committed.txt", b"committed change\n")
        self.git("add", "committed.txt")
        self.git("commit", "--quiet", "-m", "task commit")
        self.write("staged.txt", b"staged change\n")
        self.git("add", "staged.txt")
        self.write("dirty.txt", b"unstaged change\n")
        (self.repo / "deleted.txt").unlink()
        self.write("new folder/中文.txt", b"new task file\n")
        self.write("new.bin", b"\0\x01\xff")
        paths = ["committed.txt", "staged.txt", "dirty.txt", "deleted.txt", "new folder/中文.txt", "new.bin"]
        before = (self.git("status", "--porcelain=v1", "-z"), (self.repo / ".git/index").read_bytes(),
                  self.git("rev-parse", "HEAD"))
        identifier = self.capture(paths)
        after = (self.git("status", "--porcelain=v1", "-z"), (self.repo / ".git/index").read_bytes(),
                 self.git("rev-parse", "HEAD"))
        self.assertEqual(before, after)
        manifest = json.loads((self.output / "manifest.json").read_bytes())
        self.assertEqual(manifest["base"], self.base)
        self.assertEqual(set(paths), {entry["path"] for entry in manifest["files"]})
        frozen = (self.output / "review.patch").read_bytes()
        for change in (b"committed change", b"staged change", b"unstaged change", b"new task file"):
            self.assertIn(change, frozen)
        self.assertIn(b"deleted file mode", frozen)
        self.assertIn(b"GIT binary patch", frozen)
        self.assertEqual((self.output / "files/new.bin").read_bytes(), b"\0\x01\xff")
        self.assertEqual(identifier, snapshot.check(self.repo, self.output))
        self.git("add", "--", *paths)
        self.assertEqual(identifier, snapshot.check(self.repo, self.output, True))

    def test_invalidates_live_or_frozen_edits_and_head_changes(self):
        self.write("dirty.txt", b"reviewed\n")
        self.capture(["dirty.txt"])
        self.write("dirty.txt", b"later edit\n")
        with self.assertRaisesRegex(snapshot.SnapshotError, "changed since review"):
            snapshot.check(self.repo, self.output)
        self.write("dirty.txt", b"reviewed\n")
        (self.output / "files/dirty.txt").write_bytes(b"tampered\n")
        with self.assertRaisesRegex(snapshot.SnapshotError, "Frozen content changed"):
            snapshot.check(self.repo, self.output)
        (self.output / "files/dirty.txt").write_bytes(b"reviewed\n")
        (self.output / "review.patch").write_bytes(b"tampered")
        with self.assertRaisesRegex(snapshot.SnapshotError, "Review patch changed"):
            snapshot.check(self.repo, self.output)

    def test_requires_matching_index_and_preserves_unrelated_staged_work(self):
        self.write("dirty.txt", b"reviewed\n")
        self.capture(["dirty.txt"])
        with self.assertRaisesRegex(snapshot.SnapshotError, "Index differs"):
            snapshot.check(self.repo, self.output, True)
        self.git("add", "dirty.txt")
        snapshot.check(self.repo, self.output, True)
        self.write("other.txt", b"user staged work\n")
        self.git("add", "other.txt")
        index_before = (self.repo / ".git/index").read_bytes()
        with self.assertRaisesRegex(snapshot.SnapshotError, "Unrelated staged paths"):
            snapshot.check(self.repo, self.output, True)
        self.assertEqual(index_before, (self.repo / ".git/index").read_bytes())

    def test_crlf_worktree_matches_normalized_index(self):
        self.write(".gitattributes", b"*.txt text eol=crlf\n")
        self.git("add", ".gitattributes")
        self.git("commit", "--quiet", "-m", "attributes")
        self.base = self.git("rev-parse", "HEAD").decode().strip()
        self.write("dirty.txt", b"reviewed\r\n")
        self.capture(["dirty.txt"])
        self.git("add", "dirty.txt")
        snapshot.check(self.repo, self.output, True)

    def test_rejects_unsupported_and_unsafe_inputs_without_output(self):
        self.write(".gitignore", b"ignored.txt\n")
        self.write("ignored.txt", b"ignored\n")
        for paths in (["../outside.txt"], [".git/config"], ["absent.txt"], ["."], ["committed.txt"]):
            with self.subTest(paths=paths), self.assertRaises(snapshot.SnapshotError):
                self.capture(paths)
            self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(snapshot.SnapshotError, "Ignored untracked task file: ignored.txt"):
            self.capture(["ignored.txt"])
        self.assertFalse(self.output.exists())
        self.write("dirty.txt", b"reviewed\n")
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.capture(self.repo, self.base, ["dirty.txt"], self.repo / "snapshot")
        self.write(".gitattributes", b"dirty.txt filter=custom\n")
        with self.assertRaisesRegex(snapshot.SnapshotError, "Custom Git filters"):
            self.capture(["dirty.txt"])

    def test_detects_concurrent_capture_and_refuses_overwrite(self):
        self.write("dirty.txt", b"reviewed\n")
        real_observe = snapshot.observe
        calls = 0

        def concurrent(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.write("dirty.txt", b"concurrent edit\n")
            return real_observe(*args)

        with patch.object(snapshot, "observe", side_effect=concurrent):
            with self.assertRaisesRegex(snapshot.SnapshotError, "changed during capture"):
                self.capture(["dirty.txt"])
        self.assertFalse(self.output.exists())
        self.capture(["dirty.txt"])
        original = (self.output / "manifest.json").read_bytes()
        with self.assertRaises(snapshot.SnapshotError):
            self.capture(["dirty.txt"])
        self.assertEqual(original, (self.output / "manifest.json").read_bytes())

    def test_committed_tree_matches_reviewed_files_and_old_review_expires(self):
        self.write("dirty.txt", b"final artifact\n")
        (self.repo / "deleted.txt").unlink()
        self.write("new.txt", b"added artifact\n")
        paths = ["dirty.txt", "deleted.txt", "new.txt"]
        self.capture(paths)
        self.git("--literal-pathspecs", "add", "--", *paths)
        self.assertEqual(set(paths), set(self.git("diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""})
        snapshot.check(self.repo, self.output, True)
        self.git("commit", "--quiet", "-m", "reviewed task")
        manifest = json.loads((self.output / "manifest.json").read_bytes())
        tree = snapshot.entries(self.repo, ("ls-tree", "-rz", "HEAD"), paths)
        for entry in manifest["files"]:
            expected = None if entry["mode"] is None else (entry["mode"], entry["git_blob"])
            self.assertEqual(expected, tree.get(entry["path"]))
        self.assertEqual(set(paths), set(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").decode().splitlines()))
        with self.assertRaisesRegex(snapshot.SnapshotError, "HEAD changed"):
            snapshot.check(self.repo, self.output)

    def test_literal_filenames_and_empty_untracked_file(self):
        paths = ["empty.txt", "brackets[1].txt", "-leading.txt"]
        self.write("empty.txt", b"")
        self.write("brackets[1].txt", b"literal brackets\n")
        self.write("-leading.txt", b"literal dash\n")
        self.write("brackets1.txt", b"unrelated glob match\n")
        self.capture(paths)
        self.assertEqual((self.output / "files/empty.txt").read_bytes(), b"")
        frozen = (self.output / "review.patch").read_bytes()
        self.assertIn(b"empty.txt", frozen)
        self.assertNotIn(b"unrelated glob match", frozen)
        self.git("--literal-pathspecs", "add", "--", *paths)
        self.assertEqual(set(paths), set(self.git("diff", "--cached", "--name-only", "-z").decode().split("\0")) - {""})
        snapshot.check(self.repo, self.output, True)

    def test_refuses_index_deletion_with_retained_or_recreated_worktree_file(self):
        self.git("rm", "--cached", "dirty.txt")
        self.write("dirty.txt", b"retained task content\n")
        index_before = (self.repo / ".git/index").read_bytes()
        with self.assertRaisesRegex(snapshot.SnapshotError, "Baseline file absent from index but present in worktree"):
            self.capture(["dirty.txt"])
        self.assertFalse(self.output.exists())
        self.assertEqual(index_before, (self.repo / ".git/index").read_bytes())
        self.git("add", "dirty.txt")
        self.capture(["dirty.txt"])
        self.git("rm", "--cached", "dirty.txt")
        index_before = (self.repo / ".git/index").read_bytes()
        with self.assertRaisesRegex(snapshot.SnapshotError, "Baseline file absent from index but present in worktree"):
            snapshot.check(self.repo, self.output, True)
        self.assertEqual(index_before, (self.repo / ".git/index").read_bytes())


if __name__ == "__main__":
    unittest.main()
