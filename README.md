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
