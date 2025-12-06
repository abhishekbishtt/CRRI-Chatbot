"""
Script to analyze scraped staff data and compare with master division lists.
"""
import json
from collections import defaultdict
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_DIR / "data" / "raw"

def get_latest_staff_file():
    """Find the most recent scraped_staff_org_*.json file."""
    files = list(RAW_DATA_DIR.glob("scraped_staff_org_*.json"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)

def main():
    file_path = get_latest_staff_file()
    
    if not file_path:
        logger.error("No staff data file found in data/raw/")
        return

    logger.info(f"Analyzing file: {file_path.name}")

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return

    logger.info(f"Total entries in JSON: {len(data)}")

    # 1. Find the 'division_wise_staff' entry to get the master list of divisions
    divisions_master_list = {}
    for entry in data:
        if entry.get('page_type') == 'division_wise_staff' and 'divisions_available' in entry:
            for div in entry['divisions_available']:
                divisions_master_list[div['name']] = div['value']
            break

    logger.info(f"\nFound {len(divisions_master_list)} divisions in master list.")

    # 2. Analyze Staff Profiles
    staff_profiles = []
    staff_by_division = defaultdict(list)
    unique_staff_names = set()

    for entry in data:
        if entry.get('page_type') == 'staff_profile':
            name = entry.get('name', 'Unknown')
            
            if name in unique_staff_names:
                continue
            unique_staff_names.add(name)
            
            staff_profiles.append(entry)
            
            divs = entry.get('divisions', [])
            if not divs and entry.get('division'):
                divs = [entry.get('division')]
                
            for div in divs:
                if div:
                    staff_by_division[div.strip()].append(name)
            
    logger.info(f"\nTotal Unique Staff Profiles Scraped: {len(staff_profiles)}")

    # 3. Compare with Master List
    logger.info(f"\n--- Staff Count by Division (Matched with Master List) ---")
    missing_divisions = []
    for div_name in sorted(divisions_master_list.keys()):
        count = len(staff_by_division.get(div_name, []))
        logger.info(f"{div_name}: {count}")
        if count == 0:
            missing_divisions.append(div_name)

    logger.info(f"\n--- Divisions with 0 Scraped Staff ---")
    if missing_divisions:
        for div in missing_divisions:
            logger.info(f"- {div}")
    else:
        logger.info("None! All divisions have at least one staff member.")

    # 4. Check 'staff_list' page summaries
    logger.info(f"\n--- Scraped Page Summaries ---")
    for entry in data:
        if entry.get('page_type') == 'staff_list':
            cat = entry.get('staff_category', 'unknown')
            logger.info(f"Page: {entry.get('title')} ({cat}) - Count: {entry.get('staff_count', 0)}")

if __name__ == "__main__":
    main()
