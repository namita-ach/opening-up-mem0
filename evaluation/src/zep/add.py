# import argparse  # Import argparse for parsing command-line arguments (run_id parameter)
# import json  # Import JSON library for loading conversation data from files
# import os  # Import OS library to access environment variables for API credentials

# from dotenv import load_dotenv  # Import function to load environment variables from .env file
# from tqdm import tqdm  # Import tqdm for displaying progress bars during conversation processing
# from zep_cloud import Message  # Import Message class to structure chat messages for Zep API
# from zep_cloud.client import Zep  # Import Zep client to interact with Zep's memory API

# load_dotenv()  # Load environment variables from .env file (ZEP_API_KEY)


# class ZepAdd:  # Class to handle adding conversation memories to Zep's memory system
#     def __init__(self, data_path=None):  # Initialize with optional path to conversation data JSON file
#         """
#         Initializes the ZepAdd system by setting up the Zep client connection.
#         Creates a Zep client instance using API credentials from environment variables.
#         Optionally loads conversation data if a file path is provided during initialization.
#         Unlike Mem0, Zep uses a session-based memory model where conversations are organized into sessions.
#         """
#         self.zep_client = Zep(api_key=os.getenv("ZEP_API_KEY"))  # Create Zep client instance using API key from environment variables
#         self.data_path = data_path  # Store the path to the conversation data JSON file
#         self.data = None  # Initialize data as None, will be loaded later if path is provided
#         if data_path:  # Check if a data path was provided
#             self.load_data()  # If yes, automatically load the conversation data from the file

#     def load_data(self):  # Method to load conversation data from JSON file into memory
#         """
#         Loads conversation data from a JSON file and stores it for processing.
#         Opens the file using a context manager to ensure proper cleanup.
#         Parses the JSON content into a Python data structure containing conversations.
#         Returns the loaded data for immediate use if needed.
#         """
#         with open(self.data_path, "r") as f:  # Open the JSON file in read mode using context manager (auto-closes file)
#             self.data = json.load(f)  # Parse JSON file and store the conversation data in self.data
#         return self.data  # Return the loaded data for immediate use if needed

#     def process_conversation(self, run_id, item, idx):  # Method to process a single conversation and add it to Zep as a session
#         """
#         Processes one conversation by creating a Zep user and session, then adding all messages.
#         Unlike Mem0's dual-perspective approach, Zep stores the entire conversation in a single session.
#         Creates unique user and session IDs using the run_id and conversation index for tracking.
#         Messages are added sequentially with timestamps prepended to maintain temporal context.
#         Zep automatically extracts memories from the conversation flow rather than requiring role reversal.
#         """
#         conversation = item["conversation"]  # Extract the conversation dictionary from the data item

#         user_id = f"run_id_{run_id}_experiment_user_{idx}"  # Create unique user ID combining run identifier and conversation index
#         session_id = f"run_id_{run_id}_experiment_session_{idx}"  # Create unique session ID combining run identifier and conversation index

#         # # delete all memories for the two users (commented out to preserve existing data)
#         # self.zep_client.user.delete(user_id=user_id)  # Would delete the user and all associated data
#         # self.zep_client.memory.delete(session_id=session_id)  # Would delete the session and all messages

#         self.zep_client.user.add(user_id=user_id)  # Create a new user in Zep with the generated user ID
#         self.zep_client.memory.add_session(  # Create a new memory session for this user
#             user_id=user_id,  # Associate the session with the user ID
#             session_id=session_id,  # Assign the unique session ID for this conversation
#         )

#         print("Starting to add memories... for user", user_id)  # Log which user's memories are being processed
#         for key in tqdm(conversation.keys(), desc=f"Processing user {user_id}"):  # Loop through all conversation segments with progress bar
#             if key in ["speaker_a", "speaker_b"] or "date" in key:  # Skip metadata keys (speaker names and date fields)
#                 continue  # Move to the next key without processing

#             date_time_key = key + "_date_time"  # Construct the key name for the timestamp field (e.g., "chat_1_date_time")
#             timestamp = conversation[date_time_key]  # Get the timestamp for when this conversation segment occurred
#             chats = conversation[key]  # Get the list of chat messages for this conversation segment

#             for chat in tqdm(chats, desc=f"Adding chats for {key}", leave=False):  # Loop through each message in this segment with nested progress bar
#                 message = Message(
#                     role="user",  # Zep expects 'user' or 'assistant', not speaker name
#                     role_type="user",
#                     content=f"{timestamp}: [{chat['speaker']}] {chat['text']}",  # Preserve speaker name in content
#                 )
#                 await self.zep_client.memory.add(  # Add a single message to the Zep session
#                     session_id=session_id,  # Specify which session this message belongs to
#                     messages=[  # Provide a list of messages (single message in this case)
#                         message,
#                     ],
#                 )

#     def process_all_conversations(self, run_id):  # Method to process all conversations from the loaded data
#         """
#         Processes all conversations from the loaded dataset sequentially.
#         Validates that data has been loaded before attempting to process.
#         Currently only processes the first conversation (idx == 0) for testing purposes.
#         The run_id parameter allows multiple experimental runs without ID conflicts.
#         Could be modified to process all conversations by removing the idx == 0 condition.
#         """
#         if not self.data:  # Check if conversation data has been loaded
#             raise ValueError("No data loaded. Please set data_path and call load_data() first.")  # Raise error if no data is available
#         for idx, item in tqdm(enumerate(self.data)):  # Loop through all conversations with progress bar and index
#             if idx == 0:  # Only process the first conversation (test mode)
#                 self.process_conversation(run_id, item, idx)  # Process this conversation with the run ID and index


# if __name__ == "__main__":  # Execute this block only when the script is run directly (not imported)
#     parser = argparse.ArgumentParser()  # Create argument parser to handle command-line arguments
#     parser.add_argument("--run_id", type=str, required=True)  # Define required run_id argument to identify this experimental run
#     args = parser.parse_args()  # Parse the command-line arguments provided by the user
#     zep_add = ZepAdd(data_path="/Users/namita.achyuthan/Documents/opening-up-mem0/evaluation/dataset/locomo10.json")  # Create ZepAdd instance with path to the dataset file
#     zep_add.process_all_conversations(args.run_id)  # Process all conversations using the provided run_id


import argparse
import json
import os
import uuid
import asyncio
from dotenv import load_dotenv
from tqdm import tqdm
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

load_dotenv()

class ZepAdd:
    def __init__(self, data_path=None):
        self.zep_client = AsyncZep(api_key=os.getenv("ZEP_API_KEY"))
        self.data_path = data_path
        self.data = None
        if data_path:
            self.load_data()

    def load_data(self):
        with open(self.data_path, "r") as f:
            self.data = json.load(f)
        return self.data

    async def process_conversation(self, run_id, item, idx):
        conversation = item["conversation"]
        user_id = f"run_id_{run_id}_experiment_user_{idx}"
        thread_id = f"run_id_{run_id}_experiment_thread_{idx}"

        # Create user if not exists
        try:
            await self.zep_client.user.get(user_id=user_id)
        except Exception:
            await self.zep_client.user.add(user_id=user_id)

        # Create thread/session
        try:
            await self.zep_client.thread.get(thread_id=thread_id)
        except Exception:
            await self.zep_client.thread.create(thread_id=thread_id, user_id=user_id)

        print("Starting to add memories... for user", user_id)
        for key in tqdm(conversation.keys(), desc=f"Processing user {user_id}"):
            if key in ["speaker_a", "speaker_b"] or "date" in key:
                continue
            date_time_key = key + "_date_time"
            timestamp = conversation[date_time_key]
            chats = conversation[key]
            for chat in tqdm(chats, desc=f"Adding chats for {key}", leave=False):
                message = Message(
                    role="user",  # Zep expects 'user' or 'assistant', not speaker name
                    role_type="user",
                    content=f"{timestamp}: [{chat['speaker']}] {chat['text']}",  # Preserve speaker name in content
                )
                await self.zep_client.thread.add_messages(
                    thread_id=thread_id,
                    messages=[message],
                )

    async def process_all_conversations(self, run_id):
        if not self.data:
            raise ValueError("No data loaded. Please set data_path and call load_data() first.")
        for idx, item in enumerate(self.data):
            if idx == 0:  # Only process the first conversation (test mode)
                await self.process_conversation(run_id, item, idx)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, required=True)
    args = parser.parse_args()
    zep_add = ZepAdd(data_path="/Users/namita.achyuthan/Documents/opening-up-mem0/evaluation/dataset/locomo10.json")
    await zep_add.process_all_conversations(args.run_id)

if __name__ == "__main__":
    asyncio.run(main())