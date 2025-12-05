# scripts/create_pinecone_index.py
"""
Script to create a Pinecone index for the CRRI RAG system.

This script initializes the Pinecone client using your API key from .env,
checks if the specified index exists, and creates it if necessary
with the correct dimension for the Hugging Face embedding model.
"""

import os
import logging
import pinecone
# Add these lines to load the .env file
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") # Get from environment variable loaded by load_dotenv()
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable not found in .env file.")

# Pinecone Configuration - Update these values as needed
PINECONE_CLOUD = "aws" # e.g., "aws", "gcp", "azure"
PINECONE_REGION = "us-east-1" # e.g., "us-east-1"
PINECONE_INDEX_NAME = "crri-kb-index-hf" # The name of your Pinecone index
HF_EMBEDDING_MODEL_DIMENSION = 384 # Dimension for sentence-transformers/all-MiniLM-L6-v2

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/create_index.log"), # Log to a file
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_index_if_not_exists():
    """Initialize Pinecone client and create the index if it doesn't exist."""
    logger.info("Initializing Pinecone client...")
    try:
        # Initialize Pinecone using the high-level client instance
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
        logger.info("Pinecone client initialized successfully.")

        # Check if index exists using the client instance
        existing_indexes = pc.list_indexes().names() # Use the client instance
        if PINECONE_INDEX_NAME not in existing_indexes:
            logger.info(f"Index '{PINECONE_INDEX_NAME}' does not exist. Creating it with dimension {HF_EMBEDDING_MODEL_DIMENSION}...")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=HF_EMBEDDING_MODEL_DIMENSION,
                metric="cosine",
                spec=pinecone.ServerlessSpec(
                    cloud=PINECONE_CLOUD,
                    region=PINECONE_REGION
                )
            )
            logger.info(f"Index '{PINECONE_INDEX_NAME}' created successfully.")
        else:
            logger.info(f"Index '{PINECONE_INDEX_NAME}' already exists.")

    except Exception as e:
        logger.error(f"Error initializing Pinecone client or managing index: {e}")
        raise # Re-raise to stop the script if it fails critically

def main():
    """Main execution function."""
    logger.info("Starting Pinecone index creation process...")
    create_index_if_not_exists()
    logger.info("Pinecone index creation process finished.")

if __name__ == "__main__":
    main()