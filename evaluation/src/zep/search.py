import argparse  # Import argparse for parsing command-line arguments (run_id parameter)
import json  # Import JSON library for loading data and saving results
import os  # Import OS library to access environment variables for API keys
import time  # Import time to measure search and response generation latency
from collections import defaultdict  # Import defaultdict to automatically create lists for new conversation indices

from dotenv import load_dotenv  # Import function to load environment variables from .env file
from jinja2 import Template  # Import Template for rendering prompts with search context
from openai import OpenAI  # Import OpenAI client to generate answers using LLM
from prompts import ANSWER_PROMPT_ZEP  # Import Zep-specific prompt template for answer generation
from tqdm import tqdm  # Import tqdm for displaying progress bars during processing
from zep_cloud import EntityEdge, EntityNode  # Import Zep types for graph entities and relationships
from zep_cloud.client import Zep  # Import Zep client to search graph-based memories

load_dotenv()  # Load environment variables from .env file (ZEP_API_KEY, MODEL)

TEMPLATE = """  # Template string for formatting Zep's graph search results into readable context
FACTS and ENTITIES represent relevant context to the current conversation.  # Explanation of what the formatted data represents

# These are the most relevant facts and their valid date ranges  # Section header for fact listings
# format: FACT (Date range: from - to)  # Format specification showing temporal validity

{facts}  # Placeholder that will be replaced with actual facts from graph edges


# These are the most relevant entities  # Section header for entity listings
# ENTITY_NAME: entity summary  # Format specification for entity name and description

{entities}  # Placeholder that will be replaced with actual entities from graph nodes

"""


class ZepSearch:  # Class to handle searching Zep's graph-based memories and answering questions
    def __init__(self):  # Initialize the ZepSearch system with necessary clients
        """
        Initializes the ZepSearch system for graph-based memory retrieval and question answering.
        Sets up Zep client for searching knowledge graphs and OpenAI client for answer generation.
        Uses defaultdict to automatically create result lists for new conversation indices.
        Zep's approach differs from Mem0 by using a knowledge graph with entities and relationships.
        """
        self.zep_client = Zep(api_key=os.getenv("ZEP_API_KEY"))  # Create Zep client using API key from environment variables
        self.results = defaultdict(list)  # Initialize results dictionary that auto-creates empty lists for new indices
        self.openai_client = OpenAI()  # Create OpenAI client to generate answers based on retrieved graph context

    def format_edge_date_range(self, edge: EntityEdge) -> str:  # Method to format the temporal validity range of a graph edge (fact)
        """
        Formats the date range during which a graph edge (fact) is valid.
        Returns a string showing when the fact became valid and when it expired or is still valid.
        Uses 'date unknown' if the start date is missing and 'present' if no end date exists.
        This temporal information helps the LLM understand if facts are current or historical.
        """
        # return f"{datetime(edge.valid_at).strftime('%Y-%m-%d %H:%M:%S') if edge.valid_at else 'date unknown'} - {(edge.invalid_at.strftime('%Y-%m-%d %H:%M:%S') if edge.invalid_at else 'present')}"  # Commented out formatted datetime version
        return f"{edge.valid_at if edge.valid_at else 'date unknown'} - {(edge.invalid_at if edge.invalid_at else 'present')}"  # Return raw date range or defaults

    def compose_search_context(self, edges: list[EntityEdge], nodes: list[EntityNode]) -> str:  # Method to format graph search results into readable context for the LLM
        """
        Transforms graph search results (edges and nodes) into formatted text for LLM consumption.
        Edges represent facts with temporal validity (relationships between entities).
        Nodes represent entities with summaries (people, places, things mentioned in conversations).
        Formats everything into a structured template that the LLM can easily parse and use.
        """
        facts = [f"  - {edge.fact} ({self.format_edge_date_range(edge)})" for edge in edges]  # Format each edge as a fact with its date range
        entities = [f"  - {node.name}: {node.summary}" for node in nodes]  # Format each node as an entity name with its summary
        return TEMPLATE.format(facts="\n".join(facts), entities="\n".join(entities))  # Combine facts and entities into the template structure

    def search_memory(self, run_id, idx, query, max_retries=3, retry_delay=1):  # Method to search Zep's knowledge graph for relevant facts and entities
        """
        Searches Zep's knowledge graph for relevant information using the query.
        Performs two separate searches: one for edges (facts/relationships) and one for nodes (entities).
        Uses different rerankers for each: cross_encoder for edges and rrf for nodes.
        Combines the results into formatted context text for the LLM.
        Includes retry logic to handle transient API failures gracefully.
        """
        start_time = time.time()  # Record start time to measure search latency
        retries = 0  # Initialize retry counter
        while retries < max_retries:  # Loop until max retry attempts are exhausted
            try:  # Attempt to search the graph, catching any exceptions
                user_id = f"run_id_{run_id}_experiment_user_{idx}"  # Construct user ID from run_id and conversation index
                edges_results = (  # Search for relevant edges (facts/relationships) in the graph
                    self.zep_client.graph.search(  # Call Zep's graph search API
                        user_id=user_id, reranker="cross_encoder", query=query, scope="edges", limit=20  # Search user's graph, use cross_encoder reranker, scope to edges only, return top 20
                    )
                ).edges  # Extract the edges list from the search results
                node_results = (  # Search for relevant nodes (entities) in the graph
                    self.zep_client.graph.search(user_id=user_id, reranker="rrf", query=query, scope="nodes", limit=20)  # Search user's graph, use rrf reranker, scope to nodes only, return top 20
                ).nodes  # Extract the nodes list from the search results
                context = self.compose_search_context(edges_results, node_results)  # Format the edges and nodes into readable context text
                break  # If search succeeds, exit the retry loop
            except Exception as e:  # If an error occurs during the search
                print("Retrying...")  # Log that we're retrying
                retries += 1  # Increment retry counter
                if retries >= max_retries:  # Check if we've exhausted all retry attempts
                    raise e  # Re-raise the exception to propagate the error
                time.sleep(retry_delay)  # Wait 1 second before retrying

        end_time = time.time()  # Record end time after successful search

        return context, end_time - start_time  # Return formatted context and search duration

    def process_question(self, run_id, val, idx):  # Method to process a single question by extracting metadata and generating an answer
        """
        Processes one evaluation question by extracting details and generating an answer.
        Extracts question metadata including expected answer, category, and evidence.
        Calls answer_question to search the graph and generate an LLM response.
        Consolidates all results into a structured dictionary for evaluation.
        """
        question = val.get("question", "")  # Extract the question text from input dictionary
        answer = val.get("answer", "")  # Extract the expected/ground-truth answer
        category = val.get("category", -1)  # Extract the question category/type
        evidence = val.get("evidence", [])  # Extract the evidence/source information
        adversarial_answer = val.get("adversarial_answer", "")  # Extract adversarial/incorrect answer for comparison

        response, search_memory_time, response_time, context = self.answer_question(run_id, idx, question)  # Generate answer and get timing metrics and context used

        result = {  # Create result dictionary with all relevant data
            "question": question,  # The original question text
            "answer": answer,  # The expected/ground-truth answer
            "category": category,  # The question category
            "evidence": evidence,  # Source evidence
            "response": response,  # The LLM-generated answer
            "adversarial_answer": adversarial_answer,  # Adversarial answer
            "search_memory_time": search_memory_time,  # Time taken to search the graph
            "response_time": response_time,  # Time taken for LLM to generate answer
            "context": context,  # The formatted context (facts and entities) used for answering
        }

        return result  # Return the complete result dictionary

    def answer_question(self, run_id, idx, question):  # Method to answer a question using graph-based memory retrieval
        """
        Generates an answer to a question by searching the graph and using an LLM.
        First searches Zep's knowledge graph for relevant facts and entities.
        Renders the search results into a prompt using the Zep-specific template.
        Calls OpenAI's LLM to generate an answer based on the graph context.
        """
        context, search_memory_time = self.search_memory(run_id, idx, question)  # Search the graph for relevant context and measure search time

        template = Template(ANSWER_PROMPT_ZEP)  # Create Jinja2 template from Zep-specific prompt
        answer_prompt = template.render(memories=context, question=question)  # Render template by inserting graph context and question

        t1 = time.time()  # Record start time for LLM answer generation
        response = self.openai_client.chat.completions.create(  # Call OpenAI API to generate answer
            model=os.getenv("MODEL"), messages=[{"role": "system", "content": answer_prompt}], temperature=0.0  # Use model from environment, system prompt with context, temperature 0 for deterministic output
        )
        t2 = time.time()  # Record end time after receiving LLM response
        response_time = t2 - t1  # Calculate LLM generation time
        return response.choices[0].message.content, search_memory_time, response_time, context  # Return generated answer, search time, generation time, and context used

    def process_data_file(self, file_path, run_id, output_file_path):  # Method to process all conversations and questions from an evaluation data file
        """
        Processes an entire evaluation dataset by loading the file and processing all questions.
        Loads JSON data containing conversations with Q&A pairs.
        Iterates through conversations and questions with progress bars for visibility.
        Saves results incrementally after each question to prevent data loss.
        """
        with open(file_path, "r") as f:  # Open evaluation data file in read mode
            data = json.load(f)  # Parse JSON file into Python data structure

        for idx, item in tqdm(enumerate(data), total=len(data), desc="Processing conversations"):  # Loop through all conversations with progress bar
            qa = item["qa"]  # Extract the list of question-answer pairs for this conversation

            for question_item in tqdm(  # Loop through all questions for this conversation
                qa, total=len(qa), desc=f"Processing questions for conversation {idx}", leave=False  # Nested progress bar, don't leave after completion
            ):
                result = self.process_question(run_id, question_item, idx)  # Process the question and get result dictionary
                self.results[idx].append(result)  # Add result to the list for this conversation index

                # Save results after each question is processed to prevent data loss
                with open(output_file_path, "w") as f:  # Open output file in write mode
                    json.dump(self.results, f, indent=4)  # Write all results as formatted JSON

        # Final save at the end to ensure complete results are persisted
        with open(output_file_path, "w") as f:  # Open output file in write mode
            json.dump(self.results, f, indent=4)  # Write complete results as formatted JSON


if __name__ == "__main__":  # Execute this block only when script is run directly
    parser = argparse.ArgumentParser()  # Create argument parser for command-line arguments
    parser.add_argument("--run_id", type=str, required=True)  # Define required run_id argument to identify this experimental run
    args = parser.parse_args()  # Parse command-line arguments
    zep_search = ZepSearch()  # Create ZepSearch instance
    zep_search.process_data_file("../../dataset/locomo10.json", args.run_id, "results/zep_search_results.json")  # Process dataset and save results to JSON file
