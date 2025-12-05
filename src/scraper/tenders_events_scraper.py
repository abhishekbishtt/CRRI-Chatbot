import scrapy
from urllib.parse import urljoin
import re
from datetime import datetime
import requests
import fitz  
from io import BytesIO
import hashlib

class CrriTendersEventsSpider(scrapy.Spider):
    name = 'crri_tenders_events'
    allowed_domains = ['crridom.gov.in']
    
    def start_requests(self):
        """Start with Tenders and Events main pages"""
        urls = [
            'https://crridom.gov.in/tenders  ',
            'https://crridom.gov.in/events  ',
        ]
        
        for url in urls:
            yield scrapy.Request(url, callback=self.parse_listing_page)
    
    def parse_listing_page(self, response):
        """Parse tenders or events listing pages"""
        
        # Detect page type from URL
        if '/tenders' in response.url:
            yield from self.parse_tenders_page(response)
        elif '/events' in response.url:
            yield from self.parse_events_page(response)
        
        # Handle pagination
        next_page = response.css('li.pager-next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_listing_page)
    
    def parse_tenders_page(self, response):
        """Parse tenders table and check for detail page links"""
        
        breadcrumb = response.css('#breadcrumb .breadcrumb ::text').getall()
        
        # Extract tender rows from table
        tender_rows = response.css('table.views-table tbody tr')
        
        for row in tender_rows:
            # Extract tender title and check for detail link
            title_cell = row.css('td.views-field-title')
            tender_title_text = title_cell.css('::text').get()
            detail_link = title_cell.css('a::attr(href)').get()
            
            # If no text in ::text, try getting it from the link
            if not tender_title_text and detail_link:
                tender_title_text = title_cell.css('a::text').get()
            
            tender_title = tender_title_text.strip() if tender_title_text else None
            
            # Extract bid submission deadline
            date_cell = row.css('td.views-field-field-last-date-issue-of-tender-')
            date_span = date_cell.css('span.date-display-single::text').get()
            deadline = date_span.strip() if date_span else None
            
            # Extract PDF files information from table
            files_cell = row.css('td.views-field-field-upload-tender-file')
            pdf_files = []
            
            pdf_links = files_cell.css('span.file a')
            for link in pdf_links:
                pdf_url = link.css('::attr(href)').get()
                pdf_title = link.css('::text').get()
                pdf_size = link.xpath('following-sibling::span[@class="file-size"]/text()').get()
                
                if pdf_url:
                    pdf_full_url = response.urljoin(pdf_url)
                    pdf_files.append({
                        'url': pdf_full_url,
                        'title': pdf_title.strip() if pdf_title else None,
                        'size': pdf_size.strip() if pdf_size else None
                    })
            
            # If there's a detail page link, follow it for full information
            if detail_link:
                yield scrapy.Request(
                    response.urljoin(detail_link),
                    callback=self.parse_tender_detail,
                    meta={
                        'tender_title': tender_title,
                        'deadline': deadline,
                        'pdf_files': pdf_files,
                        'breadcrumb': breadcrumb,
                        'list_url': response.url
                    }
                )
            else:
                # Fallback: No detail page, extract from table only
                tender_data = {
                    'page_type': 'tender',
                    'breadcrumb': breadcrumb,
                    'source_url': response.url,
                    'scraped_at': datetime.utcnow().isoformat(),
                    'tender_title': tender_title,
                    'bid_submission_deadline': deadline,
                    'pdf_files': pdf_files,
                    'pdf_count': len(pdf_files),
                    'has_detail_page': False
                }
                
                # Extract PDF content for each file
                pdf_contents = []
                for pdf_file in pdf_files:
                    pdf_content = self.extract_pdf_content(pdf_file['url'])
                    if pdf_content:
                        pdf_contents.append({
                            'file_title': pdf_file['title'],
                            'file_url': pdf_file['url'],
                            'content': pdf_content,
                            'content_length': len(pdf_content)
                        })
                
                tender_data['pdf_contents'] = pdf_contents
                tender_data['total_pdf_text_length'] = sum(p['content_length'] for p in pdf_contents)
                
                yield tender_data
    
    def parse_tender_detail(self, response):
        """Parse individual tender detail page"""
        
        # Get metadata from the listing page
        tender_title = response.meta.get('tender_title', '')
        deadline = response.meta.get('deadline', '')
        pdf_files = response.meta.get('pdf_files', [])
        breadcrumb = response.meta.get('breadcrumb', [])
        list_url = response.meta.get('list_url', '')
        
        # Extract full description from detail page
        description_parts = []
        
        # Try multiple selectors for content
        content_selectors = [
            'div.field-name-body .field-item',
            'div.field-name-field-tender-description .field-item',
            'div.content',
            'article .content'
        ]
        
        for selector in content_selectors:
            content = response.css(selector)
            if content:
                text = ' '.join(content.css('*::text').getall()).strip()
                if text and len(text) > 50:  # Ensure meaningful content
                    description_parts.append(text)
                    break
        
        full_description = ' '.join(description_parts) if description_parts else None
        
        # Extract any additional PDF links from detail page
        detail_pdf_links = response.css('a[href$=".pdf"]::attr(href)').getall()
        for pdf_link in detail_pdf_links:
            pdf_url = response.urljoin(pdf_link)
            # Avoid duplicates
            if not any(pf['url'] == pdf_url for pf in pdf_files):
                pdf_files.append({
                    'url': pdf_url,
                    'title': response.css(f'a[href="{pdf_link}"]::text').get(),
                    'size': None
                })
        
        # Extract structured fields if present
        requirements = None
        eligibility = None
        
        # Look for requirements section
        req_section = response.css('div.field-name-field-requirements .field-item')
        if req_section:
            requirements = ' '.join(req_section.css('*::text').getall()).strip()
        
        # Look for eligibility section
        elig_section = response.css('div.field-name-field-eligibility .field-item')
        if elig_section:
            eligibility = ' '.join(elig_section.css('*::text').getall()).strip()
        
        # Build tender data
        tender_data = {
            'page_type': 'tender_detail',
            'breadcrumb': breadcrumb,
            'source_url': response.url,
            'list_url': list_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'tender_title': tender_title or response.css('h1.title::text').get(),
            'bid_submission_deadline': deadline,
            'full_description': full_description,
            'requirements': requirements,
            'eligibility': eligibility,
            'pdf_files': pdf_files,
            'pdf_count': len(pdf_files),
            'has_detail_page': True
        }
        
        # Extract PDF content for each file
        pdf_contents = []
        for pdf_file in pdf_files:
            pdf_content = self.extract_pdf_content(pdf_file['url'])
            if pdf_content:
                pdf_contents.append({
                    'file_title': pdf_file['title'],
                    'file_url': pdf_file['url'],
                    'content': pdf_content,
                    'content_length': len(pdf_content)
                })
        
        tender_data['pdf_contents'] = pdf_contents
        tender_data['total_pdf_text_length'] = sum(p['content_length'] for p in pdf_contents)
        
        yield tender_data
    
    def parse_events_page(self, response):
        """Parse events table"""
        
        breadcrumb = response.css('#breadcrumb .breadcrumb ::text').getall()
        
        # Extract event rows from table
        event_rows = response.css('table tbody tr')
        
        for row in event_rows:
            event_data = {
                'page_type': 'event',
                'breadcrumb': breadcrumb,
                'source_url': response.url,
                'scraped_at': datetime.utcnow().isoformat()
            }
            
            cells = row.css('td')
            if len(cells) >= 7:  # Based on your table structure
                # Extract event details
                event_data['serial_number'] = cells[0].css('::text').get()
                event_data['event_name'] = cells[1].css('::text').get()
                event_data['from_date'] = cells[2].css('::text').get()
                event_data['to_date'] = cells[3].css('::text').get()
                
                # Extract brochure download link
                brochure_cell = cells[4]
                brochure_link = brochure_cell.css('a::attr(href)').get()
                brochure_text = brochure_cell.css('a::text').get()
                
                if brochure_link:
                    event_data['brochure_url'] = response.urljoin(brochure_link)
                    event_data['brochure_text'] = brochure_text
                    
                    # Extract brochure PDF content if available
                    if brochure_link.endswith('.pdf'):
                        brochure_content = self.extract_pdf_content(event_data['brochure_url'])
                        event_data['brochure_content'] = brochure_content
                
                event_data['time_remaining'] = cells[5].css('::text').get()
                event_data['event_category'] = cells[6].css('::text').get()
                
                # Handle event status if present
                if len(cells) > 7:
                    event_data['event_status'] = cells[7].css('::text').get()
            
            yield event_data
    
    def extract_pdf_content(self, pdf_url):
        """Extract text content from PDF while preserving layout"""
        try:
            # Download PDF content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=response.content, filetype="pdf")
            
            # Extract text preserving layout
            full_text = []
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                
                # Extract text blocks to preserve layout
                blocks = page.get_text("blocks")
                page_text = []
                
                for block in blocks:
                    if len(block) >= 5:  # Text block
                        block_text = block[4].strip()
                        if block_text:
                            page_text.append(block_text)
                
                if page_text:
                    full_text.append(f"\n--- Page {page_num + 1} ---\n")
                    full_text.append('\n\n'.join(page_text))
            
            pdf_document.close()
            
            # Clean and format text
            extracted_text = '\n'.join(full_text)
            
            # Basic cleaning
            extracted_text = re.sub(r'\n\s*\n', '\n\n', extracted_text)  # Remove extra blank lines
            extracted_text = re.sub(r'[ \t]+', ' ', extracted_text)  # Normalize spaces
            
            return extracted_text.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF content from {pdf_url}: {str(e)}")
            return None
    
    def extract_table_from_html(self, response, table_selector):
        """Helper method to extract table data in structured format"""
        tables = []
        
        for table in response.css(table_selector):
            # Extract headers
            headers = []
            header_cells = table.css('thead th, thead td')
            for cell in header_cells:
                header_text = cell.css('::text').get()
                if header_text:
                    headers.append(header_text.strip())
            
            # Extract rows
            rows = []
            for row in table.css('tbody tr'):
                cells = []
                for cell in row.css('td'):
                    cell_text = ' '.join(cell.css('::text').getall()).strip()
                    cells.append(cell_text)
                
                if cells:
                    row_data = dict(zip(headers, cells)) if headers else cells
                    rows.append(row_data)
            
            if rows:
                tables.append({
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows)
                })
        
        return tables