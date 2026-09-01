# Todo-list Agent

A pure-Python ADK agent that maintains a **per-session** todo list
using the ADK's `ToolContext.state` mechanism. The list survives
across multiple turns in the same conversation, so the user can
"add three tasks, mark one done, list the rest" all in one chat.

## Tools

All tools receive a `ToolContext` (injected by ADK) and read/write
the same session-scoped state dict.

| Tool | Purpose |
| --- | --- |
| `add_task(title, ctx)` | Append a task; auto-assigns an integer id. |
| `list_tasks(ctx, show_done=True)` | Return all tasks, optionally hiding completed ones. |
| `complete_task(ctx, task_id=None, title_match=None)` | Mark a task as done by id or substring. |
| `remove_task(ctx, task_id)` | Delete a task by id. |
| `clear_tasks(ctx)` | Empty the list. |

## How State Works Here

The agent uses two keys in `ctx.state`:

* `todo_list`   - list of `{"id", "title", "done", "uuid"}` dicts
* `todo_next_id` - monotonically increasing integer id counter

Because the state is **session-scoped**, a new browser session gets
a fresh empty list. If you need persistence, swap the state dict
for a database-backed implementation (see example 6 in this repo).

## Project Structure

```
24-todo-list-agent/
└── todo_list_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + stateful tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **todo_list_agent** from the dropdown.

## Example Prompts to Try

- "Add 'Buy groceries' and 'Finish ADK homework' to my list."
- "Mark task #2 as done."
- "What is still pending?"
- "Remove 'Buy groceries' from the list."
- "Clear everything."
