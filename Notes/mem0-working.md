# Mem0 Evaluation System Documentation

This evaluation system consists of two main components that work together to test how well Mem0 stores and retrieves conversational memories.

## The Two Files

**add.py** handles the memory storage phase. It takes conversation data between two speakers and adds their memories to Mem0. The key insight is that each speaker gets their own personalized view of the conversation. When Speaker A talks, their messages are marked as "user" role and Speaker B's responses are marked as "assistant" role. This perspective is then reversed for Speaker B. This dual-perspective approach ensures that Mem0 extracts what each person learned about the other, rather than just storing raw conversation text.

**search.py** handles the memory retrieval and evaluation phase. It takes questions about the conversations and searches both speakers' memories to find relevant information. The retrieved memories are then fed to an LLM (like GPT-4) which generates answers based on what was remembered. This tests whether the stored memories are accurate, relevant, and retrievable.

## How They Work Together

The workflow is sequential. First, you run add.py to populate Mem0 with memories from conversations. It processes the data in batches, using threading to handle both speakers simultaneously for efficiency. Each conversation segment gets timestamped so memories maintain temporal context.

After memories are stored, you run search.py to evaluate them. For each question, it searches memories from both speakers' perspectives, retrieves the top-k most relevant memories (default is 10), and uses those as context for the LLM to answer. The system tracks everything: how many memories were retrieved, how long searches took, what the LLM generated, and saves all this data incrementally to a JSON file.

The evaluation is comprehensive because it captures not just whether the answer is correct, but also which memories were used, their relevance scores, and performance metrics. If graph mode is enabled, it also captures relationship information between entities mentioned in the memories.

## Memory Storage Implications

The dual-perspective storage strategy is crucial. Instead of storing "Alice said X and Bob said Y," the system stores "Alice learned that Bob likes hiking" from Alice's perspective and "Bob shared that he likes hiking" from Bob's perspective. This means memories are inherently personalized and context-aware.

Batching is used for efficiency. Messages aren't sent one at a time but in groups (default batch size of 2). This reduces API calls while still maintaining granular memory extraction. The system also includes retry logic with delays to handle API failures gracefully, which is essential for large-scale data processing.

Custom instructions guide how Mem0 extracts memories. The instructions emphasize self-contained memories with complete context, including names, dates, emotional states, and specific details. This ensures that retrieved memories are useful on their own without requiring additional conversation context.

Old memories are deleted before adding new ones for the same user IDs. This prevents duplicate memories from accumulating across multiple runs and keeps the memory store clean.

## Memory Retrieval Implications

Search operates on a relevance-based system. When you query for information, Mem0 returns memories ranked by semantic similarity scores. The top-k parameter controls how much context the LLM receives. More memories mean more context but also more noise and slower processing.

The system supports two retrieval modes. Standard mode uses pure semantic search based on vector similarity. Graph mode adds relationship traversal, which can surface memories connected through entity relationships even if they're not semantically similar to the query. For example, asking about "Bob's hobbies" might surface memories about "outdoor activities" through a relationship graph.

Timestamps in the retrieved memories provide temporal context. This helps the LLM understand the sequence of events and how information evolved over time. A memory from last week might contradict one from last month, and the timestamps help resolve this.

The filter_memories option allows additional filtering beyond just semantic similarity, though the specific filtering logic depends on Mem0's implementation. This gives you control over what gets surfaced.

## Performance Considerations

The system uses parallel processing at multiple levels. ThreadPoolExecutor processes multiple conversations concurrently (default 10 workers). Within each conversation, threading handles both speakers simultaneously. This dramatically reduces total processing time for large datasets.

Progress bars at every level (conversations, questions, memory batches) provide visibility into long-running operations. This is essential when processing hundreds or thousands of questions.

Incremental saving after each question prevents data loss. If the system crashes halfway through processing 1000 questions, you don't lose the first 500 results. This is critical for expensive LLM-based evaluations.

Timing metrics are tracked separately for memory search and LLM generation. This helps identify bottlenecks. If searches are slow, you might need to optimize your vector store. If LLM generation is slow, you might need a faster model or better prompting.

## What This System Tests

Fundamentally, this evaluation framework tests whether conversational AI systems can remember and use information correctly. It tests precision (are the retrieved memories relevant?), recall (did we retrieve all the relevant memories?), and synthesis (can the LLM combine memories to answer complex questions?).

The dual-speaker design tests whether the system can maintain separate knowledge graphs for different entities. Alice's memories about Bob should be distinct from Bob's memories about Alice, even though they participated in the same conversation.

The timestamp tracking tests temporal reasoning. Can the system understand that preferences change over time? Can it distinguish between current and past information?

The graph mode tests relational reasoning. Can the system understand not just facts but relationships between facts? This is crucial for complex questions that require connecting multiple pieces of information.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   LOCOMO Dataset                        │
│              (10 conversations with Q&A)                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │  Step 1: Add Memories      │
         │  (src/memzero/add.py)      │
         │  → Stores in Mem0 Cloud    │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │  Step 2: Search & Answer   │
         │  (src/memzero/search.py)   │
         │  → Retrieves top_k         │
         │  → Generates answers       │
         │  → Records latency         │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │  Step 3: Evaluation        │
         │  (evals.py)                │
         │  → F1 Score                │
         │  → BLEU Score              │
         │  → LLM Judge               │
         │  → Latency Metrics         │
         └────────────────────────────┘
```