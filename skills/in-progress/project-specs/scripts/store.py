"""Persist source snapshots and verified capability bodies without tracker mutations."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


class Conflict(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise Conflict("IDs must be lowercase letters, digits and hyphens (1-64 characters)")
    return value


def required_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise Conflict(f"Missing {name}")
    return value


def hash_value(value):
    if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)):
        raise Conflict("Expected SHA-256 or null")
    return value


def canonical(text):
    return text.replace("\r\n", "\n")


def target(repo, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(p == ".." or p.lower() == ".git" or ":" in p or "\\" in p for p in path.parts):
        raise Conflict(f"Invalid repository-relative file: {relative}")
    result = repo
    for part in path.parts:
        result /= part
        if result.is_symlink():
            raise Conflict(f"Symlink requires separate handling: {relative}")
    if not result.resolve().is_relative_to(repo):
        raise Conflict(f"Path escapes project: {relative}")
    if result.exists() and not result.is_file():
        raise Conflict(f"Expected regular file: {relative}")
    return result


def fingerprint(path):
    return sha(path.read_bytes()) if path.exists() else None


def encode(record, body):
    body = canonical(body)
    metadata = dict(record, schema_version=1, body_sha256=sha(body.encode("utf-8")))
    return ("---\n" + json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n---\n" + body).encode("utf-8")


def decode(path):
    raw = path.read_bytes()
    text = canonical(raw.decode("utf-8"))
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise Conflict(f"Missing project-specs provenance: {path}")
    metadata, body = text[4:].split("\n---\n", 1)
    record = json.loads(metadata)
    if record.get("schema_version") != 1 or record.get("body_sha256") != sha(body.encode("utf-8")):
        raise Conflict(f"Edited or unsupported project-specs record: {path}")
    return record, body, text.encode("utf-8")


def enabled(repo):
    workflow = target(repo, "docs/agents/workflow.md")
    if not workflow.exists() or "Project spec maintenance: enabled" not in workflow.read_text(encoding="utf-8-sig").splitlines():
        raise Conflict("Project spec maintenance is not enabled in docs/agents/workflow.md")


@contextmanager
def writer_lock(repo, owner):
    path = target(repo, "docs/.project-specs.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise Conflict("Another writer or stale lock exists; inspect docs/.project-specs.lock") from None
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"writer": owner, "pid": os.getpid()}, stream)
        yield
    finally:
        path.unlink()


def atomic_write(repo, relative, data, expected):
    path = target(repo, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".project-specs-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        path = target(repo, relative)
        if fingerprint(path) != expected:
            raise Conflict(f"File version changed: {relative}")
        if expected is None:
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise Conflict(f"File appeared during write: {relative}") from None
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def immutable(repo, relative, data):
    path = target(repo, relative)
    if path.exists():
        decode(path)
        if decode(path)[2] != data:
            raise Conflict(f"Immutable record differs: {relative}")
        return False
    atomic_write(repo, relative, data, None)
    return True


def artifact(change, kind, ticket=None, revision=None):
    root = f"docs/changes/{identifier(change)}"
    if revision:
        root += f"/revisions/{identifier(revision)}"
    if kind == "ticket":
        return root + f"/tickets/{identifier(ticket)}.md"
    return root + "/spec.md"


def source_packet(repo, packet):
    if packet.get("schema_version") != 1:
        raise Conflict("Unsupported source packet")
    body = canonical(required_text(packet.get("body"), "complete source body"))
    supplied = packet.get("source", {})
    if not isinstance(supplied, dict):
        raise Conflict("Expected source metadata object")
    source = {key: required_text(supplied.get(key), key) for key in (
        "tracker", "ref", "revision", "observed_at", "approval_basis")}
    if source["approval_basis"] not in ("seams-confirmed", "breakdown-approved", "body-approved", "not-recorded"):
        raise Conflict("Unknown approval basis")
    if source["tracker"] == "local":
        path = target(repo, source["ref"])
        if not path.exists() or canonical(path.read_bytes().decode("utf-8")) != body:
            raise Conflict("Local source is absent or differs from supplied body")
    elif source["tracker"] not in ("github", "gitlab") or not re.fullmatch(r"https://[^\s]+/issues/[^\s]+", source["ref"]):
        raise Conflict("Expected a known HTTPS issue reference or local source")
    return source, body


def capture(repo, change, kind, packet, ticket=None, revision=None, check_only=False):
    enabled(repo)
    relative = artifact(change, kind, ticket, revision)
    source, body = source_packet(repo, packet)
    if revision:
        decode(target(repo, artifact(change, kind, ticket)))
        if source["approval_basis"] != "body-approved":
            raise Conflict("A new body revision requires explicit body approval")
    path = target(repo, relative)
    if path.exists():
        record, previous, _ = decode(path)
        if record.get("kind") != kind or record.get("change") != change or record.get("source", {}).get("tracker") != source["tracker"] or record["source"].get("ref") != source["ref"] or previous != body:
            raise Conflict("Source drift or local conflict; preserve history and reconcile explicitly")
        return {"status": "unchanged", "paths": [relative]}
    if check_only:
        raise Conflict("Source snapshot is missing")
    data = encode({"kind": kind, "change": change, "source": source}, body)
    with writer_lock(repo, "capture"):
        immutable(repo, relative, data)
    return {"status": "saved", "paths": [relative]}


def implementation_basis(repo, basis, excluded):
    if not isinstance(basis, dict) or not basis:
        raise Conflict("Supply the implementation file hashes covered by verification")
    for relative, expected in basis.items():
        path = target(repo, relative)
        if path in [target(repo, name) for name in excluded]:
            raise Conflict("Implementation basis cannot include generated outputs or lock")
        if fingerprint(path) != hash_value(expected):
            raise Conflict(f"Implementation changed since verification: {relative}")


def reconciliation(repo, change, packet):
    if packet.get("schema_version") != 1:
        raise Conflict("Unsupported reconciliation packet")
    change = identifier(change)
    capability = identifier(packet.get("capability"))
    update = identifier(packet.get("update"))
    body = required_text(packet.get("body"), "complete capability body")
    writer = required_text(packet.get("writer"), "integration writer")
    observed = required_text(packet.get("observed_at"), "observation time")
    checks = packet.get("verification")
    if not isinstance(checks, list) or not checks or any(not isinstance(c, dict) or not c.get("check") or c.get("result") != "passed" for c in checks):
        raise Conflict("Reconciliation requires actual passing verification evidence")
    deviations = packet.get("deviations", [])
    if not isinstance(deviations, list) or any(not isinstance(d, str) for d in deviations):
        raise Conflict("Deviations must be a list of descriptions")
    spec_path = artifact(change, "spec", revision=packet.get("spec_revision"))
    spec, _, raw_spec = decode(target(repo, spec_path))
    if spec.get("kind") != "spec" or spec.get("change") != change:
        raise Conflict("Captured spec identity mismatch")
    capability_path = f"docs/specs/{capability}.md"
    history_path = f"docs/changes/{change}/verification/{capability}/{update}.md"
    basis = packet.get("implementation")
    implementation_basis(repo, basis, (capability_path, history_path, "docs/.project-specs.lock"))
    record = {"kind": "capability", "change": change, "capability": capability, "update": update,
              "writer": writer, "observed_at": observed, "spec": spec_path, "spec_sha256": sha(raw_spec),
              "verification": checks, "implementation": basis, "deviations": deviations,
              "expected_previous_sha256": hash_value(packet.get("expected_sha256"))}
    return capability_path, history_path, encode(record, body), record


def reconcile(repo, change, packet):
    enabled(repo)
    with writer_lock(repo, packet.get("writer", "unknown")):
        capability, history, data, record = reconciliation(repo, change, packet)
        current = target(repo, capability)
        if current.exists():
            decode(current)
        if current.exists() and decode(current)[2] == data:
            immutable(repo, history, data)
            return {"status": "unchanged", "paths": [history, capability]}
        if fingerprint(current) != record["expected_previous_sha256"]:
            raise Conflict("Capability version changed; reread, reconcile and review")
        immutable(repo, history, data)
        implementation_basis(repo, record["implementation"], (capability, history, "docs/.project-specs.lock"))
        atomic_write(repo, capability, data, record["expected_previous_sha256"])
    return {"status": "reconciled", "paths": [history, capability]}


def check(repo, change, capability, update):
    enabled(repo)
    capability = identifier(capability)
    update = identifier(update)
    change = identifier(change)
    current_path = f"docs/specs/{capability}.md"
    history_path = f"docs/changes/{change}/verification/{capability}/{update}.md"
    current, _, raw = decode(target(repo, current_path))
    previous, _, old_raw = decode(target(repo, history_path))
    if raw != old_raw or current.get("change") != change or current.get("capability") != capability or current.get("update") != update:
        raise Conflict("Verification candidate and current capability differ")
    spec, _, spec_raw = decode(target(repo, current["spec"]))
    if spec.get("kind") != "spec" or sha(spec_raw) != current["spec_sha256"]:
        raise Conflict("Captured spec changed since reconciliation")
    implementation_basis(repo, current["implementation"], (current_path, history_path, "docs/.project-specs.lock"))
    return {"status": "checked", "paths": [history_path, current_path]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "check-source", "reconcile", "check"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=Path, required=True)
        command.add_argument("--change", required=True)
        if name in ("capture", "check-source"):
            command.add_argument("--kind", choices=("spec", "ticket"), required=True)
            command.add_argument("--ticket")
            command.add_argument("--revision")
        if name == "check":
            command.add_argument("--capability", required=True)
            command.add_argument("--update", required=True)
        else:
            command.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        repo = args.repo.resolve(strict=True)
        if not repo.is_dir():
            raise Conflict("Expected existing project directory")
        if args.command == "check":
            result = check(repo, args.change, args.capability, args.update)
        else:
            packet = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                raise Conflict("Expected JSON packet object")
            if args.command == "reconcile":
                result = reconcile(repo, args.change, packet)
            else:
                result = capture(repo, args.change, args.kind, packet, args.ticket, args.revision, args.command == "check-source")
        print(json.dumps(result, ensure_ascii=False))
    except (Conflict, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Project specs stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
