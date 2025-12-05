import json
from collections import defaultdict

file_path = '/Users/abhishekbisht/CRRI-Chatbot/data/raw/scraped_staff_org_20251205_013308.json'

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"File not found: {file_path}")
    exit()

print(f"Total entries in JSON: {len(data)}")

# 1. Find the 'division_wise_staff' entry to get the master list of divisions
divisions_master_list = {}
for entry in data:
    if entry.get('page_type') == 'division_wise_staff' and 'divisions_available' in entry:
        for div in entry['divisions_available']:
            divisions_master_list[div['name']] = div['value']
        break

print(f"\nFound {len(divisions_master_list)} divisions in master list (from website dropdown).")

# 2. Analyze Staff Profiles
staff_profiles = []
staff_by_division = defaultdict(list)
staff_by_category = defaultdict(list)
unique_staff_names = set()

for entry in data:
    if entry.get('page_type') == 'staff_profile':
        name = entry.get('name', 'Unknown')
        
        # Deduplication check
        if name in unique_staff_names:
            continue
        unique_staff_names.add(name)
        
        staff_profiles.append(entry)
        
        # Handle multiple divisions if present, or single division
        divs = entry.get('divisions', [])
        if not divs and entry.get('division'):
            divs = [entry.get('division')]
            
        for div in divs:
            if div:
                staff_by_division[div.strip()].append(name)
        
        # We don't have explicit category in profile usually, but let's check if we can infer or if it's in the list pages
        # Actually, let's look at the 'staff_list' pages to see counts there too
        
print(f"\nTotal Unique Staff Profiles Scraped: {len(staff_profiles)}")

# 3. Compare with Master List
print(f"\n--- Staff Count by Division (Matched with Master List) ---")
missing_divisions = []
for div_name in sorted(divisions_master_list.keys()):
    count = len(staff_by_division.get(div_name, []))
    print(f"{div_name}: {count}")
    if count == 0:
        missing_divisions.append(div_name)

print(f"\n--- Divisions with 0 Scraped Staff ---")
if missing_divisions:
    for div in missing_divisions:
        print(f"- {div}")
else:
    print("None! All divisions have at least one staff member.")

# 4. Check 'staff_list' page summaries
print(f"\n--- Scraped Page Summaries ---")
categories_found = defaultdict(int)
for entry in data:
    if entry.get('page_type') == 'staff_list':
        cat = entry.get('staff_category', 'unknown')
        count = entry.get('staff_count', 0)
        # This might be per page, so we sum them up? 
        # The JSON structure shows 'staff_count' might be the count ON THAT PAGE or total?
        # Let's just list them
        print(f"Page: {entry.get('title')} ({cat}) - Count: {entry.get('staff_count', 0)}")

# Let's count total from profiles vs expected?
# It's hard to know expected without scraping, but 0 for a division is a strong signal.
