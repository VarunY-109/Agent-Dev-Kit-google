# Agent Development Kit (ADK) Crash Course

This repository contains examples for learning Google's Agent Development Kit (ADK), a powerful framework for building LLM-powered agents.

## Getting Started

### Setup Environment

You only need to create one virtual environment for all examples in this course. Follow these steps to set it up:

```bash
# Create virtual environment in the root directory
python -m venv .venv

# Activate (each new terminal)
# macOS/Linux:
source .venv/bin/activate
# Windows CMD:
.venv\Scripts\activate.bat
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

Once set up, this single environment will work for all examples in the repository.

### Setting Up API Keys

1. Create an account in Google Cloud https://cloud.google.com/?hl=en
2. Create a new project
3. Go to https://aistudio.google.com/apikey
4. Create an API key
5. Assign key to the project
6. Connect to a billing account

Each example folder contains a `.env.example` file. For each project you want to run:

1. Navigate to the example folder
2. Rename `.env.example` to `.env` 
3. Open the `.env` file and replace the placeholder with your API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

You'll need to repeat this for each example project you want to run.

## Examples Overview

Here's what you can learn from each example folder:

### 1. Basic Agent
Introduction to the simplest form of ADK agents. Learn how to create a basic agent that can respond to user queries.

### 2. Tool Agent
Learn how to enhance agents with tools that allow them to perform actions beyond just generating text.

### 3. LiteLLM Agent
Example of using LiteLLM to abstract away LLM provider details and easily switch between different models.

### 4. Structured Outputs
Learn how to use Pydantic models with `output_schema` to ensure consistent, structured responses from your agents.

### 5. Sessions and State
Understand how to maintain state and memory across multiple interactions using sessions.

### 6. Persistent Storage
Learn techniques for storing agent data persistently across sessions and application restarts.

### 7. Multi-Agent
See how to orchestrate multiple specialized agents working together to solve complex tasks.

### 8. Stateful Multi-Agent
Build agents that maintain and update state throughout complex multi-turn conversations.

### 9. Callbacks
Implement event callbacks to monitor and respond to agent behaviors in real-time.

### 10. Sequential Agent
Create pipeline workflows where agents operate in a defined sequence to process information.

### 11. Parallel Agent
Leverage concurrent operations with parallel agents for improved efficiency and performance.

### 12. Loop Agent
Build sophisticated agents that can iteratively refine their outputs through feedback loops.

### 13. RAG Agent
A retrieval-augmented generation agent that grounds its answers in an in-memory knowledge base using pure-Python cosine similarity.

### 14. Code Execution Agent
An agent that writes and runs short Python snippets inside a restricted sandbox to answer computational questions.

### 15. SQL Database Agent
Translates natural-language questions into read-only SQL queries against a local SQLite database and explains the results.

### 16. Web Scraping Agent
Fetches public web pages with `urllib`, strips them to readable text, and surfaces the most relevant paragraphs to the user.

### 17. Image Analysis Agent
A multimodal agent that can describe, OCR and analyse images uploaded through the ADK web UI or referenced by file path.

### 18. Weather Agent
Looks up the current weather and a short forecast for any city using the free, no-key Open-Meteo API.

### 19. Translator Agent
Translates text between 20+ languages and returns a structured Pydantic response (source, target, formality, notes).

### 20. Calculator Agent
Performs exact arithmetic, unit conversions and percentage calculations using Python's own `ast` parser.

### 21. YouTube Summarizer Agent
Fetches a YouTube video's transcript and produces a structured summary with timestamps.

### 22. PDF Reader Agent
Reads a local PDF, extracts its text and answers questions about its content (uses `pypdf`).

### 23. CSV Data Analyst Agent
Loads a local CSV file and answers analytical questions about it using pure-Python statistics.

### 24. Todo-list Agent
Maintains a per-session todo list that the user can add to, query, mark done, and clear across multiple turns.

### 25. Meeting Summarizer Agent
Parses a raw meeting transcript into a structured record (attendees, decisions, action items with owners + due dates, parking lot).

### 26. Stock Research Agent
Multi-source equity research: price snapshot + news sentiment + peer comparison, with a buy/hold/sell verdict.

### 27. Resume Tailor Agent
Compares a resume against a job description and produces a skill-gap report, keyword coverage and 5 rewritten bullets.

### 28. Trip Planner Agent
Builds a multi-city itinerary with day balance, budget check, and structured JSON output.

### 29. Diet Coach Agent
Computes a Mifflin-St Jeor calorie target, fills a single-day meal plan, and surfaces substitutions + a shopping list.

### 30. Code Reviewer Agent
Combines complexity, security, style, and duplication scans into a scored, prioritised review with fix suggestions.

### 31. Email Classifier Agent
Triages an inbox: category, priority score, action items, optional draft reply. Supports single + batch.

### 32. Investment Allocator Agent
Markowitz-lite rebalancer: drift vs target profile, buy/sell trade list, 0-100 risk score.

### 33. SQL Migrator Agent
Introspects a SQLite DB and emits PostgreSQL or MySQL DDL with type-conversion table and foreign-key plan.

### 34. Changelog Generator Agent
Turns a `git diff` or commit log into a grouped Markdown CHANGELOG entry with impact score.

### 35. Quiz Master Agent
Adaptive quiz with a Leitner-system spaced-repetition engine and per-session progress tracking.

### 36. Contract Analyzer Agent
Extracts parties, dates, obligations and risk flags from a contract, with a 0-100 risk score.

### 37. Lead Enricher Agent
Enriches a sparse lead (name + company) with industry guess, company size, tech-stack hints, news, and a 0-100 score.

### 38. Interview Coach Agent
Conducts a role-specific mock interview, scores answers against a rubric, and produces a report card.

### 39. Expense Auditor Agent
Audits a list of expenses against a policy, applies anomaly detection, and returns approve/reject/review decisions.

### 40. Knowledge Graph Agent
Maintains an in-session SPO graph with neighbour lookups and shortest-path queries.

### 41. A/B Test Analyzer Agent
Two-proportion z-test + 95% CI + Bayesian P(B>A) + sample-size calculator.

### 42. Content Moderator Agent
Three-signal moderation (toxicity, PII, policy keywords) with redaction and a 0-100 risk score.

### 43. Pantry-to-Recipe Agent
Suggests recipes from a built-in DB, lists missing ingredients, and groups them by store aisle.

### 44. System Incident Triage Agent
Clusters log lines by fingerprint, matches against a runbook library, and returns a root-cause hypothesis with confidence.

## Official Documentation

For more detailed information, check out the official ADK documentation:
- https://google.github.io/adk-docs/get-started/quickstart

## Support

Need help or run into issues? Join our free AI Developer Accelerator community on Skool:
- [AI Developer Accelerator Community](https://www.skool.com/ai-developer-accelerator/about)

In the community you'll find:
- Weekly coaching and support calls
- Early access to code from YouTube projects
- A network of AI developers of all skill levels ready to help
- Behind-the-scenes looks at how these apps are built
