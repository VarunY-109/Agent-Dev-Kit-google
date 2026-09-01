"""Changelog Generator Agent.

Turns a `git diff` (or a list of commit messages) into a
grouped, human-readable CHANGELOG entry with impact assessment.
"""

import json
import re
from collections import defaultdict
from typing import Dict, List

from google.adk.agents import Agent


_CATEGORY_PATTERNS = [
    ("breaking", re.compile(r"\b(break|breaking|removed?|incompatible|migrate)\b", re.I)),
    ("feature",  re.compile(r"\b(feat|feature|add|implement|introduce|new)\b", re.I)),
    ("fix",      re.compile(r"\b(fix|bug|patch|hotfix|resolve|repair)\b", re.I)),
    ("perf",     re.compile(r"\b(perf|performance|optimi[sz]e|speed|faster)\b", re.I)),
    ("docs",     re.compile(r"\b(docs?|readme|comment|typo)\b", re.I)),
    ("refactor", re.compile(r"\b(refactor|clean|rename|reorgani[sz]e|simplif)\b", re.I)),
    ("test",     re.compile(r"\b(test|spec|coverage|ci)\b", re.I)),
    ("chore",    re.compile(r"\b(chore|bump|upgrade|dependencies|deps)\b", re.I)),
]

_SEVERITY_RANK = {"breaking": 0, "fix": 1, "perf": 2, "feature": 3,
                  "refactor": 4, "docs": 5, "test": 6, "chore": 7, "other": 8}


def categorize(text: str) -> dict:
    """Map free-form text to a changelog category."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    scores = {cat: 0 for cat, _ in _CATEGORY_PATTERNS}
    for cat, pat in _CATEGORY_PATTERNS:
        scores[cat] += len(pat.findall(text))
    best = max(scores.items(), key=lambda kv: kv[1])
    label = best[0] if best[1] > 0 else "other"
    return {"status": "ok", "category": label, "scores": scores}


def diff_stats(diff: str) -> dict:
    """Return file-level +/- line counts for a unified diff."""
    if not diff or not diff.strip():
        return {"status": "error", "error": "diff is required."}
    files: Dict[str, Dict[str, int]] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].lstrip("b/").strip()
            files[current] = {"add": 0, "remove": 0}
        elif line.startswith("--- "):
            continue
        elif current is not None:
            if line.startswith("+") and not line.startswith("+++"):
                files[current]["add"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                files[current]["remove"] += 1
    total_add = sum(v["add"] for v in files.values())
    total_remove = sum(v["remove"] for v in files.values())
    return {
        "status": "ok",
        "file_count": len(files),
        "added": total_add,
        "removed": total_remove,
        "files": [{"path": k, **v} for k, v in files.items()],
    }


def parse_commits(commit_log: str) -> dict:
    """Parse a `git log` style list into structured commit objects.

    Input format (one per commit, blank line separated):
        abc1234
        Author: Alice <alice@example.com>
        Date:   2026-08-30
        Subject line

        Longer body...
    """
    if not commit_log or not commit_log.strip():
        return {"status": "error", "error": "commit_log is required."}
    commits: List[Dict] = []
    blocks = re.split(r"\n{2,}", commit_log.strip())
    for b in blocks:
        lines = b.splitlines()
        if not lines:
            continue
        sha = lines[0].strip()
        author = next((l[8:].strip() for l in lines if l.lower().startswith("author:")), "")
        date = next((l[5:].strip() for l in lines if l.lower().startswith("date:")), "")
        body = "\n".join(l for l in lines[1:] if not l.lower().startswith(("author:", "date:")))
        subject = body.splitlines()[0].strip() if body else ""
        rest = "\n".join(body.splitlines()[1:]).strip()
        commits.append({"sha": sha, "author": author, "date": date,
                        "subject": subject, "body": rest})
    return {"status": "ok", "count": len(commits), "commits": commits}


def group_by_category(commits_json: str) -> dict:
    """Group commits by inferred category and sort by severity."""
    try:
        commits = json.loads(commits_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(commits, list):
        return {"status": "error", "error": "expected a JSON list."}
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for c in commits:
        cat = categorize(f"{c.get('subject', '')} {c.get('body', '')}").get("category", "other")
        grouped[cat].append(c)
    ordered = sorted(grouped.items(), key=lambda kv: _SEVERITY_RANK.get(kv[0], 9))
    out = [{"category": k, "items": v, "count": len(v)} for k, v in ordered]
    return {"status": "ok", "groups": out, "total": sum(len(c["items"]) for c in out)}


def build_changelog(version: str, groups_json: str) -> dict:
    """Format grouped commits as a Markdown changelog entry."""
    try:
        groups = json.loads(groups_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    lines = [f"## [{version}] - {len(groups)} categories"]
    for g in groups:
        lines.append("")
        lines.append(f"### {g['category'].title()} ({g['count']})")
        for item in g["items"]:
            sha = item.get("sha", "")[:7]
            subj = item.get("subject", "").strip()
            lines.append(f"- {subj} (`{sha}`)")
    return {"status": "ok", "markdown": "\n".join(lines), "version": version}


def impact_score(diff_stats_json: str) -> dict:
    """Score the overall impact of a change set (0-100)."""
    try:
        stats = json.loads(diff_stats_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    files = stats.get("file_count", 0)
    add = stats.get("added", 0)
    rem = stats.get("removed", 0)
    churn = add + rem
    score = min(100, int((files * 2) + (churn * 0.3)))
    label = "high" if score >= 70 else "medium" if score >= 30 else "low"
    return {"status": "ok", "score": score, "label": label, "files": files, "churn": churn}


root_agent = Agent(
    name="changelog_generator_agent",
    model="gemini-2.0-flash",
    description=(
        "Turns a git diff or commit log into a grouped, "
        "human-readable Markdown CHANGELOG entry with impact score."
    ),
    instruction="""
    You are a release-notes writer.

    WORKFLOW:
    1. If the user provides a `git diff`, call `diff_stats` to
       size the change set and `impact_score` to rate it.
    2. If the user provides commit log, call `parse_commits`,
       then `group_by_category`.
    3. Call `build_changelog` with a sensible version label
       (today's date or the user's version string).
    4. Present: a 1-line headline (impact label + file/churn counts),
       the Markdown changelog in a fenced block, and 2-3 sentences
       of release-highlights prose.

    RULES:
    - Group by category, ordered: breaking > fix > perf > feature
       > refactor > docs > test > chore > other.
    - Never invent subjects; only use commit/diff text.
    - For breaking changes, call them out at the very top.
    """,
    tools=[
        categorize, diff_stats, parse_commits,
        group_by_category, build_changelog, impact_score,
    ],
)
