# Resume Tailor Agent

A pure-Python ADK agent that compares a candidate's resume to a
specific job description and produces a structured report:
overall match score, skill gap, keyword coverage, action-verb
strength, and 5 rewritten resume bullets.

## Tools

| Tool | Purpose |
| --- | --- |
| `extract_skills(text)` | Pull a frequency-ranked list of tech skills. |
| `normalize_resume(text)` | Split bullets, return skills + bullet list. |
| `normalize_jd(text)` | Split must-have vs nice-to-have requirements. |
| `match_score(resume_skills, jd_skills)` | 0-100 match percentage. |
| `keyword_coverage(resume, jd)` | Per-keyword hit count. |
| `action_verbs(text)` | List strong action verbs used. |

## Project Structure

```
27-resume-tailor/
└── resume_tailor_agent/
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

- "Here's my resume. Tailor it for this job description: ..."
- "What am I missing for a Senior Python Engineer role?"
- "Rate my resume's action verbs and rewrite the weakest 3 bullets."
