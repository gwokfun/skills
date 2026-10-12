"""Observable persistence and failure boundaries in disposable projects."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[2] / "skills/in-progress/project-specs/scripts/store.py"
SPEC = importlib.util.spec_from_file_location("project_specs_store", SCRIPT)
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


class ProjectSpecsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="matt-project-specs-")
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / "docs/agents").mkdir(parents=True)
        (self.repo / "docs/agents/workflow.md").write_text("Project spec maintenance: enabled\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src/feature.py").write_bytes(b"verified implementation\n")
        self.source = {"schema_version": 1, "body": "# Published spec\n\nKeep fixed model pins.\n",
                       "source": {"tracker": "github", "ref": "https://github.com/fixture/repo/issues/1",
                                  "revision": "source-v1", "observed_at": "2026-10-13T00:00:00Z",
                                  "approval_basis": "seams-confirmed"}}

    def capture(self, packet=None, **kwargs):
        return store.capture(self.repo, "model-pins", "spec", packet or self.source, **kwargs)

    def packet(self, **kwargs):
        result = {"schema_version": 1, "capability": "initialization", "update": "pass-1",
                  "writer": "integration", "observed_at": "2026-10-13T00:00:00Z",
                  "expected_sha256": None, "spec_revision": None,
                  "body": "# Initialization\n\nFixed models remain unchanged.\n",
                  "verification": [{"check": "actual fixture observation", "result": "passed"}],
                  "implementation": {"src/feature.py": store.sha((self.repo / "src/feature.py").read_bytes())},
                  "deviations": []}
        result.update(kwargs)
        return result

    def tree(self):
        return {str(p.relative_to(self.repo)): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}

    def test_disabled_mode_has_zero_writes(self):
        (self.repo / "docs/agents/workflow.md").write_text("Project spec maintenance: disabled\n", encoding="utf-8")
        before = self.tree()
        with self.assertRaisesRegex(store.Conflict, "not enabled"):
            self.capture()
        with self.assertRaisesRegex(store.Conflict, "not enabled"):
            store.reconcile(self.repo, "model-pins", self.packet())
        self.assertEqual(before, self.tree())

    def test_remote_capture_is_immutable_idempotent_and_records_actual_approval(self):
        self.assertEqual(self.capture()["status"], "saved")
        before = self.tree()
        repeated = copy.deepcopy(self.source)
        repeated["source"]["observed_at"] = "2026-10-14T00:00:00Z"
        self.assertEqual(self.capture(repeated)["status"], "unchanged")
        self.assertEqual(before, self.tree())
        record, body, _ = store.decode(self.repo / "docs/changes/model-pins/spec.md")
        self.assertEqual(body, self.source["body"])
        self.assertEqual(record["source"]["approval_basis"], "seams-confirmed")
        self.assertEqual(record["source"]["observed_at"], self.source["source"]["observed_at"])
        ticket = copy.deepcopy(self.source)
        ticket["body"] = "# Ticket 2\n"
        ticket["source"].update(ref="https://gitlab.example/owner/repo/-/issues/2", tracker="gitlab", approval_basis="breakdown-approved")
        store.capture(self.repo, "model-pins", "ticket", ticket, ticket="issue-2")
        self.assertTrue((self.repo / "docs/changes/model-pins/tickets/issue-2.md").exists())

    def test_drift_requires_new_approved_revision_and_original_remains(self):
        self.capture()
        original = (self.repo / "docs/changes/model-pins/spec.md").read_bytes()
        revised = copy.deepcopy(self.source)
        revised["body"] = "# Changed published behavior\n"
        for options in ({}, {"check_only": True}, {"revision": "r2"}):
            with self.assertRaises(store.Conflict):
                self.capture(revised, **options)
        revised["source"]["approval_basis"] = "body-approved"
        self.capture(revised, revision="r2")
        self.assertEqual(original, (self.repo / "docs/changes/model-pins/spec.md").read_bytes())
        self.capture(revised, revision="r2", check_only=True)

    def test_local_source_is_saved_completely_and_stale_packet_is_rejected(self):
        path = self.repo / ".scratch/pins/spec.md"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"# Local spec\r\n\r\nKeep pins.\r\n")
        packet = copy.deepcopy(self.source)
        packet["body"] = path.read_bytes().decode()
        packet["source"].update(tracker="local", ref=".scratch/pins/spec.md")
        self.capture(packet)
        self.assertEqual(store.decode(self.repo / "docs/changes/model-pins/spec.md")[1], packet["body"].replace("\r\n", "\n"))
        path.write_bytes(b"# Later local edit\n")
        with self.assertRaisesRegex(store.Conflict, "differs"):
            self.capture(packet, check_only=True)

    def test_reconcile_checks_basis_expected_version_and_history(self):
        self.capture()
        packet = self.packet()
        self.assertEqual(store.reconcile(self.repo, "model-pins", packet)["status"], "reconciled")
        store.check(self.repo, "model-pins", "initialization", "pass-1")
        before = self.tree()
        self.assertEqual(store.reconcile(self.repo, "model-pins", packet)["status"], "unchanged")
        self.assertEqual(before, self.tree())
        changed = self.packet(update="pass-2", body="# New verified behavior\n")
        with self.assertRaisesRegex(store.Conflict, "version changed"):
            store.reconcile(self.repo, "model-pins", changed)
        self.assertFalse((self.repo / "docs/changes/model-pins/verification/initialization/pass-2.md").exists())
        changed["expected_sha256"] = store.fingerprint(self.repo / "docs/specs/initialization.md")
        store.reconcile(self.repo, "model-pins", changed)
        store.check(self.repo, "model-pins", "initialization", "pass-2")

    def test_code_or_document_edits_invalidate_the_review_basis(self):
        self.capture()
        store.reconcile(self.repo, "model-pins", self.packet())
        (self.repo / "src/feature.py").write_bytes(b"review fix\n")
        with self.assertRaisesRegex(store.Conflict, "Implementation changed"):
            store.check(self.repo, "model-pins", "initialization", "pass-1")
        with self.assertRaisesRegex(store.Conflict, "Implementation changed"):
            store.reconcile(self.repo, "model-pins", self.packet(implementation={"src/feature.py": "0" * 64}))
        (self.repo / "docs/specs/initialization.md").write_text("user-owned rewrite\n", encoding="utf-8")
        with self.assertRaisesRegex(store.Conflict, "provenance"):
            store.reconcile(self.repo, "model-pins", self.packet(expected_sha256=store.fingerprint(self.repo / "docs/specs/initialization.md")))

    def test_crlf_checkout_keeps_provenance_and_idempotence_valid(self):
        self.capture()
        packet = self.packet()
        store.reconcile(self.repo, "model-pins", packet)
        for path in self.repo.glob("docs/**/*.md"):
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.capture(check_only=True)
        store.check(self.repo, "model-pins", "initialization", "pass-1")
        self.assertEqual(store.reconcile(self.repo, "model-pins", packet)["status"], "unchanged")

    def test_partial_write_resumes_known_candidate_without_duplicate_content(self):
        self.capture()
        packet = self.packet()
        original = store.atomic_write

        def fail_capability(repo, relative, data, expected):
            if relative.startswith("docs/specs/"):
                raise OSError("simulated interruption")
            return original(repo, relative, data, expected)

        with patch.object(store, "atomic_write", side_effect=fail_capability):
            with self.assertRaisesRegex(OSError, "interruption"):
                store.reconcile(self.repo, "model-pins", packet)
        candidate = self.repo / "docs/changes/model-pins/verification/initialization/pass-1.md"
        saved = candidate.read_bytes()
        self.assertFalse((self.repo / "docs/specs/initialization.md").exists())
        self.assertFalse((self.repo / "docs/.project-specs.lock").exists())
        store.reconcile(self.repo, "model-pins", packet)
        self.assertEqual(saved, candidate.read_bytes())
        store.check(self.repo, "model-pins", "initialization", "pass-1")

    def test_locks_conflicts_and_unsafe_paths_do_not_overwrite_user_content(self):
        self.capture()
        lock = self.repo / "docs/.project-specs.lock"
        lock.write_text("live owner", encoding="utf-8")
        with self.assertRaisesRegex(store.Conflict, "Another writer"):
            store.reconcile(self.repo, "model-pins", self.packet())
        self.assertEqual(lock.read_text(), "live owner")
        lock.unlink()
        for unsafe in ("../escape", "x/y", "../outside.md", "UPPERCASE"):
            with self.assertRaises(store.Conflict):
                store.capture(self.repo, unsafe, "spec", self.source)
        self.assertFalse((self.repo / "docs/specs").exists())
        with self.assertRaisesRegex(store.Conflict, "verification"):
            store.reconcile(self.repo, "model-pins", self.packet(verification=[]))
        self.assertFalse((self.repo / "docs/specs").exists())

    def test_review_fix_needs_new_update_and_generated_output_cannot_be_basis(self):
        self.capture()
        store.reconcile(self.repo, "model-pins", self.packet())
        current = self.repo / "docs/specs/initialization.md"
        (self.repo / "src/feature.py").write_bytes(b"fixed verified implementation\n")
        stale_id = self.packet(body="# Fixed behavior\n", expected_sha256=store.fingerprint(current))
        with self.assertRaisesRegex(store.Conflict, "Immutable record differs"):
            store.reconcile(self.repo, "model-pins", stale_id)
        corrected = self.packet(update="pass-2", body="# Fixed behavior\n", expected_sha256=store.fingerprint(current))
        corrected["implementation"]["docs/specs/./initialization.md"] = store.fingerprint(current)
        with self.assertRaisesRegex(store.Conflict, "generated outputs"):
            store.reconcile(self.repo, "model-pins", corrected)
        corrected["implementation"].pop("docs/specs/./initialization.md")
        store.reconcile(self.repo, "model-pins", corrected)
        store.check(self.repo, "model-pins", "initialization", "pass-2")

    def test_cli_uses_the_same_activation_and_persistence_contract(self):
        packet = self.repo / "packet.json"
        packet.write_text(json.dumps(self.source), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "capture", "--repo", str(self.repo),
                                 "--change", "model-pins", "--kind", "spec", "--input", str(packet)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "saved")


if __name__ == "__main__":
    unittest.main()
