import json
import subprocess
import sys
from pathlib import Path


def git(*args):
    return subprocess.run(["git", *args], text=True, capture_output=True)


def main():
    event = json.load(sys.stdin)
    root = git("rev-parse", "--show-toplevel")
    if root.returncode:
        raise RuntimeError("Cannot locate the project repository.")
    import os
    os.chdir(root.stdout.strip())
    path = "docs/agent-log/LOG.md"
    if not Path(path).is_file():
        return
    staged = git("diff", "--cached", "--quiet", "--", path)
    if staged.returncode != 0:
        raise RuntimeError("The log has staged changes; commit them manually to preserve the staged version.")
    status = git("status", "--porcelain", "--", path)
    if status.returncode:
        raise RuntimeError("Cannot inspect the log's Git status.")
    if not status.stdout.strip():
        return
    added = git("add", "-N", "--", path)
    if added.returncode:
        raise RuntimeError("Cannot prepare the log for a commit.")
    result = git("commit", "--only", "-m", "docs: update agent interaction log", "--", path)
    if result.returncode:
        raise RuntimeError("Could not commit the log; check Git identity, permissions, and repository state.")


try:
    main()
    print("{}")
except Exception as exc:
    print(json.dumps({"systemMessage": "Agent log commit skipped: " + str(exc)}))
