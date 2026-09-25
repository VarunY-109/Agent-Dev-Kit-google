#!/usr/bin/env python3
"""
Add Comments Agent - Adds timestamp comments to Python files.
Usage: python add_comments.py <number_of_files>
"""
import os
import sys
import glob
import subprocess
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_INDEX_FILE = os.path.join(REPO_ROOT, ".file_index")

IST = timezone(timedelta(hours=5, minutes=30))


def get_all_py_files():
    """Get all .py files excluding __init__.py, __pycache__, and scripts."""
    pattern = os.path.join(REPO_ROOT, "**", "*.py")
    all_files = glob.glob(pattern, recursive=True)
    filtered = []
    for f in all_files:
        rel = os.path.relpath(f, REPO_ROOT)
        if "__init__.py" in rel:
            continue
        if "__pycache__" in rel:
            continue
        if rel.startswith("scripts/"):
            continue
        filtered.append(f)
    filtered.sort()
    return filtered


def add_timestamp_comment(file_content):
    """Add or update timestamp comment at the top of the file."""
    now = datetime.now(IST).strftime("%Y-%m-%d %I:%M %p IST")
    timestamp_line = f"# Updated: {now}\n"

    lines = file_content.split("\n")

    # Remove existing timestamp line if present
    if lines and lines[0].startswith("# Updated:"):
        lines = lines[1:]

    # Add new timestamp at top
    lines.insert(0, timestamp_line.rstrip())

    return "\n".join(lines)


def git_commit(file_rel_path):
    """Stage and commit a single file."""
    subprocess.run(["git", "add", file_rel_path], cwd=REPO_ROOT, check=True)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", file_rel_path],
        cwd=REPO_ROOT
    )
    if result.returncode == 0:
        return False

    commit_msg = f"refactor: improve code documentation [skip ci]"
    subprocess.run(
        ["git", "commit", "-m", commit_msg, file_rel_path],
        cwd=REPO_ROOT, check=True
    )
    return True


def main():
    num_files = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    py_files = get_all_py_files()
    if not py_files:
        print("No Python files found.")
        sys.exit(1)

    # Read current index
    with open(FILE_INDEX_FILE, "r") as f:
        file_index = int(f.read().strip())

    committed_files = []

    for i in range(num_files):
        idx = (file_index + i) % len(py_files)
        file_path = py_files[idx]
        rel_path = os.path.relpath(file_path, REPO_ROOT)

        try:
            with open(file_path, "r") as f:
                original = f.read()

            updated = add_timestamp_comment(original)

            with open(file_path, "w") as f:
                f.write(updated)

            did_commit = git_commit(rel_path)
            if did_commit:
                committed_files.append(rel_path)

        except Exception as e:
            print(f"Error processing {rel_path}: {e}", file=sys.stderr)
            continue

    # Update file index
    new_index = (file_index + num_files) % len(py_files)
    with open(FILE_INDEX_FILE, "w") as f:
        f.write(str(new_index))

    # Output committed files for notification
    for f in committed_files:
        print(f)


if __name__ == "__main__":
    main()
