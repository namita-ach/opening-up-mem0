# Mem0 Basics and Setup


## 1. System Overview

Mem0 is a conversational memory system designed to store, retrieve, and evaluate personalized memories from dialogue data. It supports dual-perspective memory extraction, semantic search, and graph-based search.

---

## 2. Workflow Summary

### a. Memory Storage
- Stores conversations in Mem0, creating separate memory views for each speaker.
- Each speaker's perspective is stored as "user" or "assistant" roles, ensuring personalized, context-aware memories.
- Old memories are deleted before adding new ones for the same user IDs.
- Batching and retry logic are used for efficiency and robustness.

### b. Memory Retrieval & Answer Generation
- Searches both speakers' memories for each question, retrieves top-k relevant memories.
- Uses semantic similarity and optionally graph-based relationships for retrieval.
- Retrieved memories are fed to an LLM (e.g., GPT-4) to generate answers.
- Results (questions, answers, LLM responses, context, metrics) are saved to static JSON files in the results/ directory.

### c. Evaluation
- Takes the static results JSON file and computes F1, BLEU, LLM Judge, and Latency metrics.
- Optionally, summary statistics (mean, variance, std dev, min/max, count) are produced.

---

## 3. Setup & Quickstart

### Prerequisites
- Python 3.11
- OpenAI API key
- Mem0 API credentials (API key, Project ID, Organization ID)

### Quick Setup
```bash
cd /Users/namita.achyuthan/Documents/opening-up-mem0/evaluation
pip requirements.txt
python3 verify_setup.py
```

### Run Benchmarks
```bash
./run_mem0_benchmark.sh quick    # Quick test (top_k=10)
./run_mem0_benchmark.sh full     # Full benchmark (top_k=30)
./run_mem0_benchmark.sh graph    # With graph-based memory
```

Basically,

| Command | Description |
|---------|-------------|
| `full` | All categories, top_k=30 |
| `full 2` | Only category 2, top_k=30 |
| `quick` | All categories, top_k=10 |
| `quick 1` | Only category 1, top_k=10 |
| `by-category` | Each category separately, top_k=30 |
| `by-category 20` | Each category separately, top_k=20 |
| `search 20 3` | Search category 3 with top_k=20 |
| `stats <file>` | Calculate statistics only |

---

## 4. Output & Metrics

- Results saved in results/ directory (e.g., mem0_results_top_10_filter_False_graph_False_evaluated.json)
- Each question includes:
  - f1_score
  - bleu_score
  - llm_score
  - search_time
  - response_time
  - total_latency

---

## 5. Category-Based Benchmarking

- **Category 1:** Explicit statements (direct mentions)
- **Category 2:** Implicit statements (inferred information)
- **Category 3:** Event sequence (temporal ordering)
- **Category 4:** Reasoning (logical deduction)
- **Category 5:** Unanswerable (auto-skipped)

### Run Single Category
```bash
./run_mem0_benchmark.sh quick 2    # Quick test on category 2
./run_mem0_benchmark.sh full 1     # Full benchmark on category 1
./run_mem0_benchmark.sh search 20 3 # Search with top_k=20, category 3
```

### By-Category Mode
```bash
./run_mem0_benchmark.sh by-category
```

---

## 6. Statistics & Analysis

- After evaluation, statistics are auto-calculated:
  - Mean, variance, std dev, min/max, count for each metric
- Output files:
  - *_evaluated.json (full results)
  - *_statistics.json (summary stats)

---

## 7. Recent Modifications & Features

- Rate limit mitigation: Reduced batch size (2->1), added delays (2 sec after each batch), increased max_workers (15).
- Filter fix: Ensured filter_memories is never empty, defaults to {"role": "user"}.
- Incremental saving: Results saved after each question to prevent data loss.
- Progress bars added to understand where we are in the process.

---

## 8. Example Output (per question)
```json
{
  "question": "When did Caroline go to the LGBTQ support group?",
  "answer": "7 May 2023",
  "response": "Caroline attended on May 7th, 2023",
  "category": "2",
  "f1_score": 0.67,
  "bleu_score": 0.58,
  "llm_score": 1,
  "search_time": 0.85,
  "response_time": 1.42,
  "total_latency": 2.27
}
```

---

## 9. Help & Commands

```bash
./run_mem0_benchmark.sh help
```

- Lists all available commands, options, and category details.

---

## 10. What Mem0 Tests

- Precision, recall, and synthesis of conversational memories.
- Dual-speaker design: maintains separate knowledge graphs for each entity.
- Timestamp tracking: tests temporal reasoning.
- Graph mode: tests relational reasoning.

---