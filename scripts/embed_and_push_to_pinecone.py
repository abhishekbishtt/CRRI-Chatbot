# scripts/embed_and_push_to_pinecone.py
"""
Script to load the merged knowledge base, embed it using Hugging Face model,
and push it to an existing Pinecone index using LangChain.

This script reads the merged JSONL file, loads the chunks (page_content and metadata),
initializes a Hugging Face embedding model, initializes the Pinecone client,
cleans the metadata to ensure Pinecone compatibility, and upserts the chunks
to the specified existing Pinecone index.
"""

import json
from pathlib import Path
import logging
import os
import pickle # Import pickle for serialization check if needed, though json.dumps is often sufficient
# Import Hugging Face embedding model
from langchain_huggingface import HuggingFaceEmbeddings
# Import Pinecone client and LangChain Pinecone integration
import pinecone
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document # Import Document class for LangChain
# Add these lines to load the .env file
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

# --- Configuration ---
PROCESSED_DIR = Path("data/processed")

# Automatically find the latest merged knowledge base file
def get_latest_kb_file():
    """Find the most recent knowledge_base_*.jsonl or merged_knowledge_base_*.jsonl file"""
    kb_files = list(PROCESSED_DIR.glob("knowledge_base_*.jsonl")) + list(PROCESSED_DIR.glob("merged_knowledge_base_*.jsonl"))
    if not kb_files:
        raise FileNotFoundError("No knowledge base files found in data/processed/")
    # Sort by modification time, get the latest
    latest_file = max(kb_files, key=lambda p: p.stat().st_mtime)
    return latest_file

# Check if file path provided as command line argument
import sys
if len(sys.argv) > 1:
    MERGED_KB_FILEPATH = Path(sys.argv[1])
    if not MERGED_KB_FILEPATH.exists():
        raise FileNotFoundError(f"Specified file not found: {MERGED_KB_FILEPATH}")
else:
    MERGED_KB_FILEPATH = get_latest_kb_file()

# Pinecone Configuration - Update these values
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") # Get from environment variable loaded by load_dotenv()
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable not found in .env file.")
PINECONE_INDEX_NAME = "crri-kb-index-hf" # The name of your *existing* Pinecone index

# Hugging Face Model Configuration
HF_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2" # Model name for HF embeddings
# Dimension is implied by the model choice (all-MiniLM-L6-v2 -> 384)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/embed_and_push.log"), # Log to a file
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_metadata(metadata_dict: dict) -> dict:
    """
    Cleans a metadata dictionary to ensure all values are compatible with Pinecone.

    Pinecone allows: string, number, boolean, list of strings.
    This function converts incompatible types (like nested dicts, lists with non-strings)
    into strings using json.dumps.
    """
    cleaned_meta = {}
    for key, value in metadata_dict.items():
        # Check the type of the value
        if isinstance(value, (str, int, float, bool)):
            # Keep simple types as they are
            cleaned_meta[key] = value
        elif isinstance(value, list):
            # Check if it's a list of strings
            if all(isinstance(item, str) for item in value):
                # It's a list of strings, keep as is
                cleaned_meta[key] = value
            else:
                # It's a list with non-string items, convert the whole list to a string
                try:
                    cleaned_meta[key] = json.dumps(value, ensure_ascii=False) # Serialize list
                except TypeError:
                    # If json.dumps fails, convert to string representation
                    cleaned_meta[key] = str(value)
        elif isinstance(value, dict):
            # It's a dictionary, convert it to a string
            try:
                cleaned_meta[key] = json.dumps(value, ensure_ascii=False) # Serialize dict
            except TypeError:
                # If json.dumps fails, convert to string representation
                cleaned_meta[key] = str(value)
        else:
            # It's some other type (e.g., None), convert to string
            cleaned_meta[key] = str(value)

    return cleaned_meta


def load_merged_chunks_jsonl(filepath: Path):
    """Load chunks from the merged JSONL file."""
    logger.info(f"Loading chunks from JSONL file: {filepath}")
    chunks = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    try:
                        chunk_data = json.loads(line)
                        chunks.append(chunk_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping malformed JSON line {line_num} in {filepath}: {e}")
    except FileNotFoundError:
        logger.error(f"Merged knowledge base file not found: {filepath}")
        return []
    except Exception as e:
        logger.error(f"Error reading merged knowledge base file {filepath}: {e}")
        return []

    logger.info(f"Loaded {len(chunks)} chunks from {filepath}")
    return chunks

def upsert_to_pinecone_langchain(documents: list, embeddings_model, index_name: str):
    """Upsert documents to the specified *existing* Pinecone index using LangChain."""
    logger.info(f"Upserting {len(documents)} documents to *existing* Pinecone index '{index_name}' using LangChain...")

    if not documents:
        logger.error("No documents provided to upsert.")
        return

    try:
        # Use LangChain's PineconeVectorStore integration to upsert to an existing index
        # The metadata should now be compatible after cleaning
        vector_store = PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings_model, # Use the Hugging Face embedding model
            index_name=index_name,
            # pinecone_api_key=PINECONE_API_KEY # Often not needed if set globally/env
        )

        logger.info(f"Successfully upserted documents to existing Pinecone index '{index_name}'.")

    except Exception as e:
        logger.error(f"Error upserting to existing Pinecone index via LangChain: {e}")
        raise # Re-raise to potentially stop the script if this step fails critically

def main():
    """Main execution function."""
    logger.info("Starting embed and push process to existing Pinecone index...")

    # 1. Load the merged chunks from the JSONL file
    if not MERGED_KB_FILEPATH.exists():
        logger.error(f"Merged knowledge base JSONL file does not exist: {MERGED_KB_FILEPATH}")
        logger.info("Please run the merge script (scripts/merge_processed_data.py) first.")
        return

    chunks = load_merged_chunks_jsonl(MERGED_KB_FILEPATH)
    if not chunks:
        logger.error("Failed to load chunks. Exiting.")
        return

    # 2. Initialize Hugging Face embedding model
    logger.info(f"Loading Hugging Face embedding model: {HF_EMBEDDING_MODEL_NAME}")
    try:
        # Use the HuggingFaceBgeEmbeddings (or potentially HuggingFaceEmbeddings from langchain_huggingface)
        # Note: LangChain might show a deprecation warning for HuggingFaceBgeEmbeddings,
        # suggesting HuggingFaceEmbeddings from langchain_huggingface. This is fine for now.
        embeddings_model = HuggingFaceEmbeddings(
            model_name=HF_EMBEDDING_MODEL_NAME,
            # model_kwargs={"device": "cpu"}, # Optional: specify device
            # encode_kwargs={"normalize_embeddings": True} # Optional: normalize embeddings
        )
        logger.info("Hugging Face embedding model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading Hugging Face embedding model: {e}")
        return

    # 3. Initialize Pinecone client and verify index exists
    logger.info("Initializing Pinecone client...")
    try:
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
        logger.info(f"Verifying access to Pinecone index: {PINECONE_INDEX_NAME}")
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
             logger.error(f"Index '{PINECONE_INDEX_NAME}' does not exist. Please create it first using create_pinecone_index.py")
             return
        logger.info(f"Index '{PINECONE_INDEX_NAME}' verified.")

        # Delete all existing vectors to ensure replacement
        logger.info(f"Deleting all existing vectors in index '{PINECONE_INDEX_NAME}'...")
        index = pc.Index(PINECONE_INDEX_NAME)
        index.delete(delete_all=True)
        logger.info("Successfully deleted all existing vectors.")

    except Exception as e:
        logger.error(f"Error initializing Pinecone client, verifying index, or deleting vectors: {e}")
        return


    # 4. Convert chunks to LangChain Document objects, cleaning metadata
    # The chunks from your merge script should have 'page_content' and 'metadata'
    logger.info("Converting chunks to LangChain Document objects and cleaning metadata...")
    documents = []
    for i, chunk in enumerate(chunks):
        # Ensure the chunk has the expected keys from the merge process
        page_content = chunk.get("page_content", "")
        raw_metadata = chunk.get("metadata", {})

        # Clean the metadata dictionary
        cleaned_metadata = clean_metadata(raw_metadata)

        if page_content: # Only add documents with content
            doc = Document(
                page_content=page_content,
                metadata=cleaned_metadata, # Use the cleaned metadata
                # id=f"doc_{i}" # Optional: Add a unique ID if needed, LangChain/Pinecone can generate
            )
            documents.append(doc)
        else:
            logger.debug(f"Skipping chunk {i} with no page_content.")

    logger.info(f"Converted {len(documents)} chunks to Document objects with cleaned metadata.")

    # 5. Upsert the documents to the *existing* Pinecone index using LangChain
    upsert_to_pinecone_langchain(documents, embeddings_model, PINECONE_INDEX_NAME)

    logger.info("Embed and push process to existing Pinecone index finished.")

if __name__ == "__main__":
    main()