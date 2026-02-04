# Test script for LLM Judge step (step 3)
import os
from dotenv import load_dotenv
from metrics.llm_judge import evaluate_llm_judge

# Ensure .env is loaded for OpenAI key
def main():
    load_dotenv()
    # Example test case (replace with real values if needed)
    question = "When did Caroline go to the LGBTQ support group?"
    gold_answer = "7 May 2023"
    generated_answer = "Caroline attended the LGBTQ support group on May 7th, 2023."
    print(f"[TEST] Question: {question}")
    print(f"[TEST] Gold answer: {gold_answer}")
    print(f"[TEST] Generated answer: {generated_answer}")
    try:
        label = evaluate_llm_judge(question, gold_answer, generated_answer)
        print(f"[TEST RESULT] LLM Judge label: {label} (1=CORRECT, 0=WRONG)")
    except Exception as e:
        print(f"[TEST ERROR] Exception during LLM Judge: {e}")

if __name__ == "__main__":
    main()
