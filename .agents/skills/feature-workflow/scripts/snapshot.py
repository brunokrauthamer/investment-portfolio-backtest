"""Read-only identity for a feature's integrated repository snapshot (Python 3.9+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def path_name(name):
    return name.rsplit("/", 1)[-1]


def snapshot(root):
    root = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    paths = set(git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
    entries = []
    for raw in sorted(paths):
        if not raw:
            continue
        name = os.fsdecode(raw).replace("\\", "/")
        if name.startswith(("docs/tasks/", "docs/agent-log/")) and path_name(name) != "AGENTS.md":
            continue
        path = root / os.fsdecode(raw)
        try:
            info = path.lstat()
        except FileNotFoundError:
            entries.append({"path": name, "kind": "deleted"})
            continue
        if stat.S_ISLNK(info.st_mode):
            data = os.fsencode(os.readlink(path))
            kind = "symlink"
        elif stat.S_ISREG(info.st_mode):
            data = path.read_bytes()
            kind = "file"
        else:
            # Submodules and special files need explicit handling, never a partial identity.
            raise ValueError("Unsupported snapshot entry; establish its own identity: " + name)
        entries.append({
            "path": name, "kind": kind,
            "mode": stat.S_IMODE(info.st_mode),
            "sha256": hashlib.sha256(data).hexdigest()
        })
    head_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True
    )
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    payload = json.dumps(entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "head": head,
        "code_revision": (head or "unborn") + ":sha256:" + digest,
        "excluded_records": ["docs/tasks/", "docs/agent-log/"],
        "record_exceptions": ["AGENTS.md"],
        "files": entries
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="A path inside the Git repository")
    arguments = parser.parse_args()
    print(json.dumps(snapshot(arguments.root), indent=2, ensure_ascii=True))
