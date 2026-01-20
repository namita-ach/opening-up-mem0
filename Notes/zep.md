# Zep Evaluation System Documentation

This evaluation system tests how well Zep stores and retrieves conversational memories using its knowledge graph architecture. It consists of two main components that work sequentially.

## The Two Files

**add.py** handles the memory storage phase. It takes conversation data and adds messages to Zep as a session. Unlike Mem0's dual-perspective approach, Zep stores the entire conversation as a sequential flow in a single session. Each message is added with the speaker's name and timestamp prepended to the content. Zep then automatically extracts entities, relationships, and facts from this conversation flow to build a knowledge graph. The system doesn't need to create separate perspectives because Zep's graph extraction handles understanding what each participant knows about the other.

**search.py** handles the memory retrieval and evaluation phase. It searches Zep's knowledge graph for relevant facts and entities, then uses those to answer questions. The search is split into two parts: finding relevant edges (facts and relationships between entities) and finding relevant nodes (entity summaries). These results are formatted into structured text and fed to an LLM to generate answers. This tests whether Zep's knowledge graph accurately captured and can retrieve the important information from conversations.

## How They Work Together

The workflow is sequential. First, run add.py with a run_id to populate Zep with conversation data. The script creates a user and session for each conversation, then adds all messages sequentially to that session. Timestamps are prepended to message content to maintain temporal context. Zep processes these messages in the background to extract entities (people, places, things) and relationships (facts connecting entities).

After Zep has processed the conversations and built the knowledge graph, run search.py with the same run_id to evaluate retrieval quality. For each question, it performs two graph searches: one for edges using a cross_encoder reranker (finds facts and relationships) and one for nodes using an rrf reranker (finds relevant entities). The top 20 results from each search are formatted into a structured template showing facts with their temporal validity ranges and entities with their summaries. This context is then given to an LLM to answer the question.

The evaluation captures comprehensive metrics including search times, LLM generation times, the actual context retrieved (facts and entities), and the generated answers. Results are saved incrementally to prevent data loss during long evaluation runs.

## Memory Storage Implications

Zep uses a fundamentally different storage model than Mem0. Instead of storing personalized memory perspectives, Zep stores raw conversation flow and extracts structured knowledge from it. The conversation is stored as a session with messages in chronological order. Each message includes the speaker identifier, which helps Zep understand who said what.

The key advantage is simplicity. You don't need to create dual perspectives or reverse roles. Just add messages as they occur in the conversation. Zep's natural language processing extracts entities, identifies relationships, and determines temporal validity automatically.

Timestamps are crucial because they're prepended to message content. This allows Zep to understand when facts became valid. For example, if someone says "I started hiking last month," Zep can extract a fact with a validity start date based on the message timestamp.

The system uses unique IDs constructed from run_id and conversation index. This allows multiple experimental runs without ID conflicts. You can run the same conversations multiple times with different run_ids to test reproducibility or compare different Zep configurations.

Currently, the add.py script only processes the first conversation (idx == 0) for testing purposes. This is a limitation that can be removed by eliminating the condition to process all conversations in the dataset.

## Memory Retrieval Implications

Zep's retrieval is graph-based rather than purely semantic. When you query for information, Zep searches its knowledge graph for relevant facts and entities. This is fundamentally different from vector similarity search.

The dual search strategy is important. Searching edges finds facts and relationships, which answer "what happened" and "how things are connected." Searching nodes finds entities, which answer "who/what is involved." Using different rerankers for each search type optimizes retrieval quality. Cross_encoder works well for edges because it can assess semantic similarity between the query and relationship statements. RRF (reciprocal rank fusion) works well for nodes because it combines multiple ranking signals.

The limit of 20 results per search type (40 total) provides substantial context without overwhelming the LLM. Unlike Mem0's top_k parameter which controls total memories, Zep retrieves 20 edges plus 20 nodes, giving balanced coverage of both facts and entities.

Temporal validity is a distinguishing feature. Each fact (edge) has a valid_at and invalid_at timestamp. This allows Zep to understand that "Alice lived in Boston" might be true from 2020-2023 but not currently. The formatted context shows these date ranges explicitly, helping the LLM reason about temporal aspects of questions.

The formatted context template is structured for clarity. Facts are listed with their date ranges, entities are listed with summaries. This explicit structure helps the LLM parse the information correctly and distinguish between what is fact versus what is entity description.

## Architectural Differences from Mem0

The most significant difference is the knowledge graph versus memory list paradigm. Mem0 stores memories as semantic text snippets that can be searched via vector similarity. Zep extracts structured knowledge (entities and relationships) that can be queried via graph traversal and semantic search on the graph structure.

Mem0 requires you to think about memory from each participant's perspective and store it twice with role reversal. Zep requires you to provide the raw conversation and let it extract structure automatically. This makes Zep easier to use but gives you less control over what gets stored.

Mem0's custom instructions guide how memories are extracted, giving fine-grained control over memory formatting and granularity. Zep's extraction is automatic and less customizable, but it enforces consistency by using its built-in entity and relationship extraction models.

Search strategies differ fundamentally. Mem0 searches for semantically similar memories and returns them ranked by similarity score. Zep searches a knowledge graph for related entities and facts, returning structured information that may not be semantically similar to the query but is contextually relevant through graph relationships.

## Performance Considerations

The add.py script adds messages one at a time, which is slower than Mem0's batching approach. Each message is a separate API call to Zep. For large conversations, this can result in many API calls and longer processing times. However, the simplicity of the approach (no role reversal, no batching logic) makes the code easier to maintain.

There's no parallel processing in the Zep implementation. Conversations are processed sequentially, and within each conversation, messages are added sequentially. This is simpler but slower than Mem0's threading approach. For large-scale evaluations, this could be a bottleneck.

The search phase has retry logic to handle transient failures, which is important for reliability. The 1-second delay between retries prevents overwhelming the API during issues.

Progress bars at multiple levels (conversations, messages, questions) provide visibility into processing status, which is essential for long-running operations.

Incremental saving after each question prevents data loss, just like in the Mem0 implementation. This is critical because LLM-based evaluations are expensive and time-consuming.

## What This System Tests

This evaluation framework tests whether knowledge graph extraction and retrieval can effectively support question answering. It tests whether Zep can correctly extract entities and relationships from conversations, maintain temporal validity information, and retrieve relevant graph context for diverse questions.

The session-based model tests whether a single conversation view (rather than dual perspectives) provides sufficient information for accurate memory. Since Zep extracts entities and relationships from the entire conversation context, it theoretically has access to the same information as Mem0's dual perspectives, just structured differently.

Temporal reasoning is heavily tested. The date range formatting in search results explicitly shows when facts are valid. This tests whether Zep correctly identifies when information becomes valid or expires based on conversation context.

The dual search for edges and nodes tests whether the system can provide both factual relationships and entity context. Good performance requires both types of information: knowing facts without knowing what entities are involved is useless, and vice versa.

## Practical Usage

To use this system, you need conversation data in JSON format with speaker identifiers, message segments, and timestamps. You also need a Zep API key and OpenAI API key in your environment variables.

Run add.py first with a run_id parameter. This creates users and sessions in Zep and populates them with conversation messages. Zep processes these in the background to build the knowledge graph. You may need to wait some time after running add.py before the graph extraction is complete.

Run search.py after Zep has finished processing (use the same run_id). This searches the knowledge graph for each question and generates answers. Results are saved to a JSON file containing questions, expected answers, generated responses, retrieved context (facts and entities), and timing metrics.

The run_id parameter is important for tracking experiments. Using different run_ids for different experimental runs keeps data separate. Using the same run_id for add and search operations ensures you're searching the correct user's graph.

The output JSON can be analyzed using evaluation scripts to compute accuracy, retrieval quality, and latency metrics. The context field in results is particularly valuable because it shows exactly what facts and entities were used to answer each question, enabling detailed error analysis.

## Key Takeaways

Zep simplifies memory storage by accepting raw conversations and extracting structure automatically. This reduces implementation complexity but gives less control over what gets stored. The knowledge graph approach enables relationship-based retrieval that can surface relevant information even when it's not semantically similar to the query.

Temporal validity tracking is a major advantage, allowing the system to reason about when information was true versus when it changed. The dual search for facts and entities provides comprehensive context for answering questions.

The tradeoff is performance. The current implementation is slower than Mem0 due to sequential processing and lack of batching. For production use, these would need optimization. However, the fundamental architecture (knowledge graph with temporal facts) offers unique capabilities for memory systems that need to understand relationships and temporal evolution of information.
