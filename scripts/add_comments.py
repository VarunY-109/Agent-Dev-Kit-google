#!/usr/bin/env python3
"""
Add Comments Agent - Adds AI-generated comments to Python files.
Usage: python add_comments.py <number_of_files>
"""
import os
import sys
import glob
import json
import subprocess
import time
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_INDEX_FILE = os.path.join(REPO_ROOT, ".file_index")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "minimax/minimax-m3:free"


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
        if rel == "add_comments.py":
            continue
        filtered.append(f)
    filtered.sort()
    return filtered


def call_openrouter(file_content, file_name):
    """Call OpenRouter API to add comments to Python code."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    prompt = f"""You are a Python code commentor. Add meaningful docstrings and inline comments to the following Python code.

Rules:
1. Add a module-level docstring at the top if not present
2. Add docstrings to all functions and classes
3. Add inline comments only where the logic is complex
4. Do NOT change any code logic, only add comments
5. Do NOT remove existing comments
6. Return ONLY the commented Python code, no explanations

File: {file_name}

Code:
```python
{file_content}
```"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8000,
    }

    max_retries = 3
    for attempt in range(max_retries):
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 429:
            wait_time = (attempt + 1) * 30
            print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
            time.sleep(wait_time)
            continue
        response.raise_for_status()
        break
    else:
        raise Exception("Max retries exceeded for OpenRouter API")

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    # Extract code from markdown block if present
    if "```python" in content:
        start = content.index("```python") + 9
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

    return content


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

            commented = call_openrouter(original, rel_path)

            if commented.strip() != original.strip():
                with open(file_path, "w") as f:
                    f.write(commented)

                did_commit = git_commit(rel_path)
                if did_commit:
                    committed_files.append(rel_path)
            else:
                pass

        except Exception as e:
            print(f"Error processing {rel_path}: {e}", file=sys.stderr)
            continue

        time.sleep(5)

    # Update file index
    new_index = (file_index + num_files) % len(py_files)
    with open(FILE_INDEX_FILE, "w") as f:
        f.write(str(new_index))

    # Output committed files for notification
    for f in committed_files:
        print(f)


if __name__ == "__main__":
    main()
