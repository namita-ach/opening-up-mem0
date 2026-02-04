# Quick test script for MemorySearch.search_memory debug segment
import json
from src.memzero.search import MemorySearch

if __name__ == "__main__":
    # Load a real user_id and question from the locomo10 dataset
    with open("dataset/locomo10.json", "r") as f:
        data = json.load(f)
    # Use the first conversation and first QA pair
    conversation_idx = 0
    qa_idx = 0
    qa = data[conversation_idx]["qa"][qa_idx]
    question = qa["question"]
    print(f"[TEST] Using question: {question}")
    # Use the speaker name and index pattern from the main code
    speaker_a = "Caroline"
    user_id = f"{speaker_a}_{conversation_idx}"

    searcher = MemorySearch()
    try:
        semantic_memories, graph_memories, search_time = searcher.search_memory(user_id, question)
        print("\n[TEST RESULT] Semantic memories:", semantic_memories)
        print("[TEST RESULT] Graph memories:", graph_memories)
        print(f"[TEST RESULT] Search time: {search_time:.3f} seconds")
    except Exception as e:
        print(f"[TEST ERROR] Exception during search_memory: {e}")
