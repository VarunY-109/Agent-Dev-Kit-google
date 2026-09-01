# Code Execution Agent

A pure-Python ADK agent that can **write and run short Python
snippets** in a restricted sandbox to answer computational questions
("what is the standard deviation of these numbers?", "compute the
Fibonacci sequence up to n=10", etc.).

## How the Sandbox Works

The `run_python` tool:

1. Compiles the code inside a **whitelisted global namespace** that
   only exposes a small set of safe builtins and pure-stdlib modules
   (`math`, `statistics`, `random`, `datetime`, `json`, `re`).
2. Redirects `stdout` so anything the code prints is captured.
3. Evaluates the **last expression** in the snippet and returns its
   value alongside the captured stdout.
4. Refuses obviously dangerous calls (`open(`, `subprocess`, `exec(`,
   `eval(`, `__import__`, `socket`, `urllib`, ...).

> This is a **teaching sandbox**, not a security boundary. Don't point
> it at untrusted users in production. For real isolation use
> `subprocess` + `RestrictedPython`, Docker, or a remote kernel.

## Project Structure

```
14-code-execution-agent/
└── code_execution_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + sandbox tool
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate   # macOS/Linux
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **code_execution_agent** from the dropdown.

## Example Prompts to Try

- "Compute the first 10 prime numbers and print them."
- "What is the mean, median, and standard deviation of 3, 7, 8, 12, 19?"
- "Parse the string '2026-09-01' and tell me which day of the week it is."
- "Generate 5 random integers between 1 and 100 and sort them ascending."
