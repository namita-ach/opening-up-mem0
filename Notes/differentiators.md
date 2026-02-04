# Key Differentiators: Mem0 vs Zep

## Mem0

### 1. **Stateful Memory Across Sessions**
- Retains context beyond a single conversation (unlike stateless RAG).
- Use `user_id` to persist and retrieve memories across sessions.
```python
from mem0 import Memory
m = Memory()
m.add("I prefer vegetarian restaurants", user_id="alice")
# Later session
m.search("restaurant recommendations", user_id="alice")
```

### 2. **Dual Storage: Vector + Graph**
- Vector search for semantic recall; graph memory for entity relationships and multi-hop questions.
- Enable with `enable_graph=True` (benchmarking that I did had graphs disabled)
```python
from mem0 import MemoryClient
client = MemoryClient(api_key="...")
client.add(messages, user_id="joseph", enable_graph=True)
```

### 3. **Faster Retrieval**
- Retrieves only relevant context, not full histories.
- Does this using the vector search mentioned earlier.

### 4. **Memory Management**
- LLM-driven extraction, conflict resolution, and deduplication on `add`.
```python
client.add(messages, user_id="alice", infer=True)  # extraction + dedup
```

### 5. **Entity-Scoped Memory**
- Isolate memories by `user_id`, `agent_id`, `app_id`, `run_id` for multi-tenant/multi-agent apps.
- Use filters to scope reads precisely.
```python
client.add(messages, user_id="alice", agent_id="meal_planner")
client.search("preferences", filters={"user_id": "alice", "agent_id": "meal_planner"})
```

## Zep

### 1. **Temporal Knowledge Graph**
- Uses Graphiti, tracks facts with `valid_at` and `invalid_at` timestamps.
- Enables reasoning about state changes over time (which static memory stores can't handle).

### 2. **Three-Pattern Memory Architecture**
- **User Threads**: Sequential conversation messages per session.
- **User Graphs**: Personal knowledge graphs per individual.
- **Shared Graphs**: Organizational knowledge graphs shared across users.

### 3. **Intelligent Data Routing**
- Automatically routes data to thread or graph storage based on content type.
```python
# Message type
self._client.thread.add_messages(thread_id, [message])
# JSON/text type
self._client.graph.add(user_id, data=content_str, type=content_type)
```

### 4. **Parallel Multi-Scope Search**
- Concurrently searches edges (facts), nodes (entities), and episodes (events) for comprehensive context.
```python
with ThreadPoolExecutor(max_workers=3) as executor:
    future_edges = executor.submit(search_edges)
    future_nodes = executor.submit(search_nodes)
    future_episodes = executor.submit(search_episodes)
```

### 5. **Context Composition with Temporal Awareness**
- Formats search results into structured context, including temporal information for facts.

---

## Summary

| Feature                        | Mem0                                      | Zep                                      |
|--------------------------------|-------------------------------------------|------------------------------------------|
| Memory Type                    | Vector + Graph                            | Temporal Knowledge Graph                 |
| Stateful Across Sessions       | Yes                                       | Yes                                     |
| Entity/Session Scoping         | Yes (user_id, agent_id, etc.)             | Yes (user_id, thread_id, shared graph)  |
| Intelligent Extraction         | LLM-driven, deduplication, conflict-res.  | Graphiti framework, fact extraction      |
| Multimodal                     | Yes                                       | Yes                                     |
| Custom Criteria                | Yes                                       | Yes (via ontology, entity types)        |

