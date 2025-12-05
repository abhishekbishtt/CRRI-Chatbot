# src/scraper/events_scraper.py
import scrapy
from urllib.parse import urljoin
from datetime import datetime

class CrriEventsSpider(scrapy.Spider):
    name = 'crri_events'
    allowed_domains = ['crridom.gov.in']
    start_urls = ['https://crridom.gov.in/event-calendar'] # The main events calendar page

    def parse(self, response):
        """Parse the events table on the calendar page."""
        
        # Select all rows in the table body (excluding header)
        event_rows = response.css('table.views-table tbody tr')
        
        for row in event_rows:
            # Extract data from each cell in the row
            serial_number = row.css('td.views-field-counter::text').get()
            event_name = row.css('td.views-field-title::text').get()
            event_from_date = row.css('td.views-field-field-event-date span.date-display-single::text').get()
            event_to_date = row.css('td.views-field-field-event-date-2 span.date-display-single::text').get()
            
            # Extract brochure link
            brochure_link_elem = row.css('td.views-field-nothing a::attr(href)').get()
            brochure_link = response.urljoin(brochure_link_elem) if brochure_link_elem else None
            
            time_remaining = row.css('td.views-field-field-event-date-1 span.date-display-interval::text').get()
            event_category = row.css('td.views-field-field-event-category::text').get()
            event_status = row.css('td.views-field-field-event-status::text').get()
            
            # Yield the extracted data as a structured item
            yield {
                'type': 'event', # Distinguish from other data types
                'page_type': 'events_calendar',
                'url': response.url, # URL of the calendar page
                'scraped_at': datetime.utcnow().isoformat(), # Add a timestamp
                'sr_no': serial_number.strip() if serial_number else None,
                'event_name': event_name.strip() if event_name else None,
                'from_date': event_from_date.strip() if event_from_date else None,
                'to_date': event_to_date.strip() if event_to_date else None,
                'brochure_link': brochure_link,
                'time_remaining': time_remaining.strip() if time_remaining else None,
                'event_category': event_category.strip() if event_category else None,
                'event_status': event_status.strip() if event_status else None,
            }
        
        # Handle pagination to get all events
        next_page = response.css('li.pager-next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
