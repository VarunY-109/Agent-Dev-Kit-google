"""Todo-list Agent.

A pure-Python ADK agent that maintains a per-session todo list using
the ADK's ``ToolContext.state`` mechanism. The list survives across
multiple turns in the same conversation and is exposed through five
small tools.

Tools (each receives a ``ToolContext``):
    * ``add_task``        - append a task to the list.
    * ``list_tasks``      - show all tasks (optionally filtered).
    * ``complete_task``   - mark a task as done by id or title.
    * ``remove_task``     - delete a task by id.
    * ``clear_tasks``     - empty the entire list.
"""

import uuid
from typing import Dict, List, Optional

from google.adk.agents import Agent
from google.adk.tools import ToolContext

_TODO_KEY = "todo_list"
_NEXT_ID_KEY = "todo_next_id"


def _get_state(ctx: ToolContext) -> Dict:
    """Return the mutable state dict from a ToolContext (any ADK version)."""
    state = getattr(ctx, "state", None)
    if state is None:
        raise RuntimeError("ToolContext.state is unavailable in this ADK version.")
    return state


def _get_list(state) -> List[Dict]:
    """Return the todo list (creating it if missing)."""
    return list(state.get(_TODO_KEY, []) or [])


def add_task(title: str, ctx: ToolContext) -> dict:
    """Add a task to the per-session todo list.

    Args:
        title: Short description of the task.
        ctx:   ADK ``ToolContext`` (injected automatically).
    """
    title = (title or "").strip()
    if not title:
        return {"status": "error", "error": "title cannot be empty."}
    if len(title) > 200:
        title = title[:200]

    state = _get_state(ctx)
    todos = _get_list(state)
    new_id = int(state.get(_NEXT_ID_KEY, 1) or 1)
    task = {
        "id": new_id,
        "title": title,
        "done": False,
        "uuid": uuid.uuid4().hex[:8],
    }
    todos.append(task)
    state[_TODO_KEY] = todos
    state[_NEXT_ID_KEY] = new_id + 1
    return {"status": "ok", "task": task, "total": len(todos)}


def list_tasks(ctx: ToolContext, show_done: bool = True) -> dict:
    """Return all tasks, optionally hiding completed ones."""
    state = _get_state(ctx)
    todos = _get_list(state)
    if not show_done:
        todos = [t for t in todos if not t.get("done")]
    return {
        "status": "ok",
        "count": len(todos),
        "tasks": todos,
    }


def complete_task(ctx: ToolContext, task_id: Optional[int] = None,
                  title_match: Optional[str] = None) -> dict:
    """Mark a task as done.

    Provide either ``task_id`` (preferred) or ``title_match``
    (case-insensitive substring).
    """
    state = _get_state(ctx)
    todos = _get_list(state)
    if not todos:
        return {"status": "error", "error": "The todo list is empty."}

    target = None
    if task_id is not None:
        for t in todos:
            if t.get("id") == int(task_id):
                target = t
                break
    elif title_match:
        needle = title_match.lower()
        for t in todos:
            if needle in t.get("title", "").lower():
                target = t
                break

    if not target:
        return {"status": "error", "error": "No matching task found."}

    target["done"] = True
    state[_TODO_KEY] = todos
    return {"status": "ok", "task": target}


def remove_task(ctx: ToolContext, task_id: int) -> dict:
    """Remove a task by id."""
    state = _get_state(ctx)
    todos = _get_list(state)
    before = len(todos)
    todos = [t for t in todos if t.get("id") != int(task_id)]
    if len(todos) == before:
        return {"status": "error", "error": f"No task with id={task_id}."}
    state[_TODO_KEY] = todos
    return {"status": "ok", "removed_id": int(task_id), "remaining": len(todos)}


def clear_tasks(ctx: ToolContext) -> dict:
    """Empty the todo list."""
    state = _get_state(ctx)
    removed = len(_get_list(state))
    state[_TODO_KEY] = []
    return {"status": "ok", "removed": removed}


root_agent = Agent(
    name="todo_list_agent",
    model="gemini-2.0-flash",
    description=(
        "Maintains a per-session todo list that the user can add "
        "to, query, mark done, and clear across multiple turns."
    ),
    instruction="""
    You are a personal task-tracking assistant.

    WORKFLOW:
    - "Add X" / "Remind me to X" / "I need to X" -> call `add_task`.
    - "What's on my list?" / "Show pending" -> call `list_tasks`
       (pass `show_done=False` if the user only wants open items).
    - "Done with #3" / "Mark X as complete" -> call `complete_task`
       with the id (preferred) or `title_match`.
    - "Remove #2" / "Delete X" -> call `remove_task`.
    - "Clear everything" -> call `clear_tasks` (confirm with the
       user before doing it).

    RULES:
    - The list lives in the session state, so it persists across
       turns. Use the same ToolContext.state for every tool call.
    - When listing, present tasks as a small numbered list with the
       id, title, and a [done] marker.
    - If the user's intent is ambiguous, ask a clarifying question
       before mutating the list.
    - Keep titles short (<= 80 chars); trim filler words.
    """,
    tools=[add_task, list_tasks, complete_task, remove_task, clear_tasks],
)
