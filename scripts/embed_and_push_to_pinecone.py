# scripts/embed_and_push_to_pinecone.py
"""
Script to load the merged knowledge base, embed it using Hugging Face model,
and push it to an existing Pinecone index using LangChain.
"""

import json
from pathlib import Path
import logging
import os
import sys
from langchain_huggingface import HuggingFaceEmbeddings
import pinecone
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PROCESSED_DIR = Path("data/processed")

def get_latest_kb_file():
    """Find the most recent knowledge_base_*.jsonl or merged_knowledge_base_*.jsonl file"""
    kb_files = list(PROCESSED_DIR.glob("knowledge_base_*.jsonl")) + list(PROCESSED_DIR.glob("merged_knowledge_base_*.jsonl"))
    if not kb_files:
        raise FileNotFoundError("No knowledge base files found in data/processed/")
    latest_file = max(kb_files, key=lambda p: p.stat().st_mtime)
    return latest_file

if len(sys.argv) > 1:
    MERGED_KB_FILEPATH = Path(sys.argv[1])
    if not MERGED_KB_FILEPATH.exists():
        raise FileNotFoundError(f"Specified file not found: {MERGED_KB_FILEPATH}")
else:
    MERGED_KB_FILEPATH = get_latest_kb_file()

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable not found in .env file.")
PINECONE_INDEX_NAME = "crri-kb-index-hf"

# Hugging Face Model Configuration
HF_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/embed_and_push.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_metadata(metadata_dict: dict) -> dict:
    """
    Cleans a metadata dictionary to ensure all values are compatible with Pinecone.
    Pinecone allows: string, number, boolean, list of strings.
    """
    cleaned_meta = {}
    for key, value in metadata_dict.items():
        if isinstance(value, (str, int, float, bool)):
            cleaned_meta[key] = value
        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                cleaned_meta[key] = value
            else:
                try:
                    cleaned_meta[key] = json.dumps(value, ensure_ascii=False)
                except TypeError:
                    cleaned_meta[key] = str(value)
        elif isinstance(value, dict):
            try:
                cleaned_meta[key] = json.dumps(value, ensure_ascii=False)
            except TypeError:
                cleaned_meta[key] = str(value)
        else:
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
    """Upsert documents to the specified existing Pinecone index using LangChain."""
    logger.info(f"Upserting {len(documents)} documents to existing Pinecone index '{index_name}'...")

    if not documents:
        logger.error("No documents provided to upsert.")
        return

    try:
        vector_store = PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings_model,
            index_name=index_name,
        )

        logger.info(f"Successfully upserted documents to existing Pinecone index '{index_name}'.")

    except Exception as e:
        logger.error(f"Error upserting to existing Pinecone index via LangChain: {e}")
        raise

def main():
    """Main execution function."""
    logger.info("Starting embed and push process to existing Pinecone index...")

    if not MERGED_KB_FILEPATH.exists():
        logger.error(f"Merged knowledge base JSONL file does not exist: {MERGED_KB_FILEPATH}")
        logger.info("Please run the merge script (scripts/merge_processed_data.py) first.")
        return

    chunks = load_merged_chunks_jsonl(MERGED_KB_FILEPATH)
    if not chunks:
        logger.error("Failed to load chunks. Exiting.")
        return

    logger.info(f"Loading Hugging Face embedding model: {HF_EMBEDDING_MODEL_NAME}")
    try:
        embeddings_model = HuggingFaceEmbeddings(
            model_name=HF_EMBEDDING_MODEL_NAME,
        )
        logger.info("Hugging Face embedding model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading Hugging Face embedding model: {e}")
        return

    logger.info("Initializing Pinecone client...")
    try:
        pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
        logger.info(f"Verifying access to Pinecone index: {PINECONE_INDEX_NAME}")
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
             logger.error(f"Index '{PINECONE_INDEX_NAME}' does not exist. Please create it first using create_pinecone_index.py")
             return
        logger.info(f"Index '{PINECONE_INDEX_NAME}' verified.")

        logger.info(f"Deleting all existing vectors in index '{PINECONE_INDEX_NAME}'...")
        index = pc.Index(PINECONE_INDEX_NAME)
        index.delete(delete_all=True)
        logger.info("Successfully deleted all existing vectors.")

    except Exception as e:
        logger.error(f"Error initializing Pinecone client, verifying index, or deleting vectors: {e}")
        return


    logger.info("Converting chunks to LangChain Document objects and cleaning metadata...")
    documents = []
    for i, chunk in enumerate(chunks):
        page_content = chunk.get("page_content", "")
        raw_metadata = chunk.get("metadata", {})

        cleaned_metadata = clean_metadata(raw_metadata)

        if page_content:
            doc = Document(
                page_content=page_content,
                metadata=cleaned_metadata,
            )
            documents.append(doc)
        else:
            logger.debug(f"Skipping chunk {i} with no page_content.")

    logger.info(f"Converted {len(documents)} chunks to Document objects with cleaned metadata.")

    upsert_to_pinecone_langchain(documents, embeddings_model, PINECONE_INDEX_NAME)

    logger.info("Embed and push process to existing Pinecone index finished.")

if __name__ == "__main__":
    main()