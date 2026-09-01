"""Knowledge Graph Agent.

A small, in-memory subject-predicate-object (SPO) graph that lets
the user ingest entities and relations, query neighbours, and find
shortest paths between two entities.
"""

import json
import re
from collections import defaultdict, deque
from typing import Dict, List, Tuple

from google.adk.agents import Agent
from google.adk.tools import ToolContext


_GRAPH_KEY = "kg_store"


def _store(ctx: ToolContext) -> Dict:
    s = getattr(ctx, "state", None)
    if s is None:
        raise RuntimeError("ToolContext.state unavailable.")
    if _GRAPH_KEY not in s:
        s[_GRAPH_KEY] = {"entities": [], "relations": []}
    return s[_GRAPH_KEY]


_ENTITY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\- ]{0,60}$")


def add_entity(ctx: ToolContext, name: str, type_: str = "thing") -> dict:
    """Add an entity to the in-session knowledge graph."""
    name = (name or "").strip()
    if not _ENTITY_RE.match(name):
        return {"status": "error", "error": "invalid entity name."}
    store = _store(ctx)
    for e in store["entities"]:
        if e["name"].lower() == name.lower():
            return {"status": "ok", "deduplicated": True, "entity": e}
    e = {"name": name, "type": (type_ or "thing").lower()}
    store["entities"].append(e)
    return {"status": "ok", "entity": e, "count": len(store["entities"])}


def add_relation(ctx: ToolContext, subject: str, predicate: str,
                 obj: str) -> dict:
    """Add a directed relation subject -[predicate]-> object."""
    subject = (subject or "").strip()
    obj = (obj or "").strip()
    predicate = (predicate or "").strip().lower().replace(" ", "_")
    if not (_ENTITY_RE.match(subject) and _ENTITY_RE.match(obj) and predicate):
        return {"status": "error", "error": "invalid relation."}
    store = _store(ctx)
    names = {e["name"].lower() for e in store["entities"]}
    for n in (subject, obj):
        if n.lower() not in names:
            store["entities"].append({"name": n, "type": "thing"})
    rel = {"subject": subject, "predicate": predicate, "object": obj}
    store["relations"].append(rel)
    return {
        "status": "ok",
        "relation": rel,
        "relation_count": len(store["relations"]),
    }


def list_entities(ctx: ToolContext, type_: str = "") -> dict:
    """List all entities, optionally filtered by type."""
    store = _store(ctx)
    items = store["entities"]
    if type_:
        items = [e for e in items if e["type"] == type_.lower()]
    return {"status": "ok", "count": len(items), "items": items}


def list_relations(ctx: ToolContext, predicate: str = "") -> dict:
    """List all relations, optionally filtered by predicate."""
    store = _store(ctx)
    items = store["relations"]
    if predicate:
        items = [r for r in items if r["predicate"] == predicate.lower()]
    return {"status": "ok", "count": len(items), "items": items}


def neighbours(ctx: ToolContext, name: str, depth: int = 1) -> dict:
    """Return the (forward + backward) neighbour subgraph up to ``depth``."""
    store = _store(ctx)
    if depth < 1 or depth > 5:
        return {"status": "error", "error": "depth must be 1..5"}
    name_l = name.lower()
    adj_f: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    adj_b: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for r in store["relations"]:
        adj_f[r["subject"].lower()].append((r["predicate"], r["object"]))
        adj_b[r["object"].lower()].append((r["subject"], r["predicate"]))
    seen = {name_l}
    frontier = {name_l}
    edges = []
    for _ in range(depth):
        next_frontier = set()
        for node in frontier:
            for pred, nbr in adj_f.get(node, []):
                edges.append({"from": node, "predicate": pred, "to": nbr.lower()})
                if nbr.lower() not in seen:
                    seen.add(nbr.lower())
                    next_frontier.add(nbr.lower())
            for src, pred in adj_b.get(node, []):
                edges.append({"from": src.lower(), "predicate": pred, "to": node})
                if src.lower() not in seen:
                    seen.add(src.lower())
                    next_frontier.add(src.lower())
        frontier = next_frontier
        if not frontier:
            break
    return {
        "status": "ok",
        "root": name,
        "depth": depth,
        "entities_reached": sorted(seen),
        "edges": edges,
    }


def shortest_path(ctx: ToolContext, src: str, dst: str) -> dict:
    """Breadth-first shortest path between two entities."""
    store = _store(ctx)
    src_l, dst_l = src.lower(), dst.lower()
    if not any(e["name"].lower() == src_l for e in store["entities"]):
        return {"status": "error", "error": f"unknown source: {src!r}"}
    if not any(e["name"].lower() == dst_l for e in store["entities"]):
        return {"status": "error", "error": f"unknown destination: {dst!r}"}
    adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for r in store["relations"]:
        adj[r["subject"].lower()].append((r["predicate"], r["object"].lower()))
    q = deque([(src_l, [(src_l, None, None)])])
    seen = {src_l}
    while q:
        node, path = q.popleft()
        if node == dst_l:
            return {
                "status": "ok",
                "found": True,
                "length": len(path) - 1,
                "path": [
                    {"from": a, "predicate": b, "to": c} if b else {"node": a}
                    for a, b, c in path
                ],
            }
        for pred, nxt in adj.get(node, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            q.append((nxt, path + [(nxt, pred, node)]))
    return {"status": "ok", "found": False}


def clear_graph(ctx: ToolContext) -> dict:
    """Wipe the in-session graph."""
    store = _store(ctx)
    e_n, r_n = len(store["entities"]), len(store["relations"])
    store["entities"].clear()
    store["relations"].clear()
    return {"status": "ok", "cleared_entities": e_n, "cleared_relations": r_n}


root_agent = Agent(
    name="knowledge_graph_agent",
    model="gemini-2.0-flash",
    description=(
        "Maintains an in-session subject-predicate-object graph; "
        "supports neighbour lookup and shortest-path queries."
    ),
    instruction="""
    You are a knowledge-graph assistant.

    WORKFLOW:
    1. When the user names entities, call `add_entity` for each.
    2. When the user describes a relation, call `add_relation`.
    3. For questions like "what does X connect to", call
       `neighbours` with the right depth (default 1, raise to 2-3
       for indirect questions).
    4. For "how is X related to Y", call `shortest_path`.
    5. Always summarise the graph in plain English after each batch
       of insertions.

    RULES:
    - Normalise entity names to title case internally; preserve the
       user's casing on first add only.
    - Predicates are stored lowercased and underscored
       (e.g. "works_at").
    - If the user tries to relate an unknown entity, add it as
       type="thing" automatically rather than failing.
    """,
    tools=[
        add_entity, add_relation, list_entities, list_relations,
        neighbours, shortest_path, clear_graph,
    ],
)
