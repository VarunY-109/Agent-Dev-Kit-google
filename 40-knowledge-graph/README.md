# Knowledge Graph Agent

A pure-Python ADK agent that maintains an in-session
**subject-predicate-object (SPO) graph** with neighbour lookups
and shortest-path queries.

## Tools

| Tool | Purpose |
| --- | --- |
| `add_entity(ctx, name, type_="thing")` | Insert an entity. |
| `add_relation(ctx, subject, predicate, object)` | Insert an edge. |
| `list_entities(ctx, type_="")` | Browse nodes. |
| `list_relations(ctx, predicate="")` | Browse edges. |
| `neighbours(ctx, name, depth=1)` | Forward + backward BFS up to N hops. |
| `shortest_path(ctx, src, dst)` | BFS shortest path. |
| `clear_graph(ctx)` | Wipe the graph. |

## Quick Example

```text
add_entity: "Alice", "person"
add_entity: "Acme",   "company"
add_relation: "Alice", "works_at", "Acme"
shortest_path: "Alice" -> "Acme"
   -> found=True, length=1
```

## Project Structure

```
40-knowledge-graph/
└── knowledge_graph_agent/
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
