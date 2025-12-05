# settings.py

# --- Essential Settings for Your Project ---

# Define where Scrapy looks for spider files
SPIDER_MODULES = ['src.scraper'] # Tells Scrapy to look for spiders in the src.scraper package
NEWSPIDER_MODULE = 'src.scraper' # Used by the 'scrapy genspider' command

# Obey robots.txt rules (recommended)
ROBOTSTXT_OBEY = True

# Add a delay between requests to be respectful to the website
DOWNLOAD_DELAY = 1  # Wait 1 second between requests to the same domain

# # Set a User-Agent (optional but good practice)
# USER_AGENT = 'CRRI_RAG_Bot (+http://www.yourdomain.com)'

# --- Other Settings (Add as needed) ---
# LOG_LEVEL = 'INFO'  # Adjust logging level
# ITEM_PIPELINES = {} # Define pipelines for processed items if needed later
# ... etc ...