# Cron Job Setup Guide

## Automated Pipeline Execution

This guide explains how to set up automated execution of the CRRI data pipeline every 2 days.

## Prerequisites

- Ensure the pipeline script is executable:
  ```bash
  chmod +x /Users/abhishekbisht/CRRI-Chatbot/scripts/run_full_pipeline.sh
  ```

## Setting Up the Cron Job

### 1. Open Crontab Editor

```bash
crontab -e
```

### 2. Add the Following Line

```cron
# Run CRRI data pipeline every 2 days at 2 AM
0 2 */2 * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

**Cron Schedule Breakdown:**
- `0` - Minute (0 = top of the hour)
- `2` - Hour (2 AM)
- `*/2` - Day of month (every 2 days)
- `*` - Month (every month)
- `*` - Day of week (every day of the week)

### 3. Save and Exit

- If using vim: Press `ESC`, then type `:wq` and press `ENTER`
- If using nano: Press `CTRL+X`, then `Y`, then `ENTER`

### 4. Verify Cron Job

```bash
crontab -l
```

You should see your cron job listed.

## Alternative Schedules

### Run Every Day at 2 AM
```cron
0 2 * * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

### Run Every 3 Days at 2 AM
```cron
0 2 */3 * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

### Run Twice a Week (Monday and Thursday at 2 AM)
```cron
0 2 * * 1,4 cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

## Monitoring

### Check Pipeline Logs

```bash
ls -lh /Users/abhishekbisht/CRRI-Chatbot/data/logs/
```

### View Latest Log

```bash
tail -f /Users/abhishekbisht/CRRI-Chatbot/data/logs/pipeline_*.log
```

### Check Cron Execution

On macOS, cron logs are in system logs:
```bash
log show --predicate 'process == "cron"' --last 1d
```

## Troubleshooting

### Cron Not Running?

1. **Check if cron service is running:**
   ```bash
   sudo launchctl list | grep cron
   ```

2. **Grant Full Disk Access to cron:**
   - System Preferences → Security & Privacy → Privacy → Full Disk Access
   - Add `/usr/sbin/cron`

3. **Check environment variables:**
   Cron runs with a minimal environment. If you have issues, you can add environment variables to your crontab:
   ```cron
   SHELL=/bin/bash
   PATH=/usr/local/bin:/usr/bin:/bin
   
   0 2 */2 * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
   ```

### Manual Testing

Before setting up cron, test the pipeline manually:

```bash
cd /Users/abhishekbisht/CRRI-Chatbot
./scripts/run_full_pipeline.sh
```

## Removing the Cron Job

If you need to remove the automated execution:

```bash
crontab -e
```

Then delete the line or comment it out with `#`:
```cron
# 0 2 */2 * * cd /Users/abhishekbisht/CRRI-Chatbot && ./scripts/run_full_pipeline.sh
```

## Notes

- Logs are automatically cleaned up after 7 days
- Old data files are automatically removed, keeping only the latest
- The pipeline will exit on any error to prevent corrupted data
- All operations are logged to `data/logs/pipeline_YYYYMMDD_HHMMSS.log`
