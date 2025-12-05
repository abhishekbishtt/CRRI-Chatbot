# CRRI Chatbot - Automated Data Pipeline

## Overview

Production-grade automated data pipeline that keeps the CRRI Chatbot fresh with the latest data every 2 days. **Zero manual intervention required** after setup.

## What It Does

✅ **Automated Scraping**: Fetches fresh data from CRRI website  
✅ **Smart Cleanup**: Removes old files, keeps only the latest  
✅ **Data Processing**: Converts raw data into clean knowledge base  
✅ **Pinecone Sync**: Updates vector database automatically  
✅ **Zero Accumulation**: No file buildup, project stays clean  

## Quick Start

### 1. Test the Pipeline Manually

```bash
cd /Users/abhishekbisht/CRRI-Chatbot
./scripts/run_full_pipeline.sh
```

This will:
1. Clean up old data files
2. Scrape fresh data from CRRI website
3. Process data into knowledge base
4. Upload to Pinecone
5. Clean up old logs

### 2. Set Up Automation (Optional)

See [CRON_SETUP.md](CRON_SETUP.md) for instructions on setting up automated execution every 2 days.

## File Structure

```
CRRI-Chatbot/
├── data/
│   ├── raw/                    # Raw scraped data
│   │   ├── .gitkeep           # Preserves directory in git
│   │   └── scraped_*.json     # Latest scrapes only (auto-cleaned)
│   │
│   ├── processed/              # Processed knowledge bases
│   │   ├── .gitkeep           # Preserves directory in git
│   │   ├── knowledge_base_*.jsonl  # Latest only (auto-cleaned)
│   │   └── contacts.pdf       # PERMANENT (never deleted)
│   │
│   └── logs/                   # Pipeline execution logs
│       ├── .gitkeep           # Preserves directory in git
│       └── pipeline_*.log     # Last 7 days only (auto-cleaned)
│
└── scripts/
    ├── run_full_pipeline.sh           # Master automation script
    ├── cleanup_old_data.py            # Smart cleanup script
    ├── process_data_pipeline.py       # Data processor
    └── embed_and_push_to_pinecone.py  # Pinecone uploader
```

## Components

### 1. Master Pipeline Script
**File**: `scripts/run_full_pipeline.sh`

Orchestrates the entire pipeline:
- Cleanup → Scrape → Process → Upload → Cleanup
- Error handling and logging
- Exit on any failure to prevent corrupted data

### 2. Cleanup Script
**File**: `scripts/cleanup_old_data.py`

Smart cleanup that:
- Keeps only the latest file for each scraper type
- Preserves `contacts.pdf` (permanent file)
- Removes logs older than 7 days
- Logs all deletions for transparency

### 3. Data Processor
**File**: `scripts/process_data_pipeline.py`

Converts raw scraped data into clean knowledge base.

### 4. Pinecone Uploader
**File**: `scripts/embed_and_push_to_pinecone.py`

Embeds and uploads knowledge base to Pinecone vector database.

## Safety Features

🔒 **Never Deletes Essential Files**
- `contacts.pdf` is permanent and never touched
- Always keeps at least 1 file (the latest)

🔒 **Error Handling**
- Pipeline exits on any error
- Prevents corrupted data from being uploaded
- All errors logged for debugging

🔒 **Transparency**
- Every deletion is logged
- Full pipeline execution logs
- Easy to audit what happened

## Monitoring

### Check Latest Log

```bash
ls -lh data/logs/
tail -f data/logs/pipeline_*.log
```

### Verify Data Files

```bash
# Should have exactly 5 files (latest scrape for each type)
ls -lh data/raw/

# Should have exactly 2 files (latest knowledge_base + contacts.pdf)
ls -lh data/processed/
```

### Check Pinecone

Query your chatbot to verify it has fresh data.

## Manual Operations

### Run Full Pipeline

```bash
./scripts/run_full_pipeline.sh
```

### Run Cleanup Only

```bash
python scripts/cleanup_old_data.py
```

### Run Individual Scrapers

```bash
# Staff & Organization
scrapy crawl crri_staff_org -O data/raw/scraped_staff_org_$(date +%Y%m%d_%H%M%S).json

# News
python src/scraper/news_scraper.py

# Equipment
python src/scraper/equipment_facilities_scraper.py

# Tenders
python src/scraper/tenders_scraper.py

# Events
python src/scraper/events_scraper.py
```

### Process Data Only

```bash
python scripts/process_data_pipeline.py
```

### Upload to Pinecone Only

```bash
conda run -n Chatbot python scripts/embed_and_push_to_pinecone.py
```

## Troubleshooting

### Pipeline Fails

1. Check the latest log file in `data/logs/`
2. Look for error messages
3. Fix the issue
4. Re-run the pipeline

### Scrapers Fail

- Check if CRRI website is accessible
- Verify scraper scripts are up to date
- Check for website structure changes

### Pinecone Upload Fails

- Verify Pinecone API key is set
- Check conda environment is activated
- Verify network connectivity

### Cleanup Issues

- Check file permissions
- Verify directory structure exists
- Review cleanup logs for specific errors

## Git Integration

The `.gitignore` is configured to:
- ✅ Track directory structure (`.gitkeep` files)
- ✅ Track `contacts.pdf` (permanent file)
- ❌ Ignore scraped data files (`.json`)
- ❌ Ignore knowledge bases (`.jsonl`)
- ❌ Ignore log files (`.log`)

This keeps your repository clean while preserving essential files.

## Success Criteria

After running the pipeline, you should have:

✅ Exactly 5 files in `data/raw/` (latest scrape for each type)  
✅ Exactly 2 files in `data/processed/` (latest knowledge_base + contacts.pdf)  
✅ Only logs from last 7 days in `data/logs/`  
✅ Fresh data in Pinecone  
✅ Chatbot responds with up-to-date information  

## Maintenance

This pipeline is designed to be **zero-maintenance**. Once set up with cron:

- Runs automatically every 2 days
- Cleans up after itself
- No manual intervention needed
- Logs everything for monitoring

Just check the logs occasionally to ensure everything is running smoothly.

## Support

If you encounter issues:

1. Check the logs in `data/logs/`
2. Verify all dependencies are installed
3. Test each component individually
4. Review error messages for specific issues

---

**Last Updated**: December 5, 2024  
**Version**: 1.0.0
