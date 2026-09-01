"""Resume Tailor Agent.

Compares a candidate's resume to a job description and produces a
detailed skill-gap report, a tailored bullet-point rewrite, and a
match score.
"""

import json
import re
from collections import Counter
from typing import Dict, List, Set

from google.adk.agents import Agent

_BULLET_RE = re.compile(r"^[\s\-\*\u2022]+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z+\-#\.]{1,}")


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with",
    "on", "at", "by", "from", "is", "are", "was", "were", "be", "as",
    "this", "that", "we", "you", "they", "i", "our", "your", "their",
    "have", "has", "had", "will", "would", "can", "could", "should",
    "may", "might", "do", "does", "did", "any", "all", "some", "no",
    "not", "but", "if", "then", "than", "so", "into", "out", "up",
    "down", "over", "under", "more", "most", "less", "least", "very",
    "just", "also", "such", "its", "it",
}

_TECH_HINTS = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++",
    "ruby", "swift", "kotlin", "scala", "sql", "nosql", "react", "vue",
    "angular", "node", "django", "flask", "fastapi", "spring", "rails",
    "aws", "gcp", "azure", "kubernetes", "docker", "terraform", "helm",
    "kafka", "spark", "hadoop", "airflow", "dbt", "snowflake", "bigquery",
    "redshift", "postgres", "mysql", "mongodb", "redis", "graphql",
    "rest", "grpc", "kafka", "pytorch", "tensorflow", "jax", "scikit",
    "pandas", "numpy", "llm", "rag", "agents", "langchain", "llamaindex",
    "mlops", "ci", "cd", "git", "github", "gitlab", "jira", "figma",
    "scrum", "agile", "kanban",
}


def extract_skills(text: str, top_n: int = 30) -> dict:
    """Return the most relevant technical skills mentioned in ``text``."""
    if not text or not text.strip():
        return {"status": "error", "error": "text is required."}
    tokens = _tokenize(text)
    found: Counter = Counter()
    for t in tokens:
        if t in _TECH_HINTS:
            found[t] += 1
    return {
        "status": "ok",
        "skills": [{"skill": s, "count": c} for s, c in found.most_common(top_n)],
    }


def _split_bullets(text: str) -> List[str]:
    bullets: List[str] = []
    for line in text.splitlines():
        s = _BULLET_RE.sub("", line).strip()
        if s:
            bullets.append(s)
    return bullets


def normalize_resume(resume_text: str) -> dict:
    """Return the resume's bullets and detected skills."""
    if not resume_text or not resume_text.strip():
        return {"status": "error", "error": "resume_text is required."}
    bullets = _split_bullets(resume_text)
    skills = extract_skills(resume_text).get("skills", [])
    return {
        "status": "ok",
        "bullet_count": len(bullets),
        "bullets": bullets,
        "skills": skills,
    }


def normalize_jd(jd_text: str) -> dict:
    """Return requirements and detected skills from a job description."""
    if not jd_text or not jd_text.strip():
        return {"status": "error", "error": "jd_text is required."}
    sentences = re.split(r"(?<=[.!?])\s+", jd_text.replace("\n", " "))
    must_have, nice_to_have = [], []
    for s in sentences:
        low = s.lower()
        if "must" in low or "required" in low or "minimum" in low:
            must_have.append(s.strip())
        elif any(k in low for k in ("nice to have", "preferred", "bonus", "plus")):
            nice_to_have.append(s.strip())
    return {
        "status": "ok",
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "skills": extract_skills(jd_text).get("skills", []),
    }


def match_score(resume_skills_json: str, jd_skills_json: str) -> dict:
    """Compute a 0-100 match score between two skill lists."""
    try:
        resume_skills = {s["skill"] for s in json.loads(resume_skills_json)}
        jd_skills = {s["skill"] for s in json.loads(jd_skills_json)}
    except (ValueError, TypeError, KeyError) as exc:
        return {"status": "error", "error": f"invalid input: {exc}"}
    if not jd_skills:
        return {"status": "error", "error": "JD has no detectable skills."}
    overlap = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    extra = resume_skills - jd_skills
    score = round(len(overlap) / len(jd_skills) * 100, 1)
    return {
        "status": "ok",
        "score": score,
        "matched": sorted(overlap),
        "missing": sorted(missing),
        "extra": sorted(extra),
    }


def keyword_coverage(resume_text: str, jd_text: str) -> dict:
    """Return which JD keywords appear (and how often) in the resume."""
    if not resume_text or not jd_text:
        return {"status": "error", "error": "both inputs required."}
    r_tokens = Counter(_tokenize(resume_text))
    jd_keywords = [w for w, c in Counter(_tokenize(jd_text)).most_common(40)
                   if w not in _STOPWORDS and len(w) > 2]
    coverage = []
    for kw in jd_keywords:
        coverage.append({"keyword": kw, "resume_hits": r_tokens.get(kw, 0)})
    return {"status": "ok", "coverage": coverage}


def action_verbs(text: str) -> dict:
    """List the strongest action verbs used in the resume's bullets."""
    VERBS = {
        "led", "built", "designed", "shipped", "launched", "reduced",
        "increased", "cut", "saved", "migrated", "implemented",
        "delivered", "scaled", "mentored", "owned", "drove", "architected",
        "optimised", "optimized", "refactored", "automated", "negotiated",
        "authored", "founded", "recruited", "trained", "presented",
        "researched", "analysed", "analyzed", "spearheaded", "orchestrated",
    }
    verbs = []
    for line in _split_bullets(text):
        first = line.split(maxsplit=1)[0].lower().strip(",.;:") if line else ""
        if first in VERBS:
            verbs.append(first)
    return {
        "status": "ok",
        "verb_counts": dict(Counter(verbs).most_common()),
        "unique_strong_verbs": sorted(set(verbs)),
    }


root_agent = Agent(
    name="resume_tailor_agent",
    model="gemini-2.0-flash",
    description=(
        "Compares a resume against a job description and produces "
        "a skill-gap report with a match score and tailored bullets."
    ),
    instruction="""
    You are a senior technical recruiter and resume coach.

    WORKFLOW:
    1. Call `normalize_resume` and `normalize_jd` on the user's
       inputs to extract structured skills and bullets.
    2. Call `match_score` to compute an overall match percentage.
    3. Call `keyword_coverage` to find under-represented JD terms.
    4. Call `action_verbs` to grade the resume's verb strength.

    DELIVERABLES (in this order):
    a) Match score (0-100) with a one-line interpretation.
    b) Skill-gap list: "You have X but the JD asks for Y" - sorted
       by impact.
    c) Five rewritten resume bullets that:
        - Lead with a strong action verb
        - Quantify impact wherever the user provided a number
        - Naturally weave in 2-3 missing skills the user plausibly has
    d) Three concrete suggestions the user can implement today
       (e.g. "Add a 'Technologies' sidebar listing X, Y, Z").

    RULES:
    - Never fabricate experience; only rephrase what the user
       provided.
    - If match_score < 50, mention which "must-have" requirements
       the resume is missing.
    - Keep tone supportive and specific.
    """,
    tools=[
        extract_skills, normalize_resume, normalize_jd,
        match_score, keyword_coverage, action_verbs,
    ],
)
