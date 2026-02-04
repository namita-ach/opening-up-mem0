import json  # Import JSON library for loading data files and saving results
import os  # Import OS library to access environment variables for API keys and model names
import time  # Import time to measure memory search and response generation latency
from collections import defaultdict  # Import defaultdict to automatically create lists for new conversation indices
from concurrent.futures import ThreadPoolExecutor  # Import ThreadPoolExecutor for parallel question processing

from dotenv import load_dotenv  # Import function to load environment variables from .env file
from jinja2 import Template  # Import Template for rendering dynamic prompts with speaker memories
from openai import OpenAI  # Import OpenAI client to generate answers using LLM based on retrieved memories
from prompts import ANSWER_PROMPT, ANSWER_PROMPT_GRAPH  # Import prompt templates for standard and graph-based memory retrieval
from tqdm import tqdm  # Import tqdm for displaying progress bars during batch processing

from mem0 import MemoryClient  # Import MemoryClient to search and retrieve memories from Mem0 API

load_dotenv()  # Load environment variables from .env file (API keys, org ID, project ID, model name)


class MemorySearch:  # Class to handle searching memories and answering questions based on retrieved context
    def __init__(self, output_path="results.json", top_k=10, filters=None, is_graph=False, category=None):  # Use filters dict for filtering
        """
        Initializes the MemorySearch system for retrieving memories and answering questions.
        Sets up both Mem0 and OpenAI clients to search memories and generate answers respectively.
        The top_k parameter controls how many relevant memories are retrieved per query.
        Graph mode enables relationship-based memory retrieval for more contextual answers.
        Results are incrementally saved to the output file to prevent data loss during long runs.
        """
        self.mem0_client = MemoryClient(  # Create Mem0 client instance to search and retrieve memories
            api_key=os.getenv("MEM0_API_KEY"),  # Get Mem0 API key from environment variables for authentication
            org_id=os.getenv("MEM0_ORGANIZATION_ID"),  # Get organization ID to scope memory searches to this organization
            project_id=os.getenv("MEM0_PROJECT_ID"),  # Get project ID to retrieve memories from this specific project
        )
        self.top_k = top_k  # Store the number of top relevant memories to retrieve for each search query (default: 10)
        self.openai_client = OpenAI()  # Create OpenAI client to generate answers using LLM based on retrieved memories
        self.results = defaultdict(list)  # Initialize results dictionary that auto-creates empty lists for new conversation indices
        self.output_path = output_path  # Store path where results will be saved (default: results.json)
        self.filters = filters if filters is not None else {}  # Store filters dict for search
        self.is_graph = is_graph  # Store whether to use graph-based memory retrieval (enables relationship context)
        self.category = category  # Store category filter (None means all categories, 1-5 for specific category)

        if self.is_graph:  # Check if graph mode is enabled
            self.ANSWER_PROMPT = ANSWER_PROMPT_GRAPH  # Use graph-specific prompt template that includes relationship information
        else:  # If standard mode
            self.ANSWER_PROMPT = ANSWER_PROMPT  # Use standard prompt template for semantic memory retrieval only

    def search_memory(self, user_id, query, max_retries=3, retry_delay=1):  # Method to search memories for a specific user with retry logic
        """
        Searches for relevant memories in Mem0 for a given user and query with automatic retry on failure.
        Supports both semantic search (vector similarity) and graph-based search (relationship traversal).
        Times the search operation to measure retrieval performance and identify bottlenecks.
        Implements retry logic with configurable delay to handle transient API failures gracefully.
        Returns formatted memories with timestamps and relevance scores, plus graph relationships if enabled.
        """
        start_time = time.time()  # Record the start time to measure how long the memory search takes
        retries = 0  # Initialize retry counter to track how many attempts have been made
        while retries < max_retries:  # Loop until max retry attempts are exhausted
            try:  # Attempt to search memories, catching any exceptions
                if self.is_graph:
                    # print(f"[BOB IS DEBUG] Searching with graph for user_id={user_id}, query='{query}', filters={self.filters}")
                    memories = self.mem0_client.search(
                        query,
                        user_id=user_id,
                        top_k=self.top_k,
                        filters=self.filters,
                        enable_graph=True,
                        output_format="v1.1",
                    )
                else:
                    debug_filters = {"user_id": user_id}
                    # print(f"[BOB IS DEBUG] Non-graph search for user_id={user_id}, query='{query}', filters={debug_filters}")
                    memories = self.mem0_client.search(
                        query,
                        user_id=user_id,
                        top_k=self.top_k,
                        filters=debug_filters,
                    )
                # print(f"[BOB IS DEBUG] Memories returned: {memories}")
                break
            except Exception as e:
                # print(f"[BOB IS DEBUG] Exception during search_memory: {e}")
                print("Retrying...")
                retries += 1
                if retries >= max_retries:
                    raise e
                time.sleep(retry_delay)

        end_time = time.time()  # Record the end time to calculate total search duration
        if not self.is_graph:
            # Handle both list and dict API responses
            if isinstance(memories, dict) and "results" in memories:
                memory_list = memories["results"]
            else:
                memory_list = memories
            semantic_memories = [
                {
                    "memory": memory["memory"],
                    "timestamp": memory["metadata"]["timestamp"],
                    "score": round(memory["score"], 2),
                }
                for memory in memory_list
            ]
            graph_memories = None
        else:
            semantic_memories = [
                {
                    "memory": memory["memory"],
                    "timestamp": memory["metadata"]["timestamp"],
                    "score": round(memory["score"], 2),
                }
                for memory in memories["results"]
            ]
            graph_memories = [
                {"source": relation["source"], "relationship": relation["relationship"], "target": relation["target"]}
                for relation in memories["relations"]
            ]
        return semantic_memories, graph_memories, end_time - start_time

    def answer_question(self, speaker_1_user_id, speaker_2_user_id, question, answer, category):  # Method to answer a question using memories from both speakers in a conversation
        """
        Generates an answer to a question by retrieving and synthesizing memories from both conversation participants.
        First searches memories for both speakers to gather relevant context about the question.
        Then uses Jinja2 to render a prompt template with the retrieved memories and graph relationships.
        Finally calls OpenAI's LLM to generate an answer based on the enriched context.
        Returns the generated answer, all retrieved memories, graph relationships, and timing metrics.
        """
        speaker_1_memories, speaker_1_graph_memories, speaker_1_memory_time = self.search_memory(  # Search for relevant memories from speaker 1's perspective
            speaker_1_user_id, question  # Pass speaker 1's user ID and the question as search query
        )
        speaker_2_memories, speaker_2_graph_memories, speaker_2_memory_time = self.search_memory(  # Search for relevant memories from speaker 2's perspective
            speaker_2_user_id, question  # Pass speaker 2's user ID and the question as search query
        )

        search_1_memory = [f"{item['timestamp']}: {item['memory']}" for item in speaker_1_memories]  # Format speaker 1's memories as "timestamp: memory text" strings
        search_2_memory = [f"{item['timestamp']}: {item['memory']}" for item in speaker_2_memories]  # Format speaker 2's memories as "timestamp: memory text" strings

        template = Template(self.ANSWER_PROMPT)  # Create a Jinja2 template object from the prompt string (ANSWER_PROMPT or ANSWER_PROMPT_GRAPH)
        answer_prompt = template.render(  # Render the template by replacing placeholders with actual values
            speaker_1_user_id=speaker_1_user_id.split("_")[0],  # Extract speaker 1's name by removing the conversation index suffix
            speaker_2_user_id=speaker_2_user_id.split("_")[0],  # Extract speaker 2's name by removing the conversation index suffix
            speaker_1_memories=json.dumps(search_1_memory, indent=4),  # Convert speaker 1's memories to formatted JSON string
            speaker_2_memories=json.dumps(search_2_memory, indent=4),  # Convert speaker 2's memories to formatted JSON string
            speaker_1_graph_memories=json.dumps(speaker_1_graph_memories, indent=4),  # Convert speaker 1's graph relationships to formatted JSON string (None if not graph mode)
            speaker_2_graph_memories=json.dumps(speaker_2_graph_memories, indent=4),  # Convert speaker 2's graph relationships to formatted JSON string (None if not graph mode)
            question=question,  # Include the question being answered
        )

        t1 = time.time()  # Record start time to measure how long the LLM takes to generate an answer
        response = self.openai_client.chat.completions.create(  # Call OpenAI API to generate an answer based on the prompt
            model=os.getenv("MODEL"), messages=[{"role": "system", "content": answer_prompt}], temperature=0.0  # Use model from environment, system prompt with memories, and temperature 0 for deterministic responses
        )
        t2 = time.time()  # Record end time after receiving the LLM response
        response_time = t2 - t1  # Calculate total time taken for LLM answer generation
        return (  # Return all relevant data as a tuple
            response.choices[0].message.content,  # The generated answer text from the LLM
            speaker_1_memories,  # Retrieved memories for speaker 1 with timestamps and scores
            speaker_2_memories,  # Retrieved memories for speaker 2 with timestamps and scores
            speaker_1_memory_time,  # Time taken to search speaker 1's memories
            speaker_2_memory_time,  # Time taken to search speaker 2's memories
            speaker_1_graph_memories,  # Graph relationships for speaker 1 (or None)
            speaker_2_graph_memories,  # Graph relationships for speaker 2 (or None)
            response_time,  # Time taken for LLM to generate the answer
        )

    def process_question(self, val, speaker_a_user_id, speaker_b_user_id):  # Method to process a single question-answer pair and save results
        """
        Processes a single evaluation question by extracting metadata, generating an answer, and saving results.
        Extracts question details from the input dictionary including expected answer, category, and evidence.
        Calls answer_question to retrieve memories and generate an LLM response.
        Consolidates all data (question, answer, memories, timings) into a structured result dictionary.
        Incrementally saves results to disk after each question to prevent data loss during long runs.
        """
        question = val.get("question", "")  # Extract the question text from the input dictionary (empty string if missing)
        answer = val.get("answer", "")  # Extract the expected/ground-truth answer (empty string if missing)
        category = val.get("category", -1)  # Extract the question category/type (-1 if not specified)
        evidence = val.get("evidence", [])  # Extract the evidence/source information (empty list if missing)
        adversarial_answer = val.get("adversarial_answer", "")  # Extract adversarial/incorrect answer for evaluation (empty string if missing)

        (  # Unpack the tuple returned by answer_question into separate variables
            response,  # The LLM-generated answer to the question
            speaker_1_memories,  # Retrieved memories from speaker 1's perspective
            speaker_2_memories,  # Retrieved memories from speaker 2's perspective
            speaker_1_memory_time,  # Time taken to search speaker 1's memories
            speaker_2_memory_time,  # Time taken to search speaker 2's memories
            speaker_1_graph_memories,  # Graph relationships for speaker 1 (or None)
            speaker_2_graph_memories,  # Graph relationships for speaker 2 (or None)
            response_time,  # Time taken for LLM to generate the answer
        ) = self.answer_question(speaker_a_user_id, speaker_b_user_id, question, answer, category)  # Call answer_question with both speakers' IDs and question details

        result = {  # Create a comprehensive result dictionary containing all relevant data
            "question": question,  # The original question text
            "answer": answer,  # The expected/ground-truth answer
            "category": category,  # The question category/type
            "evidence": evidence,  # Source evidence for the answer
            "response": response,  # The LLM-generated answer
            "adversarial_answer": adversarial_answer,  # Adversarial/incorrect answer for comparison
            "speaker_1_memories": speaker_1_memories,  # All retrieved memories for speaker 1
            "speaker_2_memories": speaker_2_memories,  # All retrieved memories for speaker 2
            "num_speaker_1_memories": len(speaker_1_memories),  # Count of memories retrieved for speaker 1
            "num_speaker_2_memories": len(speaker_2_memories),  # Count of memories retrieved for speaker 2
            "speaker_1_memory_time": speaker_1_memory_time,  # Search latency for speaker 1
            "speaker_2_memory_time": speaker_2_memory_time,  # Search latency for speaker 2
            "speaker_1_graph_memories": speaker_1_graph_memories,  # Graph relationships for speaker 1
            "speaker_2_graph_memories": speaker_2_graph_memories,  # Graph relationships for speaker 2
            "response_time": response_time,  # LLM generation latency
        }

        # Save results after each question is processed to prevent data loss
        with open(self.output_path, "w") as f:  # Open output file in write mode using context manager
            json.dump(self.results, f, indent=4)  # Write the entire results dictionary as formatted JSON

        return result  # Return the result dictionary for this question

    def process_data_file(self, file_path, max_conversations=None):  # Method to process an entire evaluation data file sequentially, with optional limit
        """
        Processes all conversations and questions from an evaluation data file sequentially.
        Loads the JSON file containing multiple conversations, each with associated Q&A pairs.
        Iterates through each conversation, creates user IDs for both speakers, and processes all questions.
        Uses nested progress bars to show both conversation-level and question-level progress.
        Incrementally saves results after each question to ensure no data is lost if processing fails.
        """
        with open(file_path, "r") as f:  # Open the evaluation data file in read mode using context manager
            data = json.load(f)  # Parse the JSON file into a Python data structure
        if max_conversations is not None:
            data = data[:max_conversations]

        for idx, item in tqdm(enumerate(data), total=len(data), desc="Processing conversations"):  # Loop through all conversations with progress bar
            qa = item["qa"]  # Extract the list of question-answer pairs for this conversation
            conversation = item["conversation"]  # Extract the conversation dictionary containing speaker info
            speaker_a = conversation["speaker_a"]  # Get the name/ID of speaker A
            speaker_b = conversation["speaker_b"]  # Get the name/ID of speaker B

            speaker_a_user_id = f"{speaker_a}_{idx}"  # Create unique user ID for speaker A by appending conversation index
            speaker_b_user_id = f"{speaker_b}_{idx}"  # Create unique user ID for speaker B by appending conversation index

            for question_item in tqdm(  # Loop through all questions for this conversation with nested progress bar
                qa, total=len(qa), desc=f"Processing questions for conversation {idx}", leave=False  # Show question progress, don't leave bar after completion
            ):
                # Skip questions that don't match the category filter (if specified)
                if self.category is not None and question_item.get("category") != self.category:
                    continue  # Skip this question if it doesn't match the requested category
                
                result = self.process_question(question_item, speaker_a_user_id, speaker_b_user_id)  # Process the question and get the result dictionary
                self.results[idx].append(result)  # Add the result to the list for this conversation index

                # Save results after each question is processed to prevent data loss
                with open(self.output_path, "w") as f:  # Open output file in write mode
                    json.dump(self.results, f, indent=4)  # Write all results as formatted JSON

        # Final save at the end to ensure all results are persisted
        with open(self.output_path, "w") as f:  # Open output file in write mode
            json.dump(self.results, f, indent=4)  # Write complete results as formatted JSON

    def process_questions_parallel(self, qa_list, speaker_a_user_id, speaker_b_user_id, max_workers=1):  # Method to process multiple questions in parallel using thread pool
        """
        Processes multiple questions concurrently using parallel execution for improved performance.
        Defines an inner function that wraps process_question with automatic result saving.
        Uses ThreadPoolExecutor to distribute questions across multiple worker threads.
        Progress bar shows real-time status as questions are completed across all workers.
        Default max_workers=1 provides sequential execution; increase for true parallelism.
        """
        def process_single_question(val):  # Inner function to process one question and save results
            result = self.process_question(val, speaker_a_user_id, speaker_b_user_id)  # Process the question using the main logic
            # Save results after each question is processed to ensure incremental persistence
            with open(self.output_path, "w") as f:  # Open output file in write mode
                json.dump(self.results, f, indent=4)  # Write all results as formatted JSON
            return result  # Return the result dictionary for this question

        with ThreadPoolExecutor(max_workers=max_workers) as executor:  # Create thread pool with specified number of workers (default: 1)
            results = list(  # Convert iterator to list to get all results
                tqdm(executor.map(process_single_question, qa_list), total=len(qa_list), desc="Answering Questions")  # Map questions to workers with progress bar tracking completion
            )

        # Final save at the end to ensure complete results are persisted
        with open(self.output_path, "w") as f:  # Open output file in write mode
            json.dump(self.results, f, indent=4)  # Write all results as formatted JSON

        return results  # Return the list of all result dictionaries
