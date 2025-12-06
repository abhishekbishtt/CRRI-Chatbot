"""
Cleanup script that deletes old data files while preserving essentials.
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
    """Delete old raw scraped files, keep only the latest for each type."""
    logger.info("Starting raw data cleanup...")
    
    if not RAW_DATA_DIR.exists():
        logger.warning(f"Raw data directory does not exist: {RAW_DATA_DIR}")
        return
    
    pattern = re.compile(r'scraped_(.+?)_(\d{8}_\d{6})\.json')
    
    files_by_type: Dict[str, List[tuple]] = {}
    
    for file_path in RAW_DATA_DIR.glob("scraped_*.json"):
        match = pattern.match(file_path.name)
        if match:
            file_type = match.group(1)
            timestamp = match.group(2)
            
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            
            files_by_type[file_type].append((timestamp, file_path))
    
    total_deleted = 0
    for file_type, files in files_by_type.items():
        if len(files) <= 1:
            logger.info(f"Type '{file_type}': Only 1 file found, keeping it")
            continue
        
        files.sort(key=lambda x: x[0], reverse=True)
        
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
    """Delete old processed knowledge bases, merged databases, and PDF contacts."""
    logger.info("Starting processed data cleanup...")
    
    if not PROCESSED_DATA_DIR.exists():
        logger.warning(f"Processed data directory does not exist: {PROCESSED_DATA_DIR}")
        return
        
    ARCHIVE_DIR = PROCESSED_DATA_DIR / "archive"
    
    patterns = {
        'knowledge_base': re.compile(r'knowledge_base_(\d{8}_\d{6})\.jsonl'),
        'merged_knowledge_base': re.compile(r'merged_knowledge_base_(\d{8}_\d{6})\.jsonl'),
        'processed_pdf_contacts': re.compile(r'processed_pdf_contacts_(\d{8}_\d{6})\.jsonl'),
        'processed_chunks': re.compile(r'processed_chunks_(\d{8}_\d{6})\.jsonl')
    }
    
    total_deleted = 0
    
    for file_type, pattern in patterns.items():
        found_files = []
        
        for file_path in PROCESSED_DATA_DIR.glob("*.jsonl"):
            match = pattern.match(file_path.name)
            if match:
                timestamp = match.group(1)
                found_files.append((timestamp, file_path))
                
        if ARCHIVE_DIR.exists():
            for file_path in ARCHIVE_DIR.glob("*.jsonl"):
                match = pattern.match(file_path.name)
                if match:
                    timestamp = match.group(1)
                    found_files.append((timestamp, file_path))
        
        if not found_files:
            continue
            
        found_files.sort(key=lambda x: x[0], reverse=True)
        
        latest_file = found_files[0][1]
        logger.info(f"Type '{file_type}': Keeping latest file: {latest_file.name}")
        
        for timestamp, file_path in found_files[1:]:
            try:
                file_path.unlink()
                logger.info(f"  Deleted: {file_path.name}")
                total_deleted += 1
            except Exception as e:
                logger.error(f"  Failed to delete {file_path.name}: {e}")

    logger.info(f"Processed data cleanup completed. Deleted {total_deleted} old files.")
    logger.info("Note: contacts.pdf in data/raw/ is permanent and was not touched")


def cleanup_logs():
    """Delete old log files to prevent buildup."""
    logger.info("Starting log cleanup...")
    
    cutoff_date = datetime.now() - timedelta(days=7)
    total_deleted = 0
    
    for log_dir in LOG_DIRS:
        if not log_dir.exists():
            logger.warning(f"Log directory does not exist: {log_dir}")
            continue
        
        for log_file in log_dir.glob("*.log"):
            try:
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
