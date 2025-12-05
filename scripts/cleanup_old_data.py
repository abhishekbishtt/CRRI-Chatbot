"""
Smart cleanup script that deletes old data files while preserving essentials.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Dict, List
import re

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_DIR / "data" / "processed"
LOG_DIRS = [PROJECT_DIR / "data" / "logs", PROCESSED_DATA_DIR]


def cleanup_raw_data():
    """
    Delete old raw scraped files, keep only the latest for each type.
    
    Logic:
    1. Find all files matching pattern: scraped_*.json in data/raw/
    2. Group by type: staff_org, news, equipment, tenders, events
    3. For each type, keep ONLY the most recent file (by timestamp in filename)
    4. DELETE all older files
    """
    logger.info("Starting raw data cleanup...")
    
    if not RAW_DATA_DIR.exists():
        logger.warning(f"Raw data directory does not exist: {RAW_DATA_DIR}")
        return
    
    # Pattern to match scraped files: scraped_<type>_<timestamp>.json
    pattern = re.compile(r'scraped_(.+?)_(\d{8}_\d{6})\.json')
    
    # Group files by type
    files_by_type: Dict[str, List[tuple]] = {}
    
    for file_path in RAW_DATA_DIR.glob("scraped_*.json"):
        match = pattern.match(file_path.name)
        if match:
            file_type = match.group(1)
            timestamp = match.group(2)
            
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            
            files_by_type[file_type].append((timestamp, file_path))
    
    # For each type, keep only the latest file
    total_deleted = 0
    for file_type, files in files_by_type.items():
        if len(files) <= 1:
            logger.info(f"Type '{file_type}': Only 1 file found, keeping it")
            continue
        
        # Sort by timestamp (descending)
        files.sort(key=lambda x: x[0], reverse=True)
        
        # Keep the first (latest), delete the rest
        latest_file = files[0][1]
        logger.info(f"Type '{file_type}': Keeping latest file: {latest_file.name}")
        
        for timestamp, file_path in files[1:]:
            try:
                file_path.unlink()
                logger.info(f"  Deleted: {file_path.name}")
                total_deleted += 1
            except Exception as e:
                logger.error(f"  Failed to delete {file_path.name}: {e}")
    
    logger.info(f"Raw data cleanup completed. Deleted {total_deleted} old files.")


def cleanup_processed_data():
    """
    Delete old processed knowledge bases and PDF contacts, keep only the latest.
    
    Logic:
    1. Find all files matching: knowledge_base_*.jsonl in data/processed/
    2. Keep ONLY the most recent file (by timestamp)
    3. DELETE all older files
    4. Also clean up old processed_pdf_contacts_*.jsonl files
    5. CRITICAL: contacts.pdf in data/raw/ is permanent (never touched)
    """
    logger.info("Starting processed data cleanup...")
    
    if not PROCESSED_DATA_DIR.exists():
        logger.warning(f"Processed data directory does not exist: {PROCESSED_DATA_DIR}")
        return
    
    total_deleted = 0
    
    # Clean up knowledge bases
    pattern = re.compile(r'knowledge_base_(\d{8}_\d{6})\.jsonl')
    knowledge_bases = []
    
    for file_path in PROCESSED_DATA_DIR.glob("knowledge_base_*.jsonl"):
        match = pattern.match(file_path.name)
        if match:
            timestamp = match.group(1)
            knowledge_bases.append((timestamp, file_path))
    
    if len(knowledge_bases) > 1:
        knowledge_bases.sort(key=lambda x: x[0], reverse=True)
        latest_kb = knowledge_bases[0][1]
        logger.info(f"Keeping latest knowledge base: {latest_kb.name}")
        
        for timestamp, file_path in knowledge_bases[1:]:
            try:
                file_path.unlink()
                logger.info(f"  Deleted: {file_path.name}")
                total_deleted += 1
            except Exception as e:
                logger.error(f"  Failed to delete {file_path.name}: {e}")
    elif len(knowledge_bases) == 1:
        logger.info(f"Only 1 knowledge base found, keeping it: {knowledge_bases[0][1].name}")
    
    # Clean up processed PDF contacts
    pdf_pattern = re.compile(r'processed_pdf_contacts_(\d{8}_\d{6})\.jsonl')
    pdf_contacts = []
    
    for file_path in PROCESSED_DATA_DIR.glob("processed_pdf_contacts_*.jsonl"):
        match = pdf_pattern.match(file_path.name)
        if match:
            timestamp = match.group(1)
            pdf_contacts.append((timestamp, file_path))
    
    if len(pdf_contacts) > 1:
        pdf_contacts.sort(key=lambda x: x[0], reverse=True)
        latest_pdf = pdf_contacts[0][1]
        logger.info(f"Keeping latest PDF contacts: {latest_pdf.name}")
        
        for timestamp, file_path in pdf_contacts[1:]:
            try:
                file_path.unlink()
                logger.info(f"  Deleted: {file_path.name}")
                total_deleted += 1
            except Exception as e:
                logger.error(f"  Failed to delete {file_path.name}: {e}")
    elif len(pdf_contacts) == 1:
        logger.info(f"Only 1 PDF contacts file found, keeping it: {pdf_contacts[0][1].name}")
    
    logger.info(f"Processed data cleanup completed. Deleted {total_deleted} old files.")
    logger.info("Note: contacts.pdf in data/raw/ is permanent and was not touched")



def cleanup_logs():
    """
    Delete old log files to prevent buildup.
    
    Logic:
    1. Find all *.log files in data/logs/ and data/processed/
    2. DELETE logs older than 7 days
    3. Keep recent logs for debugging
    """
    logger.info("Starting log cleanup...")
    
    cutoff_date = datetime.now() - timedelta(days=7)
    total_deleted = 0
    
    for log_dir in LOG_DIRS:
        if not log_dir.exists():
            logger.warning(f"Log directory does not exist: {log_dir}")
            continue
        
        for log_file in log_dir.glob("*.log"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    log_file.unlink()
                    logger.info(f"  Deleted old log: {log_file.name} (modified: {mtime.strftime('%Y-%m-%d')})")
                    total_deleted += 1
            except Exception as e:
                logger.error(f"  Failed to process {log_file.name}: {e}")
    
    logger.info(f"Log cleanup completed. Deleted {total_deleted} old log files (>7 days).")


def main():
    """Run all cleanup functions with logging."""
    logger.info("=" * 50)
    logger.info("Starting CRRI Data Cleanup")
    logger.info("=" * 50)
    
    try:
        cleanup_raw_data()
        cleanup_processed_data()
        cleanup_logs()
        
        logger.info("=" * 50)
        logger.info("Cleanup completed successfully!")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"Cleanup failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
