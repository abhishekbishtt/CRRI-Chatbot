#!/bin/bash
# Production-grade automated data pipeline
# Runs: Cleanup → Scrape → Process → Upload to Pinecone

set -e  # Exit on any error

# Configuration
PROJECT_DIR="/Users/abhishekbisht/CRRI-Chatbot"
LOG_DIR="$PROJECT_DIR/data/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Starting CRRI Data Pipeline"
log "========================================="

# STEP 1: Cleanup old data
log "STEP 1: Cleaning up old data files..."
cd "$PROJECT_DIR"
conda run -n Chatbot python scripts/cleanup_old_data.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "✓ Cleanup completed"
else
    log "✗ Cleanup failed (continuing anyway)"
fi

# STEP 2: Run all scrapers
log "STEP 2: Running scrapers..."

log "  - Scraping staff & organizational data..."
conda run -n Chatbot scrapy crawl crri_staff_org -O "data/raw/scraped_staff_org_$(date +%Y%m%d_%H%M%S).json" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "    ✓ Staff scraper completed"
else
    log "    ✗ Staff scraper failed"
    exit 1
fi

log "  - Scraping news..."
conda run -n Chatbot python src/scraper/news_scraper.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "    ✓ News scraper completed"
else
    log "    ✗ News scraper failed"
    exit 1
fi

log "  - Scraping equipment..."
conda run -n Chatbot scrapy crawl crri_equipment -O "data/raw/scraped_equipment_$(date +%Y%m%d_%H%M%S).json" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "    ✓ Equipment scraper completed"
else
    log "    ✗ Equipment scraper failed"
    exit 1
fi

log "  - Scraping tenders..."
conda run -n Chatbot python src/scraper/tenders_events_scraper.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "    ✓ Tenders scraper completed"
else
    log "    ✗ Tenders scraper failed"
    exit 1
fi

log "  - Scraping events..."
conda run -n Chatbot python src/scraper/events_scraper.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "    ✓ Events scraper completed"
else
    log "    ✗ Events scraper failed"
    exit 1
fi

log "✓ All scrapers completed"

# STEP 3: Process data
log "STEP 3: Processing scraped data..."
conda run -n Chatbot python scripts/process_data_pipeline.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "✓ Data processing completed"
else
    log "✗ Data processing failed"
    exit 1
fi

# STEP 4: Push to Pinecone
log "STEP 4: Uploading to Pinecone..."
conda run -n Chatbot python scripts/embed_and_push_to_pinecone.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "✓ Pinecone upload completed"
else
    log "✗ Pinecone upload failed"
    exit 1
fi

# STEP 5: Final cleanup (remove old logs)
log "STEP 5: Final cleanup..."
conda run -n Chatbot python scripts/cleanup_old_data.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "✓ Final cleanup completed"
else
    log "✗ Final cleanup failed (non-critical)"
fi

log "========================================="
log "Pipeline completed successfully!"
log "Log file: $LOG_FILE"
log "========================================="
