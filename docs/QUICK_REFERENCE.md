# CRRI Pipeline - Quick Reference

## 🚀 Quick Commands

### Run Full Pipeline
```bash
cd /Users/abhishekbisht/CRRI-Chatbot
./scripts/run_full_pipeline.sh
```

### Run Cleanup Only
```bash
python scripts/cleanup_old_data.py
```

### Check Status
```bash
# View data files
ls -lh data/raw/
ls -lh data/processed/

# View latest log
tail -f data/logs/pipeline_*.log
```

## 📁 What Gets Kept

### data/raw/
- ✅ Latest scrape for each type (5 files total)
- ❌ Old scrapes (auto-deleted)

### data/processed/
- ✅ Latest knowledge_base_*.jsonl
- ✅ contacts.pdf (PERMANENT - never deleted)
- ❌ Old knowledge bases (auto-deleted)

### data/logs/
- ✅ Logs from last 7 days
- ❌ Older logs (auto-deleted)

## ⏰ Automation (Optional)

### Set Up Cron Job
```bash
crontab -e
```

Add this line:
```cron
0 2 */2 * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

### Check Cron Job
```bash
crontab -l
```

## 🔍 Troubleshooting

### Pipeline Failed?
```bash
# Check the log
tail -100 data/logs/pipeline_*.log

# Run steps manually
python scripts/cleanup_old_data.py
scrapy crawl crri_staff_org -O data/raw/scraped_staff_org_$(date +%Y%m%d_%H%M%S).json
python scripts/process_data_pipeline.py
conda run -n Chatbot python scripts/embed_and_push_to_pinecone.py
```

### Too Many Files?
```bash
# Run cleanup
python scripts/cleanup_old_data.py
```

## 📚 Full Documentation

- **Pipeline Overview:** `PIPELINE_README.md`
- **Cron Setup:** `CRON_SETUP.md`
- **Implementation Status:** `IMPLEMENTATION_CHECKLIST.md`

## ✅ Expected Results

After running pipeline:
- 5 files in `data/raw/` (latest scrapes)
- 2 data files in `data/processed/` (knowledge_base + contacts.pdf)
- Fresh data in Pinecone
- Chatbot has up-to-date information
