import json  # Import JSON library for parsing conversation data files
import os  # Import OS library to access environment variables
import threading  # Import threading for parallel memory addition for multiple speakers
import time  # Import time for retry delays when API calls fail
from concurrent.futures import ThreadPoolExecutor  # Import ThreadPoolExecutor for processing multiple conversations concurrently

from dotenv import load_dotenv  # Import function to load environment variables from .env file
from tqdm import tqdm  # Import tqdm for displaying progress bars during batch processing

from mem0 import MemoryClient  # Import MemoryClient to interact with the Mem0 API

load_dotenv()  # Load environment variables from .env file (API keys, org ID, project ID)


# Define custom instructions that guide how Mem0 should extract and format memories
custom_instructions = """
Generate personal memories that follow these guidelines:  # Instructions for the LLM on how to process and store memories

1. Each memory should be self-contained with complete context, including:
   - The person's name, do not use "user" while creating memories
   - Personal details (career aspirations, hobbies, life circumstances)
   - Emotional states and reactions
   - Ongoing journeys or future plans
   - Specific dates when events occurred

2. Include meaningful personal narratives focusing on:
   - Identity and self-acceptance journeys
   - Family planning and parenting
   - Creative outlets and hobbies
   - Mental health and self-care activities
   - Career aspirations and education goals
   - Important life events and milestones

3. Make each memory rich with specific details rather than general statements
   - Include timeframes (exact dates when possible)
   - Name specific activities (e.g., "charity race for mental health" rather than just "exercise")
   - Include emotional context and personal growth elements

4. Extract memories only from user messages, not incorporating assistant responses

5. Format each memory as a paragraph with a clear narrative structure that captures the person's experience, challenges, and aspirations
"""


class MemoryADD:  # Class to handle adding memories to Mem0 from conversation data
    def __init__(self, data_path=None, batch_size=2, is_graph=False):  # Initialize with optional data path, batch size for processing, and graph mode flag
        """
        Initializes the MemoryADD system by setting up the Mem0 client and configuration.
        This constructor establishes the connection to Mem0 API using credentials from environment variables,
        applies custom instructions to guide memory extraction, and optionally loads conversation data.
        The batch_size controls how many messages are processed together for efficiency,
        while is_graph enables relationship tracking between memories for more sophisticated memory storage.
        """
        self.mem0_client = MemoryClient(  # Create a Mem0 client instance to interact with the API
            api_key=os.getenv("MEM0_API_KEY"),  # Get API key from environment variables for authentication
            org_id=os.getenv("MEM0_ORGANIZATION_ID"),  # Get organization ID from environment variables
            project_id=os.getenv("MEM0_PROJECT_ID"),  # Get project ID from environment variables to scope memories to this project
        )

        self.mem0_client.update_project(custom_instructions=custom_instructions)  # Update the project with custom instructions to guide memory extraction
        self.batch_size = batch_size  # Store batch size - how many messages to process together (default: 2)
        self.data_path = data_path  # Store the path to the conversation data JSON file
        self.data = None  # Initialize data as None, will be loaded later if path is provided
        self.is_graph = is_graph  # Store whether to use graph-based memory storage (enables relationship tracking)
        if data_path:  # Check if a data path was provided
            self.load_data()  # If yes, automatically load the data from the file

    def load_data(self):  # Method to load conversation data from JSON file
        """
        Loads conversation data from a JSON file into memory.
        This method reads the JSON file specified in data_path and deserializes it into a Python data structure.
        The loaded data typically contains multiple conversations with speaker information, messages, and timestamps.
        Using a context manager ensures the file is properly closed even if an error occurs during reading.
        """
        with open(self.data_path, "r") as f:  # Open the JSON file in read mode using context manager (auto-closes file)
            self.data = json.load(f)  # Parse JSON file and store the conversation data in self.data
        return self.data  # Return the loaded data for immediate use if needed

    def add_memory(self, user_id, message, metadata, retries=3):  # Method to add memories with retry logic (default: 3 attempts)
        """
        Adds memories to Mem0 with built-in retry logic for resilience against transient API failures.
        This method implements an exponential backoff strategy - if the API call fails, it waits 1 second before retrying.
        The retry mechanism helps handle temporary network issues, rate limits, or service hiccups.
        On the final retry attempt, any exception is re-raised to alert the caller of a persistent failure.
        Graph mode can be enabled to store memories with relationship tracking between different memory nodes.
        """
        for attempt in range(retries):  # Loop through retry attempts (0, 1, 2 for 3 retries)
            try:  # Attempt to add the memory, catching any exceptions
                _ = self.mem0_client.add(  # Call Mem0 API to add memories (underscore indicates we don't use the return value)
                    message, user_id=user_id, version="v2", metadata=metadata, enable_graph=self.is_graph  # Pass message content, user ID, API version, metadata (timestamp), and graph mode flag
                )
                return  # If successful, exit the method immediately
            except Exception as e:  # If an error occurs during the API call
                if attempt < retries - 1:  # Check if we have more retry attempts remaining
                    time.sleep(1)  # Wait 1 second before retrying to avoid overwhelming the API
                    continue  # Skip to the next retry attempt
                else:  # If this was the last retry attempt
                    raise e  # Re-raise the exception to propagate the error up

    def add_memories_for_speaker(self, speaker, messages, timestamp, desc):  # Method to add all memories for a specific speaker in batches
        """
        Processes and adds all messages for a single speaker in configurable batches with progress tracking.
        Batching is crucial for efficiency - instead of making individual API calls for each message,
        multiple messages are grouped together, reducing network overhead and API call count.
        The tqdm progress bar provides real-time feedback on processing status, which is helpful for large datasets.
        All messages in a batch share the same timestamp metadata to maintain temporal context.
        """
        for i in tqdm(range(0, len(messages), self.batch_size), desc=desc):  # Loop through messages in batch_size increments with progress bar
            batch_messages = messages[i : i + self.batch_size]  # Extract a batch of messages (e.g., messages 0-2, then 2-4, etc.)
            self.add_memory(speaker, batch_messages, metadata={"timestamp": timestamp})  # Add the batch of messages for this speaker with timestamp metadata

    def process_conversation(self, item, idx):  # Method to process a single conversation between two speakers
        """
        Processes a two-person conversation by creating personalized memory perspectives for each participant.
        The key concept: each speaker gets their own view where their messages are 'user' role and the other's are 'assistant'.
        This role reversal ensures memories are extracted from each person's perspective, capturing what they learned about the other.
        Threading parallelizes memory addition for both speakers, cutting processing time roughly in half.
        Old memories are deleted first to ensure clean, duplicate-free memory storage on each run.
        """
        conversation = item["conversation"]  # Extract the conversation dictionary from the data item
        speaker_a = conversation["speaker_a"]  # Get the name/ID of the first speaker
        speaker_b = conversation["speaker_b"]  # Get the name/ID of the second speaker

        speaker_a_user_id = f"{speaker_a}_{idx}"  # Create unique user ID for speaker A by appending conversation index
        speaker_b_user_id = f"{speaker_b}_{idx}"  # Create unique user ID for speaker B by appending conversation index

        # Delete all existing memories for both users to start fresh (avoid duplicates from previous runs)
        self.mem0_client.delete_all(user_id=speaker_a_user_id)  # Remove all memories associated with speaker A's user ID
        self.mem0_client.delete_all(user_id=speaker_b_user_id)  # Remove all memories associated with speaker B's user ID

        for key in conversation.keys():  # Iterate through all keys in the conversation dictionary
            if key in ["speaker_a", "speaker_b"] or "date" in key or "timestamp" in key:  # Skip metadata keys (speaker names, dates, timestamps)
                continue  # Move to the next key without processing

            date_time_key = key + "_date_time"  # Construct the key name for the timestamp field (e.g., "chat_1_date_time")
            timestamp = conversation[date_time_key]  # Get the timestamp for when this chat segment occurred
            chats = conversation[key]  # Get the list of chat messages for this conversation segment

            messages = []  # Initialize empty list to store messages from speaker A's perspective
            messages_reverse = []  # Initialize empty list to store messages from speaker B's perspective (reversed roles)
            for chat in chats:  # Loop through each individual chat message in this segment
                if chat["speaker"] == speaker_a:  # Check if speaker A sent this message
                    messages.append({"role": "user", "content": f"{speaker_a}: {chat['text']}"})  # For speaker A's view, their messages are "user" role
                    messages_reverse.append({"role": "assistant", "content": f"{speaker_a}: {chat['text']}"})  # For speaker B's view, speaker A's messages are "assistant" role
                elif chat["speaker"] == speaker_b:  # Check if speaker B sent this message
                    messages.append({"role": "assistant", "content": f"{speaker_b}: {chat['text']}"})  # For speaker A's view, speaker B's messages are "assistant" role
                    messages_reverse.append({"role": "user", "content": f"{speaker_b}: {chat['text']}"})  # For speaker B's view, their messages are "user" role
                else:  # If the speaker is neither A nor B (data error)
                    raise ValueError(f"Unknown speaker: {chat['speaker']}")  # Raise error with the unknown speaker name

            # Add memories for both speakers concurrently using separate threads for efficiency
            thread_a = threading.Thread(  # Create a new thread for speaker A's memory addition
                target=self.add_memories_for_speaker,  # Set the method to run in this thread
                args=(speaker_a_user_id, messages, timestamp, "Adding Memories for Speaker A"),  # Pass arguments: user ID, messages from A's perspective, timestamp, and progress bar description
            )
            thread_b = threading.Thread(  # Create a new thread for speaker B's memory addition
                target=self.add_memories_for_speaker,  # Set the method to run in this thread
                args=(speaker_b_user_id, messages_reverse, timestamp, "Adding Memories for Speaker B"),  # Pass arguments: user ID, messages from B's perspective, timestamp, and progress bar description
            )

            thread_a.start()  # Start executing speaker A's thread (runs in parallel)
            thread_b.start()  # Start executing speaker B's thread (runs in parallel)
            thread_a.join()  # Wait for speaker A's thread to complete before continuing
            thread_b.join()  # Wait for speaker B's thread to complete before continuing

        print("Messages added successfully")  # Print confirmation message after all conversation segments are processed

    def process_all_conversations(self, max_workers=10):  # Method to process all conversations using parallel execution (default: 10 workers)
        """
        Orchestrates parallel processing of all conversations using a thread pool for maximum efficiency.
        The ThreadPoolExecutor manages up to 10 concurrent conversation processing tasks by default,
        dramatically reducing total processing time compared to sequential execution.
        Each conversation is submitted as an independent task, and the executor handles thread allocation and scheduling.
        The method blocks until all conversations complete, ensuring data integrity before returning control.
        """
        if not self.data:  # Check if conversation data has been loaded
            raise ValueError("No data loaded. Please set data_path and call load_data() first.")  # Raise error if no data is available
        with ThreadPoolExecutor(max_workers=max_workers) as executor:  # Create thread pool with specified number of workers for parallel processing
            futures = [executor.submit(self.process_conversation, item, idx) for idx, item in enumerate(self.data)]  # Submit all conversations to the thread pool, creating a future object for each

            for future in futures:  # Loop through all submitted futures
                future.result()  # Wait for each future to complete and get its result (blocks until done, propagates any exceptions)
