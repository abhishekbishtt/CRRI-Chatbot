# src/scraper/news_scraper.py
import scrapy
from urllib.parse import urljoin
import re

class CrriNewsSpider(scrapy.Spider):
    name = 'crri_news'
    allowed_domains = ['crridom.gov.in']
    start_urls = ['https://crridom.gov.in/news']

    def parse(self, response):
        """Parse the news listing page and follow links to full news items."""
        
        # Extract news items from the current page
        news_items = response.css('table.views-view-grid tbody tr td')
        
        for item in news_items:
            # Extract headline/link
            headline_link_elem = item.css('h2 a::text').get()
            headline_link_url = item.css('h2 a::attr(href)').get()
            
            if headline_link_elem and headline_link_url:
                headline = headline_link_elem.strip()
                full_url = response.urljoin(headline_link_url)
                
                # Extract brief news content (custom-left div)
                news_brief = item.css('div.custom-left::text').getall()
                news_brief = ' '.join(news_brief).strip() # Combine text parts and clean
                
                # Yield the news item data
                yield {
                    'type': 'news_summary', # Distinguish from full articles
                    'url': full_url,
                    'headline': headline,
                    'brief_content': news_brief,
                    'scraped_from_page': response.url,
                    'page_type': 'news_summary'
                }
                
                # Follow the link to get the full news content
                yield response.follow(full_url, callback=self.parse_news_detail, 
                                      meta={'headline': headline, 'brief': news_brief})
        
        # Handle pagination
        next_page_url = response.css('li.pager-next a::attr(href)').get()
        if next_page_url:
            next_page_full_url = response.urljoin(next_page_url)
            yield response.follow(next_page_full_url, callback=self.parse)

    def parse_news_detail(self, response):
        """Parse the individual news detail page."""
        
        # Get headline and brief from meta
        headline = response.meta.get('headline', 'No Headline')
        brief = response.meta.get('brief', 'No Brief Summary')
        
        # Extract main content from the detail page
        # This selector might need adjustment based on the actual structure of the node pages
        # Common selectors for main content areas
        content_selectors = [
            'div.field-name-body .field-item', # Drupal body field
            'div.content', # General content div
            'article', # Article tag
            'div#content', # Content by ID
            'div.main-content', # Main content div
            'div.page-content' # Page content div
        ]
        
        full_content = ""
        for selector in content_selectors:
            content_elem = response.css(selector)
            if content_elem:
                full_content = ' '.join(content_elem.css('*::text').getall()).strip()
                if full_content: # If content found with this selector, break
                    break
        
        # If no content found with common selectors, try getting all text from body
        if not full_content:
            full_content = ' '.join(response.css('body *::text').getall()).strip()
        
        # Clean up the content (remove extra whitespace)
        full_content = re.sub(r'\s+', ' ', full_content)
        
        yield {
            'type': 'news_detail', # Distinguish from summaries
            'url': response.url,
            'headline': headline,
            'brief_summary': brief,
            'full_content': full_content,
            'scraped_from_page': response.request.url, # The detail page URL
            'page_type': 'news_detail'
        }
