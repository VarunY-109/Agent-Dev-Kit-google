# Changelog Generator Agent

A pure-Python ADK agent that turns a `git diff` (or a commit log)
into a **grouped, Markdown CHANGELOG entry** with impact score.

## Tools

| Tool | Purpose |
| --- | --- |
| `categorize(text)` | Map free-form text to a category. |
| `diff_stats(diff)` | File-level +/- line counts. |
| `parse_commits(log)` | Parse git log into structured commits. |
| `group_by_category(commits_json)` | Group & severity-sort. |
| `build_changelog(version, groups_json)` | Render Markdown. |
| `impact_score(stats_json)` | 0-100 impact rating. |

## Category Order

1. breaking
2. fix
3. perf
4. feature
5. refactor
6. docs
7. test
8. chore
9. other

## Project Structure

```
34-changelog-generator/
└── changelog_generator_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```

## Example Prompts

- "Generate a CHANGELOG entry for the last 10 commits."
- "Score the impact of this diff and write release notes."
- "Group my commits by category and render a Markdown block."
