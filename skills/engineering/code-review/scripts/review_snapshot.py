"""Freeze explicit task files for review without changing Git's index or history."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys


class SnapshotError(Exception):
    pass


def git(repo, *args, data=None, accepted=(0,), literal=True):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_LITERAL_PATHSPECS="1" if literal else "0")
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            capture_output=True, env=env, timeout=30)
    if result.returncode not in accepted:
        raise SnapshotError(result.stderr.decode("utf-8", "replace").strip()
                            or f"Git exited with {result.returncode}")
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def task_path(repo, value):
    path = PurePosixPath(value.replace("\\", "/"))
    if (path.is_absolute() or not path.parts or any(
            part in ("..", ".") or part.lower() == ".git" or ":" in part
            for part in path.parts)):
        raise SnapshotError(f"Use an explicit repository-relative file: {value}")
    target = repo
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise SnapshotError(f"Symlinks require a separate review procedure: {value}")
    if not target.resolve().is_relative_to(repo):
        raise SnapshotError(f"Path escapes the repository: {value}")
    return path.as_posix(), target


def entries(repo, command, paths):
    found = {}
    for record in git(repo, *command, "--", *paths).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        fields = metadata.decode().split()
        name = path.decode("utf-8")
        if command[0] == "ls-files":
            mode, oid, stage = fields
            if stage != "0":
                raise SnapshotError(f"Unmerged task file: {name}")
        else:
            mode, _, oid = fields
        if mode not in ("100644", "100755"):
            raise SnapshotError(f"Only regular task files are supported: {name} ({mode})")
        found[name] = (mode, oid)
    return found


def observe(repo, base, paths):
    baseline = entries(repo, ("ls-tree", "-rz", base), paths)
    index = entries(repo, ("ls-files", "--stage", "-z"), paths)
    attributes = git(repo, "check-attr", "-z", "filter", "--", *paths).split(b"\0")
    for offset in range(0, len(attributes) - 1, 3):
        if attributes[offset + 2] not in (b"unspecified", b"unset"):
            raise SnapshotError("Custom Git filters require a separate review procedure")
    filemode = git(repo, "config", "--bool", "core.filemode", accepted=(0, 1)).strip() == b"true"
    records, contents = [], {}
    for name in paths:
        _, target = task_path(repo, name)
        if not target.exists():
            if name not in baseline:
                raise SnapshotError(f"Absent file has no baseline to review: {name}")
            records.append({"path": name, "mode": None, "sha256": None, "git_blob": None})
            continue
        if not target.is_file():
            raise SnapshotError(f"Select individual regular files: {name}")
        if name in baseline and name not in index:
            raise SnapshotError(f"Baseline file absent from index but present in worktree: {name}; separate review required")
        if name not in baseline and name not in index:
            ignored = git(repo, "check-ignore", "--no-index", "--", name, accepted=(0, 1), literal=False)
            if ignored:
                raise SnapshotError(f"Ignored untracked task file: {name}")
        content = target.read_bytes()
        mode = ("100755" if target.stat().st_mode & stat.S_IXUSR else "100644") if filemode else (
            index.get(name, baseline.get(name, ("100644", None)))[0])
        oid = git(repo, "hash-object", f"--path={name}", "--stdin", data=content).decode().strip()
        records.append({"path": name, "mode": mode, "sha256": digest(content), "git_blob": oid})
        contents[name] = content
    patch = git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary", "--full-index",
                "--no-renames", base, "--", *paths)
    for name in paths:
        if name not in baseline and name not in index and name in contents:
            patch += git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary", "--full-index",
                         "--no-index", "--", "/dev/null", name, accepted=(0, 1), literal=False)
    return records, contents, patch


def capture(repo, base, paths, output):
    repo = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    base = git(repo, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").decode().strip()
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    paths = sorted(set(task_path(repo, value)[0] for value in paths))
    output = output.resolve()
    if output.is_relative_to(repo) or output.exists():
        raise SnapshotError("Snapshot output must be a new directory outside the repository")
    first = observe(repo, base, paths)
    if not first[2]:
        raise SnapshotError("Empty task diff")
    if first != observe(repo, base, paths) or head != git(repo, "rev-parse", "HEAD").decode().strip():
        raise SnapshotError("Workspace changed during capture; start a fresh capture")
    records, contents, patch = first
    manifest = {"schema_version": 1, "repo": str(repo), "base": base, "head": head,
                "files": records, "patch_sha256": digest(patch)}
    manifest["snapshot_id"] = digest(encode(manifest))
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes(encode(manifest))
    (output / "review.patch").write_bytes(patch)
    for name, content in contents.items():
        destination = output / "files" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return manifest["snapshot_id"]


def check(repo, snapshot, index_check=False):
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    identifier = manifest.pop("snapshot_id")
    if manifest["schema_version"] != 1 or digest(encode(manifest)) != identifier:
        raise SnapshotError("Invalid snapshot manifest")
    repo = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if str(repo) != manifest["repo"] or git(repo, "rev-parse", "HEAD").decode().strip() != manifest["head"]:
        raise SnapshotError("Repository or HEAD changed since review")
    if digest((snapshot / "review.patch").read_bytes()) != manifest["patch_sha256"]:
        raise SnapshotError("Review patch changed")
    for record in manifest["files"]:
        name, _ = task_path(repo, record["path"])
        frozen = snapshot / "files" / name
        if record["sha256"] is not None and digest(frozen.read_bytes()) != record["sha256"]:
            raise SnapshotError(f"Frozen content changed: {name}")
        if record["sha256"] is None and frozen.exists():
            raise SnapshotError(f"Deleted snapshot file reappeared: {name}")
    paths = [record["path"] for record in manifest["files"]]
    current, _, _ = observe(repo, manifest["base"], paths)
    if current != manifest["files"]:
        raise SnapshotError("Task files changed since review; capture and review again")
    if index_check:
        index = entries(repo, ("ls-files", "--stage", "-z"), paths)
        for record in current:
            expected = None if record["mode"] is None else (record["mode"], record["git_blob"])
            if index.get(record["path"]) != expected:
                raise SnapshotError(f"Index differs from reviewed content: {record['path']}")
        staged = set(git(repo, "diff", "--cached", "--name-only", "-z", "--no-renames").decode().split("\0")) - {""}
        if staged - set(paths):
            raise SnapshotError("Unrelated staged paths exist; preserve them and resolve commit scope")
    return identifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    freeze = subcommands.add_parser("capture")
    freeze.add_argument("--repo", type=Path, required=True)
    freeze.add_argument("--base", required=True)
    freeze.add_argument("--path", action="append", required=True)
    freeze.add_argument("--output", type=Path, required=True)
    verify = subcommands.add_parser("check")
    verify.add_argument("--repo", type=Path, required=True)
    verify.add_argument("--snapshot", type=Path, required=True)
    verify.add_argument("--index", action="store_true")
    args = parser.parse_args()
    try:
        identifier = (capture(args.repo, args.base, args.path, args.output) if args.command == "capture"
                      else check(args.repo, args.snapshot, args.index))
        print(identifier)
    except (SnapshotError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"Snapshot check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
